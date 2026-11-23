# ⚖️ Asistente Legal Mexicano

**Español** · [English](README.en.md)

Agente RAG especializado en legislación mexicana (legislación básica, SEGOB, transparencia,
tres poderes, FCE) y trámites de gob.mx. Recupera fragmentos normativos de ChromaDB y redacta
con DeepSeek.

**En producción:** https://protocolo01-app-v2-879901246493.us-central1.run.app
(Cloud Run, `us-central1`). La primera visita tras un rato sin uso tarda ~1 min en cargar.

## Pestañas

1. **Cita Precisa** — recuperación literal de artículos.
2. **Razonamiento Jurídico** — respuesta en streaming con fundamentos numerados.
3. **Catálogo FAISS** — inventario del acervo, por materia.

Bases a elegir: **General** (básica + transparencia + tres poderes), **FCE** y **Trámites SEGOB**.

## Correr en local

Requiere **Python 3.12** (la versión de la imagen de producción); con otra, las dependencias
fijas pueden no instalarse.

```bash
python3 -m venv .venv && source .venv/bin/activate

# Producción (FastAPI + front): mismas versiones que la imagen
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -c constraints.txt

# Modelo de embeddings (una vez, ~2 GB): intfloat/multilingual-e5-large-instruct → ./modelo_e5
python3 descargar_modelo.py

# Clave de DeepSeek
echo "DEEPSEEK_API_KEY=..." > .env

python3 -u main.py        # http://localhost:8080
```

El acervo (`procesado-mx/`, `faiss-lista/`) **no está en el repo**: vive en el bucket
`gs://chromadb-alma-juridica-aipp`. Sin él, la app arranca pero `/api/estado` marca las bases
como no disponibles.

Para la interfaz Gradio de legado (`python3 -u app.py`) y los scripts de ingesta
(`script_embeddings_*.py`, `init_faiss.py`): `pip install -r requirements_local.txt`.
Si falta `faiss-lista/`, `app.py` arranca con una advertencia y sin búsqueda de títulos (Cita
Precisa no resuelve nombres de leyes).

## Desplegar

Lo ejecuta el responsable del proyecto. Cambio de código o del front:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Dependencias, modelo, acervo, configuración, revertir o cerrar el servicio: `docs/OPERACION.md`.

## Más información

- `CLAUDE.md` — arquitectura, mapa del repo y convenciones.
- `docs/BITACORA-REMAKE.md` — historia del despliegue y pendientes abiertos.
