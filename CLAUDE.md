# CLAUDE.md — Wall-E Legal 2.0

Guía operativa para Claude Code en este repositorio. Léela completa antes de tocar cualquier archivo.

---

## 1. Qué es este proyecto

Agente de IA legal mexicana con arquitectura RAG. Responde consultas sobre legislación nacional recuperando fragmentos normativos de bases vectoriales y redactando con un LLM externo (DeepSeek).

- **Interfaz actual:** Gradio 3.50.2 (`app.py`), servida en `0.0.0.0:$PORT` (8080 por defecto).
- **Vectores:** ChromaDB persistente, 6 colecciones bajo `procesado-mx/`.
- **Índice de títulos:** FAISS (`faiss-lista/`), usado para resolver nombres coloquiales de leyes contra el título exacto del acervo.
- **Embeddings:** `intfloat/multilingual-e5-large`, cacheado localmente en `./modelo_e5` (1024 dimensiones).
- **LLM:** DeepSeek `deepseek-chat` vía HTTP, con y sin streaming.
- **Despliegue:** Cloud Build → Cloud Run. Imagen base + imagen de app (`Dockerfile.base` y `Dockerfile`).

---

## 2. Trabajo en curso

**Estamos reemplazando el frontend de Gradio por una interfaz HTML propia.** El backend no cambia salvo donde sea estrictamente necesario para exponerlo.

La propuesta visual aprobada ("plata grabada") tiene tres pestañas:

1. **Cita Precisa** — caja de consulta en modo fijo, con selector de base: `FCE`, `Trámites SEGOB`, `General`.
2. **Razonamiento Jurídico** — misma caja, mismo selector, respuesta en streaming con fundamentos numerados.
3. **Catálogo FAISS** — inventario completo del acervo indexado, agrupado por materia, con buscador y filtros.

El botón **General** es nuevo: agrupa `basic-mx + transp-mx + 3p-mx`, que hoy se consultan de forma implícita dentro de cada modo.

### Regla de oro

**No reescribas la lógica de negocio.** `logica_a.py`, `logica_b.py`, `logica_c.py`, `utils_rag.py` y `catalogo_axiomas.py` son el núcleo probado. El trabajo de frontend consiste en exponerlos por HTTP, no en reimplementarlos. Si crees que una de esas funciones debe cambiar, dilo y espera confirmación antes de editarla.

---

## 3. Mapa del repositorio

```
app.py                      Interfaz Gradio + enrutado modo → colecciones (punto de entrada)
logica_a.py                 Cita Precisa: entidades → FAISS → Chroma filtrado (retorna str)
logica_b.py                 Razonamiento Jurídico: RAG + streaming (generador de str acumulado)
logica_c.py                 Trámites SEGOB: cruce segob + tramites (retorna str)
utils_rag.py                DeepSeek (stream y no-stream), normalizar_titulo, FAISS helpers
catalogo_axiomas.py         generar_catalogo() → Markdown del acervo leyendo el .pkl de FAISS
init_faiss.py               Construye indice_titulos_leyes.faiss + metadata_titulos_leyes.pkl
descargar_modelo.py         Baja y cachea el modelo e5 en ./modelo_e5
script_embeddings_*.py      Ingesta por acervo (basic, segob, transp, 3p, fce, tramites, excep)
startup.sh                  Sincroniza datos desde GCS y lanza app.py (entrypoint de Cloud Run)
cloudbuild.yaml             Pipeline de build en dos capas con caché
requirements.txt            Dependencias de producción (Linux/Cloud Run)
requirements_local.txt      Dependencias de desarrollo local
```

### Datos que NO viven en el repo

Se sincronizan desde `$GCS_BUCKET_PATH` con `startup.sh`:

```
procesado-mx/basic-mx/chroma_db_basic
procesado-mx/segob-mx/chroma_db_segob
procesado-mx/transp-mx/chroma_db_transp
procesado-mx/3p-mx/chroma_db_3p
procesado-mx/fce-mx/chroma_db_fce
procesado-mx/tramites-mx/chroma_db_tramites_mx    (colección: tramites_gob_mx, fallback: langchain)
faiss-lista/indice_titulos_leyes.faiss
faiss-lista/metadata_titulos_leyes.pkl
procesado-unam/
modelo_e5/
```

Sin `faiss-lista/` fallan Cita Precisa y el catálogo. Es la dependencia más frágil del sistema.

---

## 4. Mapeo modo → colecciones

