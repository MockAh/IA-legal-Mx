# BITÁCORA-REMAKE-F1 — Fase 1: inventario del bucket

Desglose de la **Fase 1** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-12
- **Estado:** completada (2026-10-12). Fase 2 autorizada.
- **Objetivo:** saber con exactitud qué hay en `gs://chromadb-alma-juridica-aipp`, cuánto
  pesa, si coincide con lo que espera el backend y cómo está desplegado hoy, **sin cambiar
  nada**. Con estos datos se decide la memoria del servicio y se pasa a la Fase 2.

## Reglas de esta fase

1. **Solo lectura.** Ningún comando de esta fase sube, borra ni modifica nada en Google Cloud.
   Las descargas van del bucket a la máquina local, nunca al revés.
2. **No se toca la lógica del backend.** Funciona tal como está; el rehecho cambia el front y
   el despliegue. Quedan fuera de alcance: `logica_a.py`, `logica_b.py`, `logica_c.py`,
   `utils_rag.py`, `catalogo_axiomas.py`, `recursos.py`, `catalogo_datos.py`, `main.py`
   y `app.py`. Si algo del inventario sugiere cambiarlos, se anota en §Hallazgos y se discute
   aparte.
3. **Ningún archivo del repo cambia en esta fase**, salvo esta bitácora.
4. **El bucket se conserva tal cual.** Todo lo que ya existe en Storage se queda ahí, incluidos
   los sobrantes. Nada de este plan borra ni sobrescribe en el bucket; la subida de datos solo
   agrega, y cualquier borrado se hace aparte, de forma específica, por el responsable.
5. **No se descarga el acervo al repo.** Las pruebas locales usan lo que ya hay en local
   (`basic`) o archivos sueltos en una carpeta temporal fuera del repo, que se borra al terminar.
6. Cada mini-tarea termina con su casilla marcada y sus datos anotados. Si una tarea revela un
   problema, se anota y se sigue con la siguiente; no se corrige sobre la marcha.

## Variables de la sesión

Pegar al inicio de cada terminal nueva:

```bash
export PROYECTO=alma-juridica-aipp
export REGION=us-central1
export BUCKET=chromadb-alma-juridica-aipp
export B=gs://$BUCKET
export REPO=/home/mock_/WandaVision/Backend01__
```

---

## Resumen de mini-tareas

| # | Mini-tarea | Tiempo | Estado |
|---|---|---|---|
| F1-01 | Preparar la sesión de `gcloud` | 15 min | ☑ |
| F1-02 | Ficha técnica del bucket | 15 min | ☑ |
| F1-03 | Mapa de primer nivel del bucket | 15 min | ☑ |
| F1-04 | Verificar las 6 rutas de Chroma | 15 min | ☑ |
| F1-05 | Medir tamaños por carpeta | 15 min | ☑ |
| F1-06 | Verificar `faiss-lista/` | 15 min | ☑ |
| F1-07 | Verificar `modelo_e5/` | 15 min | ☑ |
| F1-08 | Comparar `basic-mx` local contra el bucket | 15 min | ☑ |
| F1-09 | Bajar solo los `chroma.sqlite3` a una carpeta temporal | 15 min* | ☑ |
| F1-10 | Revisar compatibilidad leyendo los `chroma.sqlite3` | 15 min | ☑ |
| F1-11 | Inventario de sobrantes en el bucket | 15 min | ☑ |
| F1-12 | Permisos actuales del bucket | 15 min | ☑ |
| F1-13 | Radiografía del despliegue actual | 15 min | ☑ |
| F1-14 | Cierre: estimar memoria y decidir paso a Fase 2 | 15 min | ☑ |

Total estimado: **~3.5 h**. \*F1-09 depende del tamaño de los `chroma.sqlite3` (F1-05).

---

## F1-01 — Preparar la sesión de `gcloud`

**Objetivo:** confirmar con qué cuenta y proyecto se trabaja.

```bash
gcloud auth list
gcloud config list
gcloud auth login              # solo si la cuenta activa no es la correcta
gcloud config set project $PROYECTO
```

