# BITÁCORA-REMAKE-F6 — Fase 6: abrir la app a internet

Desglose de la **Fase 6** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** en curso — pausa el 2026-10-13 tras F6-04; se retoma en **F6-05**
- **Objetivo:** que `protocolo01-app-v2` se pueda usar desde cualquier navegador en
  `https://protocolo01-app-v2-879901246493.us-central1.run.app`, verificarlo desde fuera,
  vigilar las primeras horas y dejar documentado cómo operar el sistema nuevo.

## Reglas de esta fase

1. **Hacerlo público es un cambio visible para todos.** F6-02 se ejecuta solo con autorización
   explícita, y se puede revertir en segundos (F6-02, *Cómo revertir*).
2. **No se toca nada existente:** `protocolo01-app`, `ia-legal-mexicana-web`, el bucket y sus
   imágenes siguen igual. Su retiro es la limpieza (§5 de `BITACORA-REMAKE.md`), aparte.
3. **No se toca la lógica del backend.** P17 (FCE) se resuelve después del rehecho.
4. **Las llamadas a DeepSeek cuestan.** Las pruebas públicas se limitan a lo indicado.
5. Cada mini-tarea termina con su casilla marcada y sus datos anotados.

## Punto de partida (verificado el 2026-10-13)

| Pieza | Estado |
|---|---|
| Servicio | `protocolo01-app-v2`, revisión `00002-7f2` con 100 % del tráfico; privado (403 sin token) |
| Configuración | 2 vCPU · 4 GiB · `minScale: 0` · `maxScale: 2` · concurrencia 10 · bucket en solo lectura |
| Límites externos (P18) | Límite de gasto en DeepSeek y alerta de presupuesto: configurados por el responsable |
| Política de organización | El proyecto **no pertenece a una organización** → no hay *Domain Restricted Sharing* que bloquee `allUsers` |
| Dominio | Sin dominio propio (D5); se usa la URL `*.run.app` |
| Conocido | Cita Precisa con base FCE no encuentra artículos con títulos acentuados (P17) |

---

## Resumen de mini-tareas

| # | Mini-tarea | Quién | Efecto | Estado |
|---|---|---|---|---|
| F6-01 | Pre-vuelo público (solo lectura) | Claude | — | ☑ |
| F6-02 | Hacer público el servicio (`allUsers` → invocador) | Claude, **con tu autorización** | **Cualquiera puede usarlo** | ☑ |
| F6-03 | Verificar desde fuera, sin credenciales | Claude | — | ☑ |
| F6-04 | Probar desde otro dispositivo y red (celular con datos) | **Tú** | 1–2 consultas | ☑ |
| F6-05 | Revisar los logs desde la apertura (ventana acumulada; repetir a los 7 días) | Claude | — | ◐ 1.ª pasada; 2.ª en la etapa E (2026-10-20) |
| F6-06 | Decidir sobre `/api/docs` (Swagger público) | **Tú** | — | ☑ diferida → P20 |
| F6-07 | Actualizar `CLAUDE.md` y `readme.md` con la arquitectura nueva | Claude propone, tú apruebas | Cambia documentación | ☑ |
| F6-08 | Guía de operación (desplegar, revertir, actualizar acervo) | Claude propone, tú apruebas | Archivo nuevo en `docs/` | ☑ |
| F6-09 | Plan de limpieza del esquema viejo (orden y fechas) | Claude propone, tú decides | — (solo plan) | ☑ aprobado; etapa A ✅; v1 "dormida" (2026-10-16) |
| F6-10 | Unir la rama `remake/protocolo01-v2` a `master` (PR) | Tú decides | Git / GitHub | ☐ |
| F6-11 | Cierre del rehecho | Claude propone, tú decides | — | ☐ |

Total estimado: **~2.5 h** (más la espera de F6-05).

---

## F6-01 — Pre-vuelo público (solo lectura)

```bash
gcloud run services describe protocolo01-app-v2 --region=us-central1 \
  --format="value(status.latestReadyRevisionName,status.traffic[0].percent,spec.template.spec.containers[0].resources.limits)"
gcloud run services get-iam-policy protocolo01-app-v2 --region=us-central1
curl -s -o /dev/null -w "%{http_code}\n" https://protocolo01-app-v2-879901246493.us-central1.run.app/   # 403
```

