# BITÁCORA-REMAKE-F3 — Fase 3: archivos de despliegue del repo

Desglose de la **Fase 3** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** completada (2026-10-13). Fase 4 autorizada.
- **Objetivo:** dejar en el repo los archivos que construyen la imagen pesada, la imagen ligera
  y la configuración del servicio `protocolo01-app-v2`. **No se construye ni se despliega nada**
  (Fase 4 prueba en local, Fase 5 en la nube). Los borradores de partida están en
  `BITACORA-REMAKE.md` §3.

## Reglas de esta fase

1. **No se toca la lógica del backend.** Fuera de alcance: `main.py`, `recursos.py`,
   `catalogo_datos.py`, `logica_a.py`, `logica_b.py`, `logica_c.py`, `utils_rag.py`,
   `catalogo_axiomas.py`, `app.py` y `web/`. Las imágenes los copian tal como están.
2. **Un archivo por mini-tarea.** Claude muestra el diff propuesto, el responsable da luz verde,
   y solo entonces se escribe (`CLAUDE.md` §8).
3. **Nada en Google Cloud cambia** en esta fase. No se ejecuta `gcloud builds submit`.
4. **El servicio viejo no se rompe.** `protocolo01-app` usa imágenes ya construidas en `gcr.io`;
   cambiar estos archivos no le afecta. Los archivos viejos quedan en el historial de git.
5. **El bucket se conserva tal cual** y el acervo no se descarga al repo.
6. Cada mini-tarea termina con su casilla marcada y sus datos anotados.

## Punto de partida (2026-10-13)

| Pieza | Estado |
|---|---|
| Rama de git | `master`, con cambios sin confirmar (los que ya había al empezar el rehecho) |
| Archivos actuales | `Dockerfile`, `Dockerfile.base`, `cloudbuild.yaml`, `startup.sh`, `requirements.txt`, `.gcloudignore`, `.dockerignore` |
| Carpeta `deploy/` | No existe |
| Docker en WSL | **No disponible**: Docker Desktop está instalado en Windows, pero falta activar la integración con WSL (afecta a F3-13 y a la Fase 4) |
| Versiones de referencia | Python 3.12.3 y paquetes del `venv/` local, que ya abren el acervo (F1-10) |

---

## Resumen de mini-tareas

| # | Mini-tarea | Quién | Cambia archivos | Estado |
|---|---|---|---|---|
| F3-01 | Punto de control en git (rama de trabajo) | Tú decides; Claude ejecuta | Git | ☑ |
| F3-02 | Inventario de imports en ejecución (solo lectura) | Claude | No | ☑ |
| F3-03 | Decidir P5: Gradio fuera de producción | **Tú** | No | ☑ |
| F3-04 | `requirements.txt` de producción, con versiones fijas | Claude propone, tú apruebas | Sí | ☑ |
| F3-05 | Validar que `requirements.txt` resuelve (sin instalar) | Claude | No | ☑ |
| F3-05b | `constraints.txt` (nuevo): fija las dependencias indirectas | Claude propone, tú apruebas | Sí | ☑ |
| F3-06 | `Dockerfile.pesada` (nuevo; incluye P7) | Claude propone, tú apruebas | Sí | ☑ |
| F3-07 | `cloudbuild-pesada.yaml` (nuevo) | Claude propone, tú apruebas | Sí | ☑ |
| F3-08 | `startup.sh` | Claude propone, tú apruebas | Sí | ☑ |
| F3-09 | `Dockerfile` (imagen ligera) | Claude propone, tú apruebas | Sí | ☑ |
| F3-10 | `cloudbuild.yaml` (ligera + despliegue) | Claude propone, tú apruebas | Sí | ☑ |
| F3-11 | `deploy/service.yaml` (nuevo) | Claude propone, tú apruebas | Sí | ☑ |
| F3-12 | `.gcloudignore` y `.dockerignore` | Claude propone, tú apruebas | Sí | ☑ |
| F3-13 | Revisión estática de todo lo escrito | Claude | No | ☑ |
| F3-14 | Cierre: confirmar cambios en git y paso a Fase 4 | Tú decides | Git | ☑ |

