# BITÁCORA-REMAKE — Wall-E Legal 2.0 en Google Cloud

Bitácora del rehecho de la arquitectura de despliegue: nuevo entorno en Google Cloud,
imagen pesada + imagen ligera, y la app pública en internet.

- **Inicio:** 2026-10-12
- **Estado:** Fases 1–5 completas; **Fase 6 en curso** (servicio público desde el 2026-10-13).
  El detalle vive en `BITACORA-REMAKE-F<n>.md`; las secciones §1 y §3 de este archivo son el
  plan original y se conservan como referencia.
- **Regla:** el bucket se conserva íntegro: nada de este plan borra ni sobrescribe en él, y el
  acervo no se descarga al repo para probar.
- **Regla:** cada fase se ejecuta y verifica antes de pasar a la siguiente. Los comandos
  `gcloud` los ejecuta el responsable del proyecto, no Claude (ver `CLAUDE.md` §8).

---

## 0. Punto de partida (verificado el 2026-10-12)

| Pieza | Estado |
|---|---|
| Bucket `gs://chromadb-alma-juridica-aipp` | Ya tiene `procesado-mx/`, `faiss-lista/`, `modelo_e5/` (dicho por el responsable; falta medir tamaños, ver Fase 1). |
| `main.py` + `recursos.py` + `web/` | Probado en local con `TestClient`: `/`, `/web/app.js`, `/api/estado` y `/api/catalogo` responden 200; el catálogo devuelve 42 títulos. |
| Consultas reales (A, B, C) | **No probadas de punta a punta.** En local solo existe `basic-mx` y cada consulta cuesta una llamada a DeepSeek. |
| Modelo de embeddings | `./modelo_e5` es `multilingual-e5-large-instruct`, el mismo con el que `script_embeddings_*_55.py` generó los vectores. |
| Versiones que abren el acervo | Python 3.12.3, `chromadb==1.4.0`, `langchain-chroma==1.1.0` (venv local). Se fijan en producción. |
| Despliegue anterior | `protocolo01-app` (revisión 00013, 2026-04-29): `gcr.io/…/protocolo01-app:latest`, 2 vCPU / 4 GiB, rsync de todo (modelo incluido) al arrancar. Ver F1-13. |

### Problemas del esquema anterior que este rehecho corrige

1. **Memoria justa:** el servicio corre con 4 GiB (corregido en F1-13; antes se supuso 512 MiB). En Cloud Run el disco que se escribe vive en RAM: 2.1 GB del modelo descargados + ~2.5 GB del modelo cargado + Chroma rebasan o rozan los 4 GiB.
2. **Arranque lento y frágil:** `startup.sh` descargaba ~2.3 GB antes de abrir el puerto, y con `set -e` cualquier carpeta ausente (`procesado-unam`) tumbaba el contenedor.
3. ~~**Ruta del bucket:** `GCS_BUCKET_PATH` termina en `/`~~ Descartado en F1-13: el servicio real usa `gs://chromadb-alma-juridica-aipp` sin `/` final (la `/` solo estaba en las notas de `llamada_deepseek.txt`).
4. **Imagen sucia:** `COPY *.py` mete scripts de ingesta, pruebas y prototipos.
5. **Versiones sueltas:** `requirements.txt` sin versiones fijas; un `chromadb` distinto puede no abrir las bases ya generadas.
6. **Registro deprecado:** `gcr.io` (Container Registry) está deprecado en favor de Artifact Registry.
7. **Clave expuesta:** `llamada_deepseek.txt` guarda una clave de DeepSeek en texto plano.

---

## 1. Arquitectura objetivo

```
                    Internet
                       │  HTTPS (URL *.run.app o dominio propio)
                       ▼
        ┌──────────────────────────────────────┐
        │ Cloud Run: protocolo01-app-v2 (gen2)        │
        │  imagen LIGERA  ── FROM ──► PESADA   │
        │  ─ main.py, recursos.py, logica_*    │   Python 3.12 + deps fijas
        │  ─ utils_rag.py, catalogo_datos.py   │   + /app/modelo_e5 (2.2 GB, horneado)
        │  ─ web/                              │
        │  /mnt/acervo  (volumen GCS, solo lectura)
        └──────┬───────────────────────┬───────┘
               │ cp al arrancar        │ Secret Manager
               ▼                       ▼
   gs://chromadb-alma-juridica-aipp   DEEPSEEK_API_KEY
     procesado-mx/  faiss-lista/
```

### Decisiones de diseño