| Dato | Valor |
|---|---|
| Revisión y tráfico | ✅ `00002-7f2`, 100 %, lista · 2 vCPU · 4 GiB |
| Política actual | Solo `protocolo01-v2-build` como `run.developer`; **sin `allUsers`** |
| Respuesta sin token | 403 (privado) · 0 errores en los logs |

---

## F6-02 — Hacer público el servicio

```bash
gcloud run services add-iam-policy-binding protocolo01-app-v2 --region=us-central1 \
  --member=allUsers --role=roles/run.invoker
```

**Efecto:** cualquiera con la URL puede abrir el front y hacer consultas (que gastan DeepSeek,
dentro de los límites de P18 y `maxScale: 2`).

**Cómo revertir** (vuelve a privado en segundos):

```bash
gcloud run services remove-iam-policy-binding protocolo01-app-v2 --region=us-central1 \
  --member=allUsers --role=roles/run.invoker
```

| Dato | Valor |
|---|---|
| Aplicado | ✅ 2026-10-13: `allUsers` → `roles/run.invoker`. Sin token: **200** |
| Autorización | Responsable, explícita ("¡Hazlo público! ¡Ya!") |

---

## F6-03 — Verificar desde fuera, sin credenciales

```bash
U=https://protocolo01-app-v2-879901246493.us-central1.run.app
for p in / /web/app.js /web/app.css /api/estado /api/catalogo "/web/app.js:Zone.Identifier"; do
  curl -s -o /dev/null -w "$p → %{http_code} (%{time_total}s)\n" "$U$p"; done
curl -sI $U/ | grep -iE "^(content-type|strict-transport|server)"
```

Sin consultas a DeepSeek (las hace F6-04).

| Prueba | Resultado |
|---|---|
| Front (`/`, `app.js`, `app.css`) | ✅ 200 / 200 / 200 (0.2–0.7 s) · título *"Asistente Legal Mexicano"* |
| `/api/estado` (6 bases) | ✅ basic 3688 · segob 3169 · transp 413 · 3p 935 · fce 3080 · tramites 81; las 3 bases del front completas |
| `/api/catalogo` | ✅ 45 títulos |
| `Zone.Identifier` (404) | ✅ 404 |
| HTTPS | ✅ HTTP/2 con `Google Frontend`; `http://` redirige con 302 a `https://`; HTTP/3 anunciado (`alt-svc`) |
| `HEAD /` | 405: `main.py` solo acepta `GET` en `/`. Ver §Hallazgos |

---

## F6-04 — Probar desde otro dispositivo y red

**Tú**, desde el celular **con datos móviles** (no la red de casa):

1. Abrir la URL.
2. Revisar las tres pestañas: Cita Precisa, Razonamiento Jurídico, Catálogo FAISS.
3. Hacer 1–2 consultas (p. ej. Cita Precisa General y Razonamiento).
4. Anotar si algo se ve mal en pantalla chica.

| Prueba | Resultado |
|---|---|
| Carga en celular | ✅ (responsable, smartphone con datos móviles) |
| Tres pestañas | ✅ |
| Consultas | ✅ "todo en orden" |
| Problemas de diseño | Ninguno reportado |

---

## F6-05 — Revisar los logs desde la apertura (ventana acumulada)

El uso real es **intermitente**: no hay una hora continua de tráfico que observar. Se revisa
todo lo recibido desde la apertura (2026-10-13); los logs se conservan 30 días. Se repite a
los 7 días.

`gcloud logging read` solo mira el último día por omisión: por eso `--freshness=7d`.

```bash
S='resource.type="cloud_run_revision" AND resource.labels.service_name="protocolo01-app-v2"'

# Errores
gcloud logging read "$S AND severity>=WARNING" --freshness=7d --limit=50

# Consultas (incluye /api/consulta/stream)
gcloud logging read "$S AND httpRequest.requestUrl:\"/api/consulta\"" --freshness=7d \
  --format="value(timestamp,httpRequest.status,httpRequest.latency,httpRequest.remoteIp)" --limit=100

# Arranques en frío (uno por instancia nueva)
gcloud logging read "$S AND textPayload:\"Iniciando Wall-E\"" --freshness=7d \
  --format="value(timestamp,resource.labels.revision_name)" --limit=50

# Tráfico inesperado: rutas que no existen o la doc de la API
gcloud logging read "$S AND (httpRequest.status=404 OR httpRequest.requestUrl:\"/api/docs\")" --freshness=7d \
  --format="value(timestamp,httpRequest.status,httpRequest.requestUrl,httpRequest.remoteIp)" --limit=50
```

