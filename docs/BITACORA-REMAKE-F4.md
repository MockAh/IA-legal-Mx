# BITÁCORA-REMAKE-F4 — Fase 4: probar las imágenes en local con Docker

Desglose de la **Fase 4** de `BITACORA-REMAKE.md` en mini-tareas de ~15 minutos.

- **Inicio:** 2026-10-13
- **Estado:** en curso
- **Objetivo:** construir la imagen pesada y la ligera **en la PC**, arrancarlas con el acervo
  local montado como si fuera el bucket, y confirmar que el contenedor arranca, sirve el front
  y la API, carga el modelo y cabe en memoria. Con esto se decide la memoria final y se pasa a la
  Fase 5 (construir y desplegar en la nube).

## Reglas de esta fase

1. **Nada en Google Cloud cambia.** No se sube ninguna imagen ni se ejecuta `gcloud builds submit`.
2. **No se descarga el acervo al repo.** Se usa lo que ya hay en local (`basic` y `faiss-lista`,
   desactualizados frente al bucket, P12), montado **en solo lectura**. Las bases que no existen en
   local (`segob`, `transp`, `3p`, `fce`, `tramites`) se prueban en la nube (Fase 5).
3. **No se toca la lógica del backend** ni los archivos de la Fase 3, salvo que una prueba revele
   un error; en ese caso se anota en §Hallazgos y se propone el cambio aparte.
4. **Las llamadas a DeepSeek cuestan.** Solo se hacen en F4-09, con autorización, una por modo.
   La clave se pasa al contenedor desde el `.env` local (`--env-file`), sin que Claude la lea.
5. Cada mini-tarea termina con su casilla marcada y sus datos anotados.

## Punto de partida (verificado el 2026-10-13)

| Pieza | Estado |
|---|---|
| Rama de git | `remake/protocolo01-v2`, último commit `3d5d398` (Fase 3) |
| Docker en WSL | Activado por el responsable el 2026-10-13 (F4-01) |
| Memoria de WSL | **7.8 GiB** en total (`.wslconfig`: `memory=8GB`, `swap=4GB`); 6.9 GiB libres |
| CPU / disco | 8 núcleos; 923 GB libres |
| Acervo local | `procesado-mx/basic-mx/chroma_db_basic` (marzo, 2170 fragmentos) y `faiss-lista/` (43 títulos) |
| Modelo local | `modelo_e5/` idéntico al del bucket (F1-07) |

> **Ojo con la memoria:** Docker Desktop usa la misma máquina virtual de WSL, limitada a 8 GB.
> El servicio en la nube tendrá 8 GiB, pero en local el contenedor no podrá pasar de ~6 GiB.
> Alcanza para el consumo estimado (~5.3 GiB, F1-14), pero va justo (ver F4-02).

---

## Resumen de mini-tareas

| # | Mini-tarea | Quién | Costo | Estado |
|---|---|---|---|---|
| F4-01 | Activar Docker en WSL y comprobarlo | **Tú** activas; Claude comprueba | — | ☑ |
| F4-02 | Revisar memoria disponible para Docker | Claude; tú si hay que ampliar | — | ☑ |
| F4-03 | Construir la imagen pesada en local | Claude | — | ☑ |
| F4-04 | Inspeccionar la pesada (tamaño, versiones) | Claude | — | ☑ |
| F4-05 | Construir la imagen ligera en local | Claude | — | ☐ |
| F4-06 | Inspeccionar la ligera (qué archivos lleva) | Claude | — | ☐ |
| F4-07 | Arrancar el contenedor con el acervo local montado | Claude | — | ☐ |
| F4-08 | Probar front y API sin DeepSeek | Claude | — | ☐ |
| F4-09 | Medir memoria con el modelo cargado | Claude | — | ☐ |
| F4-10 | Una consulta real por modo (DeepSeek) | Claude, **con tu autorización** | 2 llamadas | ☐ |
| F4-11 | Pruebas de fallo controlado | Claude | — | ☐ |
| F4-12 | Cierre: memoria final y paso a Fase 5 | Claude propone, tú decides | — | ☐ |

Total estimado: **~3.5 h** (la construcción de la pesada puede tardar 20–40 min por sí sola).

---

## F4-01 — Activar Docker en WSL y comprobarlo

**Objetivo:** poder usar `docker` desde esta distro.

1. **Tú:** Docker Desktop → *Settings* → *Resources* → *WSL integration* → activar la distro
   (Ubuntu) → *Apply & restart*.
2. **Claude** comprueba:

```bash
docker version --format '{{.Client.Version}} / {{.Server.Version}}'
docker info --format 'CPUs={{.NCPU}} Memoria={{.MemTotal}} Driver={{.Driver}}'
docker run --rm hello-world | head -3
```