| Tema | Decisión | Por qué |
|---|---|---|
| **Imagen pesada** | `python:3.12-slim` + dependencias fijas + `modelo_e5` horneado. Se reconstruye solo cuando cambian `requirements.txt` o el modelo. | Los archivos de la imagen **no** consumen RAM de la instancia; lo que se descarga al arrancar, sí. El modelo casi nunca cambia. |
| **Imagen ligera** | `FROM` la pesada + solo los 7 módulos de ejecución + `web/` + `startup.sh`. Se reconstruye en cada cambio de código (segundos). | Despliegues rápidos; la imagen lleva solo lo que corre. |
| **Acervo (Chroma + FAISS)** | Se monta el bucket como volumen de Cloud Storage (solo lectura) en `/mnt/acervo` y `startup.sh` **copia** las carpetas necesarias a `/app`. | El acervo cambia sin redeploy. Se copia porque ChromaDB usa SQLite, que no funciona bien directo sobre FUSE. Así ya no hace falta `gcloud` dentro de la imagen. |
| **Qué se copia** | Solo las 6 carpetas `chroma_db_*` que usa `recursos.py` + `faiss-lista/`. **No** `procesado-unam` ni `modelo_e5`. | Lo copiado ocupa RAM: copiar solo lo necesario. |
| **Registro** | Artifact Registry `us-central1-docker.pkg.dev/<PROYECTO>/protocolo01-v2/…` | Reemplazo vigente de `gcr.io`. |
| **Secreto** | `DEEPSEEK_API_KEY` en Secret Manager, inyectado como variable de entorno. Clave **nueva** (la actual está expuesta). | No hay claves en el repo ni en la imagen. |
| **Identidades** | Una cuenta de servicio para ejecutar (`protocolo01-v2-run`) y otra para construir (`protocolo01-v2-build`), cada una con permisos mínimos. | Evita usar la cuenta de cómputo por defecto (rol Editor). |
| **Gradio** | Fuera de la imagen de producción (sin `gradio`, `flask`, `gunicorn`). `app.py` sigue en el repo para uso local. | `main.py` no importa `app.py`; Gradio 3.50.2 solo agrega peso. *(Decisión D4, a confirmar.)* |
| **Configuración del servicio** | Declarativa en `deploy/service.yaml` (`gcloud run services replace`). Los builds ligeros solo cambian la imagen. | Memoria, probes, volumen y secreto quedan versionados en un solo lugar. |

---

## 2. Decisiones pendientes (las toma el responsable)

| # | Pregunta | Recomendación |
|---|---|---|
| D1 | ¿Proyecto nuevo o el mismo `alma-juridica-aipp`? | **Decidido (2026-10-12): `alma-juridica-aipp`.** El servicio nuevo `protocolo01-app-v2` convive con `protocolo01-app`. |
| D2 | Región | **Decidido (F1): `us-central1`**, la misma del bucket y del servicio actual. |
| D3 | ¿Instancias mínimas 0 o 1? | **Decidido (F3-08): 0** (sin costo fijo; primera consulta lenta). Se reevalúa en F6-05 con el uso real, que es intermitente. |
| D4 | ¿Gradio en `/legacy` en producción? | **Decidido (F3-03): No.** |
| D5 | ¿Dominio propio? | Opcional; Fase 6. |
| D6 | ¿Límite de uso público? | **Decidido (F5-13): `maxScale: 2`** + límite de gasto en DeepSeek y alerta de presupuesto (P4, P18). Ver §6 (riesgos). |

---

## 2-bis. Pendientes abiertos

Lista única de pendientes. Se marca aquí cuando se cierran (y en la bitácora de la fase).