**1.ª pasada (2026-10-13, ventana 08:52–10:46 UTC; público desde ~10:03).** Las IPs no se
anotan aquí: el repo se sube a GitHub. Se distinguen como *red de casa* y *celular*.

| Dato | Valor |
|---|---|
| Errores (WARNING o más) | ✅ **Ninguno real.** 7 avisos, todos de nuestras propias pruebas: 4 × 403 antes de abrir (F5/F6-01), 2 × 404 `Zone.Identifier` y 1 × 405 `HEAD /` (F6-03, intencionales). Ningún 5xx. |
| Consultas (`/api/consulta*`) y de cuántas IPs | Ya en público: **1**, `POST /api/consulta/stream` (Razonamiento) desde el celular, 200, 38 s con el streaming incluido, en instancia caliente. Antes de abrir: 5 de las pruebas de F5 (red de casa), todas 200 (1.5–26 s). |
| Arranques en frío y espera de la primera consulta | 5 arranques (2 en rev. `00001`, 3 en `00002`). En público hubo **1**, a las 10:30, y **no lo provocó una persona**: fue la vista previa de **WhatsApp** (`WhatsApp/2`) al compartir el enlace. `GET /` tardó **47 s** en frío. Esa instancia se apagó sola a las 10:46 (~16 min sin tráfico): el escalado a 0 funciona. |
| Tráfico inesperado (bots, rutas que no existen, `/api/docs`) | ✅ Sin escáneres ni accesos a `/api/docs`. Solo vistas previas de mensajería: `TelegramBot` (10:05, instancia caliente) y `WhatsApp/2` (10:30, en frío). |
| ¿Sigue bien `minScale: 0`? | **Sí, por ahora.** Hay una sola consulta pública: no alcanza para decidir. Se reevalúa en la 2.ª pasada. Ver los hallazgos sobre la espera en frío. |

**2.ª pasada:** 2026-10-20, con los mismos comandos (`--freshness=7d` cubre la semana completa).

---

## F6-06 — Decidir sobre `/api/docs` (Swagger público)

`main.py` publica la documentación interactiva de la API en `/api/docs`. No expone datos ni
claves, pero muestra cómo llamar a la API directamente. Opciones:

| Opción | Qué implica |
|---|---|
| Dejarlo | Nada que cambiar |
| Quitarlo | Cambiar `docs_url=None` en `main.py` (regla: requiere aprobación explícita) y redesplegar |

| Decisión | Valor |
|---|---|
| `/api/docs` | **Quitarla en el próximo cambio a `main.py`** (responsable, 2026-10-13). Riesgo bajo: expone solo lo que ya revela `web/app.js`. También se quita `/openapi.json` (público en la raíz). Queda como **P20**. |

---

## F6-07 — Actualizar `CLAUDE.md` y `readme.md`

Hoy describen la arquitectura vieja (Gradio como interfaz, `startup.sh` con rsync, `gcr.io`,
`Dockerfile.base`). Se proponen diffs para: §1 (qué es), §2 (trabajo en curso → hecho), §3
(mapa del repo), §5 (comandos de despliegue nuevos), §7 (arquitectura ya aplicada).

| Dato | Valor |
|---|---|
| Diff `CLAUDE.md` aprobado | ✅ 2026-10-13: §1–§8 a la arquitectura aplicada (modelo `-instruct`, endpoints reales con stream en POST, mapeo `recursos.BASES`, comandos de despliegue nuevos, reglas de trabajo en §8) |
| Diff `readme.md` aprobado | ✅ 2026-10-13: reescrito. Título **"Asistente Legal Mexicano"** (decisión del responsable); URL pública incluida; instalación local con `requirements.txt` + `constraints.txt` |

---

## F6-08 — Guía de operación

Archivo nuevo `docs/OPERACION.md`, corto: desplegar un cambio de código, reconstruir la pesada,
actualizar el acervo, revisar logs y costos, volver a una revisión anterior, hacer privado el
servicio.

| Dato | Valor |
|---|---|
| Diff aprobado | ✅ 2026-10-13: el responsable delegó la redacción ("confío en ti"). `docs/OPERACION.md`: §0 salud, §1 código, §2 pesada nueva, §3 acervo, §4 revertir, §5 cerrar/reabrir, §6 configuración, §7 logs y costos |

