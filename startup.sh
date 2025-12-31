#!/bin/bash
set -e

# 1. Sincronizar la carpeta MAESTRA (Incluye Segob y Trámites si están dentro)
echo "⬇️ Sincronizando carpeta 'procesado-mx' (Principal, Excep, Segob, Trámites)..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-mx ./procesado-mx -r

# 2. Sincronizar UNAM (Independiente)
echo "⬇️ Sincronizando carpeta 'procesado-unam'..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-unam ./procesado-unam -r

# 3. Descarga del Modelo
echo "🧠 Descargando modelo de IA soberano..."
gcloud storage rsync $GCS_BUCKET_PATH/modelo_e5 ./modelo_e5 -r

echo "🚀 Iniciando la aplicación web..."
python3 -u app.py