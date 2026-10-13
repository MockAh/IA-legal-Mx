# BITÁCORA-REMAKE-F5 — Fase 5: construir y desplegar en la nube

Desglose de la **Fase 5** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** en curso
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
| F5-01 | Pre-vuelo (solo lectura) | Claude | — | ☐ |
| F5-02 | Permiso de lectura del bucket de fuentes para `protocolo01-v2-build` | Claude con autorización | Cambia IAM de ese bucket | ☐ |
| F5-03 | Construir la pesada `v1` en Cloud Build | Claude con autorización, o tú | ~$0.25–0.40 · crea imagen | ☐ |
| F5-04 | Verificar la pesada en Artifact Registry | Claude | — | ☐ |
| F5-05 | Construir la ligera sin desplegar (`_DESPLEGAR=no`) | Claude con autorización, o tú | minutos gratis · crea imagen | ☐ |
| F5-06 | Crear el servicio privado desde `deploy/service.yaml` | Claude con autorización, o tú | crea el servicio | ☐ |
| F5-07 | Revisar el arranque en la nube | Claude | — | ☐ |
| F5-08 | Probar estado y catálogo con las 6 bases reales | Claude | — | ☐ |
| F5-09 | Una consulta real por base (DeepSeek) | Claude, **con tu autorización** | ~4 llamadas | ☐ |
| F5-10 | Revisar memoria, tiempos y errores | Claude | — | ☐ |
| F5-11 | P14: acotar `run.developer` al servicio | Claude con autorización | Cambia IAM | ☐ |
| F5-12 | Probar el despliegue normal (`cloudbuild.yaml` completo) | Claude con autorización, o tú | minutos gratis · nueva revisión | ☐ |
| F5-13 | D6: decidir límites de uso | **Tú** | — | ☐ |
| F5-14 | Cierre y paso a Fase 6 | Claude propone, tú decides | — | ☐ |

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
| Rama al día | |
| Cuenta / proyecto | |
| Archivos a subir | |
| Repo vacío / servicio inexistente | |
| Cuentas y secreto | |

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
| Permiso aplicado | |

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
| ID del build | |
| Duración | |
| `imports ok` / `modelo ok 1024` | |
| Costo aproximado | |

---

## F5-04 — Verificar la pesada en Artifact Registry

```bash
gcloud artifacts docker images list $AR --include-tags --format="table(package,tags,createTime)"
gcloud artifacts docker images describe $AR/protocolo01-v2-pesada:v1 --format="value(image_summary.digest)"
gcloud artifacts repositories describe protocolo01-v2 --location=$REGION --format="value(sizeBytes)"
```

| Dato | Valor |
|---|---|
| Etiqueta `v1` presente | |
| Digest | |
| Tamaño en el repositorio | |

---

## F5-05 — Construir la ligera sin desplegar

**Objetivo:** primera imagen ligera; el servicio aún no existe, así que se construye sin desplegar.

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_DESPLEGAR=no --region=$REGION
```

| Dato | Valor |
|---|---|
| ID del build (= etiqueta de la imagen) | |
| Duración | |
| Imagen | `$AR/protocolo01-v2-app:<BUILD_ID>` |

---

## F5-06 — Crear el servicio privado desde `deploy/service.yaml`

**Objetivo:** crear `protocolo01-app-v2` con toda su configuración (4 GiB, 2 vCPU, bucket en
solo lectura, secreto, cuenta `protocolo01-v2-run`, `minScale: 0`, `maxScale: 2`).

```bash
sed "s|IMAGEN_INICIAL|$AR/protocolo01-v2-app:<BUILD_ID>|" deploy/service.yaml \
  | gcloud run services replace - --region=$REGION
gcloud run services get-iam-policy $SERVICIO --region=$REGION   # sin allUsers
```

**Efecto:** crea el servicio. **No es público**: sin `allUsers`, cualquier petición sin token
recibe 403.

| Dato | Valor |
|---|---|
| Revisión creada | |
| URL | |
| ¿Público? | No (verificado) |

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
| Bases copiadas | |
| Tiempo de arranque | |
| Revisión lista | |

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
| Sin token (403) | |
| `/api/estado` | |
| `/api/catalogo` | |
| `/` con token | |

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
| Primera consulta en frío (tiempo) | |
| General | |
| FCE | |
| Trámites SEGOB | |
| Razonamiento (streaming a través de Cloud Run) | |

---

## F5-10 — Revisar memoria, tiempos y errores

```bash
gcloud run services logs read $SERVICIO --region=$REGION --limit=100 | grep -iE "error|memory|killed|exceeded"
```

Más la consola: Cloud Run → `protocolo01-app-v2` → Métricas → *Container memory utilization*.

| Dato | Valor |
|---|---|
| Memoria máxima usada (de 4 GiB) | |
| Errores / reinicios | |
| ¿4 GiB se queda? | |

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
| Permiso a nivel servicio | |
| Permiso a nivel proyecto retirado | |

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
| Build | |
| Revisión nueva lista | |
| Tráfico en la revisión nueva | |

---

## F5-13 — D6: decidir límites de uso

**Decisión del responsable**, con los datos de F5-09 y F5-10. Ya existen: `maxScale: 2`,
`containerConcurrency: 10`, consulta ≤ 4000 caracteres (`main.py`). Opciones adicionales:
límite de gasto en la cuenta de DeepSeek; alerta de presupuesto en Google Cloud; Cloud Armor
(requiere balanceador, Fase 6).

| Decisión | Valor |
|---|---|
| `maxScale` final | |
| Límites adicionales | |

---

## F5-14 — Cierre y paso a Fase 6

| Decisión | Valor |
|---|---|
| Imágenes locales `:local` | (borrar o conservar) |
| Pendientes cerrados | |
| ¿Pasar a Fase 6 (hacerlo público)? | ☐ Sí ☐ No — motivo: |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| (previo) | `protocolo01-v2-build` no puede leer `gs://alma-juridica-aipp_cloudbuild`, donde `gcloud builds submit` deja el código. | El primer build fallaría al leer las fuentes. | F5-02. |
| (previo) | Existe un tercer bucket, `mi-proyecto-axiomas`, no revisado. | Ninguno para el plan. | Informativo; no se toca. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 5 con 14 mini-tareas. Verificado (solo lectura): repo vacío, servicio inexistente, falta permiso de la cuenta de build sobre el bucket de fuentes. |