---

## F6-09 — Plan de limpieza del esquema viejo

Solo el plan (orden, dependencias y cuándo). Cada borrado se autoriza aparte. Candidatos de §5
y §2-bis: `protocolo01-app`, `ia-legal-mexicana-web` (P9), `mi-proyecto-axiomas` (P16), imágenes
`gcr.io`, `editor` de la cuenta de cómputo (P13), clave vieja de DeepSeek y versión 1 del secreto
(P10), `llamada_deepseek.txt` (P11), `Dockerfile.base` y archivos viejos del repo.

### Inventario (2026-10-13, solo lectura)

| Recurso | Estado | Uso en 30 días |
|---|---|---|
| Servicio `protocolo01-app` (viejo, Gradio) | **Público** (`allUsers`); secreto `DEEPSEEK_API_KEY:latest` → ya usa la clave **nueva** (v2) | ~200 peticiones; la última el 2026-10-11 (Firefox en Windows, probablemente el responsable) |
| Servicio `ia-legal-mexicana-web` | **Público**; clave de DeepSeek **en texto plano** en sus variables de entorno (no en Secret Manager) | **0 peticiones** |
| Artifact Registry `ia-legal-repo` | 51.7 GB | Imagen de `ia-legal-mexicana-web` |
| Artifact Registry `gcr.io` | 31.8 GB: `protocolo01-app`, `protocolo01-base`, `embeddings-rag`, `motor-embeddings-base` | Imagen de `protocolo01-app` |
| Artifact Registry `protocolo01-v2` | 1.8 GB | **En uso** (se conserva) |
| Bucket `mi-proyecto-axiomas` | 5 MB | P16 |
| Bucket `alma-juridica-aipp_cloudbuild` | 91 MB (fuentes que sube Cloud Build) | Se conserva; informativo |
| Secreto `DEEPSEEK_API_KEY` | v1 (2026-03-19) y v2 (2026-10-13), ambas habilitadas | Nadie lee v1: los dos servicios con secreto usan `latest` |
| Cuenta de cómputo por defecto | `roles/editor` + `roles/storage.objectViewer` | La usan los dos servicios viejos (P13) |
| `llamada_deepseek.txt` | Solo local, ignorado por git (nunca versionado) | P11 |

**Costo:** ~83 GB en registros viejos ≈ **8 USD/mes** de almacenamiento (Artifact Registry cobra
~0.10 USD/GB-mes). Es lo único del esquema viejo que cuesta sin uso.

### Plan propuesto (pendiente de aprobación; cada borrado se autoriza aparte)

| Etapa | Cuándo | Paso | Pendiente | Reversible |
|---|---|---|---|---|
| A | Ya | A1. Revocar en DeepSeek la clave en texto plano de `ia-legal-mexicana-web` y la clave vieja (v1) **(responsable)** | P10 | No (se crean otras) |
| A | Ya | A2. Borrar el servicio `ia-legal-mexicana-web` | P9 | No |
| A | Ya | A3. Deshabilitar (no destruir) la versión 1 del secreto | P10 | Sí |
| A | Ya | A4. Borrar el repositorio `ia-legal-repo` (51.7 GB) | P9 | No |
| B | 2026-10-20, tras la 2.ª pasada de F6-05 | B1. Hacer **privado** `protocolo01-app` (quitar `allUsers`) | — | Sí, en segundos |
| B | 2026-10-27, una semana sin reclamos | B2. Borrar el servicio `protocolo01-app` | — | No |
| B | Tras B2 | B3. Borrar las imágenes `gcr.io` (31.8 GB); antes, confirmar que `embeddings-rag` y `motor-embeddings-base` no se usan | — | No |
| B | Tras B2 y A2 | B4. Quitar `roles/editor` y `objectViewer` a la cuenta de cómputo | P13 | Sí |
| B | Tras B2 | B5. Destruir la versión 1 del secreto | P10 | No |
| C | Cuando sea | C1. Respaldar en local `mi-proyecto-axiomas` (5 MB) y borrar el bucket | P16 | 7 días (*soft delete*) |
| C | Cuando sea | C2. Vaciar o borrar `llamada_deepseek.txt` | P11 | — |
| C | Antes de F6-10 | C3. Commit de limpieza del repo: `Dockerfile.base`, `GUIA_RAPIDA.sh`, prototipos, copias `index.html`/`app.css` de la raíz, `app - copia.py`, `*:Zone.Identifier` (decidir cuáles) | — | Sí (git) |
| C | Al cerrar la Fase 6 | C4. Liberar ~21 GB de Docker Desktop y compactar `docker_data.vhdx` | P21 | No |