Observado el 2026-10-12: `gcloud config list` pide habilitar
`cloudresourcemanager.googleapis.com` en `alma-juridica-aipp`. **No habilitarla en esta
fase** (sería un cambio). Responder `N`; los comandos de `gcloud storage` no la necesitan. Se
habilita en la Fase 2.

**Hecho cuando:** la cuenta activa y el proyecto son los correctos.

| Dato | Valor |
|---|---|
| Cuenta activa | g.olin.xy@gmail.com (credencial válida) |
| Proyecto | alma-juridica-aipp |
| Versión de `gcloud` (`gcloud version`) | Google Cloud SDK 550.0.0 |

---

## F1-02 — Ficha técnica del bucket

**Objetivo:** ubicación, clase y configuración del bucket.

```bash
gcloud storage buckets describe $B \
  --format="yaml(name,location,location_type,default_storage_class,uniform_bucket_level_access,versioning_enabled,public_access_prevention)"
```

**Hecho cuando:** se anotan los datos. Si la ubicación **no** es `US-CENTRAL1`, anotarlo:
la región de Cloud Run debe coincidir para evitar latencia y cargos de salida.

| Dato | Valor |
|---|---|
| Ubicación | US-CENTRAL1 (coincide con la región de Cloud Run) |
| Tipo de ubicación (región / multirregión) | región |
| Clase de almacenamiento | STANDARD |
| Acceso uniforme | **No** (permite ACL por objeto → revisar en F1-12) |
| Versionado | No habilitado. Soft delete: 7 días |
| Prevención de acceso público | heredada (no forzada) |

---

## F1-03 — Mapa de primer nivel del bucket

**Objetivo:** ver qué carpetas existen arriba y dentro de `procesado-mx/`.

```bash
gcloud storage ls $B/
gcloud storage ls $B/procesado-mx/
gcloud storage ls $B/procesado-mx/*/
```

Esperado (lo que lee el backend):

```
procesado-mx/   faiss-lista/   modelo_e5/
procesado-mx/{basic-mx, segob-mx, transp-mx, 3p-mx, fce-mx, tramites-mx}/
```

**Hecho cuando:** el listado está pegado abajo y se marcó qué sobra y qué falta.

```
Raíz:          faiss-lista/  modelo_e5/  procesado-mx/  procesado-unam/ (sobra)
procesado-mx/: 3p-mx/ basic-mx/ fce-mx/ segob-mx/ tramites-mx/ transp-mx/ excep-mx/ (sobra)
Cada <base>-mx/: chroma_db_<base>/ + mapa_*.json, metadata_*.json, sincro_*.json (de ingesta)
tramites-mx/:  chroma_db_tramites_mx/ + chroma.sqlite3 suelto (sobra) + mapa.json, metadata.json
excep-mx/:     chroma_db_excep_mx/ + mapa.json, metadata.json
```

Resultado: las 6 carpetas esperadas existen. Sobran `procesado-unam/`, `excep-mx/` y un
`chroma.sqlite3` suelto en `tramites-mx/` (el backend lee `tramites-mx/chroma_db_tramites_mx/`).

---

## F1-04 — Verificar las 6 rutas de Chroma

**Objetivo:** que cada base exista en la ruta exacta que espera el backend y tenga la forma de
una base Chroma (`chroma.sqlite3` + carpeta(s) con nombre UUID).

```bash
for r in basic-mx/chroma_db_basic segob-mx/chroma_db_segob transp-mx/chroma_db_transp \
         3p-mx/chroma_db_3p fce-mx/chroma_db_fce tramites-mx/chroma_db_tramites_mx; do
  echo "== $r"
  gcloud storage ls $B/procesado-mx/$r/ 2>&1
done
```

**Hecho cuando:** las 6 filas están llenas.

| Base | Ruta existe | `chroma.sqlite3` | Carpetas UUID |
|---|---|---|---|
| basic | ✅ | ✅ | 1 (`2ad97c8f…`) |
| segob | ✅ | ✅ | 1 (`b0fdc7fc…`) |
| transp | ✅ | ✅ | 1 (`486acf00…`) |
| 3p | ✅ | ✅ | 1 (`634286c1…`) |
| fce | ✅ | ✅ | 1 (`6d021033…`) |
| tramites | ✅ | ✅ | 1 (`73d2ce2e…`) |

---

