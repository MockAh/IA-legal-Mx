# nombre_archivo: script_embeddings_transp_55.py
# === SCRIPT ESPECIALIZADO PARA DOCUMENTOS DE TRANSPARENCIA (AUTO-GESTIONADO + DUAL) ===
# VERSIÓN 5.5 Basado en eva_5_5.py - Dominio específico: Axiomas/legislacion-mx/Transparencia
# enrutar_procesamiento: primero semantico y luego eva; 

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import docx
import torch
from tqdm import tqdm

# --- Dependencias de LangChain ---
# NUEVO: Splitter semántico
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- IMPORTACIÓN DE EXCEPCIONES ---
try:
    from script_embeddings_excep_mx import TODAS_LAS_EXCEPCIONES
    print(f"✅ Sincronización exitosa: Se excluirán {len(TODAS_LAS_EXCEPCIONES)} archivos de excepciones.")
except ImportError:
    print("⚠️ ADVERTENCIA: No se encontró 'script_embeddings_excep_mx.py'.")
    TODAS_LAS_EXCEPCIONES = set()

# 1. --- CONFIGURACIÓN INICIAL ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DOCS_DIR = BASE_DIR / "Axiomas" / "legislacion-mx" / "Transparencia"
OUTPUT_DIR = BASE_DIR / "procesado-mx" / "transp-mx"
DB_PATH = OUTPUT_DIR / "chroma_db_transp"
METADATA_FILE_PATH = OUTPUT_DIR / "metadata_transp.json"

# --- CAMBIO IMPORTANTE: SEPARACIÓN DE ESTADO Y REPORTE ---
SYNC_FILE_PATH = OUTPUT_DIR / "sincro_transp.json" # EL CEREBRO (No tocar)
MAP_FILE_PATH = OUTPUT_DIR / "mapa_transp.json"            # EL REPORTE (Lectura humana)
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"

# --- DETECCIÓN DE HARDWARE ---
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# 2. --- MÓDULOS DE PROCESAMIENTO ---

def parse_filename_for_metadata(file_path: Path) -> dict:
    """Extrae metadatos y define la ESTRUCTURA (legal/semantic)."""
    filename = file_path.name
    name_without_ext = file_path.stem
    parts = name_without_ext.split('_')
    
    try:
        relative_parts = file_path.relative_to(INPUT_DOCS_DIR).parts
        dominio = relative_parts[0] if len(relative_parts) > 0 else "transparencia"
        sub_dominio = relative_parts[1] if len(relative_parts) > 1 else "general"
    except Exception:
        dominio = "transparencia"
        sub_dominio = "general"

    metadata = {"dominio": dominio, "sub_dominio": sub_dominio, "source": filename}

    # LÓGICA DE DETECCIÓN DE ESTRUCTURA
    if len(parts) == 4:
        # Ejemplo: 2023_Ley_Transparencia_Legal.docx
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = parts[3].lower() # 'legal' o 'semantic'
    elif len(parts) >= 3:
        # Ejemplo: 2023_Ley_Transparencia.docx -> Asumimos LEGAL por defecto
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = "legal"
    else:
        metadata["titulo_documento"] = name_without_ext.replace('_', ' ').replace('-', ' ').lower()
        metadata["estructura"] = "legal"

    return metadata