| Dato | Valor |
|---|---|
| Plan aprobado | ✅ 2026-10-13, completo, por el responsable ("apruebo todo"). Cada borrado se ejecuta como mini-tarea propia |
| A1 — claves viejas revocadas en DeepSeek | ✅ 2026-10-13 (responsable). Verificado después (Claude): el servicio nuevo sigue redactando con la clave v2 (consulta de Razonamiento: 200, 108 eventos de texto). Ojo: Cita Precisa no sirve para verificar la clave, porque `extraer_entidades_con_llm` devuelve `{}` en silencio si DeepSeek falla |
| A2 — borrar `ia-legal-mexicana-web` | ✅ 2026-10-13 (Claude, autorizado): `gcloud run services delete`. Su URL responde 404; quedan `protocolo01-app` y `protocolo01-app-v2` (este, 200) |
| A3 — deshabilitar la versión 1 del secreto | ✅ 2026-10-13 (Claude, autorizado): v1 `disabled`, v2 `enabled`; servicio nuevo 200. Revertir: `gcloud secrets versions enable 1 --secret=DEEPSEEK_API_KEY` |
| A3-bis — borrar los Cloud Run Jobs `job-indexador-legal` y `procesar-embeddings-job` | ✅ 2026-10-13 (Claude, autorizado). No queda ningún job; servicio nuevo 200 |
| A4 — borrar el repositorio `ia-legal-repo` | ✅ 2026-10-13 (Claude, autorizado): 25 imágenes, 51.7 GB. Quedan `gcr.io` (31.8 GB, B3) y `protocolo01-v2` (1.8 GB, en uso); servicio nuevo 200 |

### Cambio al plan (2026-10-16): `protocolo01-app` se conserva "dormido"

Decisión del responsable: **no borrar la v1**, sino dejarla guardada sin costo de uso.

Datos (2026-10-16, solo lectura):

- Sin `minScale` (escala a 0) · `maxScale: 20` · revisión `00013-6zv` con el 100 % (13 revisiones en total).
- Imagen en uso: `gcr.io/alma-juridica-aipp/protocolo01-app@sha256:ab61e2d…` (etiqueta `latest`, 2026-03-19, ~5 GB).
- Apagado no cobra CPU. Lo que cuesta es el almacenamiento de `gcr.io` (~3.2 USD/mes) y DeepSeek mientras siga público.

| Paso | Qué | Sustituye a | Reversible |
|---|---|---|---|
| D1 | Hacer **privado** `protocolo01-app` (quitar `allUsers`) | B1 | Sí, en segundos |
| D2 | Borrar de `gcr.io` **todo menos** `protocolo01-app@sha256:ab61e2d…` (`latest`): 4 digests viejos de `protocolo01-app`, `protocolo01-base` (2), `embeddings-rag` (v1, v3) y `motor-embeddings-base` (v1). Quedan ~5 GB, unos 0.50 USD/mes | B3 | No |
| — | **No se borra el servicio** | B2 (cancelado) | — |
| B4 | Quitar `roles/editor` a la cuenta de cómputo. **No rompe el servicio dormido:** conserva `storage.objectViewer` (bucket) y `secretAccessor` sobre `DEEPSEEK_API_KEY`, y la imagen la descarga el agente de Cloud Run, no esta cuenta. Se quita `editor` y se conserva `objectViewer`, al revés de lo que planteaba P13 | B4 (ajustado) | Sí |
| B5 | Destruir la versión 1 del secreto (sin cambio: el servicio viejo usa `latest`) | — | No |

Cómo reactivarla: quitar la restricción de D1 (`add-iam-policy-binding … --member=allUsers --role=roles/run.invoker`). El código de la v1 está en `master`.