## F1-05 — Medir tamaños por carpeta

**Objetivo:** el dato que define la memoria del servicio (lo copiado al arrancar vive en RAM).

```bash
for r in basic-mx/chroma_db_basic segob-mx/chroma_db_segob transp-mx/chroma_db_transp \
         3p-mx/chroma_db_3p fce-mx/chroma_db_fce tramites-mx/chroma_db_tramites_mx; do
  gcloud storage du -s -r $B/procesado-mx/$r
done
gcloud storage du -s -r $B/faiss-lista
gcloud storage du -s -r $B/modelo_e5
gcloud storage du -s -r $B/procesado-mx
```

**Hecho cuando:** la tabla está llena y está calculado el total que se copiará al arrancar.

| Carpeta | Tamaño |
|---|---|
| chroma_db_basic | 46.39 MiB |
| chroma_db_segob | 50.10 MiB |
| chroma_db_transp | 6.24 MiB |
| chroma_db_3p | 13.48 MiB |
| chroma_db_fce | 44.15 MiB |
| chroma_db_tramites_mx | 2.18 MiB |
| faiss-lista | 246 KiB |
| **Total copiado al arrancar** (6 Chroma + FAISS) | **≈ 163 MiB** |
| modelo_e5 (va en la imagen, no en RAM de disco) | 2.10 GiB |
| procesado-mx completo (para ver cuánto sobra) | 187.88 MiB (sobran ~25 MiB: excep-mx + JSON de ingesta) |
| Bucket completo | 2.30 GiB, 78 objetos |
| Suma de los 6 `chroma.sqlite3` (lo que bajaría F1-09) | ≈ 124 MiB |

---

## F1-06 — Verificar `faiss-lista/`

**Objetivo:** que el índice del bucket sea el mismo que el local, con el que el catálogo
devuelve 42 títulos.

```bash
gcloud storage ls -L $B/faiss-lista/ | grep -E "gs://|Content-Length|Hash \(md5\)"
gcloud storage hash $REPO/faiss-lista/* --skip-crc32c
```

**Hecho cuando:** se compararon los MD5 de los dos archivos.

| Archivo | MD5 bucket | MD5 local | ¿Igual? |
|---|---|---|---|
| indice_titulos_leyes.faiss | 188 461 B (2026-04-29) | 176 173 B (2026-03-10) | ❌ |
| metadata_titulos_leyes.pkl | 16 001 B | 14 943 B | ❌ |
| inspeccion_base_datos.json | 46 documentos | 43 documentos | ❌ |

El tamaño ya difiere, así que no hizo falta comparar MD5. El bucket tiene 3 títulos más que
la copia local: *Ley Federal de los Trabajadores al Servicio del Estado*, *Ley Federal del
Trabajo* y *Reglamento Interior de la Secretaría de Educación Pública*. No hay títulos que
estén solo en local. **El bucket es la versión vigente.**

Si difieren: el bucket tiene otra versión del índice. Anotarlo en §Hallazgos; F1-10 dirá
cuántos títulos trae.

---

## F1-07 — Verificar `modelo_e5/`

**Objetivo:** que el bucket tenga el modelo correcto (`multilingual-e5-large-instruct`, el
que usaron los scripts de ingesta) y completo.

```bash
gcloud storage ls -r $B/modelo_e5/
gcloud storage cat $B/modelo_e5/README.md | grep -iE "name:|base_model" | head -5
gcloud storage ls -L $B/modelo_e5/model.safetensors | grep -E "Content-Length|Hash \(md5\)"
gcloud storage hash $REPO/modelo_e5/model.safetensors --skip-crc32c
```

Archivos esperados (los del modelo local): `1_Pooling/`, `2_Normalize/`, `README.md`,
`config.json`, `config_sentence_transformers.json`, `model.safetensors`, `modules.json`,
`sentence_bert_config.json`, `special_tokens_map.json`, `tokenizer.json`,
`tokenizer_config.json`.

**Hecho cuando:** se confirmó el nombre del modelo y que `model.safetensors` es igual al local.

