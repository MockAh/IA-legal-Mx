# CLAUDE.md — Wall-E Legal 2.0

Guía operativa para Claude Code en este repositorio. Léela completa antes de tocar cualquier archivo.

---

## 1. Qué es este proyecto

Agente de IA legal mexicana con arquitectura RAG. Responde consultas sobre legislación nacional recuperando fragmentos normativos de bases vectoriales y redactando con un LLM externo (DeepSeek).

- **Interfaz:** front propio (`web/`) servido por FastAPI (`main.py`) en `0.0.0.0:$PORT` (8080 por defecto). Gradio (`app.py`) queda solo para uso local; no está en la imagen de producción.
- **Vectores:** ChromaDB persistente, 6 colecciones bajo `procesado-mx/`.
- **Índice de títulos:** FAISS (`faiss-lista/`), usado para resolver nombres coloquiales de leyes contra el título exacto del acervo.
- **Embeddings:** `intfloat/multilingual-e5-large-instruct` (1024 dimensiones), el mismo con el que se generaron los vectores. En local vive en `./modelo_e5`; en producción va horneado en la imagen pesada (`/app/modelo_e5`).
- **LLM:** DeepSeek `deepseek-chat` vía HTTP, con y sin streaming.
- **Despliegue:** Cloud Build → Artifact Registry (`protocolo01-v2`) → Cloud Run `protocolo01-app-v2` (`us-central1`, público). Dos imágenes: pesada (dependencias + modelo) y ligera (código + front).

---

## 2. Estado del proyecto

**La migración de Gradio al front propio está hecha y en producción** desde el 2026-10-13
(rehecho `protocolo01-v2`; detalle en `docs/BITACORA-REMAKE*.md`).

El front tiene tres pestañas:

1. **Cita Precisa** — caja de consulta en modo fijo, con selector de base: `FCE`, `Trámites SEGOB`, `General`.
2. **Razonamiento Jurídico** — misma caja, mismo selector, respuesta en streaming con fundamentos numerados.
3. **Catálogo FAISS** — inventario completo del acervo indexado, agrupado por materia, con buscador y filtros.

**General** agrupa `basic-mx + transp-mx + 3p-mx`.

Pendientes abiertos: `docs/BITACORA-REMAKE.md` §2-bis. Destacan P17 (Cita Precisa no
encuentra artículos en FCE por acentos en los títulos) y los cambios en espera a `main.py` /
`recursos.py` (P8, P19, P20).

### Regla de oro

**No reescribas la lógica de negocio.** `logica_a.py`, `logica_b.py`, `logica_c.py`, `utils_rag.py` y `catalogo_axiomas.py` son el núcleo probado. `main.py` y `recursos.py` solo los exponen por HTTP. Si crees que una de esas funciones debe cambiar, dilo y espera confirmación antes de editarla.

---

## 3. Mapa del repositorio

```
main.py                     FastAPI: sirve web/ y la API JSON/SSE (punto de entrada de producción)
recursos.py                 Parche SQLite, rutas del acervo, bases del front, caché de modelo y colecciones
catalogo_datos.py           Catálogo como datos ({materia: [títulos]}) para /api/catalogo
web/                        Front de tres pestañas (index.html, app.css, app.js)
logica_a.py                 Cita Precisa: entidades → FAISS → Chroma filtrado (retorna str)
logica_b.py                 Razonamiento Jurídico: RAG + streaming (generador de str acumulado)
logica_c.py                 Trámites SEGOB: cruce segob + tramites (retorna str)
utils_rag.py                DeepSeek (stream y no-stream), normalizar_titulo, FAISS helpers
catalogo_axiomas.py         generar_catalogo() → Markdown del acervo (lo usa app.py)
app.py                      Interfaz Gradio, solo local (fuera de la imagen de producción)
init_faiss.py               Construye indice_titulos_leyes.faiss + metadata_titulos_leyes.pkl
descargar_modelo.py         Baja y cachea el modelo e5 en ./modelo_e5
script_embeddings_*.py      Ingesta por acervo (basic, segob, transp, 3p, fce, tramites, excep)

Dockerfile.pesada           Imagen pesada: Python 3.12 + deps fijas + modelo_e5 horneado
Dockerfile                  Imagen ligera: FROM pesada + 7 módulos + web/ + startup.sh
startup.sh                  Copia el acervo del volumen del bucket a /app y lanza main.py
cloudbuild-pesada.yaml      Construye la pesada (solo si cambian dependencias o modelo)
cloudbuild.yaml             Construye la ligera y despliega (cada cambio de código)
deploy/service.yaml         Configuración declarativa del servicio Cloud Run
requirements.txt            Dependencias de producción, con versiones fijas
constraints.txt             Versiones exactas de todo el árbol (reproduce el venv que abre el acervo)
requirements_local.txt      Dependencias de desarrollo local
docs/                       Guía de operación (OPERACION.md) y bitácoras del rehecho (BITACORA-REMAKE*.md)
```

