# === SCRIPT DE PROCESAMIENTO Y GENERACIÓN DE EMBEDDINGS PARA DOCX ===
# VERSIÓN 5.1 - PROCESAMIENTO DUAL (LEGAL / SEMÁNTICO) + GPU + NORMALIZACIÓN
# Este script ahora puede procesar dos tipos de estructuras de documentos,
# seleccionadas a través de la nomenclatura del archivo:
# 1. ..._legal.docx: Para documentos con estructura de Ley, Título, Capítulo, Artículo.
# 2. ..._semantic.docx: Para documentos de prosa, reglamentos o procedimientos.

import os
import re
import json
import torch  # <--- NUEVO: Necesario para detectar hardware
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import docx  # DEPENDENCIA: python-docx
from tqdm import tqdm

# --- Dependencias de LangChain ---
# MODIFICADO: Se añade RecursiveCharacterTextSplitter para el procesamiento semántico
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 1. --- CONFIGURACIÓN INICIAL ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DOCS_DIR = BASE_DIR / "Axiomas" / "legislacion-unam"
OUTPUT_DIR = BASE_DIR / "procesado-unam"
DB_PATH = OUTPUT_DIR / "chroma_db_unam"
METADATA_FILE_PATH = OUTPUT_DIR / "metadata.json"
MAP_FILE_PATH = OUTPUT_DIR / "mapa.json"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"

# --- DETECCIÓN DE HARDWARE INTELIGENTE ---
# <--- NUEVO: Switch automático de GPU/CPU
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
print(f"⚡ Hardware detectado para indexación (UNAM): {device.upper()}")


# 2. --- MÓDULOS DE PROCESAMIENTO ---

# MODIFICADO: La función ahora parsea 4 partes del nombre del archivo.
def parse_filename_for_metadata(file_path: Path) -> dict:
    """
    Extrae metadatos del nombre del archivo, incluyendo la ESTRUCTURA de procesamiento.
    Espera el formato: 'fecha_tipo_titulo_estructura.docx'
    """
    filename = file_path.name
    name_without_ext = file_path.stem
    parts = name_without_ext.split('_')
    
    try:
        relative_parts = file_path.relative_to(INPUT_DOCS_DIR).parts
        dominio = relative_parts[0]
        sub_dominio = relative_parts[1]
    except IndexError:
        dominio = "desconocido"
        sub_dominio = "general"

    metadata = {
        "dominio": dominio,
        "sub_dominio": sub_dominio,
        "source": filename
    }

    if len(parts) == 4:
        fecha_str, tipo_doc_raw, titulo_doc_raw, estructura = parts
        metadata["fecha_documento"] = fecha_str
        metadata["tipo_documento"] = tipo_doc_raw.replace('-', ' ')
        metadata["titulo_documento"] = titulo_doc_raw.replace('-', ' ').lower()
        metadata["estructura"] = estructura.lower()  # 'legal' o 'semantic'
    else:
        print(f"  (ADVERTENCIA: El archivo '{filename}' no sigue el formato 'fecha_tipo_titulo_estructura'.)")
        metadata["titulo_documento"] = name_without_ext.replace('_', ' ').replace('-', ' ').lower()
        metadata["estructura"] = "semantic" # Asignar 'semantic' por defecto para seguridad
        print("  -> Se asumirá procesamiento 'semantic' por defecto.")

    return metadata

def extraer_parrafos_limpios_de_docx(file_path: Path) -> list[str]:
    """
    Abre un documento de Word y extrae directamente cada párrafo.
    """
    parrafos_extraidos = []
    try:
        document = docx.Document(file_path)
        for para in document.paragraphs:
            cleaned_paragraph = re.sub(r'\s+', ' ', para.text).strip()
            if cleaned_paragraph:
                parrafos_extraidos.append(cleaned_paragraph)
    except Exception as e:
        print(f"\n--- ❌ ERROR al procesar el archivo {file_path.name}: {e} ---")
        return []
    
    return parrafos_extraidos

