#!/usr/bin/env python3
"""
Test rápido: Inspeccionar qué artículos existen en ChromaDB
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

from utils_rag import normalizar_titulo

titulo_original = "Constitucion-Politica-de-los-Estados-Unidos-Mexicanos"
titulo_normalizado = normalizar_titulo(titulo_original)

print("=" * 80)
print("🔎 INSPECCIÓN RÁPIDA: ¿QUÉ ARTÍCULOS EXISTEN EN CHROMADB?")
print("=" * 80)

print(f"\nBuscando artículos de: '{titulo_normalizado}'")

db_path = BASE_DIR / "procesado-mx" / "basic-mx" / "chroma_db_basic"
client = chromadb.PersistentClient(path=str(db_path))
col = client.get_or_create_collection("langchain")

# Obtener TODOS los documentos de la Constitución
all_docs = col.get(where={"titulo_documento": {"$eq": titulo_normalizado}})

if all_docs and all_docs['metadatas']:
    print(f"\n✅ Total de documentos encontrados: {len(all_docs['metadatas'])}")
    
    # Extraer información
    articulos_info = {}
    for meta in all_docs['metadatas']:
        art_num = meta.get('Articulo')
        art_trans = meta.get('Transitorio')
        
        if art_num not in articulos_info:
            articulos_info[art_num] = []
        articulos_info[art_num].append(art_trans)
    
    # Mostrar resumen
    print(f"\n📊 RESUMEN POR ARTÍCULO:")
    print(f"{'Artículo':<10} {'Principal':<15} {'Transitorios':<30}")
    print("-" * 55)
    
    for art in sorted(articulos_info.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
        transitorio_vals = articulos_info[art]
        has_principal = "Principal" in transitorio_vals
        trans_count = len([x for x in transitorio_vals if x != "Principal"])
        
        principal_str = "✅" if has_principal else "❌"
        trans_str = f"{trans_count} trans." if trans_count > 0 else "ninguno"
        
        print(f"{art:<10} {principal_str:<15} {trans_str:<30}")
    
    # Buscar artículos específicos
    print(f"\n\n🔍 BÚSQUEDA ESPECÍFICA:")
    articulos_buscar = [3, 7, 16]
    
    for art_num in articulos_buscar:
        print(f"\n  Artículo {art_num}:")
        
        # Buscar con filtro exacto Principal
        found_principal = False
        found_other = []
        
        for meta in all_docs['metadatas']:
            if str(meta.get('Articulo')) == str(art_num):
                if meta.get('Transitorio') == "Principal":
                    found_principal = True
                else:
                    found_other.append(meta.get('Transitorio'))
        
        if found_principal:
            print(f"    ✅ EXISTE como 'Principal'")
        else:
            print(f"    ❌ NO existe como 'Principal'")
        
        if found_other:
            print(f"    ⚠️  Existe como transitorio: {', '.join(found_other)}")
        elif not found_principal:
            print(f"    ❌ NO existe en ningún formato")
            
else:
    print(f"❌ No se encontraron documentos para '{titulo_normalizado}'")

print("\n" + "=" * 80)
