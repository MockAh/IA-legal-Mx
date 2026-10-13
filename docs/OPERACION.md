# OPERACIÓN — Asistente Legal Mexicano (`protocolo01-app-v2`)

Recetas para operar el servicio en producción. Los comandos que **cambian** algo en Google
Cloud los ejecuta el responsable del proyecto (ver `CLAUDE.md` §8). Los de solo lectura se
pueden correr en cualquier momento.

| Dato | Valor |
|---|---|
| Proyecto / región | `alma-juridica-aipp` / `us-central1` |
| Servicio | `protocolo01-app-v2` (público) |
| URL | https://protocolo01-app-v2-879901246493.us-central1.run.app |
| Imágenes | `us-central1-docker.pkg.dev/alma-juridica-aipp/protocolo01-v2/` → `protocolo01-v2-pesada:vN` y `protocolo01-v2-app:<BUILD_ID>` |
| Acervo | `gs://chromadb-alma-juridica-aipp` (montado en solo lectura en `/mnt/acervo`) |
| Clave | Secreto `DEEPSEEK_API_KEY` (Secret Manager, versión `latest`) |

Variables usadas abajo:

```bash
export REGION=us-central1
export SERVICIO=protocolo01-app-v2
export URL=https://protocolo01-app-v2-879901246493.us-central1.run.app
```

---

## 0. ¿Está sano? (solo lectura)

```bash
gcloud run services describe $SERVICIO --region=$REGION \
  --format="value(status.latestReadyRevisionName,status.traffic)"
curl -s $URL/api/estado | python3 -m json.tool      # las 6 bases con disponible: true
```

Si la instancia está apagada, `curl` tarda ~47 s (arranque en frío). No es una falla.

---

## 1. Desplegar un cambio de código o del front

Para cambios en `main.py`, `recursos.py`, `logica_*.py`, `utils_rag.py`, `catalogo_datos.py`,
`web/` o `startup.sh`:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Construye la imagen ligera sobre la pesada de `_VERSION_PESADA` y despliega una revisión nueva
(solo cambia la imagen; lo demás se queda como está). Tarda unos minutos. Después, revisar §0.

---

## 2. Cambiar dependencias o el modelo (imagen pesada nueva)

1. Editar `requirements.txt` (y regenerar `constraints.txt`, ver su encabezado) o subir el
   modelo nuevo a `gs://chromadb-alma-juridica-aipp/modelo_e5/`.
2. Construir la pesada con una **versión nueva** (el build se niega a sobrescribir una que exista):

   ```bash
   gcloud builds submit --config cloudbuild-pesada.yaml --substitutions=_VERSION_PESADA=v2
   ```

3. Construir y desplegar la ligera sobre ella:

   ```bash
   gcloud builds submit --config cloudbuild.yaml --substitutions=_VERSION_PESADA=v2
   ```

4. **Cambiar `_VERSION_PESADA: v2` en `cloudbuild.yaml`** (y en `cloudbuild-pesada.yaml`) y hacer
   commit. Si no, el siguiente despliegue de §1 vuelve en silencio a la pesada anterior.

Un modelo distinto al `multilingual-e5-large-instruct` exige **reingestar todo el acervo**: los
vectores tienen que salir del mismo modelo que las consultas.

---

## 3. Actualizar el acervo

Cada instancia copia el acervo del bucket **al arrancar**. Con `minScale: 0`, la siguiente
instancia que arranque (tras ~15 min sin uso) ya toma lo nuevo.

1. Subir los datos al bucket (responsable). Sin opciones que borren en destino: la regla es
   **no borrar nada del bucket**.
2. Para que entre de inmediato, forzar una revisión nueva:

   ```bash
   gcloud run services update $SERVICIO --region=$REGION --update-env-vars=ACERVO_FECHA=AAAAMMDD
   ```

   (`ACERVO_FECHA` no la lee el código; solo obliga a crear la revisión. Se pierde en el
   próximo `services replace` de §6, sin consecuencias.)

