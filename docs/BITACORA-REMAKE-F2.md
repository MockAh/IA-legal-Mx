# BITÁCORA-REMAKE-F2 — Fase 2: crear el entorno en Google Cloud

Desglose de la **Fase 2** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-12
- **Estado:** completada (2026-10-13). Fase 3 autorizada.
- **Objetivo:** dejar listo en `alma-juridica-aipp` todo lo que necesitan las imágenes y el
  servicio `protocolo01-app-v2`: APIs, repositorio de imágenes, cuentas de servicio, permisos
  y la clave nueva de DeepSeek. **No se construye ni se despliega nada todavía** (Fase 5).

## Reglas de esta fase

1. **Esta fase sí crea recursos.** Cada mini-tarea que cambia algo en Google Cloud la ejecuta
   el responsable, o Claude con autorización explícita **para esa mini-tarea**.
2. **No se toca nada existente:** ni `protocolo01-app`, ni `ia-legal-mexicana-web`, ni sus
   imágenes, ni el contenido del bucket. Solo se **agregan** recursos y permisos nuevos.
3. **El bucket se conserva tal cual.** Agregar un permiso de lectura al bucket cambia su
   política IAM, no sus datos.
4. **No se toca la lógica del backend** ni ningún archivo del repo, salvo las bitácoras.
5. **La clave de DeepSeek no pasa por Claude.** La genera y la carga el responsable.
6. Cada mini-tarea termina con su casilla marcada y sus datos anotados.

## Variables de la sesión

```bash
export PROYECTO=alma-juridica-aipp
export NUM_PROYECTO=879901246493
export REGION=us-central1
export BUCKET=chromadb-alma-juridica-aipp
export REPO_AR=protocolo01-v2
export SA_RUN=protocolo01-v2-run@$PROYECTO.iam.gserviceaccount.com
export SA_BUILD=protocolo01-v2-build@$PROYECTO.iam.gserviceaccount.com
```

## Punto de partida (verificado el 2026-10-12, solo lectura)

| Pieza | Estado |
|---|---|
| Facturación | Activa |
| APIs ya habilitadas | `run`, `cloudbuild`, `artifactregistry`, `secretmanager`, `iam`, `logging`, `storage`, `compute`, `containerregistry`, `serviceusage` |
| API que falta | `cloudresourcemanager` (para leer y editar el IAM del proyecto) |
| Secreto `DEEPSEEK_API_KEY` | Existe, 1 versión (2026-03-19); lo usa `protocolo01-app` |

---

## Resumen de mini-tareas

| # | Mini-tarea | Quién | Cambia algo | Estado |
|---|---|---|---|---|
| F2-01 | Habilitar la API `cloudresourcemanager` | Claude con autorización, o tú | Sí | ☑ |
| F2-02 | Revisar el IAM del proyecto (P2) | Claude | No | ☑ |
| F2-03 | Crear el repositorio de imágenes `protocolo01-v2` | Claude con autorización, o tú | Sí | ☑ |
| F2-04 | Crear la cuenta de servicio `protocolo01-v2-run` | Claude con autorización, o tú | Sí | ☑ |
| F2-05 | Crear la cuenta de servicio `protocolo01-v2-build` | Claude con autorización, o tú | Sí | ☑ |
| F2-06 | Permisos de `protocolo01-v2-run` | Claude con autorización, o tú | Sí | ☑ |
| F2-07 | Permisos de `protocolo01-v2-build` | Claude con autorización, o tú | Sí | ☑ |
| F2-08 | Clave nueva de DeepSeek como versión 2 del secreto (P1) | **Solo tú** | Sí | ☑ |
| F2-09 | Verificar todo lo creado | Claude | No | ☑ |
| F2-10 | Cierre y paso a Fase 3 | Claude propone, tú decides | No | ☑ |

Total estimado: **~2.5 h**.

---

## F2-01 — Habilitar la API `cloudresourcemanager`

**Objetivo:** poder leer (F2-02) y editar (F2-07) el IAM a nivel proyecto. Es la única API que
falta; las demás ya están habilitadas.

```bash
gcloud services enable cloudresourcemanager.googleapis.com --project=$PROYECTO
gcloud services list --enabled --project=$PROYECTO --filter="config.name:cloudresourcemanager" --format="value(config.name)"
```

**Efecto sobre lo existente:** ninguno. Habilitar una API no cambia servicios ni permisos y no
tiene costo por sí misma.