Total estimado: **~3.5 h**.

---

## F3-01 — Punto de control en git (rama de trabajo)

**Objetivo:** trabajar en una rama aparte, para poder comparar o volver atrás sin tocar `master`.

Hay cambios sin confirmar desde antes del rehecho (front nuevo, `main.py`, `recursos.py`,
`catalogo_datos.py`, `web/`, `CLAUDE.md`, bitácoras, etc.). Opciones:

| Opción | Qué hace |
|---|---|
| A (recomendada) | Crear la rama `remake/protocolo01-v2` y **confirmar ahí** el estado actual como punto de partida; los cambios de la F3 van en confirmaciones aparte |
| B | Crear la rama sin confirmar nada; todo se confirma al final (F3-14) |
| C | Seguir en `master` sin rama |

```bash
git switch -c remake/protocolo01-v2
# Solo con la opción A, revisando antes qué entra (excluye *:Zone.Identifier):
git status --short
```

**Hecho cuando:** se eligió una opción y se aplicó.

| Dato | Valor |
|---|---|
| Opción elegida | A |
| Rama | `remake/protocolo01-v2` (desde `master` en `bc50d0e`) |
| Confirmación de partida | `65601b2` — 24 archivos (front, servidor FastAPI, CLAUDE.md, bitácoras, cambios previos). Excluidos los 17 `*:Zone.Identifier`. Sin claves `sk-` en lo confirmado. `master` sin cambios. |

---

## F3-02 — Inventario de imports en ejecución (solo lectura)

**Objetivo:** saber exactamente qué paquetes importan los 7 módulos que llevará la imagen
ligera (`main.py`, `recursos.py`, `catalogo_datos.py`, `logica_a.py`, `logica_b.py`,
`logica_c.py`, `utils_rag.py`), para que `requirements.txt` tenga todo lo necesario y nada más.

```bash
grep -hE '^\s*(import|from) ' main.py recursos.py catalogo_datos.py logica_a.py logica_b.py logica_c.py utils_rag.py | sort -u
./venv/bin/pip show langchain-huggingface chromadb | grep -E '^(Name|Requires)'
```

**Hecho cuando:** la tabla está llena.

| Paquete (pip) | Import | Lo importa | Versión en el venv | Nota |
|---|---|---|---|---|
| `fastapi` | `fastapi` | main | 0.128.0 | Trae `starlette` |
| `pydantic` | `pydantic` | main | 2.12.5 | |
| `uvicorn[standard]` | `uvicorn` | main | 0.40.0 | |
| `chromadb` | `chromadb` | recursos | 1.4.0 | |
| `pysqlite3-binary` | `__import__("pysqlite3")` | recursos | 0.5.4.post2 | **Import dinámico** con respaldo silencioso: si falta, no hay error visible |
| `python-dotenv` | `dotenv` | recursos | 1.2.1 | |
| `langchain-huggingface` | `langchain_huggingface` | recursos | 1.2.0 | Requiere `huggingface-hub`, `langchain-core`, `tokenizers` |
| `sentence-transformers` | (indirecto) | `HuggingFaceEmbeddings` | 5.2.0 | **No** lo declara `langchain-huggingface`, pero lo usa al instanciar: va explícito. Trae `transformers`, `torch`, `scipy`, `scikit-learn` |
| `torch` (CPU) | (indirecto) | sentence-transformers | 2.9.1 | Se instala aparte, índice CPU |
| `faiss-cpu` | `faiss` | utils_rag | 1.13.2 | **Import con respaldo silencioso**: si falta, Cita Precisa no encuentra leyes sin error visible |
| `numpy` | `numpy` | utils_rag | 1.26.4 | |
| `requests` | `requests` | utils_rag | 2.32.5 | Llamadas a DeepSeek |
| — | `json`, `os`, `sys`, `pickle`, `threading`, `unicodedata`, `functools`, `pathlib`, `typing` | varios | estándar | |

