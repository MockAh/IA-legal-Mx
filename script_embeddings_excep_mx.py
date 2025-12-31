# === SCRIPT DE PROCESAMIENTO Y GENERACIÓN DE EMBEDDINGS PARA DOCX ===
# VERSIÓN 6.0: Enfocado en excepciones, eliminando el algoritmo estándar.

import os
import re
import json
import torch  # <--- NUEVO: Necesario para detección de hardware
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import docx
from tqdm import tqdm

# --- Dependencias de LangChain ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. --- CONFIGURACIÓN INICIAL ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DOCS_DIR = BASE_DIR / "Axiomas" / "legislacion-mx"
OUTPUT_DIR = BASE_DIR / "procesado-mx" / "excep-mx"
DB_PATH = OUTPUT_DIR / "chroma_db_excep_mx"
METADATA_FILE_PATH = OUTPUT_DIR / "metadata.json"
MAP_FILE_PATH = OUTPUT_DIR / "mapa.json"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"

# --- DETECCIÓN DE HARDWARE (Copiado de EVA 5.2) ---
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
print(f"🖥️ Hardware detectado: {device.upper()}")

# --- LISTAS DE EXCEPCIONES (Se mantienen igual) ---
ARCHIVOS_CON_ORDINALES = [
    "2020-08-14_Acuerdo_Acuerdo-para-la-Actuación-Policial-en-Manifestaciones.docx",
    "2017-03-29_Acuerdo_Protocolo-de-Actuación-Policial-de-la-Secretaría-de-Seguridad-Pública.docx",
    "2022-06-24_lineamientos_LINEAMIENTOS-POR-LOS-QUE-SE-ESTABLECE-EL-PROCESO-DE-CALIDAD-REGULATORIA-EN-EL-FCE.docx",
    "2012-10-03_Acuerdo_ACUERDO-por-el-que-se-establecen-las-disposiciones-en-Materia-de-Recursos-Materiales-y-Servicios-Generales_excep.docx"
]

ARCHIVOS_CON_NUMERACION = [
    "2017-03-29_Protocolo_Protocolo-de-Actuación-Policial-de-la-Secretaría-de-Seguridad-Pública.docx"
]

# NUEVO: Unión de todas las excepciones para exportar al script principal
# Usamos set() para eliminar duplicados y optimizar la búsqueda
TODAS_LAS_EXCEPCIONES = set(ARCHIVOS_CON_ORDINALES + ARCHIVOS_CON_NUMERACION)

# 2. --- MÓDULOS DE PROCESAMIENTO ---

def parse_filename_for_metadata(file_path: Path) -> dict:
    """
    Extrae metadatos y define la ESTRUCTURA (legal/semantic).
    HOMOLOGADO CON EVA 5.2: Detecta 3 o 4 partes en el nombre.
    """
    filename = file_path.name
    name_without_ext = file_path.stem
    parts = name_without_ext.split('_')
    
    # 1. Extracción de Dominio/Subdominio
    # Usamos BASE_DIR / "Axiomas" como ancla fija para que coincida con el script principal,
    # independientemente de donde esté apuntando INPUT_DOCS_DIR en este script específico.
    try:
        root_axiomas = BASE_DIR / "Axiomas"
        if file_path.is_relative_to(root_axiomas):
            relative_parts = file_path.relative_to(root_axiomas).parts
            # Ejemplo: si está en Axiomas/legislacion-mx/archivo.docx
            # parts[0] = legislacion-mx (dominio)
            # parts[1] = archivo.docx (ignorado como subdominio si no hay carpetas extra)
            dominio = relative_parts[0] if len(relative_parts) > 0 else "general"
            # Si hay subcarpetas intermedias, las tomamos; si no, 'general'
            sub_dominio = relative_parts[1] if len(relative_parts) > 2 else "general"
        else:
            dominio = "desconocido"
            sub_dominio = "general"
    except Exception:
        dominio = "desconocido"
        sub_dominio = "general"

    metadata = {
        "dominio": dominio,
        "sub_dominio": sub_dominio,
        "source": filename
    }

    # 2. LÓGICA DE DETECCIÓN DE ESTRUCTURA Y PARTES DEL NOMBRE
    # Caso A: Nombre con 4 partes (incluye estructura explícita)
    # Ejemplo: 2023_Ley_GuardiaNacional_Legal.docx
    if len(parts) == 4:
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = parts[3].lower() # 'legal' o 'semantic'
        
    # Caso B: Nombre con 3 partes (Estándar habitual) -> Asumimos LEGAL
    # Ejemplo: 2023_Ley_GuardiaNacional.docx
    elif len(parts) >= 3:
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = "legal" # Default indispensable para consistencia
        
    # Caso C: Nombres fuera de formato
    else:
        metadata["titulo_documento"] = name_without_ext.replace('_', ' ').replace('-', ' ').lower()
        metadata["estructura"] = "legal"

    return metadata