| Dato | Valor |
|---|---|
| Nombre del modelo en README | `multilingual-e5-large-instruct` ✅ |
| Archivos completos | ✅ 10 archivos, mismos nombres y tamaños que local |
| MD5 `model.safetensors` bucket / local | El bucket no guarda MD5 de este archivo (subida compuesta); se comparó CRC32C: `6Db52g==` en ambos ✅. Los otros 9 archivos: MD5 idénticos ✅ |

---

## F1-08 — Comparar `basic-mx` local contra el bucket

**Objetivo:** saber si la base `basic` local (2170 documentos, abre con `chromadb==1.4.0`) es
la misma que la del bucket. Si es igual, ya está probado que esa versión de Chroma la abre.

```bash
gcloud storage ls -L $B/procesado-mx/basic-mx/chroma_db_basic/chroma.sqlite3 | grep -E "Content-Length|Hash \(md5\)|Update time"
gcloud storage hash $REPO/procesado-mx/basic-mx/chroma_db_basic/chroma.sqlite3 --skip-crc32c
ls -la $REPO/procesado-mx/basic-mx/chroma_db_basic/
```

**Hecho cuando:** se sabe si son iguales.

| Dato | Bucket | Local |
|---|---|---|
| MD5 `chroma.sqlite3` | `roHsKCBu…` | `ZOM6Y9Mb…` ❌ |
| Tamaño `chroma.sqlite3` | 34.3 MB | 28.0 MB |
| Tamaño `data_level0.bin` (vectores) | 14.0 MB | 5.2 MB |
| UUID de la colección | `2ad97c8f…` | `957ef9b8…` ❌ |
| Fecha | 2026-04-29 | 2026-03-08 (el `.sqlite3` marca 2026-10-12, ver hallazgo) |

**Resultado:** son bases distintas, no solo versiones parecidas: los 6 archivos difieren y
la colección tiene otro UUID, o sea que se reconstruyó. La del bucket es la vigente y tiene
bastante más contenido (vectores ~2.7× más grandes). La prueba de compatibilidad con
`basic` local **no** sirve como referencia para el bucket; F1-10 debe comparar las
migraciones entre las 6 bases del bucket y contra la local solo como dato.

---

## F1-09 — Bajar solo los `chroma.sqlite3` a una carpeta temporal

**Objetivo:** tener lo mínimo para revisar la compatibilidad en F1-10 **sin descargar el
acervo al repo**. Solo se bajan los 6 archivos `chroma.sqlite3` (esquema, colecciones y
conteos viven ahí), a una carpeta temporal **fuera del repo**, que se borra en F1-10.

> Revisar antes el tamaño de cada `chroma_db_*` en F1-05. Si algún `chroma.sqlite3` es
> demasiado grande para bajarlo, se omite esa base y se anota.

```bash
export TMP_F1=$(mktemp -d /tmp/f1-acervo-XXXX)
for r in basic-mx/chroma_db_basic segob-mx/chroma_db_segob transp-mx/chroma_db_transp \
         3p-mx/chroma_db_3p fce-mx/chroma_db_fce tramites-mx/chroma_db_tramites_mx; do
  mkdir -p $TMP_F1/$(basename $r)
  gcloud storage cp $B/procesado-mx/$r/chroma.sqlite3 $TMP_F1/$(basename $r)/
done
du -sh $TMP_F1/*
```

**Hecho cuando:** los 6 archivos están en `$TMP_F1` (o se anotó cuál se omitió).

| Dato | Valor |
|---|---|
| Carpeta temporal | scratchpad de la sesión de Claude (`…/scratchpad/f1-acervo-kkhk`), fuera del repo |
| Tamaño bajado | ≈ 126 MiB en 26 s (basic 33, segob 37, fce 34, 3p 14, transp 5.9, tramites 1.8) |
| Bases omitidas | ninguna |

---

## F1-10 — Revisar compatibilidad leyendo los `chroma.sqlite3` (solo lectura)

**Objetivo:** confirmar que las 6 bases son compatibles con la versión de Chroma del backend
(`chromadb==1.4.0`), sin usar Chroma, sin tocar código y sin llamar a DeepSeek. Se abren con
`sqlite3` en **modo solo lectura** y se comparan contra `basic` local, que ya está probado
que abre (2170 documentos).