def extraer_parrafos_limpios_de_docx(file_path: Path) -> list[str]:
    """
    Lee el DOCX y limpia el texto usando la estrategia "Delimitadores DOF".
    1. Busca DOF y sus fechas.
    2. Captura hacia atrás hasta encontrar un delimitador (.:;()\n).
    3. Fusiona esa 'frase DOF' con el párrafo anterior.
    4. Fuerza un salto de línea para el texto restante.
    """
    parrafos_crudos = []
    try:
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            # Normalizamos espacios pero MANTENEMOS la puntuación intacta para el regex
            texto = re.sub(r'\s+', ' ', p.text).strip()
            if texto:
                parrafos_crudos.append(texto)
    except Exception as e:
        print(f"❌ Error en {file_path.name}: {e}")
        return []

    parrafos_finales = []

    # REGEX MAESTRA:
    # Grupo 1 (Captura): 
    #   [^\.\:\;\(\)\n]*?  -> 0 o más caracteres que NO sean delimitadores (búsqueda perezosa hacia atrás/inicio)
    #   DOF\s+             -> La palabra ancla
    #   (?:[\d]{2}-...)+   -> Las fechas (soporta listas con comas y espacios)
    regex_dof = re.compile(r'([^\.\:\;\(\)\n]*?DOF\s+(?:[\d]{2}-[\d]{2}-[\d]{4}(?:[,\s]*)*)+)', re.IGNORECASE)

    for p in parrafos_crudos:
        # re.split con paréntesis de captura devuelve: [Texto_Previo, MATCH_DOF, Texto_Restante]
        partes = regex_dof.split(p)

        # Si no hubo match, 'partes' tiene solo 1 elemento (el párrafo original)
        if len(partes) == 1:
            parrafos_finales.append(partes[0])
            continue

        # Si hubo match, procesamos las piezas tripartitas
        # Iteramos de 3 en 3 (en caso raro de que haya múltiples DOFs en una misma línea)
        for i in range(0, len(partes) - 1, 2):
            texto_previo = partes[i].strip()
            dof_completo = partes[i+1].strip() # Este es el string "Artículo reformado DOF..."
            
            # 1. Gestionar el TEXTO PREVIO (El final del artículo anterior)
            if texto_previo:
                parrafos_finales.append(texto_previo)
            
            # 2. Gestionar la FUSIÓN DEL DOF (Se pega al último elemento existente)
            if parrafos_finales:
                parrafos_finales[-1] += " " + dof_completo
            else:
                # Caso borde: El documento empieza directo con un DOF (raro, pero posible)
                parrafos_finales.append(dof_completo)
        
        # 3. Gestionar el TEXTO RESTANTE (El nuevo artículo)
        texto_restante = partes[-1].strip()
        if texto_restante:
            parrafos_finales.append(texto_restante)
    
    return parrafos_finales

# --- ALGORITMOS DE CHUNKING ---