**No se importan en ejecución** (pueden salir de producción): `gradio`, `flask`, `gunicorn`,
`argparse` (es estándar), `tqdm` (lo trae chromadb), `langchain`, `langchain-community`,
`langchain-chroma` (el backend usa `chromadb` directo), `python-docx` (solo ingesta).

`metadata_titulos_leyes.pkl` solo contiene `list`/`dict` básicos: no exige paquetes extra para
leerlo.

---

## F3-03 — Decidir P5: Gradio fuera de producción

**Objetivo:** confirmar si la imagen de producción lleva Gradio.

- `main.py` **no** importa `app.py`, así que el servicio nuevo no necesita Gradio.
- Quitarlo (con `flask` y `gunicorn`, que tampoco se usan) hace la imagen más ligera y evita
  conflictos de versiones con FastAPI.
- `app.py` sigue en el repo y funciona en local con `requirements_local.txt`.

| Decisión | Valor |
|---|---|
| ¿Gradio en producción? | ☑ **No** — decidido por el responsable el 2026-10-13. Salen también `flask` y `gunicorn`. `app.py` sigue en el repo para uso local. |

---

## F3-04 — `requirements.txt` de producción, con versiones fijas

**Objetivo:** que la imagen instale exactamente las versiones que ya abren el acervo.

- Parte del borrador de `BITACORA-REMAKE.md` §3.1, ajustado con F3-02 y F3-03.
- `torch` **no** va aquí: se instala aparte desde el índice de CPU en `Dockerfile.pesada`.
- `requirements_local.txt` no se toca.

**Hecho cuando:** el diff está aprobado y aplicado.

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; aplicado |
| Paquetes fijados | 14: fastapi, pydantic, uvicorn[standard], requests, python-dotenv, chromadb, pysqlite3-binary, faiss-cpu, numpy, langchain-core, langchain-huggingface, sentence-transformers, transformers, huggingface-hub (+ torch 2.9.1 CPU en el Dockerfile). Salen 9: gradio, flask, gunicorn, argparse, tqdm, langchain, langchain-community, langchain-chroma, python-docx. |

---

## F3-05 — Validar que `requirements.txt` resuelve (sin instalar)

**Objetivo:** detectar conflictos de versiones antes de construir nada. Se hace en un entorno
temporal fuera del repo, sin instalar.

```bash
TMP_VENV=$(mktemp -d)
python3 -m venv $TMP_VENV
$TMP_VENV/bin/pip install --quiet --upgrade pip
$TMP_VENV/bin/pip install --dry-run --index-url https://download.pytorch.org/whl/cpu torch==2.9.1
$TMP_VENV/bin/pip install --dry-run -r requirements.txt
rm -rf $TMP_VENV
```

**Hecho cuando:** los dos `--dry-run` terminan sin errores.

| Dato | Valor |
|---|---|
| torch CPU resuelve | ✅ `torch-2.9.1+cpu` (Python 3.12.3, linux x86_64) |
| `requirements.txt` resuelve | ✅ 116 paquetes en total, 0 errores |
| Conflictos | Ninguno. Pero **75 dependencias indirectas** saldrían en versiones distintas a las del venv probado (p. ej. `onnxruntime` 1.23→1.31, `protobuf` 6→7, `scipy` 1.16→1.17, `websockets` 11→17). Entorno temporal borrado. |

---

## F3-05b — `constraints.txt` (nuevo): fija las dependencias indirectas

**Objetivo:** que la imagen pesada instale exactamente las versiones del venv probado, no las
más recientes (hallazgo de F3-05). Lo aprobó el responsable el 2026-10-13.