3. Revisar §0: los conteos de `/api/estado` deben reflejar el acervo nuevo.

Si cambian los títulos de las leyes, también hay que regenerar `faiss-lista/` (`init_faiss.py`).

---

## 4. Volver a una revisión anterior

```bash
gcloud run revisions list --service=$SERVICIO --region=$REGION --limit=5
gcloud run services update-traffic $SERVICIO --region=$REGION --to-revisions=<REVISION>=100
```

**Ojo:** mientras el tráfico esté fijado a una revisión, los despliegues nuevos (§1) **no
reciben tráfico**. Para volver al comportamiento normal, una vez corregido el problema:

```bash
gcloud run services update-traffic $SERVICIO --region=$REGION --to-latest
```

---

## 5. Hacer privado el servicio (emergencia) y volver a abrirlo

Ante un gasto anormal, abuso o un error grave, en segundos:

```bash
# Cerrar (deja de responder a internet: 403)
gcloud run services remove-iam-policy-binding $SERVICIO --region=$REGION \
  --member=allUsers --role=roles/run.invoker

# Reabrir
gcloud run services add-iam-policy-binding $SERVICIO --region=$REGION \
  --member=allUsers --role=roles/run.invoker
```

Si se sospecha de la clave de DeepSeek: revocarla en el panel de DeepSeek, crear una nueva y
agregarla como versión nueva del secreto (`gcloud secrets versions add DEEPSEEK_API_KEY
--data-file=-`, leyendo la clave con `read -s`, nunca escrita en la terminal ni en archivos).
Después forzar una revisión (§3 paso 2) para que la tome.

---

## 6. Cambiar la configuración del servicio (memoria, instancias, límites)

La configuración vive en `deploy/service.yaml`. Editarlo, hacer commit y aplicarlo **con la
imagen que corre hoy** (el archivo trae el marcador `IMAGEN_INICIAL`):

```bash
IMAGEN=$(gcloud run services describe $SERVICIO --region=$REGION \
  --format="value(spec.template.spec.containers[0].image)")
sed "s|IMAGEN_INICIAL|$IMAGEN|" deploy/service.yaml > /tmp/service.yaml
gcloud run services replace /tmp/service.yaml --region=$REGION
```

`services replace` no toca los permisos: el servicio sigue público.

### Instancias mínimas (arranque en frío)

`minScale: "0"` → sin costo fijo, ~1 min de espera en la primera visita.
`minScale: "1"` → sin espera, pero una instancia (2 vCPU · 4 GiB) se cobra todo el mes.
Se decide con los datos de uso (F6-05). Se cambia en `deploy/service.yaml` y se aplica como arriba.

---

## 7. Logs y costos (solo lectura)

`gcloud logging read` mira **solo el último día** si no se indica `--freshness`.

```bash
S='resource.type="cloud_run_revision" AND resource.labels.service_name="protocolo01-app-v2"'

# Errores
gcloud logging read "$S AND severity>=WARNING" --freshness=7d --limit=50

# Consultas (cada una cuesta DeepSeek)
gcloud logging read "$S AND httpRequest.requestUrl:\"/api/consulta\"" --freshness=7d \
  --format="value(timestamp,httpRequest.status,httpRequest.latency,httpRequest.remoteIp)" --limit=100

# Arranques en frío
gcloud logging read "$S AND textPayload:\"Iniciando Wall-E\"" --freshness=7d \
  --format="value(timestamp,resource.labels.revision_name)" --limit=50

# Tráfico raro (rutas inexistentes)
gcloud logging read "$S AND httpRequest.status=404" --freshness=7d \
  --format="value(timestamp,httpRequest.requestUrl,httpRequest.remoteIp,httpRequest.userAgent)" --limit=50
```

Costos:
- **DeepSeek:** panel de DeepSeek (uso y límite de gasto).
- **Google Cloud:** consola → *Facturación* → *Informes* (filtrar por Cloud Run, Cloud Build,
  Artifact Registry) y *Presupuestos y alertas* (la alerta ya está configurada).

Los logs se conservan 30 días.
