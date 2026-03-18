#!/usr/bin/env python3
"""
Script de debugging para entender qué está pasando en logica_a.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Configuración
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

# Importar las funciones
from utils_rag import extraer_entidades_con_llm, buscar_titulo_en_faiss, cargar_indice_faiss, normalizar_titulo
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

def debug_articulo(query):
    """Function para debuggear una consulta específica"""
    print(f"\n{'='*80}")
    print(f"❓ QUERY: {query}")
    print(f"{'='*80}")
    
    # Test 1: Extraer entidades
    print(f"\n1️⃣  EXTRAYENDO ENTIDADES CON LLM...")
    entidades = extraer_entidades_con_llm(query)
    print(f"   Result: {entidades}")
    
    titulo_usuario = entidades.get("titulo_documento")
    articulo_num = entidades.get("Articulo")
    print(f"   ✓ Título extraído: '{titulo_usuario}'")
    print(f"   ✓ Artículo extraído: {articulo_num} (tipo: {type(articulo_num).__name__})")
    
    if not titulo_usuario or not articulo_num:
        print(f"   ❌ No se pudieron extraer entidades")
        return
    
    # Test 2: Búsqueda en FAISS
    print(f"\n2️⃣  BUSCANDO TÍTULO EN FAISS...")
    try:
        embedding_fn = HuggingFaceEmbeddings(
            model_name="./modelo_e5", model_kwargs={'device': 'cpu'}
        )
        titulo_exacto = buscar_titulo_en_faiss(titulo_usuario, embedding_fn, k=1)
        print(f"   ✓ Título exacto encontrado: '{titulo_exacto}'")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 3: Normalizar
    print(f"\n3️⃣  NORMALIZANDO TÍTULO...")
    titulo_normalizado = normalizar_titulo(titulo_exacto)
    print(f"   ✓ Normalizado: '{titulo_normalizado}'")
    
    # Test 4: Inspeccionar ChromaDB
    print(f"\n4️⃣  INSPECCIONANDO CHROMADB...")
    try:
        db_path = BASE_DIR / "procesado-mx" / "basic-mx" / "chroma_db_basic"
        client = chromadb.PersistentClient(path=str(db_path))
        col = client.get_or_create_collection("langchain")
        
        # Buscar sin filtros para ver qué artículos existen
        print(f"   🔎 Buscando TODOS los artículos de '{titulo_normalizado}'...")
        all_docs = col.get(where={"titulo_documento": {"$eq": titulo_normalizado}})
        
        if all_docs and all_docs['metadatas']:
            print(f"   ✓ Encontrados {len(all_docs['metadatas'])} documentos")
            
            # Extraer números de artículos únicos
            articulos_disponibles = set()
            transitorio_values = set()
            
            for meta in all_docs['metadatas']:
                art = meta.get('Articulo')
                trans = meta.get('Transitorio')
                articulos_disponibles.add(str(art))
                transitorio_values.add(str(trans))
            
            print(f"\n   📊 Números de artículos disponibles:")
            print(f"      Total: {len(articulos_disponibles)}")
            arts_sorted = sorted(articulos_disponibles, key=lambda x: int(x) if x.isdigit() else float('inf'))
            
            # Mostrar información sobre el artículo que buscamos
            print(f"\n   🎯 Buscando artículo {articulo_num}:")
            found = False
            for meta in all_docs['metadatas']:
                if str(meta.get('Articulo')) == str(articulo_num):
                    found = True
                    print(f"      ✅ ENCONTRADO!")
                    print(f"         - Artículo: {meta.get('Articulo')} (tipo: {type(meta.get('Articulo')).__name__})")
                    print(f"         - Transitorio: '{meta.get('Transitorio')}'")
                    print(f"         - Otros campos: {list(meta.keys())}")
                    break
            
            if not found:
                print(f"      ❌ NO ENCONTRADO en ChromaDB")
                print(f"\n      Artículos disponibles (muestra):")
                for art in arts_sorted[:20]:
                    print(f"         - Artículo {art}")
            
            print(f"\n   🔍 Valores únicos de 'Transitorio':")
            for trans in sorted(transitorio_values):
                print(f"      - '{trans}'")
        else:
            print(f"   ❌ No se encontraron documentos para '{titulo_normalizado}'")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Main
print("\n" + "="*80)
print("🔍 DEBUG AVANZADO: LOGICA A - BÚSQUEDA POR ARTÍCULOS")
print("="*80)

queries = [
    "¿Qué dice el Artículo 16 de la Constitución?",
    "¿Qué dice el Artículo 3 de la Constitución?",
    "¿Qué dice el Artículo 7 de la Constitución?",
]

for q in queries:
    debug_articulo(q)

print(f"\n\n{'='*80}")
print("✅ Debug completado")
print("="*80)