```bash
python3 - "$TMP_F1" "$REPO/procesado-mx/basic-mx/chroma_db_basic/chroma.sqlite3" <<'PY'
import sqlite3, sys, pathlib
tmp, ref = pathlib.Path(sys.argv[1]), sys.argv[2]
def leer(ruta):
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    mig = con.execute("select dir, max(version) from migrations group by dir").fetchall()
    cols = [r[0] for r in con.execute("select name from collections")]
    emb = con.execute("select count(*) from embeddings").fetchone()[0]
    con.close()
    return dict(mig), cols, emb
m_ref, _, _ = leer(ref)
print("referencia (basic local):", m_ref)
for f in sorted(tmp.glob("*/chroma.sqlite3")):
    m, cols, emb = leer(f)
    print(f"{f.parent.name:24} migraciones_iguales={m == m_ref!s:5} colecciones={cols} embeddings={emb}")
PY
rm -rf "$TMP_F1"     # limpieza: nada queda en local
```

**Hecho cuando:** la tabla está llena y la carpeta temporal está borrada.
`migraciones_iguales=False` no siempre es fatal (puede ser más viejo y Chroma lo migra al
abrir), pero se anota en §Hallazgos.

| Base | Migraciones (queue / metadb / sysdb) | Colección | Dimensión | Embeddings |
|---|---|---|---|---|
| basic | 2 / 5 / 10 ✅ | `langchain` | 1024 | 3688 |
| segob | 2 / 5 / 10 ✅ | `langchain` | 1024 | 3169 |
| transp | 2 / 5 / 10 ✅ | `langchain` | 1024 | 413 |
| 3p | 2 / 5 / 10 ✅ | `langchain` | 1024 | 935 |
| fce | 2 / 5 / 10 ✅ | `langchain` | 1024 | 3080 |
| tramites | 2 / 5 / 10 ✅ | `tramites_gob_mx` | 1024 | 81 |
| *basic local (referencia)* | *2 / 5 / 10* | *`langchain`* | *1024* | *2170* |

**Resultado:** las 6 bases tienen el mismo nivel de esquema que la `basic` local después de
abrirla con `chromadb==1.4.0` (sysdb 10; el paquete Python trae hasta la 9 en `.sql` y la 10 la
aplica el núcleo en Rust). Esquema idéntico → **compatibles con `chromadb==1.4.0`**. Los nombres
de colección son los que espera `recursos.py`, todas en 1024 dimensiones (e5-large). Total:
11 366 fragmentos. Carpeta temporal borrada.

---|---|---|---|
| basic | | | |
| segob | | | |
| transp | | | |
| 3p | | | |
| fce | | | |
| tramites | | | (se espera `tramites_gob_mx` o `langchain`) |

---

## F1-11 — Inventario de sobrantes en el bucket

**Objetivo:** listar lo que hay en el bucket y **no** usa el backend (por ejemplo
`principal-mx`, `excep-mx`, `procesado-unam`), con su tamaño. Solo se anota; no se borra.

```bash
gcloud storage ls $B/
gcloud storage ls $B/procesado-mx/
gcloud storage du -s -r $B/procesado-unam 2>&1
gcloud storage du -s -r $B/procesado-mx/principal-mx $B/procesado-mx/excep-mx 2>&1
```

**Hecho cuando:** la tabla está llena.

| Ruta sobrante | Tamaño | ¿Quién la usa? |
|---|---|---|
| `procesado-unam/` (chroma_db_unam + json) | 17.11 MiB | Solo el prototipo `rag_app_deepseek.py` y el `startup.sh` actual (la sincroniza, pero la app no la lee). El backend nuevo no. |
| `procesado-mx/excep-mx/` (chroma_db_excep_mx + json) | 4.85 MiB | Su script de ingesta `script_embeddings_excep_mx.py`, los prototipos `rag_*.py` y `test_81_homoclaves_d.py`. El backend no. |
| `procesado-mx/tramites-mx/chroma.sqlite3` (suelto) | 164 KiB | Nadie lo lee; el backend abre `tramites-mx/chroma_db_tramites_mx/`. Origen no confirmado. |
| `*/mapa_*.json`, `metadata_*.json`, `sincro_*.json` | ≈ 21 MiB | Los scripts de ingesta (control de sincronización incremental). El backend no, pero **son necesarios para seguir agregando datos**. |
| `faiss-lista/inspeccion_base_datos.json` | 47 KiB | Lo escribe `init_faiss.py` como reporte. El backend no. |

