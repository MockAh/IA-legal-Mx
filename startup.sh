#!/bin/bash
set -e

# 1. Sincronizar la carpeta de Vectores (ChromaDB)
echo "⬇️ Sincronizando carpeta 'procesado-mx'..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-mx ./procesado-mx -r

# 2. CRÍTICO: Sincronizar el Índice de Títulos (FAISS)
# Sin esto, el catálogo y la Lógica A fallarán.
echo "⬇️ Sincronizando carpeta 'faiss-lista'..."
gcloud storage rsync $GCS_BUCKET_PATH/faiss-lista ./faiss-lista -r

# 3. Sincronizar UNAM (Independiente)
echo "⬇️ Sincronizando carpeta 'procesado-unam'..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-unam ./procesado-unam -r

# 4. Descarga del Modelo de Embeddings (Caché local)
echo "🧠 Descargando modelo de IA..."
gcloud storage rsync $GCS_BUCKET_PATH/modelo_e5 ./modelo_e5 -r

echo "🚀 Iniciando Wall-E Legal 2.0..."
# El flag -u asegura que los logs se vean en tiempo real en Google Cloud
python3 -u main.py          # antes: python3 -u app.py