def algoritmo_eva_mx(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    Algoritmo Jerárquico (Blindado).
    Detecta Artículos incluso con formato sucio y evita fusiones masivas.
    """
    
    # 1. Estado inicial
    estado_actual = {
        "Decreto": "<No aplica>",
        "Libro": "<No aplica>", 
        "Titulo": "<No aplica>", 
        "Capitulo": "<No aplica>", 
        "Seccion": "<No aplica>", 
        "Articulo": "<No aplica>", 
        "Transitorio": "Principal"
    }

    parrafos_etiquetados = []
    
    # --- FASE 1: ETIQUETADO SECUENCIAL ---
    print(f"\n🔍 Iniciando escaneo de {len(lista_de_parrafos)} párrafos...")

    for i, p in enumerate(lista_de_parrafos):
        
        # A. Limpieza Profunda: Quitamos espacios y caracteres invisibles (BOM)
        p_clean = p.strip().lstrip('\ufeff') 
        
        # B. Detección Jerárquica (Resetea niveles inferiores; El orden importa)
        # 1. DECRETO (Nuevo Nivel Supremo)
        if m := re.match(r'DECRETO\s*(.*)', p_clean, re.IGNORECASE):
            texto_decreto = m.group(1).strip()
            # Si el párrafo es solo la palabra "DECRETO", le ponemos un nombre genérico o lo dejamos vacío
            if not texto_decreto: texto_decreto = "Decreto"
            
            estado_actual.update({
                "Decreto": texto_decreto,
                "Libro": "<No aplica>", 
                "Titulo": "<No aplica>", 
                "Capitulo": "<No aplica>", 
                "Seccion": "<No aplica>", 
                "Articulo": "<No aplica>"
            })

        elif m := re.match(r'LIBRO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Libro": m.group(1).strip(), "Titulo": "<No aplica>", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'T[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Titulo": m.group(1).strip(), "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'CAP[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Capitulo": m.group(1).strip(), "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'SECCI[ÓO]N\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Seccion": m.group(1).strip(), "Articulo": "<No aplica>"})
        
        # C. Detección de Artículos (REGEX MEJORADO)
        elif match := re.match(r'(?:ART[ÍI]?CULO|ART\.?)\s+([\w°º.-]+)', p_clean, re.IGNORECASE):
            
            # Captura bruta del ID (ej: "1.-" o "PRIMERO")
            id_articulo_raw = match.group(1).strip()
            
            # 1. Limpieza universal de PUNTUACIÓN/SÍMBOLOS al final
            # Corregido: Mover el guion al final y usar '+' para borrar uno o más símbolos
            LIMPIEZA_SIMBOLOS_FIN = r'[º.:;\s"\'\'-]+$'
            id_limpio = re.sub(LIMPIEZA_SIMBOLOS_FIN, '', id_articulo_raw).strip() 

            # 2. Lógica de Extracción Numérica Prioritaria (EL CAMBIO CLAVE)
            
            # Caso 1: El ID comienza con un dígito (ej. 1, 20, 5BIS)
            if id_limpio and id_limpio[0].isdigit():
                # Nueva lógica robusta: Extraer todos los dígitos consecutivos al inicio.
                # Regex: ^(\d+) busca uno o más dígitos (\d+) al inicio (^) y los captura.
                match_num = re.match(r'^(\d+)', id_limpio)
                
                if match_num:
                    # Capturamos solo el número (ej. "6to" -> "6", "20Bis" -> "20")
                    id_articulo_final = match_num.group(1) 
                else:
                    # Fallback si por alguna razón no se capturó el número, aunque la lógica lo implica
                    id_articulo_final = id_limpio
            
            # Caso 2: El ID NO comienza con un dígito (ej. PRIMERO, TRANSITORIO)
            else:
                # Se mantiene íntegro el ID literal (ya limpio de puntuación final)
                id_articulo_final = id_limpio
            
            # 3. ACTUALIZACIÓN CRÍTICA DEL ESTADO
            estado_actual["Articulo"] = id_articulo_final
            
            # Lógica de Transitorios
            if estado_actual["Transitorio"] != "Principal":
                estado_actual["Transitorio"] = "Transitorio"
        
        elif re.match(r'(?:ART[ÍI]CULOS\s+)?TRANSITORIOS\b', p_clean, re.IGNORECASE):
            # ... (Lógica de transitorios permanece igual) ...
            estado_actual.update({"Libro": "<No aplica>", "Titulo": "Artículos Transitorios", "Capitulo": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Encabezado"})


        # D. Asignación (Herencia implícita)
        # Importante: Guardamos una COPIA del estado.
        parrafos_etiquetados.append({
            "texto": p, 
            "etiquetas": estado_actual.copy()
        })

    # --- FASE 2: FUSIÓN (CHUNKING) ---
    chunks_fusionados = []
    if not parrafos_etiquetados: return []

    buffer_actual = parrafos_etiquetados[0]
    
    for item in parrafos_etiquetados[1:]:
        # COMPARA: ¿Son idénticos todos los metadatos?
        # Si el "Articulo" cambió de "1" a "2", esto será Falso y forzará el corte.
        if item["etiquetas"] == buffer_actual["etiquetas"]:
            buffer_actual["texto"] += "\n" + item["texto"]
        else:
            chunks_fusionados.append(buffer_actual)
            buffer_actual = item
    
    chunks_fusionados.append(buffer_actual)

    # --- FASE 3: FORMATO FINAL ---
    resultado_final = []
    for i, chunk in enumerate(chunks_fusionados):
        meta_final = {**metadatos_base, **chunk["etiquetas"]}
        
        # Corrección de seguridad para "Articulo" vacío
        if not meta_final.get("Articulo"): 
            meta_final["Articulo"] = "<No aplica>"

        meta_final["chunk_index"] = i + 1
        meta_final["texto_chunk"] = chunk["texto"].strip()
        resultado_final.append(meta_final)

    print(f"✅ Procesamiento terminado. Generados {len(resultado_final)} chunks.")
    return resultado_final

def algoritmo_semantico(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """Algoritmo Semántico (Recursive Splitter) para prosa."""
    texto_completo = "\n\n".join(lista_de_parrafos)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_text(texto_completo)
    
    final_chunks = []
    for i, txt in enumerate(chunks):
        final_chunks.append({
            **metadatos_base,
            "Libro": "<No aplica>", "Titulo": "<No aplica>", "Capitulo": "<No aplica>", 
            "Seccion": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Principal",
            "chunk_index": i + 1, "texto_chunk": txt.strip()
        })
    return final_chunks

def enrutar_procesamiento(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    Router Inteligente V2 (Preámbulo Semántico + Cuerpo Legal):
    1. Escanea los párrafos buscando el primer indicio de estructura legal.
    2. Todo lo ANTERIOR a ese punto -> Algoritmo Semántico.
    3. Todo A PARTIR de ese punto -> Algoritmo Eva MX.
    """
    
    # Si el archivo está forzado como 'semantic' desde el nombre, omitimos la detección legal
    if metadatos_base.get("estructura") == "semantic":
        print(f"  -> 📄 Modo Semántico Forzado para: {metadatos_base['source']}")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    # --- LÓGICA DE DETECCIÓN DEL PUNTO DE QUIEBRE ---
    indice_corte = -1
    
    # Regex que busca el inicio de la estructura legal (las llaves de tu diccionario)
    # Cubre: DECRETO, LIBRO, TÍTULO, CAPÍTULO, SECCIÓN, ARTÍCULO, TRANSITORIOS
    patron_arranque_legal = re.compile(
        r'^\s*(DECRETO|LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|(?:ART[ÍI]?CULO|ART\.?)|(?:ART[ÍI]CULOS\s+)?TRANSITORIOS)\b', 
        re.IGNORECASE
    )

    for i, p in enumerate(lista_de_parrafos):
        # Limpieza ligera solo para detectar el match al inicio
        p_clean = p.strip().lstrip('\ufeff')
        if patron_arranque_legal.match(p_clean):
            indice_corte = i
            break
    
    chunks_finales = []

    # CASO 1: No se encontró estructura legal en todo el documento.
    if indice_corte == -1:
        print(f"  -> 📄 No se detectó estructura legal estricta. Procesando todo como semántico.")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    # CASO 2: Se encontró estructura. Dividimos el documento.
    # Parte A: Preámbulo (Semántico)
    parte_preambulo = lista_de_parrafos[:indice_corte]
    # Parte B: Ley (Eva MX)
    parte_legal = lista_de_parrafos[indice_corte:]

    print(f"  -> ✂️  Corte detectado en párrafo {indice_corte}.")

    # Procesar Preámbulo
    if parte_preambulo:
        print(f"     📄 Procesando {len(parte_preambulo)} párrafos de preámbulo (Semántico)...")
        # Forzamos metadatos neutros para la parte semántica
        meta_sem = metadatos_base.copy()
        meta_sem["estructura"] = "semantic_preamble" # Etiqueta opcional para distinguir
        chunks_sem = algoritmo_semantico(parte_preambulo, meta_sem)
        chunks_finales.extend(chunks_sem)

    # Procesar Cuerpo Legal (CON ALGORITMO EVA INTACTO)
    if parte_legal:
        print(f"     ⚖️  Procesando {len(parte_legal)} párrafos de cuerpo legal (Eva MX)...")
        chunks_leg = algoritmo_eva_mx(parte_legal, metadatos_base)
        chunks_finales.extend(chunks_leg)

    # --- RE-INDEXADO FINAL ---
    # Como unimos dos listas, los chunk_index se reinician. Hay que corregirlo para que sean continuos.
    for idx, chunk in enumerate(chunks_finales):
        chunk["chunk_index"] = idx + 1

    return chunks_finales

# 3. --- FUNCIÓN PRINCIPAL ---
def main():
    print(f"--- 🔄 Iniciando Indexador TRANSPARENCIA (v5.6 - Estado Desacoplado) en {device.upper()} ---")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. CARGA DEL ESTADO DE SINCRONIZACIÓN (LA VERDAD DEL SISTEMA)
    estado_sincronizacion = {} # Estructura: { "ruta/relativa": timestamp_modificacion }
    chunks_totales = []
    
    # Intentamos cargar el archivo de sincronización. 
    # MIGRACIÓN: Si no existe 'sincro_transp.json' pero existe 'mapa_transp.json' antiguo,
    # podríamos intentar reconstruir, pero para limpieza, asumiremos inicio limpio o archivo existente.
    if SYNC_FILE_PATH.exists():
        with open(SYNC_FILE_PATH, "r", encoding="utf-8") as f:
            estado_sincronizacion = json.load(f)
    else:
        print("ℹ️  No se encontró archivo de sincronización. Se creará uno nuevo.")

    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
            chunks_totales = json.load(f)

    # 2. ESCANEO EN DISCO Y COMPARACIÓN (Con detección de cambios)
    archivos_en_disco_info = {}
    
    # Escaneamos disco y guardamos ruta + fecha de modificación
    # Excluimos archivos con 'excep' en el último segmento (ej: archivo_excep.docx)
    raw_files = [f for f in INPUT_DOCS_DIR.rglob('*.docx') 
                 if f.name not in TODAS_LAS_EXCEPCIONES 
                 and f.stem.split('_')[-1].lower() != "excep"]
    
    for f in raw_files:
        ruta_rel = f.relative_to(BASE_DIR).as_posix()
        mtime = f.stat().st_mtime # Timestamp de última modificación
        archivos_en_disco_info[ruta_rel] = mtime

    # 3. Lógica de Conjuntos para Determinar Acciones
    set_disco = set(archivos_en_disco_info.keys())
    set_sync = set(estado_sincronizacion.keys())
    
    # A) Lo que está en Sync pero ya no en disco -> BORRAR
    a_borrar = set_sync - set_disco
    
    # B) Lo que está en disco pero no en Sync -> CREAR
    a_crear = set_disco - set_sync
    
    # C) Lo que está en ambos, pero la fecha de modificación cambió -> ACTUALIZAR (Borrar + Crear)
    a_actualizar = set()
    for archivo in (set_disco & set_sync):
        mtime_disco = archivos_en_disco_info[archivo]
        mtime_sync = estado_sincronizacion[archivo]
        # Si la fecha del disco es distinta a la guardada (con tolerancia pequeña), se actualiza
        if abs(mtime_disco - mtime_sync) > 1.0: 
            a_actualizar.add(archivo)
    
    # Fusión de listas de tareas
    total_a_procesar = a_crear | a_actualizar
    total_a_eliminar = a_borrar | a_actualizar # Para actualizar, primero borramos lo viejo

    print(f"📊 Estado del Sistema:")
    print(f"   Archivos en Disco: {len(set_disco)} | Archivos en Sync: {len(set_sync)}")
    print(f"   ➕ Nuevos: {len(a_crear)} | 🔄 Modificados: {len(a_actualizar)} | ➖ Borrar: {len(a_borrar)}")
    
    if not total_a_procesar and not total_a_eliminar:
        print("✅ Todo sincronizado. Generando reporte actualizado...")
        # Aún si no hay cambios, regeneramos mapa.json por si el humano lo borró
        pass 
    else:
        # --- CARGA DE MODELO ---
        print(f"🚀 Cargando modelo e5-large-instruct en {device}...")
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
        db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)

        # --- EJECUCIÓN DE BORRADOS ---
        if total_a_eliminar:
            print(f"🗑️  Eliminando {len(total_a_eliminar)} registros obsoletos...")
            for ruta_relativa in total_a_eliminar:
                filename_original = os.path.basename(ruta_relativa)
                
                # Borrar de Chroma
                try:
                    db.delete(where={"source": filename_original})
                except Exception:
                    pass # Puede no existir si falló una carga previa
                
                # Borrar de Metadata (memoria JSON)
                chunks_totales = [c for c in chunks_totales if c.get("source") != filename_original]
                
                # Borrar de Estado Sync
                if ruta_relativa in estado_sincronizacion:
                    del estado_sincronizacion[ruta_relativa]

        # --- EJECUCIÓN DE CREACIONES / ACTUALIZACIONES ---
        if total_a_procesar:
            print(f"🔨 Procesando {len(total_a_procesar)} archivos...")
            lista_archivos = [BASE_DIR / f for f in total_a_procesar]
            
            for fpath in tqdm(lista_archivos):
                ruta_rel_posix = fpath.relative_to(BASE_DIR).as_posix()
                paras = extraer_parrafos_limpios_de_docx(fpath)
                
                if not paras: 
                    # Si falla lectura, no actualizamos sync para reintentar luego
                    continue 
                
                meta = parse_filename_for_metadata(fpath)
                chunks = enrutar_procesamiento(paras, meta)
                
                if chunks:
                    docs = [Document(page_content=c.pop("texto_chunk"), metadata=c) for c in chunks]
                    db.add_documents(docs)
                    
                    # Agregar a metadata global
                    for d in docs: 
                        d.metadata["texto_chunk"] = d.page_content
                        chunks_totales.append(d.metadata)
                    
                    # ACTUALIZAR EL ESTADO DE SINCRONIZACIÓN
                    # Guardamos la fecha de modificación actual del archivo
                    estado_sincronizacion[ruta_rel_posix] = archivos_en_disco_info[ruta_rel_posix]

        # --- GUARDADO FINAL DE SISTEMA ---
        print("💾 Guardando bases de datos de sistema...")
        # 1. Metadata Global
        with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(chunks_totales, f, indent=4, ensure_ascii=False)
        
        # 2. Sincronización (Estado Técnico)
        with open(SYNC_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(estado_sincronizacion, f, indent=4)

    # --- GENERACIÓN DE REPORTE HUMANO (MAPA_TRANSP.JSON) ---
    # Esto ocurre SIEMPRE al final, independientemente de si hubo cambios o no.
    # Reconstruye el mapa basándose puramente en lo que el sistema sabe ahora.
    print("📝 Generando reporte legible (mapa_transp.json)...")
    
    mapa_legible = {}
    # Agrupamos chunks por archivo para el reporte
    conteo_chunks = defaultdict(int)
    for c in chunks_totales:
        if "source" in c:
            conteo_chunks[c["source"]] += 1
            
    for ruta, mtime in estado_sincronizacion.items():
        filename = os.path.basename(ruta)
        mapa_legible[ruta] = {
            "status": "sincronizado",
            "chunks_en_db": conteo_chunks.get(filename, 0),
            "ultima_modificacion": datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        }

    with open(MAP_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "report_date": datetime.now().isoformat(),
            "note": "Este archivo se genera automáticamente. Puedes borrarlo o editarlo sin afectar el sistema.",
            "resumen_sesion": {
                "archivos_nuevos": len(a_crear),
                "archivos_actualizados": len(a_actualizar),
                "archivos_eliminados": len(a_borrar)
            },
            "total_files": len(mapa_legible),
            "archivos": mapa_legible
        }, f, indent=4, ensure_ascii=False)

    print("🎉 Proceso finalizado.")

if __name__ == "__main__":
    main()