**Resultado:** ≈ 43 MiB del bucket no los usa el backend. **Todo se conserva** (regla 4).
Efecto en el diseño: ninguno, porque el `startup.sh` nuevo copia solo las 6 `chroma_db_*` y
`faiss-lista/`. El único sobrante que se copia es `inspeccion_base_datos.json` (47 KiB, va
dentro de `faiss-lista/`), que no estorba.

---

## F1-12 — Permisos actuales del bucket

**Objetivo:** saber quién lee el bucket hoy, para replicarlo con la cuenta `protocolo01-v2-run` en la
Fase 2.

```bash
gcloud storage buckets get-iam-policy $B --format=json
```

Esperado (de `llamada_deepseek.txt`): `879901246493-compute@developer.gserviceaccount.com`
con `roles/storage.objectViewer`.

**Hecho cuando:** la lista de miembros y roles está anotada.

| Miembro | Rol | Vía |
|---|---|---|
| Propietarios del proyecto (`projectOwner`) | `legacyBucketOwner` + OWNER en cada objeto | IAM + ACL |
| Editores del proyecto (`projectEditor`) | `legacyBucketOwner` + OWNER en cada objeto | IAM + ACL |
| Lectores del proyecto (`projectViewer`) | `legacyBucketReader` + READER en cada objeto | IAM + ACL |
| `879901246493-compute@developer.gserviceaccount.com` | `storage.objectViewer` | IAM |
| `user-g.olin.xy@gmail.com` | OWNER en los 78 objetos | ACL (por haberlos subido) |

Revisadas las ACL de los **78 objetos**: todas iguales, sin entradas extra.

¿Aparece `allUsers` o `allAuthenticatedUsers`? ☑ No ☐ Sí → anotarlo en §Hallazgos (el acervo
quedaría público).

---

## F1-13 — Radiografía del despliegue actual

**Objetivo:** documentar cómo está corriendo hoy `protocolo01-app` (si existe), para comparar
y para poder volver atrás.

```bash
gcloud run services list --region=$REGION
gcloud run services describe protocolo01-app --region=$REGION \
  --format="yaml(status.url,spec.template.spec.containers[0].image,spec.template.spec.containers[0].resources,spec.template.spec.containers[0].env,spec.template.spec.serviceAccountName,spec.template.metadata.annotations)"
gcloud secrets list
gcloud container images list --repository=gcr.io/$PROYECTO 2>&1
```

Si alguna API no está habilitada, `gcloud` preguntará si habilitarla: responder `N` y anotarlo.

**Hecho cuando:** la tabla está llena (o se anotó que el servicio no existe).

| Dato | Valor |
|---|---|
| URL actual | https://protocolo01-app-879901246493.us-central1.run.app (pública: `allUsers` como invocador) |
| Imagen | `gcr.io/alma-juridica-aipp/protocolo01-app:latest` — revisión `00013-6zv` (2026-04-29), lista ✅ |
| Memoria / CPU | 4 GiB / 2 vCPU · concurrencia 80 · maxScale 20 · timeout 1200 s · cpu-boost · probe TCP 240 s |
| Cuenta de servicio | `879901246493-compute@developer.gserviceaccount.com` (la de cómputo por defecto) |
| `GCS_BUCKET_PATH` | `gs://chromadb-alma-juridica-aipp` (sin `/` final ✅) |
| ¿Secreto `DEEPSEEK_API_KEY` existe? | Sí, 1 versión (2026-03-19), inyectado como variable. No se leyó su valor. |
| Imágenes en `gcr.io` | `protocolo01-app`, `protocolo01-base`, `embeddings-rag`, `motor-embeddings-base` |
| Otros servicios Cloud Run | `ia-legal-mexicana-web` (público, 8 GiB / 2 vCPU, imagen en Artifact Registry `ia-legal-repo`, último despliegue 2025-12-26) |
| Repos de Artifact Registry | `gcr.io` (respaldo de Container Registry), `ia-legal-repo` |
| Revisiones previas para revertir | `00012-bl6` (2026-03-19), `00011-n8f` (2025-12-29) |