# SIN CAMBIOS: El algoritmo original para estructura legal se mantiene intacto.
def algoritmo_eva(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    --- ALGORITMO DE CHUNKING ESTRUCTURADO (LEGAL) ---
    Procesa una lista de párrafos de un documento legislativo para asignar etiquetas
    semánticas jerárquicas (Libro, Título, Capítulo, Artículo).
    """
    parrafos_etiquetados = []
    estado_actual = {
        "Libro": "<No aplica>", "Titulo": "<No aplica>", "Capitulo": "<No aplica>",
        "Seccion": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Principal"
    }

    for p in lista_de_parrafos:
        if match := re.match(r'LIBRO\s+(.*)', p, re.IGNORECASE):
            estado_actual.update({"Libro": match.group(1).strip(), "Titulo": "<No aplica>", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif match := re.match(r'T[ÍI]TULO\s+(.*)', p, re.IGNORECASE):
            estado_actual.update({"Titulo": match.group(1).strip(), "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif match := re.match(r'CAP[ÍI]TULO\s+(.*)', p, re.IGNORECASE):
            estado_actual.update({"Capitulo": match.group(1).strip(), "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
        elif match := re.match(r'SECCI[ÓO]N\s+(.*)', p, re.IGNORECASE):
            estado_actual.update({"Seccion": match.group(1).strip(), "Articulo": "<No aplica>"})
        
        elif match := re.match(r'ART[ÍI]CULO\s+([\w°º.-]+)', p, re.IGNORECASE):
            
            # 1. Capturar el ID tal cual, incluyendo símbolos
            id_articulo_raw = match.group(1).strip()

            # Lista de limpieza optimizada, SIN incluir la letra 'o'
            LIMPIEZA_SIMBOLOS = r'[º.-:;\s"\'\’]'
            
            # 2. Verificar si el ID comienza con un dígito (casi siempre es numérico)
            if id_articulo_raw and id_articulo_raw[0].isdigit():
                # Lógica para números: Limpia el 'o' y otros sufijos
                id_articulo = re.sub(r'[o°º.-:;\s"\'\’]', '', id_articulo_raw).strip()
            else:
                # Lógica para palabras: Solo elimina símbolos de ruido, preserva la 'o'
                id_articulo = re.sub(LIMPIEZA_SIMBOLOS, '', id_articulo_raw).strip()
                
            if estado_actual["Transitorio"] != "Principal":
                estado_actual["Transitorio"] = "Transitorio"
                
            estado_actual["Articulo"] = id_articulo # Guarda el ID limpio        

        elif re.match(r'(?:ART[ÍI]CULOS\s+)?TRANSITORIOS\b', p, re.IGNORECASE):
            estado_actual.update({"Libro": "<No aplica>", "Titulo": "Artículos Transitorios", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Encabezado"})
        
        parrafos_etiquetados.append({"texto": p, "etiquetas": estado_actual.copy()})

    chunks_fusionados = defaultdict(lambda: {"texto_combinado": "", "etiquetas": {}})
    for p_etiquetado in parrafos_etiquetados:
        etiquetas = p_etiquetado["etiquetas"]
        clave_fusion = tuple(etiquetas.values())
        if not chunks_fusionados[clave_fusion]["etiquetas"]:
            chunks_fusionados[clave_fusion]["etiquetas"] = etiquetas
        chunks_fusionados[clave_fusion]["texto_combinado"] += p_etiquetado["texto"] + "\n"

    chunks_finales = []
    for i, (_, chunk_data) in enumerate(chunks_fusionados.items()):
        chunk_completo = {**metadatos_base, **chunk_data["etiquetas"], "chunk_index": i + 1, "texto_chunk": chunk_data["texto_combinado"].strip()}
        chunks_finales.append(chunk_completo)
        
    return chunks_finales

# NUEVO: Algoritmo para procesamiento semántico de documentos de prosa.
def algoritmo_semantico(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    --- ALGORITMO DE CHUNKING SEMÁNTICO PARA PROSA ---
    Usa un divisor de texto recursivo para crear chunks basados en la estructura
    lógica del texto (párrafos, saltos de línea), ideal para RAG.
    """
    texto_completo = "\n\n".join(lista_de_parrafos)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks_de_texto = text_splitter.split_text(texto_completo)
    
    chunks_finales = []
    for i, texto in enumerate(chunks_de_texto):
        # Para documentos semánticos, las etiquetas jerárquicas no aplican.
        chunk_completo = {
            **metadatos_base,
            "Libro": "<No aplica>", "Titulo": "<No aplica>", "Capitulo": "<No aplica>",
            "Seccion": "<No aplica>", "Articulo": "<No aplica>", "Transitorio": "Principal",
            "chunk_index": i + 1,
            "texto_chunk": texto.strip()
        }
        chunks_finales.append(chunk_completo)
        
    return chunks_finales

# NUEVO: Función "enrutadora" que elige el algoritmo a usar.
def enrutar_procesamiento_por_estructura(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    Enruta el documento al algoritmo de chunking correcto basándose en la
    etiqueta 'estructura' extraída del nombre del archivo.
    """
    estructura = metadatos_base.get("estructura", "semantic")

    if estructura == "legal":
        print(f"  -> ⚖️  Procesando '{metadatos_base['source']}' con 'algoritmo_eva' (legal).")
        return algoritmo_eva(lista_de_parrafos, metadatos_base)
    
    elif estructura == "semantic":
        print(f"  -> 📄 Procesando '{metadatos_base['source']}' con 'algoritmo_semantico' (semántico).")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)
    
    else:
        print(f"  (ADVERTENCIA: Estructura '{estructura}' no reconocida en '{metadatos_base['source']}'. Usando 'algoritmo_semantico' por defecto.)")
        return algoritmo_semantico(lista_de_parrafos, metadatos_base)


# 3. --- FUNCIÓN PRINCIPAL DEL PIPELINE ---
def main():
    """Orquesta el proceso de SINCRONIZACIÓN para archivos .docx."""
    print(f"--- 🔄 Iniciando Pipeline de Sincronización de Embeddings (v5.1 - Dual) en {device.upper()} ---")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("STEP 1: Cargando registros y escaneando archivos actuales...")
    archivos_procesados_map = {}
    all_chunks_finales = []

    if MAP_FILE_PATH.exists():
        with open(MAP_FILE_PATH, "r", encoding="utf-8") as f:
            mapa_previo = json.load(f)
            archivos_procesados_map = mapa_previo.get("archivos_procesados", {})
    
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
            all_chunks_finales = json.load(f)

    archivos_actuales_en_disco = {str(f.relative_to(BASE_DIR)) for f in INPUT_DOCS_DIR.rglob('*.docx')}
    
    print("\nSTEP 2: Comparando registros con el estado actual del disco...")
    archivos_ya_procesados_set = set(archivos_procesados_map.keys())
    files_to_delete = archivos_ya_procesados_set - archivos_actuales_en_disco
    files_to_process = archivos_actuales_en_disco - archivos_ya_procesados_set
    
    if not files_to_delete and not files_to_process:
        print("\n✨ ¡Perfecto! La base de datos ya está sincronizada.")
        return

    print(f"  -> ➕ {len(files_to_process)} archivos NUEVOS para añadir.")
    print(f"  -> ➖ {len(files_to_delete)} archivos para ELIMINAR.")

    print("\nSTEP 3: Ejecutando acciones de sincronización...")
    print(f"\n🧠 Cargando modelo de embeddings: '{EMBEDDING_MODEL}'...")
    
    # <--- MODIFICADO: Uso de device dinámico y normalización activada
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL, 
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)
    
    if files_to_delete:
        print(f"\n🗑️  Eliminando {len(files_to_delete)} archivo(s) de la base de datos...")
        source_filenames_to_delete = {os.path.basename(f) for f in files_to_delete}
        for filename in tqdm(source_filenames_to_delete, desc="Eliminando chunks de la DB"):
            db.delete(where={"source": filename})
        all_chunks_finales = [chunk for chunk in all_chunks_finales if chunk.get("source") not in source_filenames_to_delete]
        for file_path in files_to_delete:
            archivos_procesados_map.pop(file_path, None)

    if files_to_process:
        print(f"\n➕ Procesando y añadiendo {len(files_to_process)} archivo(s) nuevo(s)...")
        files_to_process_list = [BASE_DIR / f for f in files_to_process]

        for file_path in tqdm(files_to_process_list, desc="Procesando documentos nuevos"):
            lista_de_parrafos = extraer_parrafos_limpios_de_docx(file_path)
            if not lista_de_parrafos:
                continue
            
            base_metadata = parse_filename_for_metadata(file_path)
            
            # MODIFICADO: Se llama a la función enrutadora en lugar de directamente a 'algoritmo_eva'.
            chunks_del_documento = enrutar_procesamiento_por_estructura(lista_de_parrafos, base_metadata)
            
            if chunks_del_documento:
                documents_for_db = [Document(page_content=chunk.pop("texto_chunk"), metadata=chunk) for chunk in chunks_del_documento]
                db.add_documents(documents=documents_for_db)
                
                for doc in documents_for_db:
                    doc.metadata["texto_chunk"] = doc.page_content
                    all_chunks_finales.append(doc.metadata)

                relative_path_str = str(file_path.relative_to(BASE_DIR))
                archivos_procesados_map[relative_path_str] = {"chunks_generados": len(chunks_del_documento)}

    print("\nSTEP 4: Guardando el estado final sincronizado...")
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

    print("\n🎉 ¡VICTORIA! Sincronización completada con éxito.")
    print(f"👉 Archivos de estado y DB actualizados en: '{OUTPUT_DIR}'")

# 4. --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    main()