| # | Pendiente | Origen | Se resuelve en | Estado |
|---|---|---|---|---|
| P1 | Generar clave nueva de DeepSeek y agregarla como versión 2 del secreto `DEEPSEEK_API_KEY` | §0 punto 7 | F2-08 | ☑ versión 2 (2026-10-13) |
| P2 | Revisar los miembros IAM del proyecto (en especial si la cuenta de cómputo por defecto es Editor) | F1-12 | F2-02 | ☑ Sí es Editor → P13 |
| P3 | D3: instancias mínimas 0 o 1 | §2 | Fase 5 | ☑ **0** (F3-08): sin costo fijo; primera consulta lenta |
| P4 | D6: límite de uso público (costo de DeepSeek) | §2, §6 | Fase 5 / 6 | ☑ F5-13: `maxScale: 2` definitivo + límites externos (P18) |
| P5 | D4: confirmar Gradio fuera de producción | §2 | Fase 3 | ☑ Fuera (F3-03) |
| P6 | D5: ¿dominio propio? | §2 | Fase 6 | ☑ **No** (F5-14): se usa la URL `*.run.app`, gratuita |
| P7 | Crear `modelo_e5/2_Normalize/` vacía en la imagen pesada | F1-07 | Fase 3 (`Dockerfile.pesada`) | ☑ F3-06 |
| P8 | Cambios a `main.py` / `recursos.py` de §3.9 | §3.9 | **En pausa**: regla de no tocar el backend | ⏸ |
| P9 | Borrar el servicio `ia-legal-mexicana-web` (y decidir sus imágenes en `ia-legal-repo`) | F1-13 | §5 Limpieza | ☑ servicio, 2 jobs e `ia-legal-repo` borrados (2026-10-13, F6-09 A2/A3-bis/A4) |
| P10 | Borrar la clave vieja: revocarla en DeepSeek y deshabilitar la versión 1 del secreto, **después** de validar `protocolo01-app-v2` (el servicio viejo la sigue usando hasta entonces) | §0 punto 7 | §5 Limpieza | ☑ clave revocada (responsable) y v1 deshabilitada (2026-10-13, F6-09 A1/A3); v1 destruida (2026-10-16, B5) |
| P11 | Sacar la clave en texto plano de `llamada_deepseek.txt` | §0 punto 7 | §5 Limpieza || ☑ archivo borrado (2026-10-16, F6-09 C2) |
| P12 | Copias locales de `basic` y `faiss-lista` desactualizadas frente al bucket | F1-06, F1-08 | Informativo (regla: no se baja el acervo al repo) | — |
| P13 | Quitar `roles/editor` (y el `objectViewer` redundante) a la cuenta de cómputo por defecto `879901246493-compute@…`, cuando `protocolo01-app` e `ia-legal-mexicana-web` ya no la usen. **Ajuste 2026-10-16:** `protocolo01-app` queda dormido y sigue usando la cuenta; se quita solo `editor` y se conserva `objectViewer` (verificado que no lo rompe; F6-09) | F2-02 | §5 Limpieza | ☑ `editor` quitado (2026-10-16, F6-09 B4); `objectViewer` se conserva para la v1 dormida |
| P14 | Acotar `roles/run.developer` de `protocolo01-v2-build` del proyecto al servicio `protocolo01-app-v2` (hoy podría desplegar cualquier servicio, incluido `protocolo01-app`) | F2-07 | Fase 5, en cuanto exista el servicio | ☑ F5-11 (2026-10-13) |
| P15 | Decidir si se sube la rama `remake/protocolo01-v2` a GitHub (repo privado) | F3-14 | Cuando el responsable lo indique | ☑ Subida el 2026-10-13 (`origin/remake/protocolo01-v2`, con seguimiento) |
| P16 | Borrar el bucket `gs://mi-proyecto-axiomas` (4.79 MiB: `requirements.txt`, `legislacion-mx/`, `legislacion-unam/`, `scripts/`). Antes: confirmar que nada lo usa y decidir si se respalda su contenido | F5 (decisión del responsable, 2026-10-13) | §5 Limpieza || ☑ respaldado en `~/respaldos/mi-proyecto-axiomas/` y borrado (2026-10-16, F6-09 C1) |
| P17 | Cita Precisa no encuentra artículos en FCE: la colección guarda `titulo_documento` con acentos y `normalizar_titulo()` los quita. Muy probablemente preexistente (misma lógica y datos que `protocolo01-app`; no probado contra el servicio viejo). Caminos: reingestar FCE normalizado, o que `logica_a` pruebe ambas formas (cambio al núcleo) | F5-09 | Fuera del rehecho; decisión del responsable | ☐ |
| P18 | Configurar el límite de gasto en DeepSeek y una alerta de presupuesto en Google Cloud (Facturación → Presupuestos y alertas) | F5-13 | **El responsable**, antes de abrir al público (Fase 6) |☑ resuelto por el responsable (2026-10-13) |
| P19 | Límite de consultas por IP (no existe; la longitud de `query` sí está acotada a 4000 caracteres en `main.py:64`). Corregido el 2026-10-13: antes decía, por error, que faltaba el límite de longitud | Revisión de bitácoras (2026-10-13) | Junto con P8: requiere tocar `main.py` (o Cloud Armor) | ⏸ |
| P20 | Quitar la documentación pública de la API: `docs_url=None, openapi_url=None` en `main.py:34` (hoy `/api/docs` y `/openapi.json` responden 200) | F6-06 | En el próximo cambio a `main.py` (junto con P8/P19) | ⏸ |
| P21 | Liberar ~21 GB en la PC: borrar las imágenes y la caché de construcción locales de Docker Desktop (Fase 4; las de producción viven en Artifact Registry) y **compactar** `docker_data.vhdx` (no se encoge solo). Medido el 2026-10-13: 21.1 GB | Pregunta del responsable (2026-10-13) | Al terminar la Fase 6, con autorización | ☑ imágenes y caché borradas; `.vhdx` compactado de 21.1 a 3.27 GB (2026-10-16, F6-09 C4) |

---

## 3. Fases

> Plan original. Las casillas de esta sección no se actualizan: el avance real y sus datos
> están en `BITACORA-REMAKE-F1.md` … `BITACORA-REMAKE-F6.md` y en §7 (Registro).

### Fase 1 — Inventario del bucket (solo lectura)

```bash
export PROYECTO=<id-del-proyecto>
export REGION=us-central1
export BUCKET=chromadb-alma-juridica-aipp

gcloud storage buckets describe gs://$BUCKET --format="value(location)"
gcloud storage du -s -r gs://$BUCKET/procesado-mx/* gs://$BUCKET/faiss-lista gs://$BUCKET/modelo_e5
gcloud storage ls gs://$BUCKET/procesado-mx/*/
```

Verificar que existan exactamente estas rutas (las que lee `recursos.py`):

