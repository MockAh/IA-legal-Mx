# nombre_archivo: script_embeddings_segob.py
# === SCRIPT DE EMBEDDINGS ESPECIALIZADO: SECRETARIO DE GOBERNACIÓN IA ===
# VERSIÓN 6.0 (Estructura Unificada en procesado-mx)

import os
import re
import json
import shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import docx
import torch
from tqdm import tqdm

# --- Dependencias de LangChain ---
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

# ==============================================================================
# 1. --- CONFIGURACIÓN (ANÁLOGA A TRÁMITES 2.0) ---
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent

# A. Fuentes de Entrada (Híbridas)
INPUT_DIR_SEGOB = BASE_DIR / "Axiomas" / "legislacion-mx" / "Secretaria_Gobernacion"
INPUT_DIR_GENERAL = BASE_DIR / "Axiomas" / "legislacion-mx"

# B. Configuración de Salida (MODIFICADA)
# Ahora vive dentro de 'procesado-mx', al igual que 'tramites-mx' y 'principal-mx'
OUTPUT_DIR = BASE_DIR / "procesado-mx" / "segob-mx"
DB_PATH = OUTPUT_DIR / "chroma_db_segob"  # Subcarpeta para la DB, más ordenado
METADATA_FILE_PATH = OUTPUT_DIR / "metadata_segob.json"
MAP_FILE_PATH = OUTPUT_DIR / "mapa_segob.json"

# C. Modelo y Colección
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"
# Mantenemos 'langchain' para compatibilidad fácil con app.py, 
# pero la carpeta física ya está separada.
COLLECTION_NAME = "langchain" 

# D. Lista VIP (Whitelist)
LEYES_FUNDAMENTALES = [
    "1917-02-05_Constitucion-Politica_Constitucion-Politica-de-los-Estados-Unidos-Mexicanos.docx",
    "1931-08-14_Codigo_Codigo-Penal-Federal.docx",
    "2017-02-05_Constitucion-Politca_Constitucion-Politica-de-la-Ciudad-de-Mexico.docx",
    "2019-05-27_Ley-Nacional_Ley-Nacional-Sobre-el-Uso-de-la-Fuerza.docx",
    "2025-07-16_Ley-General_Ley-General-del-Sistema-Nacional-de-Seguridad-Publica.docx"
]

# --- DETECCIÓN DE HARDWARE ---
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# 2. --- MÓDULOS DE PROCESAMIENTO ---

def parse_filename_for_metadata(file_path: Path) -> dict:
    """Extrae metadatos y define la ESTRUCTURA (legal/semantic)."""
    filename = file_path.name
    name_without_ext = file_path.stem
    parts = name_without_ext.split('_')
    
    # <--- CAMBIO 4: METADATOS ROBUSTOS (Detección de Dominio por Ubicación) --->
    # Ya no dependemos de una ruta relativa única, sino de dónde viene el archivo
    if INPUT_DIR_SEGOB in file_path.parents:
        dominio = "SEGOB_Interno"
        # Intentamos sacar subdominio si es posible, sino general
        try:
            relative_parts = file_path.relative_to(INPUT_DIR_SEGOB).parts
            sub_dominio = relative_parts[0] if len(relative_parts) > 0 else "general"
        except: sub_dominio = "general"
    else:
        dominio = "Marco_Fundamental_VIP"
        sub_dominio = "Constitucional"

    metadata = {"dominio": dominio, "sub_dominio": sub_dominio, "source": filename}

    # LÓGICA DE DETECCIÓN DE ESTRUCTURA (INTACTA)
    if len(parts) == 4:
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = parts[3].lower() # 'legal' o 'semantic'
    elif len(parts) >= 3:
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = "legal"
    else:
        metadata["titulo_documento"] = name_without_ext.replace('_', ' ').replace('-', ' ').lower()
        metadata["estructura"] = "legal"

    return metadata

def extraer_parrafos_limpios_de_docx(file_path: Path) -> list[str]:
    # ... (CÓDIGO ORIGINAL INTACTO: Limpieza DOF v5.5) ...
    parrafos_crudos = []
    try:
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            texto = re.sub(r'\s+', ' ', p.text).strip()
            if texto:
                parrafos_crudos.append(texto)
    except Exception as e:
        print(f"❌ Error en {file_path.name}: {e}")
        return []

    parrafos_finales = []
    regex_dof = re.compile(r'([^\.\:\;\(\)\n]*?DOF\s+(?:[\d]{2}-[\d]{2}-[\d]{4}(?:[,\s]*)*)+)', re.IGNORECASE)

    for p in parrafos_crudos:
        partes = regex_dof.split(p)
        if len(partes) == 1:
            parrafos_finales.append(partes[0])
            continue

        for i in range(0, len(partes) - 1, 2):
            texto_previo = partes[i].strip()
            dof_completo = partes[i+1].strip()
            
            if texto_previo:
                parrafos_finales.append(texto_previo)
            
            if parrafos_finales:
                parrafos_finales[-1] += " " + dof_completo
            else:
                parrafos_finales.append(dof_completo)
        
        texto_restante = partes[-1].strip()
        if texto_restante:
            parrafos_finales.append(texto_restante)
    
    return parrafos_finales

