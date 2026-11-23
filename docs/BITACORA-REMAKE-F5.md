# BITÁCORA-REMAKE-F5 — Fase 5: construir y desplegar en la nube

Desglose de la **Fase 5** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** completada (2026-10-13). Fase 6 autorizada.
- **Objetivo:** construir en Cloud Build la imagen pesada `v1` y la ligera, crear el servicio
  `protocolo01-app-v2` **sin hacerlo público**, y probarlo con las 6 bases reales del bucket.
  Hacerlo público y abrirlo a internet es la Fase 6.

## Reglas de esta fase

1. **Esta fase cuesta y crea recursos.** Cada mini-tarea que construye, crea o cambia algo en
   Google Cloud la ejecuta el responsable, o Claude con autorización explícita **para esa
   mini-tarea**. `CLAUDE.md` §8 prohíbe a Claude correr `gcloud builds submit` por su cuenta.
2. **No se toca nada existente:** ni `protocolo01-app`, ni `ia-legal-mexicana-web`, ni sus
   imágenes, ni el contenido del bucket del acervo (solo se lee).
3. **El servicio nuevo nace privado.** Sin `allUsers`; las pruebas usan un token de identidad
   del responsable.
4. **No se toca la lógica del backend.** Si una prueba revela un problema, se anota y se propone
   el cambio aparte.
5. **Las llamadas a DeepSeek cuestan.** Solo en F5-09, con autorización, una por base.
6. Cada mini-tarea termina con su casilla marcada y sus datos anotados.

## Variables de la sesión

```bash
export PROYECTO=alma-juridica-aipp
export REGION=us-central1
export AR=us-central1-docker.pkg.dev/alma-juridica-aipp/protocolo01-v2
export SERVICIO=protocolo01-app-v2
export SA_BUILD=protocolo01-v2-build@alma-juridica-aipp.iam.gserviceaccount.com
```

## Punto de partida (verificado el 2026-10-13, solo lectura)

| Pieza | Estado |
|---|---|
| Rama | `remake/protocolo01-v2` en `95fec84`, subida a GitHub |
| Repositorio `protocolo01-v2` | Vacío (0 imágenes) |
| Servicio `protocolo01-app-v2` | No existe |
| Bucket de fuentes de Cloud Build | `alma-juridica-aipp_cloudbuild` (US). **`protocolo01-v2-build` no tiene acceso** → el build fallaría al leer el código subido (ver F5-02) |
| Otros buckets del proyecto | `chromadb-alma-juridica-aipp` (acervo), `mi-proyecto-axiomas` (no revisado; no se toca) |
| Memoria del servicio | 4 GiB / 2 vCPU (F4-12) |

---

## Resumen de mini-tareas

| # | Mini-tarea | Quién | Costo / efecto | Estado |
|---|---|---|---|---|
| F5-01 | Pre-vuelo (solo lectura) | Claude | — | ☑ |
| F5-02 | Permiso de lectura del bucket de fuentes para `protocolo01-v2-build` | Claude con autorización | Cambia IAM de ese bucket | ☑ |
| F5-03 | Construir la pesada `v1` en Cloud Build | Claude con autorización, o tú | ~$0.25–0.40 · crea imagen | ☑ |
| F5-04 | Verificar la pesada en Artifact Registry | Claude | — | ☑ |
| F5-05 | Construir la ligera sin desplegar (`_DESPLEGAR=no`) | Claude con autorización, o tú | minutos gratis · crea imagen | ☑ |
| F5-06 | Crear el servicio privado desde `deploy/service.yaml` | Claude con autorización, o tú | crea el servicio | ☑ |
| F5-07 | Revisar el arranque en la nube | Claude | — | ☑ |
| F5-08 | Probar estado y catálogo con las 6 bases reales | Claude | — | ☑ |
| F5-09 | Una consulta real por base (DeepSeek) | Claude, **con tu autorización** | ~4 llamadas | ☑ |
| F5-10 | Revisar memoria, tiempos y errores | Claude | — | ☑ |
| F5-11 | P14: acotar `run.developer` al servicio | Claude con autorización | Cambia IAM | ☑ |
| F5-12 | Probar el despliegue normal (`cloudbuild.yaml` completo) | Claude con autorización, o tú | minutos gratis · nueva revisión | ☑ |
| F5-13 | D6: decidir límites de uso | **Tú** | — | ☑ |
| F5-14 | Cierre y paso a Fase 6 | Claude propone, tú decides | — | ☑ |