```
procesado-mx/basic-mx/chroma_db_basic
procesado-mx/segob-mx/chroma_db_segob
procesado-mx/transp-mx/chroma_db_transp
procesado-mx/3p-mx/chroma_db_3p
procesado-mx/fce-mx/chroma_db_fce
procesado-mx/tramites-mx/chroma_db_tramites_mx
faiss-lista/indice_titulos_leyes.faiss
faiss-lista/metadata_titulos_leyes.pkl
modelo_e5/   (con config.json, model.safetensors, modules.json…)
```

- [ ] Región del bucket anotada: ______
- [ ] Tamaño total de las 6 `chroma_db_*` + `faiss-lista`: ______ (define la memoria, Fase 5)
- [ ] Las 6 rutas existen

### Fase 2 — Crear el entorno en Google Cloud

```bash
gcloud config set project $PROYECTO

# APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com cloudresourcemanager.googleapis.com

# Registro de imágenes
gcloud artifacts repositories create protocolo01-v2 \
  --repository-format=docker --location=$REGION \
  --description="Imágenes de Wall-E Legal 2.0"

# Cuentas de servicio
gcloud iam service-accounts create protocolo01-v2-run   --display-name="protocolo01-v2: ejecución Cloud Run"
gcloud iam service-accounts create protocolo01-v2-build --display-name="protocolo01-v2: Cloud Build"
export SA_RUN=protocolo01-v2-run@$PROYECTO.iam.gserviceaccount.com
export SA_BUILD=protocolo01-v2-build@$PROYECTO.iam.gserviceaccount.com

# Secreto (clave NUEVA de DeepSeek; revocar la anterior en el panel de DeepSeek)
# El secreto ya existe (F1-13): se agrega una versión nueva, no se crea
printf '%s' '<CLAVE_NUEVA>' | gcloud secrets versions add DEEPSEEK_API_KEY --data-file=-
```

Permisos:

```bash
# protocolo01-v2-run: leer el bucket y el secreto
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA_RUN --role=roles/storage.objectViewer
gcloud secrets add-iam-policy-binding DEEPSEEK_API_KEY \
  --member=serviceAccount:$SA_RUN --role=roles/secretmanager.secretAccessor

# protocolo01-v2-build: leer el modelo del bucket, subir imágenes, desplegar y escribir logs
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA_BUILD --role=roles/storage.objectViewer
for ROL in roles/artifactregistry.writer roles/run.developer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROYECTO --member=serviceAccount:$SA_BUILD --role=$ROL
done
gcloud iam service-accounts add-iam-policy-binding $SA_RUN \
  --member=serviceAccount:$SA_BUILD --role=roles/iam.serviceAccountUser
```

> Si el bucket vive en otro proyecto, los `buckets add-iam-policy-binding` se ejecutan con
> permisos sobre ese proyecto; nada más cambia.

- [ ] APIs habilitadas
- [ ] Repositorio `protocolo01-v2` creado
- [ ] Cuentas `protocolo01-v2-run` y `protocolo01-v2-build` con sus roles
- [ ] Secreto creado con clave nueva; clave vieja revocada

### Fase 3 — Archivos del repo (propuestas, se aplican con luz verde una por una)

> **Aplicada (2026-10-13).** Los borradores de abajo quedaron como referencia histórica; la
> versión vigente es la del repo y el detalle de cada cambio está en `BITACORA-REMAKE-F3.md`.
> Diferencias principales: se agregó `constraints.txt`; `Dockerfile.pesada` usa
> `python:3.12-slim-bookworm` y comprueba imports y modelo en el build; `cloudbuild*.yaml`
> declaran `serviceAccount` y protegen versiones y servicio; `minScale: 0` y `maxScale: 2`.
> §3.9 (cambios a `main.py` / `recursos.py`) no se aplicó: P8 en pausa.

#### 3.1 `requirements.txt` (producción, versiones fijas)

Versiones tomadas del venv local que sí abre el acervo. `torch` se instala aparte en la
imagen pesada desde el índice CPU, así que no va aquí.

```text
# --- Servidor ---
fastapi==0.128.0
uvicorn[standard]==0.40.0
pydantic==2.12.5
requests==2.32.5
python-dotenv==1.2.1

# --- RAG ---
chromadb==1.4.0
pysqlite3-binary==0.5.4.post2
langchain-core==1.2.5
langchain-huggingface==1.2.0
langchain-chroma==1.1.0
sentence-transformers==5.2.0
transformers==4.57.3
huggingface-hub==0.36.0
faiss-cpu==1.13.2
numpy==1.26.4
```

> Por revisar antes de fijar: si `logica_*`/`utils_rag` importan algo de `langchain` o
> `langchain-community` en tiempo de ejecución (hoy no se ve en los imports). Las
> dependencias de ingesta (`python-docx`, `tqdm`, `pandas`, `langchain-text-splitters`)
> quedan en `requirements_local.txt`.

#### 3.2 `Dockerfile.pesada` (nuevo; reemplaza a `Dockerfile.base`)

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# libgomp1: lo requieren torch y faiss en CPU
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