---

## F1-14 — Cierre: estimar memoria y decidir paso a Fase 2

**Cálculo de memoria** (por instancia):

| Concepto | Estimado |
|---|---|
| Modelo e5-large-instruct cargado (pesos 2.1 GiB en float32 + PyTorch) | ~2.6 GiB |
| Acervo copiado a `/app` al arrancar (F1-05) | 0.16 GiB |
| Python, FastAPI, Chroma, FAISS | ~0.5 GiB |
| Margen para concurrencia y picos de PyTorch | ~2 GiB |
| **Total** | **~5.3 GiB** |

Comparación: hoy `protocolo01-app` funciona con 4 GiB, pero gasta ~2.1 GiB solo en guardar el
modelo descargado. En el diseño nuevo ese espacio se libera (el modelo viaja en la imagen).

| Decisión | Valor |
|---|---|
| Memoria del servicio | **8 GiB** (holgado; se confirma con `docker stats` en la Fase 4 y podría bajar a 6 GiB) |
| vCPU | **2** (el mínimo que Cloud Run exige por encima de 4 GiB; igual que hoy) |
| Concurrencia | **10** por instancia (hoy 80: demasiado para un modelo en CPU) |
| Región | **us-central1** (bucket y servicio actual ahí) → D2 cerrada |
| Bloqueos para la Fase 2 | Ninguno. Todo lo de §Hallazgos es informativo o se resuelve en fases posteriores. |
| Pendientes que no bloquean | Concentrados en `BITACORA-REMAKE.md` §2-bis (P1–P12) |
| ¿Pasar a Fase 2? | **Sí** — confirmado por el responsable el 2026-10-12 |

---

## Hallazgos