Total estimado: **~3.5 h** (los builds corren solos; el de la pesada ~15–25 min).

---

## F5-01 — Pre-vuelo (solo lectura)

**Objetivo:** confirmar que todo está en su lugar antes de gastar.

```bash
git status -sb | head -1                      # rama al día con origin
gcloud config get-value account; gcloud config get-value project
gcloud meta list-files-for-upload | wc -l     # ~52 archivos, sin datos ni claves
gcloud artifacts docker images list $AR       # vacío
gcloud run services describe $SERVICIO --region=$REGION 2>&1 | head -1   # no existe
gcloud iam service-accounts list --filter="email~protocolo01-v2" --format="value(email)"
gcloud secrets versions list DEEPSEEK_API_KEY --format="value(name,state)"
```

| Dato | Valor |
|---|---|
| Rama al día | ✅ `remake/protocolo01-v2` = `origin` |
| Cuenta / proyecto | ✅ `g.olin.xy@gmail.com` / `alma-juridica-aipp` |
| Archivos a subir | ✅ 51, sin datos, modelo, claves ni `Zone.Identifier` |
| Repo vacío / servicio inexistente | ✅ 0 imágenes · `protocolo01-app-v2` no existe |
| Cuentas y secreto | ✅ `-run` y `-build` habilitadas · secreto v1 y v2 habilitadas |
| Servicios existentes | `protocolo01-app` en `00013-6zv`, `ia-legal-mexicana-web` en `00040-qpj` (referencia para comprobar que no cambian) |

---

## F5-02 — Permiso de lectura del bucket de fuentes

**Objetivo:** `gcloud builds submit` empaqueta el código y lo sube a
`gs://alma-juridica-aipp_cloudbuild`. Como los builds corren con `protocolo01-v2-build` (y no con
la cuenta de Cloud Build por defecto), esa cuenta necesita **leer** ese bucket. Hoy no puede.

```bash
gcloud storage buckets add-iam-policy-binding gs://alma-juridica-aipp_cloudbuild \
  --member=serviceAccount:$SA_BUILD --role=roles/storage.objectViewer
```

**Efecto:** solo lectura sobre el bucket de fuentes de Cloud Build. No toca el bucket del acervo.

| Dato | Valor |
|---|---|
| Permiso aplicado | ✅ 2026-10-13: `roles/storage.objectViewer` de `protocolo01-v2-build` sobre `gs://alma-juridica-aipp_cloudbuild` (Claude, autorizado) |

---

## F5-03 — Construir la pesada `v1` en Cloud Build

**Objetivo:** la imagen pesada definitiva. Mismo `Dockerfile.pesada` probado en la Fase 4, con el
modelo bajado del bucket por el propio build.

```bash
gcloud builds submit --config cloudbuild-pesada.yaml --substitutions=_VERSION_PESADA=v1 --region=$REGION
```

Se espera: `verificar-version` libre → `bajar-modelo` (2.1 GB) → `construir-pesada` con
`imports ok` y `modelo ok 1024` → subida a Artifact Registry.

| Dato | Valor |
|---|---|
| ID del build | `bb934e55-e747-4074-a8de-68f0f1a2f2be` · **SUCCESS** |
| Duración | **5 min 57 s** (08:38:11 → 08:44:08 UTC): verificar-versión 20 s · bajar-modelo 9 s · construir 2 min 25 s · subir imagen ~3 min |
| `imports ok` / `modelo ok 1024` | ✅ / ✅ (en Cloud Logging) |
| Costo aproximado | ~6 min × $0.0156 ≈ **$0.09 USD** |
| Autorización | Responsable, 2026-10-13 (Claude ejecutó `gcloud builds submit`) |

