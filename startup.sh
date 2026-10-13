#!/bin/bash
# startup.sh — Arranque del contenedor protocolo01-app-v2
# 1. Copia el acervo desde el volumen del bucket (solo lectura) a /app.
#    Se copia porque Chroma escribe en chroma.sqlite3 al abrirlo (F1-08).
# 2. Lanza main.py (uvicorn en $PORT).
set -euo pipefail

ACERVO_DIR="${ACERVO_DIR:-/mnt/acervo}"
APP_DIR="/app"

# Solo lo que usa recursos.py (F1-04, F1-11). El resto del bucket no se copia.
CARPETAS=(
  "procesado-mx/basic-mx/chroma_db_basic"
  "procesado-mx/segob-mx/chroma_db_segob"
  "procesado-mx/transp-mx/chroma_db_transp"
  "procesado-mx/3p-mx/chroma_db_3p"
  "procesado-mx/fce-mx/chroma_db_fce"
  "procesado-mx/tramites-mx/chroma_db_tramites_mx"
  "faiss-lista"
)

for carpeta in "${CARPETAS[@]}"; do
  origen="$ACERVO_DIR/$carpeta"
  if [ -d "$origen" ]; then
    echo "⬇️  Copiando $carpeta"
    mkdir -p "$APP_DIR/$(dirname "$carpeta")"
    cp -r "$origen" "$APP_DIR/$carpeta"
  else
    # No se aborta: /api/estado reporta el acervo faltante y el front lo deshabilita
    echo "⚠️  No existe $origen"
  fi
done

if [ ! -f "$APP_DIR/faiss-lista/metadata_titulos_leyes.pkl" ]; then
  echo "❌ Falta faiss-lista: Cita Precisa y el catálogo no pueden funcionar."
  exit 1
fi

echo "🚀 Iniciando Wall-E Legal 2.0..."
exec python3 -u main.py