**Hecho cuando:** el segundo comando imprime `cloudresourcemanager.googleapis.com`.

| Dato | Valor |
|---|---|
| Habilitada | ✅ 2026-10-13 (operación `acat.p2-879901246493-9dcef1a3…`) |
| Ejecutó | Claude, con autorización del responsable |

---

## F2-02 — Revisar el IAM del proyecto (P2)

**Objetivo:** saber quién tiene qué rol en el proyecto, sin cambiar nada. Responde la duda de
F1-12: si la cuenta de cómputo por defecto es Editor (y por tanto dueña del bucket).

```bash
gcloud projects get-iam-policy $PROYECTO --format=json \
  | python3 -c "import json,sys; [print(b['role'], '←', ', '.join(b['members'])) for b in json.load(sys.stdin)['bindings']]"
gcloud iam service-accounts list --project=$PROYECTO --format="table(email,displayName,disabled)"
```

**Hecho cuando:** la tabla está llena.

| Miembro | Roles en el proyecto | Tipo |
|---|---|---|
| `user:g.olin.xy@gmail.com` | `owner`, `run.admin`, `storage.admin`, `cloudbuild.builds.editor`, `artifactregistry.reader`, `iam.serviceAccountUser` | **Única persona** |
| `879901246493-compute@developer…` | **`editor`**, `storage.objectViewer` | Cuenta de cómputo por defecto (la usa `protocolo01-app`) |
| `879901246493@cloudservices…` | `editor` | Agente de las APIs de Google (administrado por Google, estándar) |
| `879901246493@cloudbuild…` | `cloudbuild.builds.builder` | Cuenta heredada de Cloud Build (construía las imágenes `gcr.io`) |
| `service-879901246493@gcp-sa-*` / `@compute-system` / `@containerregistry` / `@serverless-robot-prod` | `*.serviceAgent` (artifactregistry, cloudbuild, compute, containerregistry, pubsub, run) | Agentes de servicio de Google (estándar, no se tocan) |

| Cuenta de servicio existente | Descripción |
|---|---|
| `879901246493-compute@developer.gserviceaccount.com` | Default compute service account (habilitada). Es la única creada en el proyecto. |

¿La cuenta de cómputo `879901246493-compute@…` es `roles/editor`? ☑ Sí ☐ No
(Si sí: se anota en §Hallazgos. **No se le quita** en esta fase, porque `protocolo01-app` la usa.)

---

## F2-03 — Crear el repositorio de imágenes `protocolo01-v2`

**Objetivo:** el lugar donde vivirán `protocolo01-v2-pesada` y `protocolo01-v2-app`, separado
de `gcr.io` y de `ia-legal-repo`.

```bash
gcloud artifacts repositories create $REPO_AR \
  --repository-format=docker --location=$REGION \
  --description="Imágenes de Wall-E Legal 2.0 (protocolo01-v2)" --project=$PROYECTO

gcloud artifacts repositories describe $REPO_AR --location=$REGION --project=$PROYECTO \
  --format="value(name,format,createTime)"
```

**Costo:** solo almacenamiento de imágenes. La pesada pesará unos 4–5 GB; conviene
limpiar versiones viejas cuando se acumulen.

**Hecho cuando:** `describe` muestra el repositorio.

| Dato | Valor |
|---|---|
| Ruta de imágenes | `us-central1-docker.pkg.dev/alma-juridica-aipp/protocolo01-v2/` |
| Creado | ✅ 2026-10-13 06:09 UTC · DOCKER · us-central1 · cifrado administrado por Google · 0 MB · Claude, autorizado |

---

## F2-04 — Crear la cuenta de servicio `protocolo01-v2-run`

**Objetivo:** la identidad con la que correrá `protocolo01-app-v2`. Reemplaza el uso de la cuenta
de cómputo por defecto en el servicio nuevo.

```bash
gcloud iam service-accounts create protocolo01-v2-run \
  --display-name="protocolo01-v2: ejecución Cloud Run" \
  --description="Corre protocolo01-app-v2. Solo lee el bucket y el secreto de DeepSeek." \
  --project=$PROYECTO

gcloud iam service-accounts describe $SA_RUN --format="value(email,disabled)"
```

**Hecho cuando:** `describe` muestra la cuenta, sin deshabilitar. Se crea **sin roles**; los
permisos se dan en F2-06.