---

## F5-04 — Verificar la pesada en Artifact Registry

```bash
gcloud artifacts docker images list $AR --include-tags --format="table(package,tags,createTime)"
gcloud artifacts docker images describe $AR/protocolo01-v2-pesada:v1 --format="value(image_summary.digest)"
gcloud artifacts repositories describe protocolo01-v2 --location=$REGION --format="value(sizeBytes)"
```

| Dato | Valor |
|---|---|
| Etiqueta `v1` presente | ✅ `protocolo01-v2-pesada:v1`, creada 2026-10-13 08:44 UTC |
| Digest | `sha256:70a09888525c927bbf2a10650bf99c3e28529500cdc9ec0d6c7b75f3a8103a9b` |
| Tamaño en el repositorio | **1.73 GiB** comprimida (6.01 GB descomprimida). Almacenamiento estimado ~$0.12 USD/mes (a ~$0.10/GB-mes tras 0.5 GB gratis; precio por confirmar) |

---

## F5-05 — Construir la ligera sin desplegar

**Objetivo:** primera imagen ligera; el servicio aún no existe, así que se construye sin desplegar.

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_DESPLEGAR=no --region=$REGION
```

| Dato | Valor |
|---|---|
| ID del build (= etiqueta de la imagen) | `51c1e8fd-b0e5-4655-bd36-49fd8abe64e5` · **SUCCESS** |
| Duración | **1 min 34 s** (máquina por defecto, minutos gratis) |
| Despliegue | Omitido como se pidió (`_DESPLEGAR=no`); ningún servicio creado ni cambiado |
| Autorización | Responsable, 2026-10-13 |
| Imagen | `$AR/protocolo01-v2-app:<BUILD_ID>` |

---

## F5-06 — Crear el servicio privado desde `deploy/service.yaml`

**Objetivo:** crear `protocolo01-app-v2` con toda su configuración (4 GiB, 2 vCPU, bucket en
solo lectura, secreto, cuenta `protocolo01-v2-run`, `minScale: 0`, `maxScale: 2`).

```bash
sed "s|IMAGEN_INICIAL|$AR/protocolo01-v2-app:<BUILD_ID>|" deploy/service.yaml > /tmp/service.yaml
gcloud run services replace /tmp/service.yaml --region=$REGION
gcloud run services get-iam-policy $SERVICIO --region=$REGION   # sin allUsers
```

**Efecto:** crea el servicio. **No es público**: sin `allUsers`, cualquier petición sin token
recibe 403.

| Dato | Valor |
|---|---|
| Revisión creada | ✅ `protocolo01-app-v2-00001-fl7`, lista en **74 s** (incluye la revisión de arranque) |
| URL | `https://protocolo01-app-v2-879901246493.us-central1.run.app` (alias `…-y6aiuastva-uc.a.run.app`) |
| Configuración aplicada | cuenta `protocolo01-v2-run` · 2 vCPU · 4 GiB |
| ¿Público? | **No** ✅: política IAM vacía (sin `allUsers`); sin token responde **403** |
| Nota | `gcloud run services replace -` (leer de la entrada estándar) no se usó: se escribió el YAML con la imagen en un archivo temporal y se aplicó ese archivo. **Comentario de `deploy/service.yaml` corregido** (aprobado por el responsable) |
| Autorización | Responsable, 2026-10-13 |

---

## F5-07 — Revisar el arranque en la nube

```bash
gcloud run services describe $SERVICIO --region=$REGION --format="value(status.conditions)"
gcloud run services logs read $SERVICIO --region=$REGION --limit=40
```

Se espera: 6 `⬇️ Copiando …`, `⬇️ Copiando faiss-lista`, `🚀 Iniciando…`, `Uvicorn running`,
revisión lista. **Esta es la primera vez que el servicio lee las 6 bases reales del bucket.**

