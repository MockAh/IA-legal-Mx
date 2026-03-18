#!/usr/bin/env python3
"""
Test de la función normalizar_titulo
"""
from utils_rag import normalizar_titulo

print("=" * 80)
print("🧪 TESTEO DE FUNCIÓN normalizar_titulo()")
print("=" * 80)

test_cases = [
    "Constitucion-Politica-de-los-Estados-Unidos-Mexicanos",
    "LEY-DE-AMPARO-REGLAMENTARIA-DE-LOS-ARTÍCULOS-103-Y-107-DE-LA-CONSTITUCIÓN-POLÍTICA",
    "LEY-ORGÁNICA-DEL-PODER-JUDICIAL-DE-LA-FEDERACIÓN",
    "Constitucion-Politica-de-la-Ciudad-de-Mexico",
]

expected_titles = [
    "constitucion politica de los estados unidos mexicanos",
    "ley de amparo reglamentaria de los articulos 103 y 107 de la constitucion politica",
    "ley organica del poder judicial de la federacion",
    "constitucion politica de la ciudad de mexico",
]

print("\n1️⃣  ANTES (FAISS) vs DESPUÉS (normalizado):")
for i, (title, expected) in enumerate(zip(test_cases, expected_titles)):
    normalized = normalizar_titulo(title)
    match = "✅" if normalized == expected else "❌"
    print(f"\n{match} Test {i+1}:")
    print(f"   ANTES  : {title}")
    print(f"   DESPUÉS: {normalized}")
    if normalized != expected:
        print(f"   ESPERADO: {expected}")

# Test con títulos de ChromaDB
print("\n\n2️⃣  TÍTULOS REALES DE CHROMADB:")
chroma_titles = [
    "constitucion politica de los estados unidos mexicanos",
    "constitucion politica de la ciudad de mexico",
    "codigo penal federal",
]

faiss_titles = [
    "Constitucion-Politica-de-los-Estados-Unidos-Mexicanos",
    "Constitucion-Politica-de-la-Ciudad-de-Mexico",
    "CODIGO-PENAL-FEDERAL",
]

print("\nComparando FAISS normalizado vs ChromaDB original:")
for faiss_title, chroma_title in zip(faiss_titles, chroma_titles):
    normalized_faiss = normalizar_titulo(faiss_title)
    match = "✅" if normalized_faiss == chroma_title else "❌"
    print(f"{match} {normalized_faiss} == {chroma_title}")

print("\n" + "=" * 80)