Definido en `obtener_colecciones_por_modo()` de `app.py`. Cualquier endpoint nuevo debe respetarlo:

| Modo / Base | Colecciones |
|---|---|
| Cita Precisa (actual) | basic + segob + transp + 3p + fce |
| Razonamiento Jurídico (actual) | basic + segob + transp + 3p |
| FCE | fce |
| Trámites SEGOB | segob (legal) + tramites (operativo) — ruta distinta, usa `logica_c` |
| **General** (nuevo) | basic + transp + 3p |

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
python3 -u app.py                 # Gradio en http://localhost:8080

# Despliegue
gcloud builds submit --config cloudbuild.yaml
```

Variables de entorno (`.env`, nunca versionado):

```
DEEPSEEK_API_KEY=...
GCS_BUCKET_PATH=gs://...
PORT=8080
```

---

## 6. Convenciones y trampas conocidas

- **El parche de SQLite va primero.** `app.py` sustituye `sqlite3` por `pysqlite3` antes de importar `chromadb`. Cualquier punto de entrada nuevo (FastAPI, worker, script) debe repetir ese bloque **antes** de importar chromadb, o ChromaDB falla en Cloud Run.
- **Gradio está anclado en 3.50.2.** No actualices sin pedirlo; la API de `gr.Chatbot` cambió en 4.x y el pipeline de eventos del `app.py` actual depende del formato de listas `[[pregunta, respuesta]]`.
- **Normalización de títulos.** Chroma guarda `titulo_documento` en minúsculas, sin acentos y con espacios. FAISS devuelve el título con guiones. Siempre pasa por `normalizar_titulo()` antes de filtrar en Chroma.
- **La Constitución está hardcodeada** en `logica_a.py`: si la consulta contiene "constitucion" se fuerza el título exacto en lugar de usar FAISS. No lo quites sin una alternativa probada.
- **Metadato `Transitorio`.** Vale `"Principal"` para el articulado ordinario. Si la consulta menciona "transitorio", el filtro se invierte.
- **El modelo se carga una vez.** `RECURSOS_CACHE` es un singleton para concurrencia; los clientes de Chroma también se cachean por ruta. No instancies `HuggingFaceEmbeddings` dentro de un handler de request.
- **Costo de API.** Cada consulta en Cita Precisa dispara una llamada a DeepSeek solo para extraer entidades. No la pongas en bucles ni en pruebas automáticas sin limitar.
- Código, comentarios, nombres de variables y mensajes al usuario **en español**.
- El texto normativo se presenta justificado, con sangría de primera línea, en serif. Esa convención tipográfica ya existe en el CSS de `app.py` (`.contenedor-legal`, `.parrafo-legal`) y se conserva en el front nuevo.

---

## 7. Arquitectura objetivo del frontend

Plan preferido, a confirmar antes de ejecutar:

```
main.py                     FastAPI: sirve el front estático + API JSON/SSE
  GET  /                    → web/index.html
  POST /api/consulta        → {modo, base, query} ; Cita Precisa y Trámites (respuesta completa)
  GET  /api/consulta/stream → SSE para Razonamiento Jurídico
  GET  /api/catalogo        → JSON del acervo (no Markdown)
web/index.html              Front de tres pestañas
web/app.css
web/app.js
app.py                      Se conserva; Gradio puede montarse en /legacy durante la transición
```

Cambio necesario en `catalogo_axiomas.py`: extraer una función que devuelva la estructura de datos (`{materia: [títulos]}`) y dejar `generar_catalogo()` como envoltorio que la formatea a Markdown. Así el front consume JSON y Gradio sigue funcionando sin cambios.

`startup.sh` cambia su última línea a lanzar `main.py` (uvicorn) cuando la migración esté lista; hasta entonces, no lo toques.

---

## 8. Cómo quiero que trabajes

- Antes de modificar un archivo del núcleo, muéstrame el diff propuesto y espera luz verde.
- Un cambio a la vez, verificable corriendo la app. Nada de refactors masivos.
- Si una ruta de datos no existe en local, dilo explícitamente en lugar de simular la respuesta o crear datos de prueba silenciosamente.
- No inventes nombres de leyes, artículos ni rutas de archivos: si no está en el acervo, el sistema debe decir que no lo tiene.
- No agregues dependencias nuevas sin justificarlas.
- No subas nada a GCS ni ejecutes `gcloud builds submit` por tu cuenta.
- `.env`, `modelo_e5/`, `procesado-*/` y `faiss-lista/` nunca se versionan.