**Hecho cuando:** los tres comandos responden.

| Dato | Valor |
|---|---|
| Versión cliente / servidor | 28.5.1 / 28.5.1 |
| CPUs y memoria que ve Docker | 8 CPUs · 8 328 011 776 B (7.76 GiB) · overlayfs |
| `hello-world` | ✅ "Hello from Docker!" |

---

## F4-02 — Revisar memoria disponible para Docker

**Objetivo:** confirmar que el contenedor cabe. Estimado del servicio: ~5.3 GiB (F1-14).

```bash
free -h
docker info --format '{{.MemTotal}}'
```

| Si Docker ve… | Entonces |
|---|---|
| ≥ 7 GiB | Seguir; el contenedor se limita a `-m 6g` en F4-07 |
| < 7 GiB | **Tú** subes `memory=` en `C:\Users\<usuario>\.wslconfig` (p. ej. `12GB`, si la PC tiene RAM para ello), luego `wsl --shutdown` y se repite F4-01 |

**Hecho cuando:** se decidió con qué límite correr.

| Dato | Valor |
|---|---|
| Memoria que ve Docker | 7.76 GiB (≥ 7 GiB) |
| Límite para el contenedor | `-m 6g` |
| ¿Se cambió `.wslconfig`? | No |

---

## F4-03 — Construir la imagen pesada en local

**Objetivo:** probar `Dockerfile.pesada` tal como lo hará Cloud Build, con el `modelo_e5/` local
(idéntico al del bucket, F1-07). Incluye las dos comprobaciones del build: imports silenciosos
(`faiss`, `pysqlite3`) y carga del modelo sin conexión (1024 dimensiones).

```bash
cd $REPO
time docker build -f Dockerfile.pesada -t protocolo01-v2-pesada:local . 2>&1 | tee /tmp/build-pesada.log | tail -20
grep -E "imports ok|modelo ok" /tmp/build-pesada.log
```

> Docker lee todo el contexto del repo menos lo de `.dockerignore` (incluye `modelo_e5/`, 2 GB);
> la primera vez tarda en enviarlo.

**Hecho cuando:** el build termina y aparecen `imports ok` y `modelo ok 1024`.

| Dato | Valor |
|---|---|
| Duración | **10 min 29 s** (07:39:59 → 07:50:28 UTC). Desglose: contexto 2.26 GB en 58 s · torch 95 s · dependencias 88 s · exportar capas 298 s |
| `imports ok` | ✅ (11 s) |
| `modelo ok 1024` | ✅ (16 s, sin conexión) |
| Errores / avisos | 0 errores. Solo el aviso estándar de pip por instalar como root (inofensivo dentro de una imagen). |

---

## F4-04 — Inspeccionar la pesada (tamaño, versiones)

**Objetivo:** confirmar que la imagen tiene exactamente el entorno probado.

```bash
docker images protocolo01-v2-pesada:local --format '{{.Size}}'
docker run --rm protocolo01-v2-pesada:local python --version
docker run --rm protocolo01-v2-pesada:local pip freeze > /tmp/freeze-pesada.txt
# Comparar contra requirements.txt + constraints.txt (deben coincidir todas las versiones)
```

**Hecho cuando:** las versiones coinciden con `requirements.txt` + `constraints.txt` y torch es
`2.9.1+cpu`.

| Dato | Valor |
|---|---|
| Tamaño | 6.01 GB sin comprimir (en Artifact Registry ocupará menos: se guarda comprimida) |
| Python | 3.12.15 sobre Debian 12.15 (bookworm) · venv local: 3.12.3 (mismo menor, solo parche) |
| Versiones distintas a requirements + constraints | **0.** 110 paquetes instalados; los 108 fijados coinciden exacto. 9 restricciones no se usan (`aiohttp` y familia, `narwhals`, `xxhash`: ningún paquete los pide) y 5 paquetes quedaron sin fijar (`coloredlogs`, `humanfriendly`, `importlib-metadata`, `pyasn1-modules`, `rsa`), pero con **la misma versión que el venv** |
| torch | ✅ `2.9.1+cpu` |

---

## F4-05 — Construir la imagen ligera en local

**Objetivo:** probar el `Dockerfile` ligero sobre la pesada local.

```bash
time docker build --build-arg IMAGEN_PESADA=protocolo01-v2-pesada:local \
  -t protocolo01-v2-app:local . 2>&1 | tail -10
```

**Hecho cuando:** el build termina sin errores (debería tardar segundos).

| Dato | Valor |
|---|---|
| Duración | |
| Errores | |

---

## F4-06 — Inspeccionar la ligera (qué archivos lleva)

