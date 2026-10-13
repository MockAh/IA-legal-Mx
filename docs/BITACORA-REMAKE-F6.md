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
| F6-05 | Revisar los logs de la primera hora pública | Claude | — | ☐ |
| F6-06 | Decidir sobre `/api/docs` (Swagger público) | **Tú** | — | ☐ |
| F6-07 | Actualizar `CLAUDE.md` y `readme.md` con la arquitectura nueva | Claude propone, tú apruebas | Cambia documentación | ☐ |
| F6-08 | Guía de operación (desplegar, revertir, actualizar acervo) | Claude propone, tú apruebas | Archivo nuevo en `docs/` | ☐ |
| F6-09 | Plan de limpieza del esquema viejo (orden y fechas) | Claude propone, tú decides | — (solo plan) | ☐ |
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

## F6-05 — Revisar los logs de la primera hora pública

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="protocolo01-app-v2" AND severity>=WARNING' --limit=50
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="protocolo01-app-v2" AND httpRequest.requestUrl:"/api/consulta"' \
  --format="value(timestamp,httpRequest.status,httpRequest.latency,httpRequest.remoteIp)" --limit=50
```

| Dato | Valor |
|---|---|
| Errores | |
| Consultas recibidas | |
| Tráfico inesperado | |

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
| `/api/docs` | |

---

## F6-07 — Actualizar `CLAUDE.md` y `readme.md`

Hoy describen la arquitectura vieja (Gradio como interfaz, `startup.sh` con rsync, `gcr.io`,
`Dockerfile.base`). Se proponen diffs para: §1 (qué es), §2 (trabajo en curso → hecho), §3
(mapa del repo), §5 (comandos de despliegue nuevos), §7 (arquitectura ya aplicada).

| Dato | Valor |
|---|---|
| Diff `CLAUDE.md` aprobado | |
| Diff `readme.md` aprobado | |

---

## F6-08 — Guía de operación

Archivo nuevo `docs/OPERACION.md`, corto: desplegar un cambio de código, reconstruir la pesada,
actualizar el acervo, revisar logs y costos, volver a una revisión anterior, hacer privado el
servicio.

| Dato | Valor |
|---|---|
| Diff aprobado | |

---

## F6-09 — Plan de limpieza del esquema viejo

Solo el plan (orden, dependencias y cuándo). Cada borrado se autoriza aparte. Candidatos de §5
y §2-bis: `protocolo01-app`, `ia-legal-mexicana-web` (P9), `mi-proyecto-axiomas` (P16), imágenes
`gcr.io`, `editor` de la cuenta de cómputo (P13), clave vieja de DeepSeek y versión 1 del secreto
(P10), `llamada_deepseek.txt` (P11), `Dockerfile.base` y archivos viejos del repo.

| Dato | Valor |
|---|---|
| Plan aprobado | |

---

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
| F6-03 | `HEAD /` responde 405 (la ruta `/` de `main.py` solo declara `GET`). | Algunos monitores de disponibilidad y vistas previas de enlaces usan `HEAD`; los navegadores no. | Informativo. Si se usa un monitor, configurarlo con `GET`. Cambiarlo requiere tocar `main.py`. |
| (previo) | El proyecto no pertenece a ninguna organización. | `allUsers` no está bloqueado por política. | Ninguna. |

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