# --- ALGORITMOS DE CHUNKING (CÓDIGO ORIGINAL V5.5 INTACTO) ---

def algoritmo_eva_mx(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    # ... (CÓDIGO ORIGINAL INTACTO: Algoritmo Jerárquico Blindado) ...
    estado_actual = {
        "Decreto": "<No aplica>", "Libro": "<No aplica>", "Titulo": "<No aplica>", 
        "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>", 
        "Transitorio": "Principal"
    }
    parrafos_etiquetados = []
    
    # print(f"\n🔍 Iniciando escaneo de {len(lista_de_parrafos)} párrafos...") # Opcional: comentar para menos ruido

    for i, p in enumerate(lista_de_parrafos):
        p_clean = p.strip().lstrip('\ufeff') 
        
        if m := re.match(r'DECRETO\s*(.*)', p_clean, re.IGNORECASE):
            texto_decreto = m.group(1).strip()
            if not texto_decreto: texto_decreto = "Decreto"
            estado_actual.update({"Decreto": texto_decreto, "Libro": "<No aplica>", "Titulo": "<No aplica>", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})

        elif m := re.match(r'LIBRO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Libro": m.group(1).strip(), "Titulo": "<No aplica>", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif m := re.match(r'T[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Titulo": m.group(1).strip(), "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif m := re.match(r'CAP[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Capitulo": m.group(1).strip(), "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif m := re.match(r'SECCI[ÓO]N\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Seccion": m.group(1).strip(), "Articulo": "<No aplica>"})
        
        elif match := re.match(r'(?:ART[ÍI]?CULO|ART\.?)\s+([\w°º.-]+)', p_clean, re.IGNORECASE):
            id_articulo_raw = match.group(1).strip()
            id_limpio = re.sub(r'[º.:;\s"\'\’-]+$', '', id_articulo_raw).strip() 
            if id_limpio and id_limpio[0].isdigit():
                match_num = re.match(r'^(\d+)', id_limpio)
                id_articulo_final = match_num.group(1) if match_num else id_limpio
            else:
                id_articulo_final = id_limpio
            
            estado_actual["Articulo"] = id_articulo_final
            if estado_actual["Transitorio"] != "Principal":
                estado_actual["Transitorio"] = "Transitorio"
        
        elif re.match(r'(?:ART[ÍI]CULOS\s+)?TRANSITORIOS\b', p_clean, re.IGNORECASE):
            estado_actual.update({"Libro": "<No aplica>", "Titulo": "Artículos Transitorios", "Capitulo": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Encabezado"})

        parrafos_etiquetados.append({"texto": p, "etiquetas": estado_actual.copy()})

    chunks_fusionados = []
    if not parrafos_etiquetados: return []

    buffer_actual = parrafos_etiquetados[0]
    for item in parrafos_etiquetados[1:]:
        if item["etiquetas"] == buffer_actual["etiquetas"]:
            buffer_actual["texto"] += "\n" + item["texto"]
        else:
            chunks_fusionados.append(buffer_actual)
            buffer_actual = item
    chunks_fusionados.append(buffer_actual)

    resultado_final = []
    for i, chunk in enumerate(chunks_fusionados):
        meta_final = {**metadatos_base, **chunk["etiquetas"]}
        if not meta_final.get("Articulo"): meta_final["Articulo"] = "<No aplica>"
        meta_final["chunk_index"] = i + 1
        meta_final["texto_chunk"] = chunk["texto"].strip()
        resultado_final.append(meta_final)

    return resultado_final

def algoritmo_semantico(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    # ... (CÓDIGO ORIGINAL INTACTO) ...
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
    # ... (CÓDIGO ORIGINAL INTACTO: Router V2) ...
    if metadatos_base.get("estructura") == "semantic":
        print(f"  -> 📄 Modo Semántico Forzado para: {metadatos_base['source']}")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    indice_corte = -1
    patron_arranque_legal = re.compile(r'^\s*(DECRETO|LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|(?:ART[ÍI]?CULO|ART\.?)|(?:ART[ÍI]CULOS\s+)?TRANSITORIOS)\b', re.IGNORECASE)

    for i, p in enumerate(lista_de_parrafos):
        p_clean = p.strip().lstrip('\ufeff')
        if patron_arranque_legal.match(p_clean):
            indice_corte = i
            break
    
    if indice_corte == -1:
        print(f"  -> 📄 No se detectó estructura legal estricta. Procesando todo como semántico.")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    parte_preambulo = lista_de_parrafos[:indice_corte]
    parte_legal = lista_de_parrafos[indice_corte:]
    chunks_finales = []

    print(f"  -> ✂️  Corte detectado en párrafo {indice_corte}.")

    if parte_preambulo:
        meta_sem = metadatos_base.copy()
        meta_sem["estructura"] = "semantic_preamble"
        chunks_sem = algoritmo_semantico(parte_preambulo, meta_sem)
        chunks_finales.extend(chunks_sem)

    if parte_legal:
        chunks_leg = algoritmo_eva_mx(parte_legal, metadatos_base)
        chunks_finales.extend(chunks_leg)

    for idx, chunk in enumerate(chunks_finales):
        chunk["chunk_index"] = idx + 1

    return chunks_finales

# 3. --- FUNCIÓN PRINCIPAL ---

def main():
    print(f"--- ⚖️  Indexador SEGOB-IA Híbrido (v6.0 - Estructura Unificada) en {device.upper()} ---")
    
    # Crear directorio si no existe (incluyendo subcarpetas)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. CARGA DE MAPAS (Con normalización)
    archivos_procesados = {}
    chunks_totales = []
    if MAP_FILE_PATH.exists():
        with open(MAP_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_procesados = data.get("archivos_procesados", {})
            archivos_procesados = {k.replace('\\', '/'): v for k, v in raw_procesados.items()}
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f: chunks_totales = json.load(f)

    # 2. RECOLECCIÓN HÍBRIDA
    print("🔎 Recolectando archivos...")
    files_to_process = set()

    # A. Carpeta SEGOB
    if INPUT_DIR_SEGOB.exists():
        files_segob = list(INPUT_DIR_SEGOB.rglob('*.docx'))
        print(f"   📂 Fuente SEGOB: {len(files_segob)} archivos.")
        files_to_process.update(files_segob)
    else: print(f"   ⚠️ ADVERTENCIA: No existe {INPUT_DIR_SEGOB}")

    # B. Lista VIP
    found_vip = 0
    for vip_name in LEYES_FUNDAMENTALES:
        found = list(INPUT_DIR_GENERAL.rglob(vip_name))
        if found:
            files_to_process.add(found[0])
            found_vip += 1
        else: print(f"   ❌ Faltante VIP: {vip_name}")
    print(f"   ⭐ Fuente VIP: {found_vip}/{len(LEYES_FUNDAMENTALES)} agregadas.")

    # 3. SINCRONIZACIÓN
    archivos_disco = {f.relative_to(BASE_DIR).as_posix() for f in files_to_process if f.name not in TODAS_LAS_EXCEPCIONES}
    procesados_set = set(archivos_procesados.keys())
    a_borrar = procesados_set - archivos_disco
    a_crear = archivos_disco - procesados_set
    
    print(f"📊 Estado Final: {len(archivos_disco)} archivos en procesado-mx/segob-mx.")
    print(f"   ➕ Nuevos: {len(a_crear)} | ➖ Borrar: {len(a_borrar)}")
    
    if not a_crear and not a_borrar:
        print("✅ Todo sincronizado. Fin.")
        return

    # --- Carga de Modelo ---
    print(f"🚀 Cargando modelo E5 en {device}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, model_kwargs={'device': device}, encode_kwargs={'normalize_embeddings': True})
    
    # ATENCIÓN: Ahora la DB se guarda en la subcarpeta definida en DB_PATH
    db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings, collection_name=COLLECTION_NAME)

    # --- BORRADO ---
    if a_borrar:
        print(f"🗑️  Limpiando {len(a_borrar)} antiguos...")
        sources_borrar = {os.path.basename(f) for f in a_borrar}
        for src in sources_borrar:
            try: db.delete(where={"source": src})
            except: pass
        chunks_totales = [c for c in chunks_totales if c["source"] not in sources_borrar]
        for f in a_borrar: del archivos_procesados[f]

    # --- CREACIÓN ---
    if a_crear:
        print(f"🔨 Procesando {len(a_crear)} archivos nuevos...")
        files_list = [BASE_DIR / f for f in a_crear]
        for fpath in tqdm(files_list):
            paras = extraer_parrafos_limpios_de_docx(fpath)
            if not paras: continue
            meta = parse_filename_for_metadata(fpath)
            chunks = enrutar_procesamiento(paras, meta)
            if chunks:
                docs = [Document(page_content=c.pop("texto_chunk"), metadata=c) for c in chunks]
                db.add_documents(docs)
                for d in docs: d.metadata["texto_chunk"] = d.page_content; chunks_totales.append(d.metadata)
                archivos_procesados[fpath.relative_to(BASE_DIR).as_posix()] = {"chunks": len(chunks)}

    # Guardado Final
    print("💾 Guardando metadatos...")
    with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f: json.dump(chunks_totales, f, indent=4, ensure_ascii=False)
    with open(MAP_FILE_PATH, "w", encoding="utf-8") as f: json.dump({"updated": datetime.now().isoformat(), "archivos_procesados": archivos_procesados}, f, indent=4, ensure_ascii=False)

    print("🎉 Sincronización terminada.")

if __name__ == "__main__":
    main()