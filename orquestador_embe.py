# orquestador_embeddings.py
# === SCRIPT ORQUESTADOR (V6.0 - MODULARIZADO) ===
# Mantiene: I/O, Limpieza DOCX, ChromaDB, Sincronización Incremental
# Importa: Lógica Legal y Semántica

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import docx
import torch
from tqdm import tqdm

# --- Dependencias de Vector Store ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- IMPORTACIÓN DE MÓDULOS DE LÓGICA ---
try:
    from script_legal import algoritmo_eva_mx
    from script_semantico import algoritmo_semantico
    print("✅ Módulos de lógica (Legal/Semántico) cargados correctamente.")
except ImportError as e:
    raise ImportError(f"❌ Error crítico: No se encuentran los scripts módulos. {e}")

# --- IMPORTACIÓN DE EXCEPCIONES ---
try:
    from script_embeddings_excep_mx import TODAS_LAS_EXCEPCIONES
    print(f"✅ Sincronización exitosa: Se excluirán {len(TODAS_LAS_EXCEPCIONES)} archivos de excepciones.")
except ImportError:
    print("⚠️ ADVERTENCIA: No se encontró 'script_embeddings_excep_mx.py'.")
    TODAS_LAS_EXCEPCIONES = set()

# 1. --- CONFIGURACIÓN INICIAL ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DOCS_DIR = BASE_DIR / "Axiomas"
OUTPUT_DIR = BASE_DIR / "procesado-mx" / "principal-mx"
DB_PATH = OUTPUT_DIR / "chroma_db_mx"
METADATA_FILE_PATH = OUTPUT_DIR / "metadata.json"
SYNC_FILE_PATH = OUTPUT_DIR / "sincro.json"
MAP_FILE_PATH = OUTPUT_DIR / "mapa.json"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# 2. --- FUNCIONES DE SOPORTE (I/O & LIMPIEZA) ---

def parse_filename_for_metadata(file_path: Path) -> dict:
    """Extrae metadatos del nombre del archivo."""
    filename = file_path.name
    name_without_ext = file_path.stem
    parts = name_without_ext.split('_')
    
    try:
        relative_parts = file_path.relative_to(INPUT_DOCS_DIR).parts
        dominio = relative_parts[0] if len(relative_parts) > 0 else "general"
        sub_dominio = relative_parts[1] if len(relative_parts) > 1 else "general"
    except Exception:
        dominio = "desconocido"
        sub_dominio = "general"

    metadata = {"dominio": dominio, "sub_dominio": sub_dominio, "source": filename}

    if len(parts) == 4:
        metadata["fecha_documento"] = parts[0]
        metadata["tipo_documento"] = parts[1].replace('-', ' ')
        metadata["titulo_documento"] = parts[2].replace('-', ' ').lower()
        metadata["estructura"] = parts[3].lower()
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
    """Lee DOCX y limpia texto usando estrategia 'Delimitadores DOF'."""
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

def enrutar_procesamiento(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """Router Inteligente: Decide si llamar a Legal, Semántico o Ambos."""
    
    if metadatos_base.get("estructura") == "semantic":
        print(f"  -> 📄 Modo Semántico Forzado para: {metadatos_base['source']}")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    indice_corte = -1
    patron_arranque_legal = re.compile(
        r'^\s*(DECRETO|LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|(?:ART[ÍI]?CULO|ART\.?)|(?:ART[ÍI]CULOS\s+)?TRANSITORIOS)\b', 
        re.IGNORECASE
    )

    for i, p in enumerate(lista_de_parrafos):
        p_clean = p.strip().lstrip('\ufeff')
        if patron_arranque_legal.match(p_clean):
            indice_corte = i
            break
    
    chunks_finales = []

    if indice_corte == -1:
        print(f"  -> 📄 No se detectó estructura legal. Procesando todo como Semántico.")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)

    parte_preambulo = lista_de_parrafos[:indice_corte]
    parte_legal = lista_de_parrafos[indice_corte:]

    print(f"  -> ✂️  Corte detectado en párrafo {indice_corte}.")

    if parte_preambulo:
        meta_sem = metadatos_base.copy()
        meta_sem["estructura"] = "semantic_preamble"
        # LLAMADA A MÓDULO SEMÁNTICO
        chunks_sem = algoritmo_semantico(parte_preambulo, meta_sem)
        chunks_finales.extend(chunks_sem)

    if parte_legal:
        meta_legal = metadatos_base.copy()
        meta_legal["estructura"] = "legal"
        # LLAMADA A MÓDULO LEGAL
        chunks_leg = algoritmo_eva_mx(parte_legal, meta_legal)
        chunks_finales.extend(chunks_leg)

    # ARMONIZACIÓN: Asignar chunk_index GLOBAL preservando chunk_index_local
    for idx, chunk in enumerate(chunks_finales):
        chunk["chunk_index_global"] = idx + 1
        # Preservar chunk_index como índice local (no sobrescribir)
        if "chunk_index_local" not in chunk:
            chunk["chunk_index_local"] = chunk.get("chunk_index", idx + 1)

    return chunks_finales