| Dato | Valor |
|---|---|
| Bases copiadas | ✅ **las 6 reales** + `faiss-lista`, en **6 s** (08:52:48 → 08:52:54) |
| Tiempo de arranque | **~27 s** desde la instancia hasta la revisión lista: montaje del bucket <1 s · copia 6 s · importar librerías 18 s · abrir las 6 bases 2 s |
| Revisión lista | ✅ la revisión de arranque pasó al 3.er intento (`/api/estado` 200) |
| Bases abiertas | ✅ basic, segob, transp, 3p, fce (`langchain`) y tramites (`tramites_gob_mx`) |
| Volumen | Montado en solo lectura (`o:[ro,…]`) con `implicit-dirs:true`, como dice la documentación |
| Acceso sin token | Rechazado (log de las 08:53:26: *"The request was not authenticated"*) — era la prueba 403 de F5-06 |

Línea de tiempo de los logs: `08:52:47` instancia nueva → `08:52:48` bucket montado → `08:52:54`
`🚀 Iniciando…` → `08:53:12` `Uvicorn running` → `08:53:14` 6 bases abiertas y revisión aprobada.

---

## F5-08 — Probar estado y catálogo con las 6 bases reales

```bash
URL=$(gcloud run services describe $SERVICIO --region=$REGION --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)
curl -s -o /dev/null -w "sin token → %{http_code}\n" $URL/                    # 403 esperado
curl -s -H "Authorization: Bearer $TOKEN" $URL/api/estado | python3 -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" $URL/api/catalogo | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])"
```

Se espera: las 6 bases `disponible: true` con los conteos de F1-10 (basic 3688, segob 3169,
transp 413, 3p 935, fce 3080, tramites 81) y el catálogo con los títulos del bucket (46 entradas).

| Prueba | Resultado |
|---|---|
| Sin token (403) | ✅ 403 en la URL directa |
| `/api/estado` | ✅ **las 6 bases disponibles**, conteos idénticos a F1-10: basic 3688 · segob 3169 · transp 413 · 3p 935 · fce 3080 · tramites 81. Las 3 bases del front (General, FCE, Trámites SEGOB) **completas** |
| `/api/catalogo` | ✅ **45 títulos** (46 entradas del índice agrupadas por título): basic 8 · FCE 17 · segob 15 · Transparencia 2 · Tres Poderes 3. En local eran 42 (basic 5); las 3 nuevas son las de F1-06 |
| `/` vía proxy | ✅ 200 · `/web/app.js` 200 · `Zone.Identifier` 404 |
| Método | `gcloud run services proxy` en `localhost:8081` (decisión del responsable; componente `google-cloud-cli-cloud-run-proxy=550.0.0-0` instalado por él). Claude no manejó el token |

---

## F5-09 — Una consulta real por base (DeepSeek)

**Requiere autorización.** ~4 llamadas: la primera mide además el arranque en frío.

| Consulta | Ruta | Base |
|---|---|---|
| Cita Precisa, ley del bucket que no está en local (p. ej. Ley Federal del Trabajo) | `/api/consulta` | `GENERAL` |
| Cita Precisa FCE | `/api/consulta` | `FCE` |
| Trámites SEGOB (logica_c) | `/api/consulta/stream` | `TRAMITES_SEGOB` |
| Razonamiento General (streaming) | `/api/consulta/stream` | `GENERAL` |

| Prueba | Resultado |
|---|---|
| Primera consulta en frío (tiempo) | No medida: el responsable prefirió probar cada base ya, con la instancia caliente |
| General · Cita Precisa | ✅ *"artículo 2 de la Ley Federal del Trabajo"* (ley que **solo** está en el bucket) → texto literal en 1.8 s |
| FCE · Cita Precisa | ❌ *"artículo 1 del Estatuto Orgánico del FCE"* → FAISS encontró la ley (similitud 0.9748) pero Chroma no: *"el artículo 1 no está en las bases de datos textuales"* (1.6 s). Ver §Hallazgos |
| Trámites SEGOB (`logica_c`) | ✅ *"¿Qué requisitos necesito para tramitar la CURP?"* → respuesta oficial con fundamento normativo y operativo en 9.0 s |
| Razonamiento General (streaming a través de Cloud Run) | ✅ despido injustificado (LFT art. 48) → 1076 fragmentos en 11.6 s, primer byte en 0.09 s: **el streaming llega en vivo a través de Cloud Run** |
| FCE · Razonamiento (consulta hecha desde el navegador vía proxy) | ✅ los logs muestran que encontró el Estatuto Orgánico por búsqueda semántica (8 fragmentos al LLM) |
| Autorización | Responsable, 2026-10-13 (4 consultas, vía proxy) |