Anotar aquí cualquier cosa inesperada. No se corrige en esta fase.

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F1-03 | `tramites-mx/chroma.sqlite3` suelto, fuera de `chroma_db_tramites_mx/`. | Ninguno: el backend no lo lee. Pero `startup.sh` viejo copiaba todo `procesado-mx/`. | Medir en F1-11. No borrar. |
| F1-03 | Los `*.json` de ingesta (mapa, metadata, sincro) viven junto a cada base. | Ninguno: el `startup.sh` nuevo copia solo `chroma_db_*`. | Ninguna. |
| F1-05 | `basic` del bucket (46.39 MiB, 2026-04-29) es más grande y reciente que la local (36 MiB). `faiss-lista` del bucket también es del 2026-04-29; la local es de marzo. | La prueba local (42 títulos, 2170 docs) usó datos viejos. | Confirmar en F1-06 y F1-08. |
| F1-06 | `faiss-lista` local está desactualizada: 43 títulos contra 46 del bucket. | Las pruebas locales del catálogo no reflejan producción. | Ninguna en esta fase (regla: no se baja el acervo). Se valida en la nube. |
| F1-07 | `2_Normalize/` es una carpeta vacía en local y no existe en el bucket (Storage no guarda carpetas vacías). `modules.json` la menciona. | Probablemente ninguno (el despliegue anterior también bajaba el modelo con rsync). | Por seguridad, crear la carpeta vacía al construir la imagen pesada (`mkdir -p /app/modelo_e5/2_Normalize`). |
| F1-08 | `basic` del bucket es una base reconstruida (otro UUID), más grande que la local. | La referencia local no sirve para probar compatibilidad. | Ajustar la lectura de F1-10. |
| F1-08 | El `chroma.sqlite3` **local** cambió de fecha a hoy: Chroma escribe en el archivo al abrirlo, y la prueba con `TestClient` de esta sesión lo abrió. | Solo en local; el bucket no se tocó. Confirma que Chroma necesita escribir (por eso en la nube se copia a `/app` y no se usa directo del volumen de solo lectura). | Ninguna. |
| F1-12 | El acceso al bucket depende de quién sea propietario/editor/lector **del proyecto**, y la cuenta de cómputo por defecto suele ser Editor del proyecto (eso le daría OWNER sobre el bucket, no solo lectura). | Quién puede borrar del bucket se decide a nivel proyecto. | Revisar los miembros del proyecto en la consola (IAM) cuando se vean permisos. No cambiar nada ahora. |
| F1-13 | El servicio actual tiene 4 GiB (no 512 MiB como se supuso) y el bucket sin `/` final. | Se corrigieron los puntos 1 y 3 de `BITACORA-REMAKE.md` §0. | Hecho. |
| F1-13 | Existe otro servicio público, `ia-legal-mexicana-web`, con su repo `ia-legal-repo`. | Ninguno para el plan, pero cuesta y expone otra URL. | **Decidido: se borra.** Anotado en `BITACORA-REMAKE.md` §5 para hacerlo oportunamente. |
| F1-13 | El secreto `DEEPSEEK_API_KEY` ya existe (1 versión). | En la Fase 2 no se crea: se le **agrega una versión** con la clave nueva. | Ajustar Fase 2. |
| (previo) | `BITACORA-REMAKE.md` §3.9 propone cambios a `main.py` y `recursos.py` (precarga del modelo, `/api/salud`, respaldo del modelo). | Contradice la regla de no tocar el backend. | Quedan en pausa. Si se retoman, será con aprobación explícita. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-12 | Se crea la bitácora de Fase 1 con 14 mini-tareas. Regla fijada: no se modifica ningún archivo de la lógica del backend. |
| 2026-10-12 | F1-01 hecha (Claude): cuenta, proyecto y credencial verificados. |
| 2026-10-12 | F1-02 hecha (Claude): bucket en US-CENTRAL1, STANDARD, sin acceso uniforme. Decisión D1: la app nueva se monta en `alma-juridica-aipp` (no se crea proyecto). |
| 2026-10-12 | F1-03 hecha (Claude): estructura completa; sobrantes anotados para F1-11. |
| 2026-10-12 | Reglas nuevas: el bucket se conserva íntegro y no se descarga el acervo al repo. F1-09/F1-10 rehechas: solo se bajan los `chroma.sqlite3` a una carpeta temporal fuera del repo. Nombres: todo pasa a `protocolo01-v2-*` (servicio `protocolo01-app-v2`). |
| 2026-10-12 | F1-04 hecha (Claude): las 6 bases tienen `chroma.sqlite3` + 1 carpeta UUID cada una. |
| 2026-10-12 | F1-05 hecha (Claude): acervo que se copia al arrancar ≈ 163 MiB; modelo 2.10 GiB; bucket 2.30 GiB. |
| 2026-10-12 | F1-06 hecha (Claude): `faiss-lista` del bucket (46 títulos, abril) es más nueva que la local (43, marzo). |
| 2026-10-12 | F1-07 hecha (Claude): `modelo_e5` del bucket es idéntico al local (`e5-large-instruct`, 2.10 GiB). |
| 2026-10-12 | F1-08 hecha (Claude): `basic` del bucket ≠ local (reconstruida, otro UUID, abril vs marzo). |
| 2026-10-12 | F1-09 hecha (Claude): 6 `chroma.sqlite3` (≈126 MiB) en carpeta temporal fuera del repo; se borra en F1-10. |
| 2026-10-12 | F1-10 hecha (Claude): 6 bases compatibles con `chromadb==1.4.0`, colecciones correctas, 11 366 fragmentos. Temporal borrada. |
| 2026-10-12 | F1-11 hecha (Claude): ≈43 MiB sin uso por el backend (unam, excep, sqlite suelto, json de ingesta). Se conservan. |
| 2026-10-12 | F1-12 hecha (Claude): bucket no público; acceso vía roles del proyecto + cuenta de cómputo (lectura) + tu usuario (dueño de los 78 objetos). |
| 2026-10-12 | F1-13 hecha (Claude): `protocolo01-app` corre con 4 GiB/2 vCPU, rev. 00013, público. Hay otro servicio `ia-legal-mexicana-web`. Secreto ya existe. Correcciones aplicadas en `BITACORA-REMAKE.md` §0. |
| 2026-10-12 | Decisión del responsable: borrar `ia-legal-mexicana-web` (anotado en `BITACORA-REMAKE.md` §5). |
| 2026-10-12 | F1-14 hecha (Claude): 8 GiB / 2 vCPU / concurrencia 10 / us-central1. Sin bloqueos. **Fase 1 completa.** |