| Dato | Valor |
|---|---|
| Correo | `protocolo01-v2-run@alma-juridica-aipp.iam.gserviceaccount.com` |
| Creada | ✅ 2026-10-13 · habilitada · ID único `117354294396600683340` · sin roles · Claude, autorizado |

---

## F2-05 — Crear la cuenta de servicio `protocolo01-v2-build`

**Objetivo:** la identidad con la que Cloud Build construirá las imágenes y desplegará.

```bash
gcloud iam service-accounts create protocolo01-v2-build \
  --display-name="protocolo01-v2: Cloud Build" \
  --description="Construye las imágenes protocolo01-v2 y despliega protocolo01-app-v2." \
  --project=$PROYECTO

gcloud iam service-accounts describe $SA_BUILD --format="value(email,disabled)"
```

**Hecho cuando:** `describe` muestra la cuenta. Sin roles todavía (F2-07).

| Dato | Valor |
|---|---|
| Correo | `protocolo01-v2-build@alma-juridica-aipp.iam.gserviceaccount.com` |
| Creada | ✅ 2026-10-13 · habilitada · ID único `108908371421868541000` · sin roles · Claude, autorizado |

---

## F2-06 — Permisos de `protocolo01-v2-run`

**Objetivo:** que el servicio pueda **leer** el bucket (montarlo como volumen) y **leer** el
secreto. Nada más.

```bash
# Leer objetos del bucket (no puede escribir ni borrar)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA_RUN --role=roles/storage.objectViewer

# Leer el secreto de DeepSeek (solo este secreto, no todos)
gcloud secrets add-iam-policy-binding DEEPSEEK_API_KEY \
  --member=serviceAccount:$SA_RUN --role=roles/secretmanager.secretAccessor --project=$PROYECTO
```

**Efecto sobre lo existente:** se agrega un miembro a la política del bucket y del secreto.
Los miembros actuales (incluida la cuenta de cómputo que usa `protocolo01-app`) no cambian.

**Hecho cuando:** ambos permisos aparecen en la verificación de F2-09.

| Permiso | Sobre | Aplicado |
|---|---|---|
| `roles/storage.objectViewer` | bucket `chromadb-alma-juridica-aipp` | ✅ 2026-10-13 (comparte el rol con la cuenta de cómputo, que sigue igual) |
| `roles/secretmanager.secretAccessor` | secreto `DEEPSEEK_API_KEY` | ✅ 2026-10-13 (comparte el rol con la cuenta de cómputo, que sigue igual) |

---

## F2-07 — Permisos de `protocolo01-v2-build`

**Objetivo:** que Cloud Build pueda bajar el modelo del bucket, subir imágenes **solo** a
`protocolo01-v2`, desplegar el servicio y escribir sus logs. Los permisos se dan al nivel más
estrecho posible.

```bash
# Leer el modelo del bucket (para hornearlo en la imagen pesada)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$SA_BUILD --role=roles/storage.objectViewer

# Subir y leer imágenes, solo en el repositorio protocolo01-v2
gcloud artifacts repositories add-iam-policy-binding $REPO_AR --location=$REGION \
  --member=serviceAccount:$SA_BUILD --role=roles/artifactregistry.writer --project=$PROYECTO

# Desplegar en Cloud Run y escribir logs de build (nivel proyecto)
gcloud projects add-iam-policy-binding $PROYECTO \
  --member=serviceAccount:$SA_BUILD --role=roles/run.developer --condition=None
gcloud projects add-iam-policy-binding $PROYECTO \
  --member=serviceAccount:$SA_BUILD --role=roles/logging.logWriter --condition=None

# Poder asignar protocolo01-v2-run al servicio (solo esa cuenta, no todas)
gcloud iam service-accounts add-iam-policy-binding $SA_RUN \
  --member=serviceAccount:$SA_BUILD --role=roles/iam.serviceAccountUser --project=$PROYECTO
```

> `roles/run.developer` a nivel proyecto permite desplegar cualquier servicio de Cloud Run del
> proyecto. Cuando `protocolo01-app-v2` exista (Fase 5) se puede acotar a ese servicio.

**Hecho cuando:** los 5 permisos aparecen en la verificación de F2-09.