---

## F5-10 — Revisar memoria, tiempos y errores

```bash
gcloud run services logs read $SERVICIO --region=$REGION --limit=100 | grep -iE "error|memory|killed|exceeded"
```

Más la consola: Cloud Run → `protocolo01-app-v2` → Métricas → *Container memory utilization*.

| Dato | Valor |
|---|---|
| Memoria máxima usada (de 4 GiB) | **22 %** ≈ **0.88 GiB** (percentil 99). Antes de las consultas, ~12 % ≈ 0.48 GiB; sube a ~22 % al cargar el modelo (09:15–09:20 UTC) y se queda ahí |
| Disco en memoria (`tmpfs`) | **~184 MiB** constantes = el acervo copiado al arrancar (≈163 MiB, F1-05) más archivos temporales |
| Fuente | CSV exportados de la consola por el responsable (carpeta `gconsole/`, ventana 08:55–09:30 UTC, percentiles 99/95/50) |
| Errores / reinicios | ✅ **ninguno**: 0 `Memory limit exceeded`, 0 `Killed`, 0 `Traceback`. El único `WARNING` es la prueba 403 sin token |
| Instancias | 08:52:47 arranque por despliegue · **09:08:22 se apagó sola** (sin tráfico ~15 min, `minScale: 0` funciona) · 09:09:42 arranque en frío por la primera petición vía proxy |
| Arranque en frío medido | **38 s** (09:09:42 instancia → 09:10:20 revisión de arranque aprobada) |
| Primera consulta con carga del modelo | **26.3 s** (Razonamiento desde el navegador, 09:13:41, incluye `🧠 Cargando modelo`) |
| Peor caso para un visitante | ~38 s + ~26 s ≈ **~1 min** (mejor que el ~1.5–2 min estimado en F4-09) |
| Latencias después | `/api/estado` y `/api/catalogo` 3–12 ms · Cita Precisa 1.5–1.8 s · Trámites 8.9 s · Razonamiento 11.5 s |
| ¿4 GiB se queda? | ✅ **Sí, con holgura**: el pico es 22 % del límite. Se mantiene 4 GiB por margen para 10 consultas simultáneas y para la caché de páginas del modelo |

---

## F5-11 — P14: acotar `run.developer` al servicio

**Objetivo:** que `protocolo01-v2-build` solo pueda desplegar `protocolo01-app-v2`, no cualquier
servicio (hoy podría tocar `protocolo01-app`).

```bash
gcloud run services add-iam-policy-binding $SERVICIO --region=$REGION \
  --member=serviceAccount:$SA_BUILD --role=roles/run.developer
gcloud projects remove-iam-policy-binding $PROYECTO \
  --member=serviceAccount:$SA_BUILD --role=roles/run.developer --condition=None
```

| Dato | Valor |
|---|---|
| Permiso a nivel servicio | ✅ `roles/run.developer` de `protocolo01-v2-build` **solo** sobre `protocolo01-app-v2` |
| Permiso a nivel proyecto retirado | ✅ a nivel proyecto le queda solo `roles/logging.logWriter` |
| Otros servicios | Sin cambios: `protocolo01-app` e `ia-legal-mexicana-web` siguen con su política (`allUsers` invocador) |
| Autorización | Responsable, 2026-10-13. Se valida en F5-12 que los permisos acotados alcancen para desplegar |

---

## F5-12 — Probar el despliegue normal

**Objetivo:** validar el camino de todos los días (construir ligera + desplegar) con los permisos ya
acotados de F5-11.

