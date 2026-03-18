#!/usr/bin/env python3
"""
Script de inicialización para generar índices FAISS.
Se ejecuta automáticamente si los índices no existen.
"""

import os
import sys
import glob
import pickle
import json
import numpy as np
from pathlib import Path

# Verificar que FAISS esté instalado
try:
    import faiss
    print("✅ FAISS disponible")
except ImportError:
    print("❌ FAISS no está instalado. Instala con: pip install faiss-cpu")
    sys.exit(1)

from sentence_transformers import SentenceTransformer

# Configuración
BASE_DIR = Path(__file__).resolve().parent
CARPETA_AXIOMAS = BASE_DIR / "Axiomas"
CARPETA_FAISS = BASE_DIR / "faiss-lista"
MODELO_RUTA = BASE_DIR / "modelo_e5"
NORMALIZAR = True
INDICE_SALIDA = CARPETA_FAISS / "indice_titulos_leyes.faiss"
METADATA_SALIDA = CARPETA_FAISS / "metadata_titulos_leyes.pkl"
JSON_INSPECCION_SALIDA = CARPETA_FAISS / "inspeccion_base_datos.json"


def extraer_titulo_desde_nombre(nombre_archivo):
    """
    Extrae el título de la ley a partir del nombre del archivo.
    Formato esperado: aaaa-mm-dd_tipo_título_categoría.docx
    """
    base = os.path.splitext(nombre_archivo)[0]
    partes = base.split('_')
    if len(partes) >= 3:
        titulo = partes[2]
        return titulo
    else:
        return base