def extraer_parrafos_limpios_de_docx(file_path: Path) -> list[str]:
    """
    Lee el DOCX y limpia el texto usando la estrategia "Delimitadores DOF".
    HOMOLOGADO CON EVA 5.2:
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

    # REGEX MAESTRA (Copiada de Eva 5.2):
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

def algoritmo_palabras_mx(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    --- ALGORITMO DE CHUNKING (PALABRAS ORDINALES) ---
    Procesa documentos estructurados por numerales ordinales (Primero, Segundo, etc.).
    HOMOLOGADO CON EVA 5.2 (Metadatos Completos).
    """
    parrafos_etiquetados = []
    
    # Mapa original de ordinales (SIN CAMBIOS)
    ordinal_map = {
        'primero': '1', 'segundo': '2', 'tercero': '3', 'cuarto': '4', 'quinto': '5',
        'sexto': '6', 'séptimo': '7', 'octavo': '8', 'noveno': '9', 'décimo': '10',
        'décimo primero': '11', 'décimo segundo': '12', 'décimo tercero': '13', 'décimo cuarto': '14',
        'décimo quinto': '15', 'décimo sexto': '16', 'décimo séptimo': '17', 'décimo octavo': '18',
        'décimo noveno': '19', 'vigésimo': '20', 'vigésimo primero': '21', 'vigésimoprimero': '21',
        'vigésimo segundo': '22', 'vigésimosegundo': '22', 'vigésimo tercero': '23', 'vigésimotercero': '23',
        'vigésimo cuarto': '24', 'vigésimocuarto': '24', 'vigésimo quinto': '25', 'vigésimoquinto': '25',
        'vigésimo sexto': '26', 'vigésimosexto': '26', 'vigésimo séptimo': '27', 'vigésimoséptimo': '27',
        'vigésimo octavo': '28', 'vigésimooctavo': '28', 'vigésimo noveno': '29', 'vigésimonoveno': '29',
        'trigésimo': '30', 'trigésimo primero': '31', 'trigésimoprimero': '31', 'trigésimo segundo': '32', 'trigésimosegundo': '32',
        'trigésimo tercero': '33', 'trigésimotercero': '33', 'trigésimo cuarto': '34', 'trigésimocuarto': '34',
        'trigésimo quinto': '35', 'trigésimoquinto': '35', 'trigésimo sexto': '36', 'trigésimosexto': '36',
        'cuadragésimo': '40'
    }
    ordinals_pattern = '|'.join(sorted(ordinal_map.keys(), key=len, reverse=True))
    pattern = re.compile(rf'^\s*({ordinals_pattern})\b', re.IGNORECASE)
    
    # 1. ESTADO ACTUAL HOMOLOGADO
    estado_actual = {
        "Decreto": "<No aplica>", # <--- NUEVO CAMPO OBLIGATORIO
        "Libro": "<No aplica>", 
        "Titulo": metadatos_base.get("tipo_documento", "Protocolo/Acuerdo"), 
        "Capitulo": "<No aplica>", 
        "Seccion": "<No aplica>", 
        "Articulo": "<No aplica>", 
        "Transitorio": "Principal"
    }
    
    in_transitorios = False
    primer_articulo_encontrado = False

    # Lógica de escaneo (SIN CAMBIOS)
    for p in lista_de_parrafos:
        if re.match(r'^\s*TRANSITORIOS\b', p, re.IGNORECASE):
            in_transitorios = True
            # Actualizamos estado manteniendo la estructura
            estado_actual.update({"Transitorio": "Encabezado", "Titulo": "Transitorios", "Articulo": "<No aplica>"})
            if not primer_articulo_encontrado:
                primer_articulo_encontrado = True
        
        match = pattern.match(p)
        if match:
            if not primer_articulo_encontrado:
                primer_articulo_encontrado = True
            ordinal_word_raw = match.group(1).lower()
            ordinal_word_clean = ordinal_word_raw.replace(" ", "")
            ordinal_number = ordinal_map.get(ordinal_word_clean, ordinal_map.get(ordinal_word_raw, ordinal_word_raw))
            id_articulo = f"{ordinal_word_raw.capitalize()} ({ordinal_number})"
            
            estado_actual["Articulo"] = id_articulo
            if in_transitorios:
                estado_actual["Transitorio"] = "Transitorio"
        
        if primer_articulo_encontrado:
            parrafos_etiquetados.append({"texto": p, "etiquetas": estado_actual.copy()})

    # Fusión de Chunks
    chunks_fusionados = defaultdict(lambda: {"texto_combinado": "", "etiquetas": {}})
    for p_etiquetado in parrafos_etiquetados:
        etiquetas = p_etiquetado["etiquetas"]
        # La clave de fusión ahora incluirá implícitamente 'Decreto' al estar en el diccionario
        clave_fusion = tuple(etiquetas.values())
        
        if not chunks_fusionados[clave_fusion]["etiquetas"]:
            chunks_fusionados[clave_fusion]["etiquetas"] = etiquetas
        chunks_fusionados[clave_fusion]["texto_combinado"] += p_etiquetado["texto"] + "\n"

    chunks_finales = []
    for i, (_, chunk_data) in enumerate(chunks_fusionados.items()):
        etiquetas = chunk_data["etiquetas"]
        texto = chunk_data["texto_combinado"].strip()
        
        # Generación final con metadatos completos
        chunk_completo = {**metadatos_base, **etiquetas, "chunk_index": i + 1, "texto_chunk": texto}
        chunks_finales.append(chunk_completo)
        
    return chunks_finales