```bash
gcloud builds submit --config cloudbuild.yaml --region=$REGION
gcloud run revisions list --service=$SERVICIO --region=$REGION --limit=3
```

| Dato | Valor |
|---|---|
| Build | `94f16751-0909-4e86-b4ce-343c5c4f7783` · **SUCCESS** en 3 min 8 s · los 4 pasos (`verificar-servicio`, `construir-ligera`, `subir-ligera`, `desplegar`) en verde |
| Revisión nueva lista | ✅ `protocolo01-app-v2-00002-7f2` (09:42:26 UTC) |
| Tráfico en la revisión nueva | ✅ 100 % en `00002`; `00001-fl7` queda disponible para volver atrás |
| Configuración conservada | ✅ 2 vCPU · 4 GiB · `protocolo01-v2-run` · `maxScale: 2` (el despliegue solo cambió la imagen) |
| Permisos acotados (F5-11) | ✅ alcanzan: el build desplegó con `run.developer` solo sobre el servicio |
| Sigue privado | ✅ 403 sin token |
| Autorización | Responsable, 2026-10-13 |

---

## F5-13 — D6: decidir límites de uso

**Decisión del responsable**, con los datos de F5-09 y F5-10. Ya existen: `maxScale: 2`,
`containerConcurrency: 10`, consulta ≤ 4000 caracteres (`main.py`). Opciones adicionales:
límite de gasto en la cuenta de DeepSeek; alerta de presupuesto en Google Cloud; Cloud Armor
(requiere balanceador, Fase 6).

| Decisión | Valor |
|---|---|
| `maxScale` final | **2** (decidido por el responsable el 2026-10-13): máx. 2 instancias × 10 consultas = 20 simultáneas |
| Límites adicionales | Límite de gasto en **DeepSeek** y alerta de **presupuesto en Google Cloud**: los configura **el responsable** por su cuenta (P18) · Cloud Armor: no por ahora |

---

## F5-14 — Cierre y paso a Fase 6