# El modelo lo baja Cloud Build desde el bucket (paso previo); no viaja desde la PC
COPY modelo_e5/ /app/modelo_e5/
```

`HF_HUB_OFFLINE=1` garantiza que nunca intente bajar de Hugging Face en producción: si el
modelo falta, falla en lugar de descargar otro.

#### 3.3 `Dockerfile` (imagen ligera)

```dockerfile
ARG IMAGEN_PESADA
FROM ${IMAGEN_PESADA}

WORKDIR /app

# Solo lo que corre en producción
COPY main.py recursos.py logica_a.py logica_b.py logica_c.py utils_rag.py catalogo_datos.py ./
COPY web/ ./web/
COPY startup.sh ./

# Saltos de línea de Windows → Linux, sin instalar dos2unix
RUN sed -i 's/\r$//' startup.sh && chmod +x startup.sh

ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["./startup.sh"]
```

#### 3.4 `startup.sh`

```bash
#!/bin/bash
set -euo pipefail

# Volumen de Cloud Storage montado por Cloud Run (solo lectura)
ACERVO_DIR="${ACERVO_DIR:-/mnt/acervo}"
APP_DIR="/app"

# Solo lo que usa recursos.py. Se copia porque Chroma (SQLite) no trabaja bien sobre FUSE.
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
```

#### 3.5 `cloudbuild-pesada.yaml` (nuevo; se corre solo si cambian dependencias o modelo)

```yaml
substitutions:
  _REGION: us-central1
  _REPO: protocolo01-v2
  _BUCKET: chromadb-alma-juridica-aipp
  _VERSION_PESADA: v1

