# ⚖️ Mexican Legal Assistant

[Español](README.md) · **English**

RAG agent specialized in Mexican legislation (core federal law, SEGOB, transparency, the three
branches of government, FCE) and gob.mx government procedures. It retrieves normative passages
from ChromaDB and drafts answers with DeepSeek. The interface and answers are in Spanish.

**In production:** https://protocolo01-app-v2-879901246493.us-central1.run.app
(Cloud Run, `us-central1`). The first visit after a period of inactivity takes ~1 min to load.

## Tabs

1. **Cita Precisa** (Exact Citation) — literal retrieval of articles.
2. **Razonamiento Jurídico** (Legal Reasoning) — streamed answer with numbered legal grounds.
3. **Catálogo FAISS** (FAISS Catalog) — inventory of the indexed corpus, grouped by subject.

Selectable bases: **General** (core + transparency + three branches), **FCE** and
**Trámites SEGOB** (SEGOB procedures).

## Run locally

Requires **Python 3.12** (the version used by the production image); with other versions the
pinned dependencies may fail to install.

```bash
python3 -m venv .venv && source .venv/bin/activate

# Production (FastAPI + front end): same versions as the image
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -c constraints.txt

# Embedding model (once, ~2 GB): intfloat/multilingual-e5-large-instruct → ./modelo_e5
python3 descargar_modelo.py

# DeepSeek key
echo "DEEPSEEK_API_KEY=..." > .env

python3 -u main.py        # http://localhost:8080
```

The corpus (`procesado-mx/`, `faiss-lista/`) **is not in the repo**: it lives in the bucket
`gs://chromadb-alma-juridica-aipp`. Without it the app starts, but `/api/estado` reports the
bases as unavailable.

For the legacy Gradio interface (`python3 -u app.py`) and the ingestion scripts
(`script_embeddings_*.py`, `init_faiss.py`): `pip install -r requirements_local.txt`.
If `faiss-lista/` is missing, `app.py` starts with a warning and without title search
(Cita Precisa cannot resolve law names).

## Deploy

Run by the project owner. For code or front-end changes:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Dependencies, model, corpus, configuration, rollback or shutting down the service:
`docs/OPERACION.md`.

## More information (in Spanish)

- `CLAUDE.md` — architecture, repository map and conventions.
- `docs/BITACORA-REMAKE.md` — deployment history and open issues.