`Dockerfile.base`, `GUIA_RAPIDA.sh`, los prototipos (`rag_app_deepseek.py`, `rag_chat_segob_d.py`) y las copias `index.html`/`app.css` de la raíz son del esquema anterior; su destino se decide en la limpieza (F6-09).

### Datos que NO viven en el repo

Viven en `gs://chromadb-alma-juridica-aipp`. En producción el bucket se monta en solo lectura
en `/mnt/acervo` y `startup.sh` **copia** a `/app` solo esto (Chroma escribe en
`chroma.sqlite3` al abrir, así que no se usa directo sobre el montaje):

```
procesado-mx/basic-mx/chroma_db_basic
procesado-mx/segob-mx/chroma_db_segob
procesado-mx/transp-mx/chroma_db_transp
procesado-mx/3p-mx/chroma_db_3p
procesado-mx/fce-mx/chroma_db_fce
procesado-mx/tramites-mx/chroma_db_tramites_mx    (colección: tramites_gob_mx, fallback: langchain)
faiss-lista/indice_titulos_leyes.faiss
faiss-lista/metadata_titulos_leyes.pkl
```

`modelo_e5/` va en la imagen pesada; `procesado-unam/` y el resto del bucket no se usan en producción.

Sin `faiss-lista/` fallan Cita Precisa y el catálogo (`startup.sh` aborta). Es la dependencia más frágil del sistema.

---

## 4. Mapeo base → colecciones

**Front y API** (`recursos.BASES` + `main.py`). Cualquier endpoint nuevo debe respetarlo:

| Base | Cita Precisa (`/api/consulta`, `logica_a`) | Razonamiento (`/api/consulta/stream`) |
|---|---|---|
| General | basic + transp + 3p | basic + transp + 3p (`logica_b`) |
| FCE | fce | fce (`logica_b`) |
| Trámites SEGOB | segob | segob + tramites (`logica_c`, respuesta completa, no streaming) |

**Gradio** (`obtener_colecciones_por_modo()` de `app.py`, solo local): Cita Precisa = basic + segob + transp + 3p + fce; Razonamiento = basic + segob + transp + 3p.

Las funciones de lógica reciben `(colecciones, embedding_function, query)`; `logica_c_avanzada` recibe `(col_segob, col_tramites, embedding_function, query)`.

---

## 5. Comandos

```bash
# Entorno local
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_local.txt

# Modelo de embeddings (una vez, ~2 GB)
python3 descargar_modelo.py

# Índice de títulos (requiere los PDFs/fuentes del acervo)
python3 init_faiss.py

# Levantar
python3 -u main.py                # FastAPI + front en http://localhost:8080
python3 -u app.py                 # Gradio (legado, solo local)

# Despliegue de código (lo ejecuta el responsable; ver §8)
gcloud builds submit --config cloudbuild.yaml
```

Pesada nueva (`_VERSION_PESADA`), acervo, configuración (`deploy/service.yaml` lleva el marcador `IMAGEN_INICIAL`: no se aplica directo), revertir o cerrar el servicio: **`docs/OPERACION.md`**.

Variables de entorno en local (`.env`, nunca versionado):

```
DEEPSEEK_API_KEY=...
PORT=8080
```

En producción `DEEPSEEK_API_KEY` sale de Secret Manager y `ACERVO_DIR=/mnt/acervo`, ambos declarados en `deploy/service.yaml`.

---

## 6. Convenciones y trampas conocidas