steps:
  - id: bajar-modelo
    name: gcr.io/google.com/cloudsdktool/cloud-sdk:slim
    entrypoint: bash
    args: ['-c', 'gcloud storage rsync gs://${_BUCKET}/modelo_e5 ./modelo_e5 -r']

  - id: construir-pesada
    name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - Dockerfile.pesada
      - -t
      - ${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-pesada:${_VERSION_PESADA}
      - .

images:
  - ${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-pesada:${_VERSION_PESADA}

options:
  machineType: E2_HIGHCPU_8
  diskSizeGb: 100
  logging: CLOUD_LOGGING_ONLY
timeout: 3600s
```

Versión explícita (`v1`, `v2`…) en lugar de `latest`: la ligera apunta a una pesada
concreta y un cambio de dependencias nunca entra sin querer.

#### 3.6 `cloudbuild.yaml` (imagen ligera + despliegue; cada cambio de código)

```yaml
substitutions:
  _REGION: us-central1
  _REPO: protocolo01-v2
  _SERVICIO: protocolo01-app-v2
  _VERSION_PESADA: v1

steps:
  - id: construir-ligera
    name: gcr.io/cloud-builders/docker
    args:
      - build
      - --build-arg
      - IMAGEN_PESADA=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-pesada:${_VERSION_PESADA}
      - -t
      - ${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-app:$BUILD_ID
      - .

  - id: subir-ligera
    name: gcr.io/cloud-builders/docker
    args: [push, '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-app:$BUILD_ID']

  # Solo cambia la imagen; memoria, volumen, secreto y probes vienen de deploy/service.yaml
  - id: desplegar
    name: gcr.io/google.com/cloudsdktool/cloud-sdk:slim
    entrypoint: gcloud
    args:
      - run
      - deploy
      - ${_SERVICIO}
      - --image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-app:$BUILD_ID
      - --region=${_REGION}

images:
  - ${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/protocolo01-v2-app:$BUILD_ID

options:
  logging: CLOUD_LOGGING_ONLY
```

#### 3.7 `deploy/service.yaml` (nuevo; configuración del servicio)

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: protocolo01-app-v2
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2   # requerido por el volumen GCS
        run.googleapis.com/startup-cpu-boost: "true"
        autoscaling.knative.dev/minScale: "0"            # D3: decidido 0 (F3-08)
        autoscaling.knative.dev/maxScale: "3"            # tope de costo (D6)
    spec:
      serviceAccountName: protocolo01-v2-run@PROYECTO.iam.gserviceaccount.com
      containerConcurrency: 10                           # F1-14
      timeoutSeconds: 600                                # el SSE de Razonamiento puede tardar
      containers:
        - image: us-central1-docker.pkg.dev/PROYECTO/protocolo01-v2/protocolo01-v2-app:INICIAL
          ports:
            - name: http1
              containerPort: 8080
          env:
            - name: ACERVO_DIR
              value: /mnt/acervo
            - name: DEEPSEEK_API_KEY
              valueFrom:
                secretKeyRef:
                  name: DEEPSEEK_API_KEY
                  key: latest
          resources:
            limits:
              cpu: "2"
              memory: 4Gi                                # F4-09 (antes 8Gi por F1-14)
          startupProbe:
            httpGet:
              path: /api/estado
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 30                         # hasta ~5 min para arrancar
          volumeMounts:
            - name: acervo
              mountPath: /mnt/acervo
      volumes:
        - name: acervo
          csi:
            driver: gcsfuse.run.googleapis.com
            readOnly: true
            volumeAttributes:
              bucketName: chromadb-alma-juridica-aipp
```

Memoria: modelo cargado (~2.5 GB) + acervo copiado (Fase 1) + margen para PyTorch y
concurrencia. 8 GiB es el punto de partida; por encima de 4 GiB Cloud Run exige al
menos 2 vCPU.

#### 3.8 `.gcloudignore` (lo que NO se sube a Cloud Build)

```text
.git/
.gitignore
.gcloudignore
.env
.venv/
venv/
__pycache__/
*.pyc
*:Zone.Identifier
llamada_deepseek.txt
modelo_e5/
procesado-mx/
procesado-unam/
faiss-lista/
Axiomas/
*.csv
docs/
```

(Corrige la línea pegada `descargar_modelo.py.git/` y excluye `Axiomas/`, que hoy sí se sube.)

#### 3.9 Cambios menores en código (no son del núcleo, pero se piden aparte)

| Archivo | Cambio | Motivo |
|---|---|---|
| `main.py` | Cargar el modelo y abrir las colecciones al arrancar (evento `lifespan`), antes de aceptar tráfico. | Hoy la carga es perezosa: la primera consulta tarda ~1 min y la probe de arranque pasa sin el modelo cargado. |
| `main.py` | Endpoint `/api/salud` barato (¿modelo cargado? ¿FAISS presente?) para la probe. | `/api/estado` sirve, pero cuenta documentos de cada colección en cada llamada. |
| `recursos.py` | El respaldo cuando falta `./modelo_e5` descarga `multilingual-e5-large` (sin `-instruct`), que **no** es el modelo de los vectores. Cambiarlo a error explícito. | Con otro modelo la búsqueda devuelve basura sin dar error. |
| `.dockerignore` | Quitar o ajustar: con `COPY` explícito en la ligera ya no protege nada, y no debe excluir `modelo_e5/` en la pesada. | Coherencia. |
| `Dockerfile.base` | Se elimina al aceptar `Dockerfile.pesada`. | Reemplazo. |

- [ ] 3.1 `requirements.txt` aprobado y aplicado
- [ ] 3.2 `Dockerfile.pesada`
- [ ] 3.3 `Dockerfile`
- [ ] 3.4 `startup.sh`
- [ ] 3.5 `cloudbuild-pesada.yaml`
- [ ] 3.6 `cloudbuild.yaml`
- [ ] 3.7 `deploy/service.yaml`
- [ ] 3.8 `.gcloudignore`
- [ ] 3.9 Cambios menores

### Fase 4 — Probar en local antes de subir

```bash
# Imagen pesada local (requiere ./modelo_e5 en disco)
docker build -f Dockerfile.pesada -t protocolo01-v2-pesada:local .

# Imagen ligera local
docker build --build-arg IMAGEN_PESADA=protocolo01-v2-pesada:local -t protocolo01-v2-app:local .

# Simular el volumen GCS con una carpeta local que tenga procesado-mx/ y faiss-lista/
docker run --rm -p 8080:8080 -m 8g \
  -e DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
  -v "$PWD":/mnt/acervo:ro \
  protocolo01-v2-app:local

curl -s localhost:8080/api/estado | python3 -m json.tool
curl -s localhost:8080/api/catalogo | head -c 300
```

- [ ] Arranca sin errores y abre lo que hay en local (hoy solo `basic`)
- [ ] `docker stats` muestra consumo de RAM con el modelo cargado: ______
- [ ] Una consulta manual por modo (cuesta DeepSeek; solo una por modo)

### Fase 5 — Construir y desplegar en la nube

```bash
# 1. Imagen pesada (solo la primera vez y cuando cambien deps o modelo)
gcloud builds submit --config cloudbuild-pesada.yaml \
  --service-account=projects/$PROYECTO/serviceAccounts/$SA_BUILD \
  --substitutions=_VERSION_PESADA=v1

# 2. Primera creación del servicio: subir una ligera y aplicar service.yaml
#    (sustituir PROYECTO e INICIAL en deploy/service.yaml por los valores reales)
gcloud run services replace deploy/service.yaml --region=$REGION

# 3. Despliegues siguientes: solo la ligera
gcloud builds submit --config cloudbuild.yaml \
  --service-account=projects/$PROYECTO/serviceAccounts/$SA_BUILD
```

Para la primera creación puede hacerse el paso 3 antes del 2 (sin el paso `desplegar`) y
usar el `BUILD_ID` resultante como imagen en `service.yaml`.

- [ ] Pesada `v1` en Artifact Registry
- [ ] Servicio creado; revisión lista
- [ ] Logs de arranque: las 6 carpetas copiadas, `🚀 Iniciando…`

### Fase 6 — Abrirla a internet

```bash
# Acceso público
gcloud run services add-iam-policy-binding protocolo01-app-v2 --region=$REGION \
  --member=allUsers --role=roles/run.invoker

gcloud run services describe protocolo01-app-v2 --region=$REGION --format="value(status.url)"
```

> Si la organización tiene la política *Domain Restricted Sharing*, `allUsers` es
> rechazado. Opciones: excepción en la política para este proyecto, o
> `gcloud run services update protocolo01-app-v2 --no-invoker-iam-check`.

Dominio propio (D5), dos caminos:
- **Mapeo de dominio de Cloud Run** (`gcloud beta run domain-mappings create`): sencillo, en vista previa y solo en algunas regiones.
- **Balanceador HTTPS externo + NEG serverless + certificado administrado:** más trabajo; permite Cloud Armor (límite de peticiones por IP) y CDN para `web/`.

- [ ] URL pública responde `/`
- [ ] `/api/estado`: las 6 bases `disponible: true`
- [ ] `/api/catalogo`: total de títulos esperado
- [ ] Una consulta por pestaña desde un navegador externo (Cita Precisa, Razonamiento con streaming visible, Catálogo)
- [ ] Probado en celular

---

## 4. Operación

| Tarea | Cómo |
|---|---|
| Cambio de código | `gcloud builds submit --config cloudbuild.yaml …` |
| Cambio de dependencias o modelo | Subir `_VERSION_PESADA` (v2…), construir pesada, luego ligera con la nueva versión. |
| Actualizar acervo | Subir al bucket y forzar nueva revisión (`gcloud run services update protocolo01-app-v2 --region=$REGION --update-labels=acervo=AAAAMMDD`) para que las instancias copien de nuevo. |
| Revertir | `gcloud run revisions list --service=protocolo01-app-v2 --region=$REGION` y `gcloud run services update-traffic protocolo01-app-v2 --to-revisions=<REV>=100 --region=$REGION` |
| Logs | `gcloud run services logs read protocolo01-app-v2 --region=$REGION --limit=100` |

---

## 5. Limpieza del esquema anterior (después de validar el nuevo)

- [ ] Borrar servicio viejo `protocolo01-app` (confirmar antes)
- [ ] **Borrar el bucket `gs://mi-proyecto-axiomas`** (P16; decidido el 2026-10-13). Antes: confirmar que ningún servicio ni script lo usa y decidir si se respalda. Comando: `gcloud storage rm --recursive gs://mi-proyecto-axiomas` (borra contenido y bucket; irreversible salvo el *soft delete* de 7 días)
- [ ] **Borrar el servicio `ia-legal-mexicana-web`** (decidido por el responsable el 2026-10-12; ver F1-13). Antes de borrar: confirmar que nadie use su URL y revisar si también se limpian sus imágenes en el repo `ia-legal-repo`. Comando: `gcloud run services delete ia-legal-mexicana-web --region=us-central1`
- [ ] Borrar imágenes `gcr.io/alma-juridica-aipp/protocolo01-*`
- [ ] Quitar `llamada_deepseek.txt` o dejarlo sin claves (comandos nuevos ya viven aquí)
- [ ] Actualizar `CLAUDE.md` §1/§5/§7 y `readme.md` con la arquitectura nueva
- [ ] Los sobrantes del bucket (`procesado-unam/`, `excep-mx/`, etc.) **se conservan**; no forman parte de esta limpieza
- [ ] Decidir el destino de `Dockerfile.base`, `GUIA_RAPIDA.sh`, prototipos (`rag_app_deepseek.py`, `rag_chat_segob_d.py`) y copias `index.html`/`app.css` de la raíz

---

## 6. Riesgos abiertos

1. **Costo de DeepSeek en un endpoint público.** Cualquiera puede disparar consultas. Mitigaciones: `maxScale` + `containerConcurrency` (ya en `service.yaml`), límite de longitud de `query` (4000 caracteres, ya en `main.py`), límite de consultas por IP (**no existe**, P19), límite de gasto en la cuenta de DeepSeek, y Cloud Armor si se usa balanceador.
2. **Compatibilidad de Chroma.** Si los datos del bucket se generaron con una versión distinta a `chromadb==1.4.0`, puede no abrirlos. F1-10 lo revisa leyendo solo los `chroma.sqlite3` en una carpeta temporal; la prueba completa ocurre en la nube (Fase 5, `/api/estado`).
3. ~~**RAM.** 8 GiB es una estimación~~ Resuelto: servicio a 4 GiB (F4-09); pico medido en la nube 22 % (F5).
4. **Arranque en frío** con `minScale: 0`: medido 38 s de arranque + 26 s de la primera consulta (F5). Con uso intermitente, casi cada visita lo sufre; se vigila en F6-05.
5. **Volumen GCS** requiere entorno gen2 (ya declarado).

---

## 7. Registro

| Fecha | Entrada |
|---|---|
| 2026-10-12 | Se crea la bitácora. Verificado en local: `main.py` sirve front y API (`/`, `/web/app.js`, `/api/estado`, `/api/catalogo` → 200; 42 títulos). Modelo local = `multilingual-e5-large-instruct`, coincide con los scripts de ingesta. Versiones del venv anotadas para fijar. No se ha modificado ningún archivo del proyecto ni ejecutado nada en Google Cloud. |
| 2026-10-12 | **Fase 1 completa** (detalle en `BITACORA-REMAKE-F1.md`): las 6 bases del bucket existen, son compatibles con `chromadb==1.4.0` y suman ≈163 MiB; modelo idéntico al local; 8 GiB / 2 vCPU / concurrencia 10 / us-central1. Correcciones en §0 (el servicio actual tiene 4 GiB y el bucket no tiene `/` final). |
| 2026-10-12 | Se agrega §2-bis con los pendientes abiertos (P1–P12). Inicia Fase 2 (`BITACORA-REMAKE-F2.md`). |
| 2026-10-13 | **Fase 2 completa** (detalle en `BITACORA-REMAKE-F2.md`): API `cloudresourcemanager`, repo `protocolo01-v2`, cuentas `protocolo01-v2-run`/`-build` con permisos mínimos, versión 2 del secreto. P1 y P2 cerrados; abiertos P13 y P14. Inicia Fase 3 (`BITACORA-REMAKE-F3.md`). |
| 2026-10-13 | **Fase 3 completa** (detalle en `BITACORA-REMAKE-F3.md`): `requirements.txt` + `constraints.txt` (entorno del venv reproducido exacto), `Dockerfile.pesada`, `Dockerfile`, `cloudbuild-pesada.yaml`, `cloudbuild.yaml`, `startup.sh`, `deploy/service.yaml`, `.gcloudignore`, `.dockerignore`. Decisiones: Gradio fuera, `minScale: 0`, `maxScale: 2` provisional, `E2_HIGHCPU_8` para la pesada. Cerrados P3, P5, P7. Inicia Fase 4 (`BITACORA-REMAKE-F4.md`). |
| 2026-10-13 | **Fase 4 completa** (detalle en `BITACORA-REMAKE-F4.md`): pesada local en 10.5 min con imports y modelo verificados; reproduce el venv exacto (110/110). Ligera en 4 s, solo con archivos de ejecución. Contenedor arranca en ~32 s; front, API, Cita Precisa (con y sin FAISS) y Razonamiento (streaming) funcionan; falla controladamente sin acervo. Memoria medida ~1.2 GiB (~3.3 GiB estimados en frío) → servicio a **4 GiB**. `constraints.txt` ajustado (95). Pendiente: confirmar paso a Fase 5. |
| 2026-10-13 | Paso a Fase 5 confirmado por el responsable. Se crea `BITACORA-REMAKE-F5.md` (14 mini-tareas). |
| 2026-10-13 | **Fase 5 completa** (detalle en `BITACORA-REMAKE-F5.md`): pesada `v1` (5 min 57 s, ~$0.09; 1.73 GiB) y ligera construidas en Cloud Build; servicio `protocolo01-app-v2` creado privado; las 6 bases reales abiertas (11 366 fragmentos), catálogo 45 títulos; General, Trámites SEGOB y Razonamiento ✅, Cita Precisa FCE ❌ (P17, preexistente); memoria pico 22 % de 4 GiB; arranque en frío 38 s + primera consulta 26 s; despliegue normal validado (rev. `00002-7f2`); `run.developer` acotado. Cerrados P4, P6, P14, P18. Inicia Fase 6 (`BITACORA-REMAKE-F6.md`). |
| 2026-10-13 | **Fase 6 en curso** (`BITACORA-REMAKE-F6.md`): F6-01 a F6-04 hechas. **`protocolo01-app-v2` es público** en `https://protocolo01-app-v2-879901246493.us-central1.run.app` y probado desde smartphone. Pausa del día; se retoma en F6-05 (logs de la primera hora pública). |
| 2026-10-13 | Revisión de bitácoras: estado, D3, D6, riesgos 1/3/4 al día; nota en §3 (plan original); nuevo P19 (límite de `query`). F6-05 redefinida como ventana acumulada desde la apertura (el uso real es intermitente). |
| 2026-10-13 | P19 corregido: el límite de longitud ya existía (4000); el hueco real es el límite por IP. Nuevo P20 (quitar `/api/docs` y `/openapi.json`, decisión F6-06). |
| 2026-10-13 | F6-07: `CLAUDE.md` actualizado a la arquitectura aplicada (aprobado por el responsable). Nuevo P21 (liberar ~21 GB de Docker Desktop al terminar la Fase 6). |
| 2026-10-13 | F6-09 etapa A completa: claves viejas revocadas (responsable), `ia-legal-mexicana-web` y 2 Cloud Run Jobs borrados, versión 1 del secreto deshabilitada, `ia-legal-repo` borrado (−51.7 GB). P9 cerrado. |
| 2026-10-16 | F6-09 etapa C completa (C1–C4): `mi-proyecto-axiomas` respaldado y borrado, repo limpio, Docker Desktop vaciado y `.vhdx` compactado (−17.84 GB). P11, P16 y P21 cerrados. |