Borrador generado desde `pip freeze` del venv, filtrado a lo que `requirements.txt` instala, sin
los 14 directos ni torch. Se validó en un entorno temporal (borrado) con
`pip install --dry-run -r requirements.txt -c constraints.txt` en 4 vueltas: la primera reveló
paquetes que solo aparecían con las versiones nuevas (`google-auth`, `pyasn1`, `zipp`,
`cachetools`), y se fijaron también.

| Dato | Valor |
|---|---|
| Restricciones | 99 |
| Paquetes instalados con restricciones | 110 (antes 116: sobraban 6 que solo traían las versiones nuevas) |
| Diferencias contra el venv | **0** (solo `torch` 2.9.1 → 2.9.1+cpu, que es lo buscado) |
| Diff aprobado | ✅ 2026-10-13 por el responsable; escrito en `constraints.txt` (raíz) |

---

## F3-06 — `Dockerfile.pesada` (nuevo; incluye P7)

**Objetivo:** la imagen pesada. `python:3.12-slim` + `libgomp1` + torch CPU + `requirements.txt`
+ `modelo_e5/` (lo baja Cloud Build del bucket) + `mkdir -p /app/modelo_e5/2_Normalize` (P7).
Con `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`: si el modelo faltara, falla en lugar de
descargar otro (cubre el riesgo del respaldo de `recursos.py` **sin tocar el código**).

Borrador: `BITACORA-REMAKE.md` §3.2. `Dockerfile.base` se conserva hasta la limpieza (§5).

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; escrito `Dockerfile.pesada` |
| P7 incluido | ✅ `mkdir -p /app/modelo_e5/2_Normalize` |
| Extras | Base `python:3.12-slim-bookworm`; usa `constraints.txt`; dos comprobaciones en build (imports silenciosos y carga del modelo sin conexión → 1024 dims) |

---

## F3-07 — `cloudbuild-pesada.yaml` (nuevo)

**Objetivo:** el pipeline que construye la pesada. Baja `modelo_e5/` del bucket con
`protocolo01-v2-build`, construye con `Dockerfile.pesada` y publica
`us-central1-docker.pkg.dev/alma-juridica-aipp/protocolo01-v2/protocolo01-v2-pesada:v1`.

Borrador: `BITACORA-REMAKE.md` §3.5. Se corre a mano solo cuando cambien las dependencias o el
modelo (Fase 5).

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; escrito `cloudbuild-pesada.yaml` |
| Etiqueta inicial | `v1` |
| Máquina | `E2_HIGHCPU_8` (elegida por el responsable): ~$0.0156 USD/min en us-central1, ~$0.25–0.40 por build; 100 GB de disco incluidos sin costo. Se cobra **solo cuando se reconstruye la pesada**. |
| Protecciones | Se detiene si la versión ya existe; el bucket solo se lee; corre como `protocolo01-v2-build` |

---

## F3-08 — `startup.sh`

**Objetivo:** el arranque del contenedor. Copia del volumen `/mnt/acervo` a `/app` solo las 6
`chroma_db_*` y `faiss-lista/`; falla si falta `faiss-lista`; lanza `python3 -u main.py`.
Ya no usa `gcloud`, no baja el modelo y no toca `procesado-unam`.

Borrador: `BITACORA-REMAKE.md` §3.4.

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; `startup.sh` reescrito |
| `bash -n startup.sh` | ✅ sintaxis ok, saltos de línea LF |

---

## F3-09 — `Dockerfile` (imagen ligera)

**Objetivo:** `FROM` la pesada (por argumento `IMAGEN_PESADA`) + los 7 módulos de ejecución
+ `web/` + `startup.sh`. Nada más: sin scripts de ingesta, pruebas ni prototipos.

Borrador: `BITACORA-REMAKE.md` §3.3.

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; `Dockerfile` reescrito |
| Archivos que copia | `main.py`, `recursos.py`, `catalogo_datos.py`, `logica_a.py`, `logica_b.py`, `logica_c.py`, `utils_rag.py`, `web/`, `startup.sh` (todos existen) |
| Notas | `IMAGEN_PESADA` sin valor por defecto (falla si no se indica); `sed` en lugar de `dos2unix`. Los `*:Zone.Identifier` de `web/` se excluyen en F3-12. |