**Objetivo:** comprobar que solo lleva lo de ejecución y nada de `Zone.Identifier`, datos o claves.

```bash
docker run --rm --entrypoint sh protocolo01-v2-app:local -c \
  'ls -la /app; ls -la /app/web; ls /app/modelo_e5; find / -name "*Zone.Identifier" 2>/dev/null | head; ls /app/.env 2>&1'
docker run --rm --entrypoint sh protocolo01-v2-app:local -c 'head -3 /app/startup.sh | od -c | grep -c "\\r"'
```

**Hecho cuando:** `/app` tiene los 7 módulos, `web/`, `startup.sh` y `modelo_e5/`; sin
`Zone.Identifier`, sin `.env`, sin scripts de ingesta; `startup.sh` sin `\r`.

| Dato | Valor |
|---|---|
| Contenido de `/app` | |
| `Zone.Identifier` / `.env` | |
| `startup.sh` con LF | |

---

## F4-07 — Arrancar el contenedor con el acervo local montado

**Objetivo:** simular Cloud Run: el repo se monta **en solo lectura** en `/mnt/acervo` (como el
bucket), `startup.sh` copia lo que encuentre y arranca `main.py`. Sin clave de DeepSeek todavía.

```bash
docker run -d --name p01v2 -p 8080:8080 -m 6g --cpus 2 \
  -v "$REPO":/mnt/acervo:ro \
  protocolo01-v2-app:local
sleep 20; docker logs p01v2
```

Esperado en los logs: `Copiando procesado-mx/basic-mx/chroma_db_basic`, `Copiando faiss-lista`,
cinco avisos `⚠️ No existe …` (las bases que no están en local), `🚀 Iniciando…`, y uvicorn
escuchando en `0.0.0.0:8080`.

**Hecho cuando:** el contenedor sigue corriendo y los logs muestran lo esperado.

| Dato | Valor |
|---|---|
| Tiempo hasta `Uvicorn running` | |
| Bases copiadas / avisos | |
| Errores | |

---

## F4-08 — Probar front y API sin DeepSeek

**Objetivo:** lo mismo que hará la revisión de arranque de Cloud Run, más el front.

```bash
curl -s -o /dev/null -w "/ → %{http_code}\n" localhost:8080/
curl -s -o /dev/null -w "/web/app.js → %{http_code}\n" localhost:8080/web/app.js
curl -s -o /dev/null -w "Zone.Identifier → %{http_code}\n" "localhost:8080/web/app.js:Zone.Identifier"
curl -s localhost:8080/api/estado | python3 -m json.tool | head -40
curl -s localhost:8080/api/catalogo | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['total'], 'títulos')"
```

**Hecho cuando:** `/` y `/web/app.js` dan 200, `Zone.Identifier` da 404, `/api/estado` muestra
`basic` disponible y las otras 5 no disponibles, y el catálogo da 43 títulos (los locales).

| Prueba | Resultado |
|---|---|
| `/` | |
| `/web/app.js` | |
| `Zone.Identifier` (debe ser 404) | |
| `/api/estado` | |
| `/api/catalogo` | |

---

## F4-09 — Medir memoria con el modelo cargado

**Objetivo:** el dato que decide la memoria del servicio. El modelo se carga en la primera
consulta (§F3-08); para medirlo sin gastar DeepSeek se carga en un proceso aparte dentro del
contenedor, que reproduce lo que hace `recursos.obtener_modelo()`.

```bash
docker stats --no-stream p01v2                 # en reposo
docker exec p01v2 python -c "
import recursos, time
t = time.time(); m = recursos.obtener_modelo(); print('cargado en', round(time.time()-t, 1), 's')
print(len(m.embed_query('prueba')), 'dims')
time.sleep(20)" &
sleep 40; docker stats --no-stream p01v2       # con el modelo cargado (proceso aparte)
```

**Hecho cuando:** se anotaron la memoria en reposo, con el modelo y el tiempo de carga.

| Dato | Valor |
|---|---|
| Memoria en reposo | |
| Memoria con el modelo cargado | |
| Tiempo de carga del modelo | |
| ¿Cabe holgado en 8 GiB? | |

---

## F4-10 — Una consulta real por modo (DeepSeek)

**Objetivo:** probar de punta a punta lo que solo se puede probar con el LLM. **Requiere
autorización** (2 llamadas a DeepSeek; Cita Precisa hace además la extracción de entidades).
Solo se prueba la base **General**, que en local tiene `basic`; FCE y Trámites quedan para la
nube.

