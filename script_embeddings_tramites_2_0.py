# -*- coding: utf-8 -*-
"""
script_embeddings_tramites_mx.py (Versión 2.0 - Optimizado Aura)
Propósito: Ingestar el CSV de trámites en ChromaDB con estrategia de:
1. Chunks Ligeros (Semánticos) para búsqueda eficiente.
2. Metadata Pesada (Total) para contexto preciso.
"""

import os
import pandas as pd
import json
import shutil
import torch
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# --- Dependencias de LangChain ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 1. --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent
# Archivo de entrada (Asegúrate que el nombre coincida exactamente)
INPUT_CSV_FILE = BASE_DIR / "tramites_secretaria_gobernacion_procesados_rapido.csv"

# Configuración de salida
OUTPUT_DIR = BASE_DIR / "procesado-mx" / "tramites-mx"
DB_PATH = OUTPUT_DIR / "chroma_db_tramites_mx"
METADATA_FILE_PATH = OUTPUT_DIR / "metadata.json"
MAP_FILE_PATH = OUTPUT_DIR / "mapa.json"

# Modelo de Embeddings (Multilingüe de alto rendimiento)
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"
COLLECTION_NAME = "tramites_gob_mx" # Nombre específico para trámites

# 2. --- FUNCIONES AUXILIARES ---

def clean_metadata_value(value):
    """
    ChromaDB solo acepta str, int, float o bool en metadata.
    Esta función asegura que no pasen objetos complejos o Nones.
    """
    if pd.isna(value):
        return "N/A"
    return value

def main():
    print("--- 🚀 INICIANDO INGESTIÓN AURA (V2.0) ---")
    
    # Validar existencia del archivo
    if not INPUT_CSV_FILE.exists():
        print(f"❌ Error: No se encuentra el archivo {INPUT_CSV_FILE}")
        return

    # Limpiar directorio de salida previo para evitar corrupción
    if OUTPUT_DIR.exists():
        print("🧹 Limpiando directorio de salida anterior...")
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. --- CARGA Y PROCESAMIENTO DEL CSV ---
    print(f"📂 Leyendo CSV: {INPUT_CSV_FILE.name}...")
    
    # IMPORTANTE: Usamos el separador '¬' detectado en el análisis previo
    try:
        df = pd.read_csv(INPUT_CSV_FILE, sep='¬', engine='python', on_bad_lines='skip')
        # Rellenar valores nulos para evitar errores en embeddings y metadata
        df = df.fillna("N/A")
        print(f"✅ CSV cargado. Total de registros: {len(df)}")
    except Exception as e:
        print(f"❌ Error al leer el CSV: {e}")
        return

    # 4. --- CONSTRUCCIÓN DE DOCUMENTOS (Directiva Aura) ---
    print("🔨 Construyendo documentos (Chunks Ligeros + Metadata Pesada)...")
    
    docs = []
    
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Procesando filas"):
        # A. METADATA: Absolutamente todas las columnas
        # Convertimos la fila a diccionario y limpiamos tipos de datos
        metadata = {k: clean_metadata_value(v) for k, v in row.to_dict().items()}
        
        # Agregamos campos extra de control para el sistema RAG
        metadata["dominio"] = "tramites"
        metadata["source"] = INPUT_CSV_FILE.name
        
        # B. CHUNK SEMÁNTICO (Solo columnas clave)
        # Extraemos las 3 columnas doradas
        nombre = str(row.get('nombre', 'Trámite sin nombre')).strip()
        desc_ciudadana = str(row.get('descripcionCiudadana', 'Sin descripción ciudadana')).strip()
        tags = str(row.get('tags', '')).strip()
        
        # Formato optimizado para embeddings (Intención + Contexto Clave)
        page_content = (
            f"TRÁMITE: {nombre}\n"
            f"¿PARA QUÉ SIRVE?: {desc_ciudadana}\n"
            f"PALABRAS CLAVE: {tags}"
        )
        
        # Crear Documento LangChain
        docs.append(Document(page_content=page_content, metadata=metadata))

    # 5. --- GENERACIÓN DE EMBEDDINGS ---
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🧠 Cargando modelo de embeddings: {EMBEDDING_MODEL} en [{device}]...")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True} # Recomendado para E5
    )

    # 6. --- CREACIÓN DE VECTOR STORE (CHROMA) ---
    print(f"💾 Guardando vectores en: {DB_PATH}...")
    
    # Procesamiento por lotes para no saturar memoria si son muchos registros
    BATCH_SIZE = 500
    for i in tqdm(range(0, len(docs), BATCH_SIZE), desc="Insertando lotes"):
        batch = docs[i:i + BATCH_SIZE]
        if i == 0:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=str(DB_PATH)
            )
        else:
            vectorstore.add_documents(batch)

    # 7. --- GENERACIÓN DE ARCHIVOS DE AUDITORÍA ---
    print("📝 Generando archivos de metadata y mapa...")

    # Guardar metadata.json (Versión legible humana con el texto del chunk añadido)
    export_data = []
    for doc in docs:
        item = doc.metadata.copy()
        item["texto_chunk_vectorizado"] = doc.page_content # Para referencia visual
        export_data.append(item)

    with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=4, ensure_ascii=False)

    # Guardar mapa.json (Resumen de ejecución)
    mapa_info = {
        "fecha_creacion": datetime.now().isoformat(),
        "archivo_origen": INPUT_CSV_FILE.name,
        "total_tramites": len(docs),
        "modelo_embeddings": EMBEDDING_MODEL,
        "estrategia": "Metadata-Rich + Semantic-Chunks",
        "columnas_vectorizadas": ["nombre", "descripcionCiudadana", "tags"],
        "path_db": str(DB_PATH)
    }
    
    with open(MAP_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(mapa_info, f, indent=4, ensure_ascii=False)

    print(f"\n✅ ¡Proceso completado con éxito!")
    print(f"   🔹 Base Vectorial: {DB_PATH}")
    print(f"   🔹 Metadata JSON: {METADATA_FILE_PATH}")
    print(f"   🔹 Trámites procesados: {len(docs)}")

if __name__ == "__main__":
    main()