| Dato | Valor |
|---|---|
| Cambio aprobado | ✅ 2026-10-16 (responsable) |
| D1 | ✅ 2026-10-16 (Claude, autorizado): `allUsers` quitado; política IAM vacía. Sin token: **403** (los primeros segundos dio 200 mientras se propagaba el cambio). `protocolo01-app-v2` sigue en 200 |
| D2 | ✅ 2026-10-16 (Claude, autorizado): 10 versiones borradas: 5 de `protocolo01-app` (una, `fdcac835…`, no salió en el primer listado porque lo corté con `head`; la usaba la revisión `00009`, sin tráfico), `protocolo01-base` ×2, `embeddings-rag` ×2 y `motor-embeddings-base` ×1. **Queda solo `protocolo01-app@sha256:ab61e2d…` (`latest`)**. El tamaño del repositorio (33.3 GB) no había bajado al terminar: Artifact Registry lo recalcula después. `protocolo01-app-v2`: 200 |
| B4 | ✅ 2026-10-16 (Claude, autorizado): `roles/editor` quitado a `879901246493-compute@…`; le quedan `storage.objectViewer` (proyecto) y `secretAccessor` (secreto). Respaldo previo de la política IAM, fuera del repo. Verificado: v2 200; v1 con token 200 (arranque en frío de **169 s**, esquema viejo con rsync), sin token 403; sin avisos en sus logs. Revertir: `add-iam-policy-binding … --role=roles/editor` |
| B5 | ✅ 2026-10-16 (responsable, desde la sesión con `!`; a Claude se lo bloqueó el filtro de auto mode): versión 1 de `DEEPSEEK_API_KEY` `destroyed`; v2 `enabled`; servicio nuevo 200 |

---

### Etapa E — Revisión a 7 días (2026-10-20)

Separada de la etapa B por decisión del responsable (2026-10-16): todo lo que espera al
2026-10-20 se agrupa aquí. Solo lectura, salvo la decisión de `minScale`.

| Paso | Qué | Quién | Hecho |
|---|---|---|---|
| E1 | 2.ª pasada de F6-05: logs de la semana con `--freshness=7d` (errores, consultas, arranques en frío, tráfico inesperado) | Claude | |
| E2 | Decidir `minScale` (0, 1 o 1 en horario de uso; ver §Hallazgos F6-05) | **Responsable** | |
| E3 | Confirmar que `gcr.io` bajó a ~5 GB tras D2 | Claude | |

### Etapa C — ejecución

| Dato | Valor |
|---|---|
| C1a — respaldo de `mi-proyecto-axiomas` | ✅ 2026-10-16 (Claude, solo lectura en GCP): copiado a `~/respaldos/mi-proyecto-axiomas/` (fuera del repo). 47 archivos, 5 026 692 bytes, idéntico al bucket; las 2 "carpetas" vacías del bucket (`scripts/procesado-mx/…`) recreadas a mano. Sin referencias al bucket en el código. *Soft delete* de 7 días activo |
| C1b — borrar el bucket | ✅ 2026-10-16 (responsable, con `!`; a Claude se lo bloqueó el filtro de auto mode): `gcloud storage rm -r gs://mi-proyecto-axiomas`. Quedan `chromadb-alma-juridica-aipp` y `alma-juridica-aipp_cloudbuild`; servicio nuevo 200. En *soft delete* hasta el **2026-10-23 09:45 UTC** (generación `1766826859660735302`); restaurar: `gcloud alpha storage buckets restore gs://mi-proyecto-axiomas#1766826859660735302` |

## F6-10 — Unir la rama a `master`

```bash
gh pr create --base master --head remake/protocolo01-v2 --title "Rehecho protocolo01-v2" ...
```

(o desde GitHub). Decisión del responsable: cuándo y cómo (merge, squash).

| Dato | Valor |
|---|---|
| PR | |
| Unido | |

---

## F6-11 — Cierre del rehecho

