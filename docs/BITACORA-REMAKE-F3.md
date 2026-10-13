# BITÁCORA-REMAKE-F3 — Fase 3: archivos de despliegue del repo

Desglose de la **Fase 3** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** en curso
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
| F3-01 | Punto de control en git (rama de trabajo) | Tú decides; Claude ejecuta | Git | ☐ |
| F3-02 | Inventario de imports en ejecución (solo lectura) | Claude | No | ☐ |
| F3-03 | Decidir P5: Gradio fuera de producción | **Tú** | No | ☐ |
| F3-04 | `requirements.txt` de producción, con versiones fijas | Claude propone, tú apruebas | Sí | ☐ |
| F3-05 | Validar que `requirements.txt` resuelve (sin instalar) | Claude | No | ☐ |
| F3-06 | `Dockerfile.pesada` (nuevo; incluye P7) | Claude propone, tú apruebas | Sí | ☐ |
| F3-07 | `cloudbuild-pesada.yaml` (nuevo) | Claude propone, tú apruebas | Sí | ☐ |
| F3-08 | `startup.sh` | Claude propone, tú apruebas | Sí | ☐ |
| F3-09 | `Dockerfile` (imagen ligera) | Claude propone, tú apruebas | Sí | ☐ |
| F3-10 | `cloudbuild.yaml` (ligera + despliegue) | Claude propone, tú apruebas | Sí | ☐ |
| F3-11 | `deploy/service.yaml` (nuevo) | Claude propone, tú apruebas | Sí | ☐ |
| F3-12 | `.gcloudignore` y `.dockerignore` | Claude propone, tú apruebas | Sí | ☐ |
| F3-13 | Revisión estática de todo lo escrito | Claude | No | ☐ |
| F3-14 | Cierre: confirmar cambios en git y paso a Fase 4 | Tú decides | Git | ☐ |

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
| Opción elegida | |
| Rama | |
| Confirmación de partida | |

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

| Paquete importado | Lo importa | Versión en el venv |
|---|---|---|
| | | |

---

## F3-03 — Decidir P5: Gradio fuera de producción

**Objetivo:** confirmar si la imagen de producción lleva Gradio.

- `main.py` **no** importa `app.py`, así que el servicio nuevo no necesita Gradio.
- Quitarlo (con `flask` y `gunicorn`, que tampoco se usan) hace la imagen más ligera y evita
  conflictos de versiones con FastAPI.
- `app.py` sigue en el repo y funciona en local con `requirements_local.txt`.

| Decisión | Valor |
|---|---|
| ¿Gradio en producción? | ☐ No (recomendado) ☐ Sí, montado en `/legacy` |

---

## F3-04 — `requirements.txt` de producción, con versiones fijas

**Objetivo:** que la imagen instale exactamente las versiones que ya abren el acervo.

- Parte del borrador de `BITACORA-REMAKE.md` §3.1, ajustado con F3-02 y F3-03.
- `torch` **no** va aquí: se instala aparte desde el índice de CPU en `Dockerfile.pesada`.
- `requirements_local.txt` no se toca.

**Hecho cuando:** el diff está aprobado y aplicado.

| Dato | Valor |
|---|---|
| Diff aprobado | |
| Paquetes fijados | |

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
| torch CPU resuelve | |
| `requirements.txt` resuelve | |
| Conflictos | |

---

## F3-06 — `Dockerfile.pesada` (nuevo; incluye P7)

**Objetivo:** la imagen pesada. `python:3.12-slim` + `libgomp1` + torch CPU + `requirements.txt`
+ `modelo_e5/` (lo baja Cloud Build del bucket) + `mkdir -p /app/modelo_e5/2_Normalize` (P7).
Con `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`: si el modelo faltara, falla en lugar de
descargar otro (cubre el riesgo del respaldo de `recursos.py` **sin tocar el código**).

Borrador: `BITACORA-REMAKE.md` §3.2. `Dockerfile.base` se conserva hasta la limpieza (§5).

| Dato | Valor |
|---|---|
| Diff aprobado | |
| P7 incluido | |

---

## F3-07 — `cloudbuild-pesada.yaml` (nuevo)

**Objetivo:** el pipeline que construye la pesada. Baja `modelo_e5/` del bucket con
`protocolo01-v2-build`, construye con `Dockerfile.pesada` y publica
`us-central1-docker.pkg.dev/alma-juridica-aipp/protocolo01-v2/protocolo01-v2-pesada:v1`.

Borrador: `BITACORA-REMAKE.md` §3.5. Se corre a mano solo cuando cambien las dependencias o el
modelo (Fase 5).

| Dato | Valor |
|---|---|
| Diff aprobado | |
| Etiqueta inicial | `v1` |

---

## F3-08 — `startup.sh`

**Objetivo:** el arranque del contenedor. Copia del volumen `/mnt/acervo` a `/app` solo las 6
`chroma_db_*` y `faiss-lista/`; falla si falta `faiss-lista`; lanza `python3 -u main.py`.
Ya no usa `gcloud`, no baja el modelo y no toca `procesado-unam`.

Borrador: `BITACORA-REMAKE.md` §3.4.

| Dato | Valor |
|---|---|
| Diff aprobado | |
| `bash -n startup.sh` | |

---

## F3-09 — `Dockerfile` (imagen ligera)

**Objetivo:** `FROM` la pesada (por argumento `IMAGEN_PESADA`) + los 7 módulos de ejecución
+ `web/` + `startup.sh`. Nada más: sin scripts de ingesta, pruebas ni prototipos.

Borrador: `BITACORA-REMAKE.md` §3.3.

| Dato | Valor |
|---|---|
| Diff aprobado | |
| Archivos que copia | |

---

## F3-10 — `cloudbuild.yaml` (ligera + despliegue)

**Objetivo:** construir la ligera, publicarla como `protocolo01-v2-app:$BUILD_ID` y actualizar
**solo la imagen** de `protocolo01-app-v2`. El resto de la configuración vive en
`deploy/service.yaml`.

Borrador: `BITACORA-REMAKE.md` §3.6. Reemplaza al `cloudbuild.yaml` viejo (que construía
`protocolo01-base` y `protocolo01-app` en `gcr.io`); el viejo queda en el historial de git.

| Dato | Valor |
|---|---|
| Diff aprobado | |

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
| Diff aprobado | |
| `minScale` / `maxScale` provisionales | |

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
| Diff `.gcloudignore` aprobado | |
| Diff `.dockerignore` aprobado | |

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
| `bash -n startup.sh` | |
| YAML válidos | |
| Lista de archivos a subir sin datos/claves | |
| Revisión cruzada | |

---

## F3-14 — Cierre: confirmar cambios en git y paso a Fase 4

**Objetivo:** dejar los cambios confirmados en la rama y decidir el paso a la Fase 4 (prueba
local con Docker).

| Decisión | Valor |
|---|---|
| Confirmación(es) en git | |
| Pendientes cerrados | (se espera P5 y P7) |
| Requisito para Fase 4 | Activar integración de Docker Desktop con WSL |
| ¿Pasar a Fase 4? | ☐ Sí ☐ No — motivo: |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| (previo) | Docker Desktop está en Windows pero sin integración con la distro WSL. | No se puede probar `docker build` desde aquí. | Activar en Docker Desktop → Settings → Resources → WSL integration, antes de la Fase 4. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 3 con 14 mini-tareas. Verificado: rama `master` con cambios previos sin confirmar; sin carpeta `deploy/`; Docker sin integración con WSL. |
