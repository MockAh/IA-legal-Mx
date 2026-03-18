#!/usr/bin/env python3
"""
Test completo de logica_a con la normalización - Versión mejorada con debugging
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

from utils_rag import (
    extraer_entidades_con_llm, 
    buscar_titulo_en_faiss, 
    normalizar_titulo
)

def test_articulo(query):
    """Test completo para una consulta específica"""
    print(f"\n{'='*80}")
    print(f"❓ QUERY: {query}")
    print(f"{'='*80}\n")
    
    # Step 1: Extraer entidades
    print("1️⃣  Extrayendo entidades...")
    entidades = extraer_entidades_con_llm(query)
    titulo_usuario = entidades.get("titulo_documento")
    articulo_num = entidades.get("Articulo")
    print(f"   ✓ Título: '{titulo_usuario}'")
    print(f"   ✓ Artículo: {articulo_num} (tipo: {type(articulo_num).__name__})")
    
    if not titulo_usuario or not articulo_num:
        print("   ❌ No se pudieron extraer entidades")
        return False
    
    # Step 2: Buscar en FAISS
    print("\n2️⃣  Buscando en FAISS...")
    embedding_fn = HuggingFaceEmbeddings(
        model_name="./modelo_e5", model_kwargs={'device': 'cpu'}
    )
    titulo_exacto = buscar_titulo_en_faiss(titulo_usuario, embedding_fn, k=1)
    print(f"   ✓ Encontrado: '{titulo_exacto}'")
    
    # Step 3: Normalizar
    print("\n3️⃣  Normalizando título...")
    titulo_normalizado = normalizar_titulo(titulo_exacto)
    print(f"   ✓ Normalizado: '{titulo_normalizado}'")
    
    # Step 4: Buscar en ChromaDB
    print("\n4️⃣  Buscando en ChromaDB con FILTRO EXACTO...")
    db_path = BASE_DIR / "procesado-mx" / "basic-mx" / "chroma_db_basic"
    client = chromadb.PersistentClient(path=str(db_path))
    col = client.get_or_create_collection("langchain")
    
    # Construir condiciones (como hace logica_a.py)
    condiciones = [
        {"titulo_documento": {"$eq": titulo_normalizado}},
        {"Articulo": {"$eq": articulo_num}},
        {"Transitorio": {"$eq": "Principal"}}
    ]
    
    print(f"   Filtros aplicados:")
    print(f"     - titulo_documento = '{titulo_normalizado}'")
    print(f"     - Articulo = {articulo_num}")
    print(f"     - Transitorio = 'Principal'")
    
    try:
        results = col.query(
            query_embeddings=[embedding_fn.embed_query(query)],
            where={"$and": condiciones},
            n_results=1
        )
        
        if results['documents'] and results['documents'][0]:
            doc = results['documents'][0][0]
            meta = results['metadatas'][0][0]
            
            print(f"\n   ✅ ENCONTRADO EL ARTÍCULO!")
            print(f"\n   📋 Ley: {meta.get('titulo_documento')}")
            print(f"   📄 Artículo: {meta.get('Articulo')}")
            print(f"   🏷️  Transitorio: '{meta.get('Transitorio')}'")
            print(f"\n   📖 Contenido:")
            print(f"   {doc[:200]}...")
            return True
        else:
            print(f"\n   ❌ No se encontró el artículo con filtros exactos\n")
            
            # DEBUGGING: Buscar SIN el filtro de Transitorio
            print(f"   🔍 DEBUG 1: Buscando SIN el filtro de Transitorio...")
            condiciones_sin_trans = [
                {"titulo_documento": {"$eq": titulo_normalizado}},
                {"Articulo": {"$eq": articulo_num}},
            ]
            
            results_debug1 = col.query(
                query_embeddings=[embedding_fn.embed_query(query)],
                where={"$and": condiciones_sin_trans},
                n_results=1
            )
            
            if results_debug1['documents'] and results_debug1['documents'][0]:
                meta_debug1 = results_debug1['metadatas'][0][0]
                print(f"      ✅ ENCONTRADO (sin filtro Transitorio)!")
                print(f"         Transitorio: '{meta_debug1.get('Transitorio')}'")
            else:
                print(f"      ❌ Tampoco se encuentra sin filtro Transitorio")
                
                # DEBUGGING: Buscar solo por número de artículo
                print(f"\n   🔍 DEBUG 2: Buscando solo por Artículo {articulo_num}...")
                all_with_art = col.get(where={"Articulo": {"$eq": articulo_num}})
                
                if all_with_art and all_with_art['metadatas']:
                    print(f"      ✅ Encontrados {len(all_with_art['metadatas'])} documentos con Artículo={articulo_num}:")
                    for i, meta in enumerate(all_with_art['metadatas'][:5]):
                        print(f"         {i+1}. Ley: {meta.get('titulo_documento')} | Transitorio: '{meta.get('Transitorio')}'")
                else:
                    print(f"      ❌ No hay documentos con Artículo={articulo_num}")
                    
                    # DEBUGGING: Ver qué artículos existen
                    print(f"\n   🔍 DEBUG 3: Listando todos los artículos disponibles...")
                    all_arts = col.get(where={"titulo_documento": {"$eq": titulo_normalizado}})
                    
                    if all_arts and all_arts['metadatas']:
                        articulos = set()
                        for meta in all_arts['metadatas']:
                            articulos.add(str(meta.get('Articulo')))
                        
                        arts_sorted = sorted(articulos, key=lambda x: int(x) if x.isdigit() else float('inf'))
                        print(f"      Artículos disponibles en '{titulo_normalizado}':")
                        print(f"      Total: {len(arts_sorted)}")
                        print(f"      Primeros 30: {', '.join(arts_sorted[:30])}")
                        
                        if articulo_num not in [str(x) for x in arts_sorted]:
                            print(f"\n      ⚠️  El Artículo {articulo_num} NO existe en la base de datos")
            
            return False
                    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Main
print("\n" + "="*80)
print("🧪 TEST AVANZADO: LOGICA A CON DEBUGGING")
print("="*80)

queries = [
    "¿Qué dice el Artículo 16 de la Constitución?",
    "¿Qué dice el Artículo 3 de la Constitución?",
    "¿Qué dice el Artículo 7 de la Constitución?",
]

resultados = []
for q in queries:
    resultado = test_articulo(q)
    resultados.append((q, "✅ ÉXITO" if resultado else "❌ FALLO"))

print(f"\n\n{'='*80}")
print("📊 RESUMEN")
print("="*80)
for query, resultado in resultados:
    print(f"{resultado} - {query}")
print("="*80)