```bash
docker rm -f p01v2
docker run -d --name p01v2 -p 8080:8080 -m 6g --cpus 2 \
  --env-file "$REPO/.env" -v "$REPO":/mnt/acervo:ro protocolo01-v2-app:local
# Cita Precisa
curl -s -X POST localhost:8080/api/consulta -H 'Content-Type: application/json' \
  -d '{"base":"GENERAL","query":"artículo 1 de la Constitución"}' | head -c 600
# Razonamiento Jurídico (streaming)
curl -sN -X POST localhost:8080/api/consulta/stream -H 'Content-Type: application/json' \
  -d '{"base":"GENERAL","query":"¿Qué garantiza el artículo 1 constitucional?"}' | tail -c 600
```

> Campos confirmados contra `Consulta` de `main.py`: `query` (1–4000 caracteres) y `base`
> (`GENERAL` por defecto). El modo lo decide la ruta: `/api/consulta` = Cita Precisa,
> `/api/consulta/stream` = Razonamiento.

**Hecho cuando:** ambas consultas responden con texto normativo y sin error.

| Prueba | Resultado |
|---|---|
| Cita Precisa (General) | |
| Razonamiento (General, streaming) | |
| Tiempo de la primera consulta (incluye carga del modelo) | |

---

## F4-11 — Pruebas de fallo controlado

**Objetivo:** comprobar que `startup.sh` se comporta como se diseñó.

```bash
# Sin faiss-lista → debe salir con error
mkdir -p /tmp/acervo-vacio
docker run --rm -m 6g protocolo01-v2-app:local; echo "salida: $?"                                  # sin volumen
docker run --rm -m 6g -v /tmp/acervo-vacio:/mnt/acervo:ro protocolo01-v2-app:local; echo "salida: $?"
rmdir /tmp/acervo-vacio
```

**Hecho cuando:** ambos terminan con `❌ Falta faiss-lista` y salida distinta de 0.

| Prueba | Resultado |
|---|---|
| Sin volumen | |
| Volumen vacío | |

---

## F4-12 — Cierre: memoria final y paso a Fase 5

**Objetivo:** decidir con datos y limpiar.

```bash
docker rm -f p01v2
# Las imágenes :local se conservan hasta terminar la Fase 5 (sirven para comparar)
```

| Decisión | Valor |
|---|---|
| Memoria del servicio (`deploy/service.yaml`) | (8 GiB salvo que F4-09 diga otra cosa) |
| Cambios necesarios a archivos de la Fase 3 | |
| ¿Pasar a Fase 5? | ☐ Sí ☐ No — motivo: |

---

## Hallazgos

| Tarea | Hallazgo | Impacto | Acción propuesta |
|---|---|---|---|
| F4-04 | `constraints.txt` tiene 9 entradas que no se instalan y le faltan 5 que sí se instalan (hoy salen con la versión del venv, pero sin garantía en un build futuro). | Ninguno ahora; riesgo bajo a futuro. | **Aplicado** (aprobado por el responsable): `constraints.txt` queda con 95 restricciones (+5, −9). Validado con `--dry-run`: resolvería exactamente los mismos 110 paquetes y versiones que la pesada local → **no hace falta reconstruirla**; el build en la nube (Fase 5) usará el archivo nuevo y dará el mismo resultado. |
| (previo) | WSL está limitado a 8 GB (`.wslconfig`) y Docker Desktop comparte esa memoria. | El contenedor local no podrá usar los 8 GiB del servicio; ~6 GiB como máximo. | Probar con `-m 6g`; si no alcanza, ampliar `.wslconfig` (F4-02). |
| (previo) | `main.py` ya limita `query` a 4000 caracteres. | Un límite parcial de uso ya existe sin tocar código. | Anotarlo en D6/P4. |
| (previo) | En local solo existe `basic` (y desactualizada); faltan 5 bases. | FCE y Trámites SEGOB no se pueden probar en local. | Probarlos en la nube (Fase 5). Regla: no se baja el acervo. |

---

## Registro

| Fecha | Entrada |
|---|---|
| 2026-10-13 | Se crea la bitácora de Fase 4 con 12 mini-tareas. Verificado: WSL con 7.8 GiB, 8 núcleos, Docker sin integración con WSL. |
| 2026-10-13 | F4-01 hecha: integración activada (responsable), Docker 28.5.1 comprobado (Claude). |
| 2026-10-13 | F4-02 hecha (aprobada por el responsable): Docker ve 7.76 GiB; se prueba con `-m 6g`, sin tocar `.wslconfig`. |
| 2026-10-13 | F4-03 hecha (Claude): pesada local construida en 10.5 min; imports y modelo verificados en el build. |
| 2026-10-13 | F4-04 hecha (Claude): la pesada reproduce el venv exacto (0 diferencias); 6.01 GB; Python 3.12.15. |
| 2026-10-13 | `constraints.txt` ajustado (+5 −9 → 95). Equivalencia con la pesada local verificada: 110/110 iguales. |