---

## F3-10 — `cloudbuild.yaml` (ligera + despliegue)

**Objetivo:** construir la ligera, publicarla como `protocolo01-v2-app:$BUILD_ID` y actualizar
**solo la imagen** de `protocolo01-app-v2`. El resto de la configuración vive en
`deploy/service.yaml`.

Borrador: `BITACORA-REMAKE.md` §3.6. Reemplaza al `cloudbuild.yaml` viejo (que construía
`protocolo01-base` y `protocolo01-app` en `gcr.io`); el viejo queda en el historial de git.

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; `cloudbuild.yaml` reescrito. YAML válido. |
| Pasos | `verificar-servicio` → `construir-ligera` → `subir-ligera` → `desplegar` |
| Protecciones | No despliega si `protocolo01-app-v2` no existe (evita crearlo con la cuenta Editor por defecto); `_DESPLEGAR=no` para la primera vez; etiqueta única `$BUILD_ID`; máquina por defecto (minutos gratis) |

---

## F3-11 — `deploy/service.yaml` (nuevo)

**Objetivo:** la configuración declarativa del servicio, con los valores de la Fase 1:
8 GiB / 2 vCPU / concurrencia 10 / `us-central1`, gen2, volumen del bucket en `/mnt/acervo`,
secreto `DEEPSEEK_API_KEY` (`latest`), cuenta `protocolo01-v2-run`, startup probe sobre
`/api/estado`, `timeoutSeconds: 600`.

Borrador: `BITACORA-REMAKE.md` §3.7. Quedan como valores provisionales, a decidir en la Fase 5:
`minScale` (P3/D3) y `maxScale` (P4/D6).

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13 por el responsable; escrito `deploy/service.yaml`. YAML válido. |
| Documentación verificada | Cloud Run activa carpetas implícitas por defecto en volúmenes de Cloud Storage; el caché del montaje usa la memoria del contenedor (~36 MB por defecto). |
| `minScale` / `maxScale` provisionales | `minScale: 0` **decidido** (D3, F3-08: se apaga del todo; la primera consulta de cada instancia tarda en cargar el modelo) · `maxScale: 2` **provisional** (D6, aprobado como recomendación: hasta 20 consultas simultáneas) |

---

## F3-12 — `.gcloudignore` y `.dockerignore`

**Objetivo:**
- `.gcloudignore`: que Cloud Build no reciba datos, modelo, entornos, claves ni basura de
  Windows; corregir la línea pegada `descargar_modelo.py.git/`; excluir `Axiomas/`.
- `.dockerignore`: que **no** excluya `modelo_e5/` (la pesada lo necesita en su contexto) y
  sí excluya lo demás.

Borrador: `BITACORA-REMAKE.md` §3.8.

| Dato | Valor |
|---|---|
| Diff `.gcloudignore` aprobado | ✅ 2026-10-13; reescrito (corrige `descargar_modelo.py.git/`, agrega `Axiomas/`, `*.csv`, `*:Zone.Identifier`, `docs/`) |
| Diff `.dockerignore` aprobado | ✅ 2026-10-13; reescrito (no excluye `modelo_e5/`; agrega `faiss-lista/`, `*.csv`, `llamada_deepseek.txt`, `.venv/`, `docs/`, `**/*:Zone.Identifier`) |
| Subida a Cloud Build (`gcloud meta list-files-for-upload`) | 51 archivos, solo código y configuración; sin datos, modelo, claves ni `Zone.Identifier` |

---

## F3-13 — Revisión estática de todo lo escrito

**Objetivo:** atrapar errores antes de la Fase 4, sin construir ni desplegar.

