import os
import glob
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Configuración
CARPETA_AXIOMAS = "Axiomas"  # Ruta a la carpeta que contiene los archivos .docx
MODELO_EMBEDDINGS = "intfloat/multilingual-e5-large"  # Mismo modelo que usas en la app
NORMALIZAR = True  # Normalizar para similitud por coseno
INDICE_SALIDA = "indice_titulos_leyes.faiss"
METADATA_SALIDA = "metadata_titulos_leyes.pkl"

def extraer_titulo_desde_nombre(nombre_archivo):
    """
    Extrae el título de la ley a partir del nombre del archivo.
    Formato esperado: aaaa-mm-dd_tipo_título_categoria.docx
    El título es la tercera parte separada por guiones bajos.
    """
    # Quitar extensión .docx
    base = os.path.splitext(nombre_archivo)[0]
    partes = base.split('_')
    if len(partes) >= 3:
        # El título puede tener guiones, pero eso no importa, lo tomamos completo
        titulo = partes[2]
        return titulo
    else:
        # Si no cumple el formato, devolvemos el nombre completo como fallback
        return base

def main():
    # 1. Buscar todos los archivos .docx en la carpeta Axiomas
    patron = os.path.join(CARPETA_AXIOMAS, "*.docx")
    archivos = glob.glob(patron)
    if not archivos:
        print(f"No se encontraron archivos .docx en {CARPETA_AXIOMAS}")
        return

    print(f"Encontrados {len(archivos)} archivos .docx")

    # 2. Extraer títulos y guardar metadatos (ruta y título original)
    titulos = []
    metadatos = []  # lista de diccionarios con información útil
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        titulo = extraer_titulo_desde_nombre(nombre)
        titulos.append(titulo)
        metadatos.append({
            "ruta": ruta,
            "nombre_archivo": nombre,
            "titulo_extraido": titulo
        })
        print(f"Procesado: {nombre} -> {titulo}")

    # 3. Cargar modelo de embeddings
    print(f"Cargando modelo {MODELO_EMBEDDINGS}...")
    model = SentenceTransformer(MODELO_EMBEDDINGS)

    # 4. Generar embeddings para todos los títulos (en lote)
    print("Generando embeddings...")
    embeddings = model.encode(titulos, normalize_embeddings=NORMALIZAR, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')

    # 5. Crear índice FAISS
    dimension = embeddings.shape[1]
    if NORMALIZAR:
        # Usamos Inner Product (equivalente a coseno si los vectores están normalizados)
        index = faiss.IndexFlatIP(dimension)
    else:
        index = faiss.IndexFlatL2(dimension)  # Distancia euclidiana

    # Añadir vectores al índice
    index.add(embeddings)
    print(f"Índice FAISS creado con {index.ntotal} vectores, dimensión {dimension}")

    # 6. Guardar índice y metadatos
    faiss.write_index(index, INDICE_SALIDA)
    with open(METADATA_SALIDA, 'wb') as f:
        pickle.dump(metadatos, f)

    print(f"Índice guardado en {INDICE_SALIDA}")
    print(f"Metadatos guardados en {METADATA_SALIDA}")

    # Opcional: prueba rápida
    print("\n--- Prueba de búsqueda ---")
    texto_prueba = "Constitución Política"
    print(f"Buscando: {texto_prueba}")
    emb_prueba = model.encode([texto_prueba], normalize_embeddings=NORMALIZAR)
    emb_prueba = np.array(emb_prueba).astype('float32')
    distancias, indices = index.search(emb_prueba, k=3)
    for i, idx in enumerate(indices[0]):
        if idx != -1:
            print(f"  {i+1}: {titulos[idx]} (distancia: {distancias[0][i]:.4f})")
        else:
            print(f"  {i+1}: <ninguno>")

if __name__ == "__main__":
    main()