| Permiso | Sobre | Aplicado |
|---|---|---|
| `roles/storage.objectViewer` | bucket | ✅ |
| `roles/artifactregistry.writer` | repositorio `protocolo01-v2` | ✅ |
| `roles/run.developer` | proyecto | ✅ (acotar al servicio en Fase 5 → P14) |
| `roles/logging.logWriter` | proyecto | ✅ |
| `roles/iam.serviceAccountUser` | cuenta `protocolo01-v2-run` | ✅ |

---

## F2-08 — Clave nueva de DeepSeek como versión 2 del secreto (P1)

**Objetivo:** que `protocolo01-app-v2` arranque con una clave que nunca estuvo en texto plano.
**La hace solo el responsable:** la clave no debe pasar por Claude ni quedar en el historial
de la terminal.

1. En el panel de DeepSeek, generar una clave nueva. **No revocar la vieja todavía**: la sigue
   usando `protocolo01-app` (P10).
2. Cargarla como versión nueva del secreto existente, sin que quede en el historial:

```bash
read -rs -p "Clave nueva de DeepSeek: " CLAVE && echo
printf '%s' "$CLAVE" | gcloud secrets versions add DEEPSEEK_API_KEY --data-file=- --project=$PROYECTO
unset CLAVE

gcloud secrets versions list DEEPSEEK_API_KEY --project=$PROYECTO --format="table(name,state,createTime)"
```

**Efecto sobre lo existente:** `protocolo01-app` lee la versión `latest`. Las instancias que ya
corren conservan la clave vieja; **las que arranquen después tomarán la nueva**. Como ambas
claves serán válidas hasta P10, el servicio viejo sigue funcionando.

**Hecho cuando:** `versions list` muestra la versión 2 `enabled`.

| Dato | Valor |
|---|---|
| Versión 2 creada | ✅ 2026-10-13 06:37 UTC, `enabled` (cargada por el responsable; Claude no leyó el valor). Primer intento falló con `Secret Payload cannot be empty` (variable vacía); no creó nada. |
| Clave vieja revocada | **No** (se hace en P10, después de validar) |

---

## F2-09 — Verificar todo lo creado (solo lectura)

**Objetivo:** comprobar en una sola pasada que todo está y con los permisos justos.

```bash
echo "== Repositorio";  gcloud artifacts repositories describe $REPO_AR --location=$REGION --format="value(name)"
echo "== Cuentas";      gcloud iam service-accounts list --filter="email~protocolo01-v2" --format="value(email)"
echo "== Bucket";       gcloud storage buckets get-iam-policy gs://$BUCKET --format=json | grep -B2 -A2 protocolo01-v2
echo "== Secreto";      gcloud secrets get-iam-policy DEEPSEEK_API_KEY --format=json | grep -B2 -A2 protocolo01-v2
echo "== Repo AR";      gcloud artifacts repositories get-iam-policy $REPO_AR --location=$REGION --format=json | grep -B2 -A2 protocolo01-v2
echo "== Proyecto";     gcloud projects get-iam-policy $PROYECTO --format=json | grep -B3 protocolo01-v2-build
echo "== Act-as";       gcloud iam service-accounts get-iam-policy $SA_RUN --format=json | grep -B2 -A2 protocolo01-v2-build
echo "== Sin cambios";  gcloud run services list --region=$REGION --format="value(metadata.name)"
```

**Hecho cuando:** todo aparece y la última línea sigue mostrando solo `protocolo01-app` e
`ia-legal-mexicana-web` (nada existente se tocó).

| Verificación | Resultado |
|---|---|
| Repositorio | ✅ `protocolo01-v2`, vacío |
| 2 cuentas de servicio | ✅ `protocolo01-v2-run` y `protocolo01-v2-build`, habilitadas |
| Permisos de `protocolo01-v2-run` (2) | ✅ objectViewer (bucket) · secretAccessor (secreto). Ninguno más. |
| Permisos de `protocolo01-v2-build` (5) | ✅ objectViewer (bucket) · artifactregistry.writer (repo) · run.developer + logging.logWriter (proyecto) · serviceAccountUser (solo sobre `-run`). Ninguno más. |
| Servicios existentes sin cambios | ✅ `protocolo01-app` sigue en `00013-6zv`; `ia-legal-mexicana-web` en `00040-qpj` |
| Bucket sin cambios | ✅ 78 objetos, 2 472 038 537 bytes (2.30 GiB), igual que en F1 |
| Secreto | ✅ versiones 1 y 2 habilitadas |

---

## F2-10 — Cierre y paso a Fase 3