def guardar_inspeccion_json(titulos, metadatos, embeddings):
    """
    Guarda un archivo JSON con toda la información de la base de datos FAISS
    para inspección humana.
    """
    try:
        datos_inspeccion = {
            "titulo_documento": "Inspección de Base de Datos FAISS - Juez Scharseinegger",
            "total_documentos": len(titulos),
            "dimension_embeddings": embeddings.shape[1],
            "normalizados": NORMALIZAR,
            "documentos": []
        }
        
        # Agregar información de cada documento
        for idx, (titulo, metadata) in enumerate(zip(titulos, metadatos)):
            doc_info = {
                "indice": idx,
                "titulo": titulo,
                "nombre_archivo": metadata["nombre_archivo"],
                "ruta_original": metadata["ruta"],
                "embedding_dimensión": embeddings.shape[1],
                # Guardar primeros/últimos valores del embedding para verificación
                "embedding_resumen": {
                    "min": float(embeddings[idx].min()),
                    "max": float(embeddings[idx].max()),
                    "media": float(embeddings[idx].mean()),
                    "primeros_5_valores": embeddings[idx][:5].tolist(),
                    "ultimos_5_valores": embeddings[idx][-5:].tolist()
                }
            }
            datos_inspeccion["documentos"].append(doc_info)
        
        # Guardar JSON con indentación para legibilidad
        with open(JSON_INSPECCION_SALIDA, 'w', encoding='utf-8') as f:
            json.dump(datos_inspeccion, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Archivo de inspección JSON guardado: {JSON_INSPECCION_SALIDA}")
        return True
    except Exception as e:
        print(f"❌ Error guardando JSON de inspección: {e}")
        return False


def generar_indices_faiss():
    """Genera índices FAISS si no existen."""
    
    # Verificar que la carpeta Axiomas exista
    if not CARPETA_AXIOMAS.exists():
        print(f"❌ Carpeta {CARPETA_AXIOMAS} no encontrada.")
        return False
    
    # Buscar archivos .docx
    patron = str(CARPETA_AXIOMAS / "**" / "*.docx")
    archivos = glob.glob(patron, recursive=True)
    
    if not archivos:
        print(f"⚠️  No se encontraron archivos .docx en {CARPETA_AXIOMAS}")
        return False
    
    print(f"📄 Encontrados {len(archivos)} archivos .docx")
    
    # Extraer títulos y metadatos
    textos_para_indexar = []
    metadatos = []
    
    print(f"🔄 Procesando {len(archivos)} archivos con nueva estructura...")
    
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        base = os.path.splitext(nombre)[0]
        partes = base.split('_')
        
        # Según tu estructura: fecha[0]_tipo[1]_titulo[2]_categoria[3]
        if len(partes) >= 3:
            tipo = partes[1].replace('-', ' ')    # "Constitucion Politica"
            titulo = partes[2].replace('-', ' ')  # "Constitucion Politica de los Estados..."
            
            # 1. TEXTO PARA EL EMBEDDING: Combinamos Tipo + Título para FAISS
            # Esto es lo que el modelo comparará contra la duda del usuario
            texto_busqueda = f"{tipo} {titulo}"
            
            # 2. VALOR PARA CHROMADB: Guardamos el título original (con guiones)
            # para que normalizar_titulo() en logica_a.py siga funcionando
            titulo_original = partes[2]
            
            print(f"  ✓ Indexando: '{texto_busqueda}'")
        else:
            texto_busqueda = base
            titulo_original = base

        textos_para_indexar.append(texto_busqueda)
        metadatos.append({
            "ruta": ruta,
            "nombre_archivo": nombre,
            "titulo_extraido": titulo_original # Crucial para el match en Chroma
        })
    
    # Cargar modelo
    print(f"\n🤖 Cargando modelo desde {MODELO_RUTA}...")
    if not MODELO_RUTA.exists():
        print(f"❌ Carpeta de modelo {MODELO_RUTA} no encontrada.")
        return False
    try:
        model = SentenceTransformer(str(MODELO_RUTA))
        print("✅ Modelo cargado")
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        return False
    
    # Generar embeddings
    print("🔄 Generando embeddings...")
    try:
        embeddings = model.encode(textos_para_indexar, normalize_embeddings=NORMALIZAR, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
        print(f"✅ {len(embeddings)} embeddings generados")
    except Exception as e:
        print(f"❌ Error generando embeddings: {e}")
        return False
    
    # Crear índice FAISS
    print("📊 Creando índice FAISS...")
    try:
        dimension = embeddings.shape[1]
        if NORMALIZAR:
            index = faiss.IndexFlatIP(dimension)
        else:
            index = faiss.IndexFlatL2(dimension)
        
        index.add(embeddings)
        print(f"✅ Índice creado: {index.ntotal} vectores, dimensión {dimension}")
    except Exception as e:
        print(f"❌ Error creando índice: {e}")
        return False
    
    # Guardar índice y metadatos
    print(f"\n💾 Guardando índices...")
    try:
        # Crear carpeta faiss-lista si no existe
        CARPETA_FAISS.mkdir(parents=True, exist_ok=True)
        
        faiss.write_index(index, str(INDICE_SALIDA))
        with open(METADATA_SALIDA, 'wb') as f:
            pickle.dump(metadatos, f)
        print(f"✅ Índice guardado: {INDICE_SALIDA}")
        print(f"✅ Metadatos guardados: {METADATA_SALIDA}")
        
        # Guardar inspección JSON
        if guardar_inspeccion_json(textos_para_indexar, metadatos, embeddings):
            print(f"✅ Inspección JSON generada")
        
        return True
    except Exception as e:
        print(f"❌ Error guardando índices: {e}")
        return False


def main():
    """Punto de entrada principal."""
    print("=" * 60)
    print("🔧 Inicializador FAISS para Juez Scharseinegger")
    print("=" * 60)
    
    # Verificar si los índices ya existen
    if INDICE_SALIDA.exists() and METADATA_SALIDA.exists():
        print(f"\n✅ Índices FAISS ya existen. No es necesario regenerar.")
        print(f"   - {INDICE_SALIDA}")
        print(f"   - {METADATA_SALIDA}")
        return True
    
    print(f"\n⚠️  Índices FAISS no encontrados. Generando...")
    resultado = generar_indices_faiss()
    
    if resultado:
        print("\n" + "=" * 60)
        print("✅ ¡Inicialización completada exitosamente!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ Error durante la inicialización. Revisa los logs.")
        print("=" * 60)
        return False


if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