- **El parche de SQLite va primero.** `recursos.py` (y `app.py`) sustituyen `sqlite3` por `pysqlite3` antes de importar `chromadb`. Cualquier punto de entrada nuevo debe importar `recursos` primero o repetir ese bloque **antes** de importar chromadb, o ChromaDB falla en Cloud Run.
- **`main.py` no importa `app.py`** a propósito: dispararía `init_faiss` (su `sys.exit(1)` tumba el proceso) y construiría Gradio.
- **Gradio está anclado en 3.50.2** y solo se usa en local. No actualices sin pedirlo; la API de `gr.Chatbot` cambió en 4.x y `app.py` depende del formato `[[pregunta, respuesta]]`.
- **Versiones fijas.** `chromadb==1.4.0` es la versión que abre el acervo. Cambiar dependencias exige una pesada nueva (`_VERSION_PESADA`) y probarla antes.
- **Normalización de títulos.** Chroma guarda `titulo_documento` en minúsculas, sin acentos y con espacios. FAISS devuelve el título con guiones. Siempre pasa por `normalizar_titulo()` antes de filtrar en Chroma. Excepción conocida: FCE guarda títulos con acentos (P17).
- **La Constitución está hardcodeada** en `logica_a.py`: si la consulta contiene "constitucion" se fuerza el título exacto en lugar de usar FAISS. No lo quites sin una alternativa probada.
- **Metadato `Transitorio`.** Vale `"Principal"` para el articulado ordinario. Si la consulta menciona "transitorio", el filtro se invierte.
- **El modelo se carga una vez.** `recursos.py` cachea el modelo y los clientes de Chroma con candados para concurrencia. No instancies `HuggingFaceEmbeddings` dentro de un handler de request.
- **Streaming acumulado.** Cada evento `texto` del SSE trae el contenido completo hasta ese momento; el cliente reemplaza, no concatena.
- **Arranque en frío.** Con `minScale: 0`, una instancia apagada tarda ~47 s en servir la página y la primera consulta suma ~26 s de carga del modelo.
- **Costo de API.** Cada consulta en Cita Precisa dispara una llamada a DeepSeek solo para extraer entidades. No la pongas en bucles ni en pruebas automáticas sin limitar; el servicio es público.
- Código, comentarios, nombres de variables y mensajes al usuario **en español**.
- El texto normativo se presenta justificado, con sangría de primera línea, en serif. Esa convención tipográfica vive en `web/app.css` (y en el CSS de `app.py`: `.contenedor-legal`, `.parrafo-legal`).

---

## 7. Arquitectura aplicada

```
main.py                         FastAPI (uvicorn), lanzado por startup.sh
  GET  /                        → web/index.html
  GET  /web/*                   → estáticos del front
  GET  /api/estado              → disponibilidad de las 6 colecciones y FAISS (probe de arranque)
  GET  /api/catalogo            → JSON del acervo (catalogo_datos.py)
  POST /api/consulta            → {query, base}; Cita Precisa, respuesta completa
  POST /api/consulta/stream     → {query, base}; Razonamiento por SSE (Trámites SEGOB vía logica_c)
  GET  /api/docs, /openapi.json → documentación de la API; se quita en el próximo cambio a main.py (P20)
```

- `query` admite de 1 a 4000 caracteres. No hay límite de consultas por IP (P19).
- `catalogo_axiomas.py` no se modificó: `catalogo_datos.py` replica sus categorías y devuelve datos.
- Gradio no se monta en producción (decisión D4).

---

## 8. Cómo quiero que trabajes

- Antes de modificar un archivo del núcleo (o `main.py` / `recursos.py`), muéstrame el diff propuesto y espera luz verde.
- Un cambio a la vez, verificable corriendo la app. Nada de refactors masivos.
- Si una ruta de datos no existe en local, dilo explícitamente en lugar de simular la respuesta o crear datos de prueba silenciosamente.
- No inventes nombres de leyes, artículos ni rutas de archivos: si no está en el acervo, el sistema debe decir que no lo tiene.
- No agregues dependencias nuevas sin justificarlas.
- No subas nada a GCS ni ejecutes `gcloud builds submit` por tu cuenta. Cualquier cambio en Google Cloud requiere autorización explícita para ese paso; lo de solo lectura se puede hacer directo.
- Nunca borres nada del bucket `chromadb-alma-juridica-aipp` ni descargues el acervo al repo.
- Anota los resultados en la bitácora de la fase (`docs/BITACORA-REMAKE-F<n>.md`) y los pendientes en `docs/BITACORA-REMAKE.md` §2-bis.
- `.env`, `modelo_e5/`, `procesado-*/` y `faiss-lista/` nunca se versionan.