| Decisión | Valor |
|---|---|
| Imágenes locales `:local` | Borradas (aprobado): `protocolo01-v2-app:local` y `protocolo01-v2-pesada:local` |
| Pendientes cerrados | P4 (límites de uso), P14 (`run.developer` acotado), P18 (límites externos: el responsable los da por resueltos) |
| Pendientes abiertos en esta fase | P16 (borrar `mi-proyecto-axiomas`), P17 (Cita Precisa FCE con acentos) |
| D5: dominio propio | **No** (decidido por el responsable; solo si fuera gratis, y registrar un dominio cuesta). Se usa la URL `*.run.app`, gratuita |
| ¿Pasar a Fase 6 (hacerlo público)? | ☑ Sí — confirmado por el responsable el 2026-10-13 |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F5-09 | **Cita Precisa no encuentra artículos en FCE.** En la colección FCE, `titulo_documento` conserva los acentos (`estatuto orgánico del fondo de cultura económica`), pero `normalizar_titulo()` los quita (`estatuto organico del fondo de cultura economica`), así que el filtro exacto `$eq` de Chroma no coincide. Las otras bases sí guardan títulos sin acentos (`CLAUDE.md` §6). | Cita Precisa con base FCE falla en los títulos que llevan acento. Razonamiento sí funciona (búsqueda semántica sin filtro de título). **Muy probablemente no es nuevo:** `protocolo01-app` usa la misma lógica y los mismos datos (inferido, no probado contra el servicio viejo). | **No se corrige en el rehecho** (regla: no tocar la lógica ni el bucket). Pendiente P17 con dos caminos, a decidir aparte: (a) reingestar FCE con títulos normalizados; (b) que `logica_a` pruebe también el título con acentos (cambio al núcleo, requiere aprobación). |
| (previo) | `protocolo01-v2-build` no puede leer `gs://alma-juridica-aipp_cloudbuild`, donde `gcloud builds submit` deja el código. | El primer build fallaría al leer las fuentes. | F5-02. |
| F5-08 | `gcloud run services proxy` requiere el componente `google-cloud-cli-cloud-run-proxy` y, como `gcloud` está instalado con apt, se instala con `sudo apt-get` (7.5 MB / ~20 MB). | Ninguno. | Instalado por el responsable en la versión 550, igual a `gcloud`. |
| (previo) | Existe un tercer bucket, `mi-proyecto-axiomas` (4.79 MiB: `requirements.txt`, `legislacion-mx/`, `legislacion-unam/`, `scripts/`). | Ninguno para el plan. | **Decidido por el responsable: se borra** → P16 en `BITACORA-REMAKE.md` §5. No se toca en esta fase. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 5 con 14 mini-tareas. Verificado (solo lectura): repo vacío, servicio inexistente, falta permiso de la cuenta de build sobre el bucket de fuentes. |
| 2026-10-13 | F5-01 hecha (Claude, solo lectura): todo listo; único bloqueo conocido es el permiso de F5-02. |
| 2026-10-13 | F5-02 hecha (Claude, autorizado): `protocolo01-v2-build` puede leer el bucket de fuentes de Cloud Build. Decisión del responsable: borrar `mi-proyecto-axiomas` (P16). |
| 2026-10-13 | F5-03 hecha (Claude, autorizado): pesada `v1` construida en Cloud Build en 5 min 57 s (~$0.09); imports y modelo verificados. |
| 2026-10-13 | F5-04 hecha (Claude, solo lectura): `pesada:v1` en Artifact Registry, 1.73 GiB comprimida, digest `sha256:70a0988…`. |
| 2026-10-13 | F5-05 hecha (Claude, autorizado): ligera `protocolo01-v2-app:51c1e8fd-…` construida en 1 min 34 s, sin desplegar. |
| 2026-10-13 | F5-06 hecha (Claude, autorizado): servicio `protocolo01-app-v2` creado, revisión `00001-fl7` lista en 74 s; privado (403 sin token). |
| 2026-10-13 | Comentario de `deploy/service.yaml` corregido (aprobado). |
| 2026-10-13 | F5-07 hecha (Claude, solo lectura): arranque en la nube en ~27 s; las 6 bases reales copiadas y abiertas. |
| 2026-10-13 | F5-08 hecha (Claude, vía proxy): 6 bases reales disponibles con los conteos de F1-10; catálogo 45 títulos; servicio sigue privado (403 directo). |
| 2026-10-13 | F5-09 hecha (Claude, autorizado): General, Trámites SEGOB y Razonamiento ✅; Cita Precisa FCE ❌ por acentos en los títulos de la colección FCE (preexistente) → P17. |
| 2026-10-13 | F5-10 (Claude, solo lectura de logs): sin errores ni falta de memoria; apagado automático confirmado; arranque en frío 38 s + primera consulta 26 s. Falta la gráfica de memoria (consola). |
| 2026-10-13 | F5-10 completa con las métricas de la consola (`gconsole/`): pico de memoria 22 % de 4 GiB (~0.88 GiB); tmpfs ~184 MiB. 4 GiB confirmado. |
| 2026-10-13 | `gconsole/` borrada por el responsable (sus datos quedaron en F5-10). |
| 2026-10-13 | F5-11 hecha (Claude, autorizado): `run.developer` de `protocolo01-v2-build` acotado al servicio `protocolo01-app-v2`; retirado del proyecto. P14 cerrado (pendiente validar en F5-12). |
| 2026-10-13 | F5-12 hecha (Claude, autorizado): despliegue normal en 3 min 8 s → revisión `00002-7f2` con 100 % del tráfico; configuración y privacidad intactas; permisos acotados suficientes. |
| 2026-10-13 | F5-13 hecha (responsable): `maxScale: 2` definitivo; límite de DeepSeek y alerta de presupuesto los configura el responsable (P18). D6/P4 cerrados. |
| 2026-10-13 | F5-14 hecha: **Fase 5 completa.** `protocolo01-app-v2` en la nube, privado, revisión `00002-7f2`, probado con las 6 bases. Imágenes locales borradas. P18 resuelto por el responsable. D5: sin dominio propio. |