def algoritmo_numeros_mx(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    --- ALGORITMO DE CHUNKING (NUMERACIÓN DECIMAL) ---
    Procesa documentos estructurados por numerales (1., 1.1, 2., etc.) y Capítulos.
    HOMOLOGADO CON EVA 5.2 (Metadatos Completos).
    """
    parrafos_etiquetados = []
    
    pattern_num = re.compile(r'^\s*(\d+(?:\.\d+)*)\b')
    
    # 1. ESTADO ACTUAL HOMOLOGADO
    estado_actual = {
        "Decreto": "<No aplica>", # <--- NUEVO CAMPO OBLIGATORIO
        "Libro": "<No aplica>", 
        "Titulo": metadatos_base.get("tipo_documento", "Protocolo"), 
        "Capitulo": "<No aplica>", 
        "Seccion": "<No aplica>", 
        "Articulo": "<No aplica>", 
        "Transitorio": "Principal"
    }

    in_transitorios = False
    procesamiento_activo = False

    # Lógica de escaneo (SIN CAMBIOS)
    for p in lista_de_parrafos:
        match_cap = re.match(r'CAP[ÍI]TULO\s+(.*)', p, re.IGNORECASE)
        match_num = pattern_num.match(p)
        match_trans = re.match(r'^\s*TRANSITORIOS\b', p, re.IGNORECASE)

        if match_cap or match_num or match_trans:
            procesamiento_activo = True
        
        if not procesamiento_activo:
            continue

        if match_trans:
            in_transitorios = True
            estado_actual.update({"Transitorio": "Encabezado", "Titulo": "Transitorios", "Capitulo": "<No aplica>", "Articulo": "<No aplica>"})
        elif match_cap:
            estado_actual.update({"Capitulo": match_cap.group(1).strip(), "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif match_num:
            id_articulo = match_num.group(1)
            estado_actual["Articulo"] = id_articulo
            if in_transitorios:
                estado_actual["Transitorio"] = "Transitorio"
        
        parrafos_etiquetados.append({"texto": p, "etiquetas": estado_actual.copy()})

    # Fusión de Chunks
    chunks_fusionados = defaultdict(lambda: {"texto_combinado": "", "etiquetas": {}})
    for p_etiquetado in parrafos_etiquetados:
        etiquetas = p_etiquetado["etiquetas"]
        
        # 2. CLAVE DE FUSIÓN ACTUALIZADA (Incluye Decreto)
        clave_fusion = (
            etiquetas["Decreto"], # <--- Se agrega a la tupla de identificación
            etiquetas["Libro"], etiquetas["Titulo"], etiquetas["Capitulo"],
            etiquetas["Seccion"], etiquetas["Articulo"], etiquetas["Transitorio"]
        )
        
        if not chunks_fusionados[clave_fusion]["etiquetas"]:
            chunks_fusionados[clave_fusion]["etiquetas"] = etiquetas
        chunks_fusionados[clave_fusion]["texto_combinado"] += p_etiquetado["texto"] + "\n"

    chunks_finales = []
    for i, (_, chunk_data) in enumerate(chunks_fusionados.items()):
        etiquetas = chunk_data["etiquetas"]
        texto = chunk_data["texto_combinado"].strip()
        
        # Filtro de seguridad (mantenido)
        if re.fullmatch(r'CAP[ÍI]TULO\s+.*', texto, re.IGNORECASE) and etiquetas["Articulo"] == "<No aplica>":
            continue
        
        chunk_completo = {**metadatos_base, **etiquetas, "chunk_index": i + 1, "texto_chunk": texto}
        chunks_finales.append(chunk_completo)
        
    return chunks_finales

def algoritmo_semantico(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """Algoritmo Semántico (Recursive Splitter) para prosa (Preámbulos/Introducciones)."""
    texto_completo = "\n\n".join(lista_de_parrafos)
    
    # Configuración estándar para prosa legal
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_text(texto_completo)
    
    final_chunks = []
    for i, txt in enumerate(chunks):
        final_chunks.append({
            **metadatos_base,
            "Decreto": "<No aplica>", "Libro": "<No aplica>", "Titulo": "<No aplica>", 
            "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>", 
            "Transitorio": "Principal",
            "chunk_index": i + 1, "texto_chunk": txt.strip(),
            "estructura": "semantic_preamble" # Etiqueta distintiva
        })
    return final_chunks

def enrutar_procesamiento(lista_de_parrafos: list[str], metadatos_base: dict, funcion_legal) -> list[dict]:
    """
    Router Inteligente (Adaptado para Excepciones).
    1. Busca el inicio de la estructura legal (Ordinales, Números o Estándar).
    2. Lo ANTERIOR -> Semántico.
    3. Lo POSTERIOR -> Algoritmo de Excepción (pasado como argumento).
    """
    
    # 1. Regex extendido para detectar inicio de excepciones (Primero, 1., Capítulo, etc.)
    # Detecta:
    # - Ordinales: PRIMERO, SEGUNDO...
    # - Números: 1., 1.1... (al inicio de línea)
    # - Estándar: ARTICULO, CAPITULO...
    patron_arranque = re.compile(
        r'^\s*(?:'
        r'(?:PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[ÉE]PTIMO|OCTAVO|NOVENO|D[ÉE]CIMO)|' # Ordinales
        r'(?:\d+\.(?:\d+)*)|' # Números (1., 1.1)
        r'(?:DECRETO|LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|(?:ART[ÍI]?CULO|ART\.?))' # Estándar
        r')\b', 
        re.IGNORECASE
    )

    indice_corte = -1
    for i, p in enumerate(lista_de_parrafos):
        p_clean = p.strip().lstrip('\ufeff')
        if patron_arranque.match(p_clean):
            indice_corte = i
            break
    
    chunks_finales = []

    # CASO A: Todo es semántico (no se halló estructura)
    if indice_corte == -1:
        print(f"  -> 📄 Estructura no detectada. Procesando todo como semántico.")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    # CASO B: Estructura detectada (Híbrido)
    parte_preambulo = lista_de_parrafos[:indice_corte]
    parte_legal = lista_de_parrafos[indice_corte:]
    
    print(f"  -> ✂️  Corte detectado en párrafo {indice_corte}.")

    # 1. Procesar Preámbulo
    if parte_preambulo:
        print(f"     📄 Procesando {len(parte_preambulo)} párrafos de preámbulo...")
        chunks_sem = algoritmo_semantico(parte_preambulo, metadatos_base)
        chunks_finales.extend(chunks_sem)

    # 2. Procesar Cuerpo Legal (Usando la función de excepción específica)
    if parte_legal:
        print(f"     ⚖️  Procesando {len(parte_legal)} párrafos de cuerpo legal...")
        # Llamamos a la función que pasamos como argumento (palabras o numeros)
        chunks_leg = funcion_legal(parte_legal, metadatos_base)
        chunks_finales.extend(chunks_leg)

    # Re-indexado consecutivo
    for idx, chunk in enumerate(chunks_finales):
        chunk["chunk_index"] = idx + 1

    return chunks_finales

# 3. --- FUNCIÓN PRINCIPAL DEL PIPELINE ---
def main():
    """
    Función Principal Orquestadora (Versión Final Blindada).
    Integra: Detección de Hardware, Normalización POSIX, Alerta de Rutas y Router V2.
    """
    print(f"--- 🔄 Iniciando Pipeline de Excepciones (vArmonizada - Final) en {device.upper()} ---")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. CARGA Y NORMALIZACIÓN DE MAPAS
    archivos_procesados_map = {}
    all_chunks_finales = []
    
    if MAP_FILE_PATH.exists():
        with open(MAP_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_procesados = data.get("archivos_procesados", {})
            # BLINDAJE 1: Normalización de backslashes a slashes (Windows -> Linux compat)
            # Esto evita que 'carpeta\archivo' se duplique como 'carpeta/archivo'
            archivos_procesados_map = {k.replace('\\', '/'): v for k, v in raw_procesados.items()}
            
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
            all_chunks_finales = json.load(f)

    # 2. ESCANEO EN DISCO (Usando la variable global unificada)
    archivos_actuales_en_disco = set()
    for f in INPUT_DOCS_DIR.rglob('*.docx'):
        if f.name in TODAS_LAS_EXCEPCIONES: # <--- Más limpio y directo
            archivos_actuales_en_disco.add(f.relative_to(BASE_DIR).as_posix())

    # 3. LÓGICA DE CONJUNTOS (Set Difference)
    procesados_set = set(archivos_procesados_map.keys())
    files_to_delete = procesados_set - archivos_actuales_en_disco
    files_to_process = archivos_actuales_en_disco - procesados_set
    
    print(f"  -> ➕ {len(files_to_process)} archivos NUEVOS.")
    print(f"  -> ➖ {len(files_to_delete)} archivos para ELIMINAR.")

    # BLINDAJE 3: ALERTA CRÍTICA DE RUTAS (Idéntico a EVA 5.2)
    # Si detecta que va a borrar y crear la misma cantidad, suele ser un error de entorno.
    if len(files_to_delete) > 0 and len(files_to_process) > 0 and len(files_to_delete) == len(files_to_process):
        print("\n⚠️  ALERTA CRÍTICA: Se detectó una posible desincronización de rutas (Slash vs Backslash).")
        print("    El script detecta que borrará y creará la misma cantidad de archivos.")
        print("    Se procederá, pero verifica si 'mapa.json' tiene rutas mezcladas.\n")

    if not files_to_delete and not files_to_process:
        print("\n✨ Todo sincronizado. No hay cambios.")
        return

    # 4. CARGA DE MODELO
    print(f"\n🧠 Cargando modelo: '{EMBEDDING_MODEL}' en {device}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL, 
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )
    db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)
    
    # 5. ELIMINACIÓN
    if files_to_delete:
        print(f"\n🗑️  Eliminando {len(files_to_delete)} archivo(s)...")
        # Borramos por 'source' (nombre de archivo) para compatibilidad con Chroma
        source_filenames_to_delete = {os.path.basename(f) for f in files_to_delete}
        
        for filename in tqdm(source_filenames_to_delete, desc="Eliminando de DB"):
            try:
                db.delete(where={"source": filename})
            except Exception as e:
                print(f"   Error borrando {filename}: {e}")
        
        # Limpieza de metadatos en memoria
        all_chunks_finales = [c for c in all_chunks_finales if c.get("source") not in source_filenames_to_delete]
        for f in files_to_delete:
            archivos_procesados_map.pop(f, None)

    # 6. CREACIÓN (CON ROUTER INTEGRADO DEL PASO 5)
    if files_to_process:
        print(f"\n➕ Procesando {len(files_to_process)} archivo(s)...")
        # Reconstruimos los paths completos
        files_to_process_list = [BASE_DIR / f for f in files_to_process]

        for file_path in tqdm(files_to_process_list, desc="Procesando"):
            lista_de_parrafos = extraer_parrafos_limpios_de_docx(file_path)
            if not lista_de_parrafos: continue
            
            base_metadata = parse_filename_for_metadata(file_path)
            
            chunks_del_documento = []
            
            # --- ROUTER V2: SELECCIÓN DE ESTRATEGIA ---
            if file_path.name in ARCHIVOS_CON_ORDINALES:
                chunks_del_documento = enrutar_procesamiento(
                    lista_de_parrafos, base_metadata, algoritmo_palabras_mx
                )
            elif file_path.name in ARCHIVOS_CON_NUMERACION:
                chunks_del_documento = enrutar_procesamiento(
                    lista_de_parrafos, base_metadata, algoritmo_numeros_mx
                )
            
            if chunks_del_documento:
                documents_for_db = [Document(page_content=chunk.pop("texto_chunk"), metadata=chunk) for chunk in chunks_del_documento]
                db.add_documents(documents=documents_for_db)
                
                # Re-inyectamos texto para el JSON de respaldo
                for doc in documents_for_db:
                    doc.metadata["texto_chunk"] = doc.page_content
                    all_chunks_finales.append(doc.metadata)

                # Guardamos en el mapa usando la ruta POSIX relativa
                relative_path_posix = file_path.relative_to(BASE_DIR).as_posix()
                archivos_procesados_map[relative_path_posix] = {"chunks_generados": len(chunks_del_documento)}

    # 7. GUARDADO FINAL
    print("\n💾 Guardando metadatos y mapa actualizado...")
    with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks_finales, f, indent=4, ensure_ascii=False)
    
    mapa_data = {
        "ultima_sincronizacion": datetime.now().isoformat(),
        "modelo_embedding": EMBEDDING_MODEL,
        "total_archivos_en_disco": len(archivos_procesados_map),
        "total_chunks_generados": sum(v.get("chunks_generados", 0) for v in archivos_procesados_map.values()),
        "archivos_procesados": archivos_procesados_map
    }
    with open(MAP_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(mapa_data, f, indent=4, ensure_ascii=False)

    print("\n🎉 ¡Sincronización de Excepciones completada con éxito!")

# 4. --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    main()