```bash
bash -n startup.sh
./venv/bin/python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ('cloudbuild.yaml','cloudbuild-pesada.yaml','deploy/service.yaml')]; print('YAML ok')"
# Lo que subiría a Cloud Build (sin subir nada):
gcloud meta list-files-for-upload | sort
```

Más una revisión cruzada a mano: nombres (`protocolo01-v2-*`), rutas del acervo iguales a
`recursos.py`, puerto 8080, región, cuentas de servicio.

> Docker no está disponible en WSL (ver Punto de partida). Si se activa la integración, se
> agrega `docker build --check` aquí; si no, la prueba con Docker queda para la Fase 4.

| Verificación | Resultado |
|---|---|
| `bash -n startup.sh` | ✅ sintaxis ok; los 10 archivos nuevos o cambiados usan LF |
| YAML válidos | ✅ `cloudbuild.yaml`, `cloudbuild-pesada.yaml`, `deploy/service.yaml` |
| Lista de archivos a subir sin datos/claves | ✅ 51 archivos, ~490 KB (F3-12) |
| Revisión cruzada | ✅ ver detalle abajo |

Detalle de la revisión cruzada:

| Punto | Resultado |
|---|---|
| Rutas del acervo `startup.sh` = `recursos.py` | ✅ las 6 iguales; `faiss-lista` coincide con `utils_rag.py` y `catalogo_datos.py` |
| `COPY` de la ligera | ✅ los 9 orígenes existen |
| Imagen pesada producida = consumida | ✅ `protocolo01-v2-pesada:${_VERSION_PESADA}`, `v1` en ambos |
| Nombres | ✅ solo `protocolo01-v2-*`; sin `walle`, sin `gcr.io` |
| Puerto | ✅ 8080 en `main.py` (`$PORT`), `Dockerfile` y `service.yaml` (contenedor y probe) |
| Probe / volumen | ✅ `/api/estado` existe en `main.py`; `ACERVO_DIR` = `mountPath` = `/mnt/acervo` |
| Rutas internas | ✅ `main.py` y `recursos.py` resuelven desde su carpeta → `/app` (`WORKDIR /app`) |
| Variables de bash en Cloud Build | ✅ `$$IMG` escapado; solo `$PROJECT_ID` y `$BUILD_ID` sin escapar |
| Sustituciones definidas = usadas | ✅ todas se usan (evita el error de Cloud Build por sustitución sobrante) |
| `requirements.txt` vs `constraints.txt` | ✅ sin solapes |
| Cuentas y repo en GCP | ✅ `protocolo01-v2-run`, `protocolo01-v2-build`, repo `protocolo01-v2` existen |
| Docker (`docker build --check`) | ⏭ no disponible en WSL; queda para la Fase 4 |

---

## F3-14 — Cierre: confirmar cambios en git y paso a Fase 4

**Objetivo:** dejar los cambios confirmados en la rama y decidir el paso a la Fase 4 (prueba
local con Docker).