**Objetivo:** revisar hallazgos y decidir si se pasa a la Fase 3 (los archivos del repo:
`requirements.txt`, Dockerfiles, `startup.sh`, `cloudbuild*.yaml`, `deploy/service.yaml`,
`.gcloudignore`).

| Decisión | Valor |
|---|---|
| Bloqueos para la Fase 3 | Ninguno |
| Pendientes cerrados en esta fase | P1 (clave nueva, versión 2) · P2 (IAM del proyecto revisado) |
| Pendientes abiertos en esta fase | P13 (quitar `editor` a la cuenta de cómputo) · P14 (acotar `run.developer`) |
| ¿Pasar a Fase 3? | ☑ Sí — confirmado por el responsable el 2026-10-13 |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F2-02 | La cuenta de cómputo por defecto es **Editor del proyecto**: puede leer, escribir y **borrar** en el bucket, y modificar casi cualquier recurso. Su `storage.objectViewer` es redundante. | Cualquier código que corra como esa cuenta (hoy `protocolo01-app` e `ia-legal-mexicana-web`) podría borrar el acervo. | No se cambia ahora (la usa `protocolo01-app`). Nuevo pendiente P13: quitarle `editor` cuando el servicio viejo se retire. `protocolo01-app-v2` usará `protocolo01-v2-run`, que solo lee. |
| F2-02 | La cuenta heredada `@cloudbuild` tiene `cloudbuild.builds.builder`, que incluye permisos de escritura en Storage del proyecto. | Los builds viejos podrían escribir en buckets. | Informativo. Los builds nuevos usan `protocolo01-v2-build`. Revisar en §5 Limpieza. |
| F2-02 | Tu usuario tiene roles redundantes con `owner` (`run.admin`, `storage.admin`, etc.). | Ninguno. | Ninguna. |
| F2-08 | `protocolo01-app` lee `latest`: sus instancias nuevas ya usan la clave nueva. | Si la clave nueva tuviera un error, el servicio viejo fallaría en cuanto arranque una instancia nueva. | Probar el servicio viejo con una consulta; si falla, deshabilitar la versión 2 (`gcloud secrets versions disable 2 --secret=DEEPSEEK_API_KEY`) y repetir F2-08. |
| (previo) | Solo falta habilitar `cloudresourcemanager`; el resto de las APIs ya está. | F2-01 se reduce a una API. | Ninguna. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-12 | Se crea la bitácora de Fase 2 con 10 mini-tareas. Verificado (solo lectura): facturación activa; solo falta la API `cloudresourcemanager`. |
| 2026-10-13 | F2-01 hecha (Claude, autorizado): API `cloudresourcemanager` habilitada. Revertible con `gcloud services disable cloudresourcemanager.googleapis.com`. |
| 2026-10-13 | F2-02 hecha (Claude, solo lectura): única persona = responsable (owner). La cuenta de cómputo es `editor` → P2 cerrado, abre P13. |
| 2026-10-13 | F2-03 hecha (Claude, autorizado): repositorio `protocolo01-v2` creado en us-central1 (vacío). |
| 2026-10-13 | F2-04 hecha (Claude, autorizado): cuenta `protocolo01-v2-run` creada, sin roles. |
| 2026-10-13 | F2-05 hecha (Claude, autorizado): cuenta `protocolo01-v2-build` creada, sin roles. |
| 2026-10-13 | F2-06 hecha (Claude, autorizado): `protocolo01-v2-run` puede leer el bucket y el secreto `DEEPSEEK_API_KEY`. Miembros previos sin cambios. |
| 2026-10-13 | F2-07 hecha (Claude, autorizado): 5 permisos a `protocolo01-v2-build`. `run.developer` queda a nivel proyecto hasta la Fase 5 (P14). |
| 2026-10-13 | F2-08 hecha (responsable): versión 2 del secreto `DEEPSEEK_API_KEY` habilitada. Versión 1 sigue activa hasta P10. P1 cerrado. |
| 2026-10-13 | F2-09 hecha (Claude, solo lectura): todo lo creado está y con permisos justos; servicios, bucket y secreto existentes sin cambios. |
| 2026-10-13 | F2-10 hecha: **Fase 2 completa.** Recursos creados: API `cloudresourcemanager`, repo `protocolo01-v2`, cuentas `protocolo01-v2-run` y `-build` con 7 permisos, versión 2 del secreto. Nada existente modificado. |