# 3. --- FUNCIÓN PRINCIPAL (LÓGICA INCREMENTAL INTACTA) ---
def main():
    print(f"--- 🔄 Iniciando Orquestador (v6.0 Modular) en {device.upper()} ---")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # A. Carga de Estado
    estado_sincronizacion = {}
    chunks_totales = []
    
    if SYNC_FILE_PATH.exists():
        with open(SYNC_FILE_PATH, "r", encoding="utf-8") as f:
            estado_sincronizacion = json.load(f)
    else:
        print("ℹ️  No se encontró archivo de sincronización. Se creará uno nuevo.")

    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
            chunks_totales = json.load(f)

    # B. Escaneo y Comparación
    archivos_en_disco_info = {}
    raw_files = [f for f in INPUT_DOCS_DIR.rglob('*.docx') if f.name not in TODAS_LAS_EXCEPCIONES]
    
    for f in raw_files:
        ruta_rel = f.relative_to(BASE_DIR).as_posix()
        mtime = f.stat().st_mtime
        archivos_en_disco_info[ruta_rel] = mtime

    set_disco = set(archivos_en_disco_info.keys())
    set_sync = set(estado_sincronizacion.keys())
    
    a_borrar = set_sync - set_disco
    a_crear = set_disco - set_sync
    a_actualizar = set()
    for archivo in (set_disco & set_sync):
        if abs(archivos_en_disco_info[archivo] - estado_sincronizacion[archivo]) > 1.0: 
            a_actualizar.add(archivo)
    
    total_a_procesar = a_crear | a_actualizar
    total_a_eliminar = a_borrar | a_actualizar

    print(f"📊 Estado: Sync({len(set_sync)}) vs Disco({len(set_disco)}) -> +{len(a_crear)} | ~{len(a_actualizar)} | -{len(a_borrar)}")
    
    if not total_a_procesar and not total_a_eliminar:
        print("✅ Todo sincronizado. Regenerando reporte...")
    else:
        print(f"🚀 Cargando modelo {EMBEDDING_MODEL}...")
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
        db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)

        # C. Eliminaciones
        if total_a_eliminar:
            print(f"🗑️  Eliminando {len(total_a_eliminar)} obsoletos...")
            for ruta_relativa in total_a_eliminar:
                filename_original = os.path.basename(ruta_relativa)
                try:
                    db.delete(where={"source": filename_original})
                except Exception: pass
                chunks_totales = [c for c in chunks_totales if c.get("source") != filename_original]
                if ruta_relativa in estado_sincronizacion:
                    del estado_sincronizacion[ruta_relativa]

        # D. Procesamiento (Llamada al Router)
        if total_a_procesar:
            print(f"🔨 Procesando {len(total_a_procesar)} archivos...")
            lista_archivos = [BASE_DIR / f for f in total_a_procesar]
            
            for fpath in tqdm(lista_archivos):
                ruta_rel_posix = fpath.relative_to(BASE_DIR).as_posix()
                paras = extraer_parrafos_limpios_de_docx(fpath)
                
                if not paras: continue 
                
                meta = parse_filename_for_metadata(fpath)
                chunks = enrutar_procesamiento(paras, meta)
                
                if chunks:
                    # Usar .get() en lugar de .pop() para evitar operaciones destructivas
                    docs = [Document(page_content=c.get("texto_chunk", ""), metadata=c) for c in chunks]
                    db.add_documents(docs)
                    for d in docs: 
                        # Sincronizar page_content con texto_chunk
                        d.metadata["texto_chunk"] = d.page_content
                        chunks_totales.append(d.metadata)
                    
                    estado_sincronizacion[ruta_rel_posix] = archivos_en_disco_info[ruta_rel_posix]

        # E. Persistencia
        print("💾 Guardando estado del sistema...")
        with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(chunks_totales, f, indent=4, ensure_ascii=False)
        with open(SYNC_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(estado_sincronizacion, f, indent=4)

    # F. Reporte Humano
    print("📝 Generando mapa.json...")
    mapa_legible = {}
    conteo_chunks = defaultdict(int)
    for c in chunks_totales:
        if "source" in c: conteo_chunks[c["source"]] += 1
            
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
            "resumen": {"nuevos": len(a_crear), "actualizados": len(a_actualizar), "borrados": len(a_borrar)},
            "archivos": mapa_legible
        }, f, indent=4, ensure_ascii=False)

    print("🎉 Orquestación finalizada.")

if __name__ == "__main__":
    main()