| Decisión | Valor |
|---|---|
| Confirmación(es) en git | `65601b2` (partida, F3-01) + confirmación de cierre de la Fase 3 en `remake/protocolo01-v2` (ver Registro). Sin claves en lo confirmado. |
| Pendientes cerrados | P3 (minScale 0), P5 (Gradio fuera), P7 (`2_Normalize`). P4 a medias (`maxScale: 2` provisional). |
| Requisito para Fase 4 | Activar integración de Docker Desktop con WSL |
| ¿Pasar a Fase 4? | ☑ Sí — el responsable pidió preparar la Fase 4 el 2026-10-13 |
| Push a GitHub | No hecho. El remoto `MockAh/gradio-local-01` responde 404 sin autenticación (privado). Pendiente de decisión del responsable (P15). |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F3-02 | `faiss` y `pysqlite3` se importan con respaldo silencioso (`try/except ImportError`). | Si faltaran en la imagen, la app arrancaría pero Cita Precisa o Chroma fallarían sin aviso claro. | Fijarlos en `requirements.txt` y comprobar en F3-13/Fase 4 que se importan. Sin tocar código. |
| F3-02 | `langchain`, `langchain-community`, `langchain-chroma` no se usan en ejecución. | Peso y riesgo de conflictos innecesarios. | Sacarlos de producción en F3-04 (siguen en `requirements_local.txt`). |
| F3-05 | Las dependencias indirectas no están fijadas: cada build de la pesada puede traer versiones nuevas, distintas a las del venv que abre el acervo. | Builds no reproducibles; riesgo bajo pero real (`chromadb` depende de `onnxruntime`, `protobuf`, `grpcio`). | Propuesta: `constraints.txt` con las versiones del venv para esas 116 dependencias, usado como `pip install -c` en `Dockerfile.pesada`. Requiere aprobación (archivo nuevo). |
| (previo) | Docker Desktop está en Windows pero sin integración con la distro WSL. | No se puede probar `docker build` desde aquí. | Activar en Docker Desktop → Settings → Resources → WSL integration, antes de la Fase 4. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 3 con 14 mini-tareas. Verificado: rama `master` con cambios previos sin confirmar; sin carpeta `deploy/`; Docker sin integración con WSL. |
| 2026-10-13 | F3-01 hecha (Claude, autorizado): rama `remake/protocolo01-v2`, confirmación de partida `65601b2`. |
| 2026-10-13 | F3-02 hecha (Claude, solo lectura): 11 paquetes necesarios en ejecución + torch CPU; 8 sobran en producción. |
| 2026-10-13 | F3-03 hecha (responsable): Gradio fuera de producción. P5 cerrado. |
| 2026-10-13 | F3-04 hecha (Claude, aprobado): `requirements.txt` reescrito con versiones fijas. |
| 2026-10-13 | F3-05 hecha (Claude): resuelve sin conflictos; 75 dependencias indirectas difieren del venv → propuesta de `constraints.txt`. |
| 2026-10-13 | F3-05b: borrador de `constraints.txt` (99 restricciones) validado; reproduce el venv exacto. En espera de luz verde para escribirlo en el repo. |
| 2026-10-13 | F3-05b hecha (Claude, aprobado): `constraints.txt` escrito en la raíz. `Dockerfile.pesada` deberá usarlo con `-c`. |
| 2026-10-13 | F3-06 hecha (Claude, aprobado): `Dockerfile.pesada` escrito. P7 cerrado. |
| 2026-10-13 | F3-07 hecha (Claude, aprobado): `cloudbuild-pesada.yaml` escrito con `E2_HIGHCPU_8`. YAML válido. |
| 2026-10-13 | Decisión del responsable (D3/P3): `minScale: 0`, sin instancia encendida; se acepta la carga lenta de la primera consulta. |
| 2026-10-13 | F3-08 hecha (Claude, aprobado): `startup.sh` reescrito (copia del volumen, sin gcloud). |
| 2026-10-13 | F3-09 hecha (Claude, aprobado): `Dockerfile` de la imagen ligera reescrito. |
| 2026-10-13 | F3-10 hecha (Claude, aprobado): `cloudbuild.yaml` reescrito (ligera + despliegue con protecciones). |
| 2026-10-13 | F3-11 hecha (Claude, aprobado): `deploy/service.yaml` escrito (8 GiB / 2 vCPU / concurrencia 10 / minScale 0 / maxScale 2 provisional / bucket solo lectura). |
| 2026-10-13 | F3-12 hecha (Claude, aprobado): `.gcloudignore` y `.dockerignore` reescritos; la subida a Cloud Build queda en 51 archivos de código. |
| 2026-10-13 | F3-13 hecha (Claude, solo lectura): 12 verificaciones cruzadas en verde; prueba con Docker pendiente para Fase 4. |
| 2026-10-13 | F3-14 hecha: **Fase 3 completa.** 11 archivos de despliegue escritos y revisados; confirmados en `remake/protocolo01-v2`. Inicia Fase 4 (`BITACORA-REMAKE-F4.md`). |