| Decisión | Valor |
|---|---|
| Estado final del servicio | |
| Pendientes que quedan abiertos | |
| Rehecho cerrado | ☐ Sí ☐ No |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F6-07 | `requirements_local.txt` no incluye `fastapi` ni `uvicorn` (y su encabezado dice `requirements-local.txt`). | Con él solo no se puede levantar `main.py` en local. | Resuelto en el readme: en local se instala con `requirements.txt` + `constraints.txt` (decisión del responsable). `requirements_local.txt` queda para Gradio e ingesta. |
| F6-08 | `deploy/service.yaml` lleva el marcador `IMAGEN_INICIAL`: aplicarlo directo con `services replace` falla. `CLAUDE.md` §5 y el readme (F6-07) lo indicaban mal. | Un cambio de configuración siguiendo esa doc habría fallado. | Corregido: ambos remiten a `OPERACION.md` §6 (sustituir con la imagen actual). |
| F6-08 | Tras fijar el tráfico a una revisión (revertir), los despliegues nuevos no reciben tráfico hasta `update-traffic --to-latest`. Y si se sube `_VERSION_PESADA` solo por línea de comandos, el siguiente despliegue vuelve a la pesada anterior. | Trampas de operación. | Documentadas en `OPERACION.md` §2 y §4. |
| F6-09 | `ia-legal-mexicana-web` guarda una clave de DeepSeek **en texto plano** en sus variables de entorno. Quedó visible en la sesión de Claude al inventariar (`services describe`). | Cualquiera con lectura del proyecto la ve; además pasó por Claude. | Revocarla en DeepSeek (A1) y borrar el servicio (A2). |
| F6-09 | **Dos Cloud Run Jobs** que no estaban en el inventario: `job-indexador-legal` (imagen `ia-legal-repo/ia-indexador:v1`, sin ejecuciones registradas) y `procesar-embeddings-job` (imagen `gcr.io/.../motor-embeddings-base:v1`, corre `script_embeddings_eva_5_2.py` sobre el bucket `mi-proyecto-axiomas`; 3 ejecuciones **fallidas**, la última el 2025-12-29). Ambos con la cuenta de cómputo por defecto. Cloud Scheduler no está habilitado: nada los dispara. | Borrar `ia-legal-repo` (A4), las imágenes `gcr.io` (B3), `mi-proyecto-axiomas` (C1) o el rol `editor` (B4) los dejaría rotos. Ninguno forma parte del flujo actual (la ingesta vigente son los `script_embeddings_*_55.py` en local). | Agregar al plan el borrado de los dos jobs **antes** de A4 (decisión del responsable). |
| F6-09 | `protocolo01-app` (viejo) sigue público y ya gasta con la clave nueva (`latest`). | Segunda puerta de gasto de DeepSeek, sin los límites del servicio nuevo. | Etapa B del plan. |
| F6-03 | `HEAD /` responde 405 (la ruta `/` de `main.py` solo declara `GET`). | Algunos monitores de disponibilidad y vistas previas de enlaces usan `HEAD`; los navegadores no. | Informativo. Si se usa un monitor, configurarlo con `GET`. Cambiarlo requiere tocar `main.py`. |
| (previo) | El proyecto no pertenece a ninguna organización. | `allUsers` no está bloqueado por política. | Ninguna. |
| F6-05 | Desde una instancia apagada, **la página tarda ~47 s en cargar** (`GET /` en frío). Eso pasa antes de cualquier consulta, porque `startup.sh` copia el acervo y arranca `main.py` antes de abrir el puerto. Además, la primera consulta paga ~26 s de carga del modelo (F5). | Con uso intermitente, casi todo visitante nuevo ve primero una pantalla en blanco de casi un minuto, y puede pensar que la app no sirve. | Decisión del responsable, en la 2.ª pasada: (a) dejar `minScale: 0` y avisarlo a los usuarios; (b) `minScale: 1` (sin espera, costo fijo mensual); (c) `minScale: 1` solo en horario de uso. |
| F6-05 | Compartir el enlace en **WhatsApp o Telegram** dispara su vista previa, y eso puede **despertar el servicio** (un arranque en frío, sin gasto de DeepSeek). La vista previa de WhatsApp esperó 47 s, así que probablemente salió sin título. | Costo mínimo de CPU por cada vez que se comparte. Vista previa pobre. | Informativo. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 6 con 11 mini-tareas. Verificado: servicio privado en `00002-7f2`, proyecto sin organización. |
| 2026-10-13 | F6-01 hecha (Claude, solo lectura): servicio sano y privado; listo para F6-02. |
| 2026-10-13 | F6-02 hecha (Claude, autorizado): **`protocolo01-app-v2` es público** en `https://protocolo01-app-v2-879901246493.us-central1.run.app`. |
| 2026-10-13 | F6-03 hecha (Claude): acceso público verificado sin credenciales; 6 bases, catálogo 45, HTTPS con redirección. |
| 2026-10-13 | F6-04 hecha (responsable): front y consultas en orden desde smartphone con datos móviles. |
| 2026-10-13 | Pausa del día. Siguiente: F6-05. |
| 2026-10-13 | F6-05 redefinida (responsable): el uso es intermitente → ventana acumulada desde la apertura con `--freshness=7d`, conteo de arranques en frío y tráfico inesperado; se repite a los 7 días. |
| 2026-10-13 | F6-05, 1.ª pasada (Claude, solo lectura): sin errores reales; 1 consulta pública (Razonamiento, celular); 1 arranque en frío público, provocado por la vista previa de WhatsApp (`GET /` 47 s); sin escáneres. 2.ª pasada: 2026-10-20. |
| 2026-10-13 | F6-06 decidida (responsable): quitar `/api/docs` y `/openapi.json` en el próximo cambio a `main.py` (P20). |
| 2026-10-13 | F6-07 hecha (aprobada por el responsable): `CLAUDE.md` y `readme.md` actualizados a la arquitectura aplicada. |
| 2026-10-13 | F6-08 hecha (delegada por el responsable): `docs/OPERACION.md`; corregido el comando de `service.yaml` en `CLAUDE.md` y readme. |
| 2026-10-13 | F6-09 preparada (Claude, solo lectura): inventario del esquema viejo (~83 GB en registros, ~8 USD/mes) y plan en tres etapas, pendiente de aprobación. Hallazgo: clave en texto plano en `ia-legal-mexicana-web`. |
| 2026-10-13 | F6-09 aprobado completo (responsable). A1 hecha (responsable: claves viejas revocadas); el servicio nuevo sigue funcionando con la v2 (verificado por Claude con una consulta de Razonamiento). |
| 2026-10-13 | A2 hecha (Claude, autorizado): servicio `ia-legal-mexicana-web` borrado (cierra P9 en lo que toca al servicio; sus imágenes son A4). |
| 2026-10-13 | A3 hecha (Claude, autorizado): versión 1 del secreto deshabilitada. |
| 2026-10-13 | A4 detenida antes de ejecutar: aparecen 2 Cloud Run Jobs que dependen de los registros viejos y de `mi-proyecto-axiomas`. Se propone borrarlos primero. |
| 2026-10-13 | A3-bis hecha (Claude, autorizado): los 2 jobs borrados. Comprobado que nada más usa `ia-legal-repo`: sin triggers de Cloud Build, sin VMs, Cloud Functions y Scheduler deshabilitados; ningún servicio usa su imagen. |
| 2026-10-13 | A4 hecha (Claude, autorizado): repositorio `ia-legal-repo` borrado (−51.7 GB). **Etapa A completa.** Siguiente: etapa B el 2026-10-20. |
| 2026-10-16 | Commit `22bcd7a` subido a `origin/remake/protocolo01-v2` (autorizado). |
| 2026-10-16 | Cambio al plan (responsable): `protocolo01-app` se conserva **dormido** (D1 privado, D2 solo la imagen `latest`); se cancela B2. Verificado que B4 no lo rompe. Etapa C, en espera hasta que el responsable lo indique. |
| 2026-10-16 | D1 hecha (Claude, autorizado): `protocolo01-app` privado (403 sin token); el servicio nuevo sigue en 200. Siguiente: D2. |
| 2026-10-16 | D2 hecha (Claude, autorizado): `gcr.io` reducido a la imagen de la v1. Ojo: las revisiones viejas de `protocolo01-app` (00001–00011) ya no tienen imagen; solo sirven `00012` y `00013` (misma imagen). Queda pendiente confirmar que el tamaño baje a ~5 GB. |
| 2026-10-16 | B4 hecha (Claude, autorizado): sin `roles/editor` en la cuenta de cómputo; v1 dormida sigue arrancando y v2 en 200. |
| 2026-10-16 | B5 hecha (responsable): versión 1 del secreto destruida (cierra P10). Siguiente: 2.ª pasada de F6-05 el 2026-10-20. |
| 2026-10-16 | La revisión del 2026-10-20 pasa a ser la **etapa E** (E1 logs, E2 `minScale`, E3 tamaño de `gcr.io`). Etapa C reanudada por el responsable: C1a hecha (respaldo local de `mi-proyecto-axiomas`). |
| 2026-10-16 | C1b hecha (responsable): bucket `mi-proyecto-axiomas` borrado, recuperable hasta el 2026-10-23 (cierra P16). |
