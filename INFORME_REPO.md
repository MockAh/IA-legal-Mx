# INFORME_REPO — Wall-E Legal 2.0

Auditoría de solo lectura generada el 2026-10-05 sobre `/home/mock_/WandaVision/Backend01__` (rama `master`).
No se ejecutó la aplicación, no se instaló nada, no se llamó a DeepSeek ni a GCS, y no se abrió el `.pkl` ni se cargó el índice FAISS.

Notas de método:
- Los archivos fuente usan finales de línea CRLF (`file` lo reporta para `app.py`, `logica_*.py`, `Dockerfile`, `Dockerfile.base`, `startup.sh`). En las transcripciones íntegras de este informe se quitó el `\r`; el resto del contenido es literal.
- Los números de línea citados corresponden a la numeración del archivo tal como está en disco.

---

## 1. ÁRBOL DEL REPO

Comando equivalente: `find . -prune` de `.git`, `.venv`, `__pycache__`, `node_modules`, `modelo_e5`, `procesado-*`, `faiss-lista`.

**Exclusión adicional:** el entorno virtual del repo se llama `venv/` (no `.venv/`) y ocupa **7.4 G**; su listado ocupaba ~2.9 MB de texto, así que también se excluyó. `.venv/` no existe.

`(*)` = archivo que NO está en la lista conocida. Los directorios no se marcan.

```
.
./.dockerignore  (*)
./.env  (*)
./.gcloudignore  (*)
./.gitignore  (*)
./Axiomas/
./Axiomas/legislacion-mx/
./Axiomas/legislacion-mx/FCE/
./Axiomas/legislacion-mx/FCE/Administrativas/
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/1994-07-26_Decreto_se-crea-el-organismo-descentralizado-Fondo-de-Cultura-Económica-y-se-ordena-la-disolución-y-liquidación-de-la-empresa-de-participación_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/1994-07-26_normas_NORMAS-Y-BASES-PARA-EL-OTORGAMIENTO-DE-USO-TEMPORAL-DE-ESPACIOS-EN-INMUEBLES-PROPIEDAD-DEL-FCE-PARA-LA-OPERACIÓN-DE-CAFETERÍAS_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2012-10-03_Acuerdo_ACUERDO-por-el-que-se-establecen-las-disposiciones-en-Materia-de-Recursos-Materiales-y-Servicios-Generales_excep.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2012-10-03_Acuerdo_ACUERDO-por-el-que-se-establecen-las-disposiciones-en-Materia-de-Recursos-Materiales-y-Servicios-Generales_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2017-07-24_Decreto_Reformas_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2018-02-21_Estatuto_ESTATUTO-ORGÁNICO-DEL-FONDO-DE-CULTURA-ECONÓMICA_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2022-06-24_lineamientos_LINEAMIENTOS-POR-LOS-QUE-SE-ESTABLECE-EL-PROCESO-DE-CALIDAD-REGULATORIA-EN-EL-FCE_excep.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2024-03-22_Manual_MANUAL-DE-ORGANIZACIÓN_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2024-12-23_Manual_MANUAL-DE-POLÍTICAS-Y-PROCEDIMIENTOS-DE-LA-COORDINACIÓN-DE-ASUNTOS-JURÍDICOS_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/2025-10-11_Decreto_se-reforman-los-artículos-9-y-10-y-se-adiciona-con-un-10bis-al-Decreto-del-organismo-descentralizado-FCE_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/Administrativas/General-Juridica/23-01-18_políticas_POLÍTICAS-PARA-LA-ELABORACIÓN-Y-ACTUALIZACIÓN-DE-DOCUMENTOS-NORMATIVOS-INTERNOS_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/estatuto_organico/
./Axiomas/legislacion-mx/FCE/estatuto_organico/2025-03-03_estatuto_Estatuto-Orgánico_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/
./Axiomas/legislacion-mx/FCE/sustantiva/1_comercializacion/
./Axiomas/legislacion-mx/FCE/sustantiva/1_comercializacion/17-12-22_manual_Manual-de-Políticas-y-Procedimientos-de-la-Gerencia-Comercial_legal.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/1_comercializacion/18-06-29_manual_Manual-de-Políticas-y-Procedimientos-de-la-Coordinación-de-Vinculación-Internacional_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/2_editorial/
./Axiomas/legislacion-mx/FCE/sustantiva/2_editorial/2016-11-25_propiedad-intelectual_Procedimiento-de-Contratación-de-Derechos-y-Propiedad-Intelectual_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/2_editorial/2019-01-10_manual_Manual-de-Políticas-y-Procedimientos-de-la-Coordinación-General-de-Obras-para-Niños-y-Jóvenes_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/2_editorial/2023-08-25_manual_Manual-de-Procedimientos-de-la-Gerencia-Editorial_semantic.docx  (*)
./Axiomas/legislacion-mx/FCE/sustantiva/3_mercadotecnia/
./Axiomas/legislacion-mx/FCE/sustantiva/3_mercadotecnia/2021-12-29_manual_Manual-de-Políticas-y-Procedimientos-de-la-Subgerencia-de-Mercadotecnia_semantic.docx  (*)
./Axiomas/legislacion-mx/Transparencia/
./Axiomas/legislacion-mx/Transparencia/2021-02-26_ley-cdmx_LEY-DE-TRANSPARENCIA,-ACCESO-A-LA-INFORMACIÓN-PÚBLICA-Y-RENDICIÓN-DE-CUENTAS-DE-LA-CDMX_legal.docx  (*)
./Axiomas/legislacion-mx/Transparencia/2021-02-26_ley-cdmx_LEY-DE-TRANSPARENCIA,-ACCESO-A-LA-INFORMACIÓN-PÚBLICA-Y-RENDICIÓN-DE-CUENTAS-DE-LA-CDMX_legal.docx:Zone.Identifier  (*)
./Axiomas/legislacion-mx/Transparencia/2025-03-20_ley-federal_LEY-FEDERAL-DE-PROTECCIÓN-DE-DATOS-PERSONALES-EN-POSESIÓN-DE-LOS-PARTICULARES_legal.docx  (*)
./Axiomas/legislacion-mx/Transparencia/2025-03-20_ley-federal_LEY-FEDERAL-DE-PROTECCIÓN-DE-DATOS-PERSONALES-EN-POSESIÓN-DE-LOS-PARTICULARES_legal.docx:Zone.Identifier  (*)
./Axiomas/legislacion-mx/Tres_Poderes/
./Axiomas/legislacion-mx/Tres_Poderes/2024-04-01_Ley_LEY-FEDERAL-DE-RESPONSABILIDADES-DE-LOS-SERVIDORES-PÚBLICOS_legal.docx  (*)
./Axiomas/legislacion-mx/Tres_Poderes/2025-10-16_Ley_LEY-DE-AMPARO-REGLAMENTARIA-DE-LOS-ARTÍCULOS-103-Y-107-DE-LA-CONSTITUCIÓN-POLÍTICA_legal.docx  (*)
./Axiomas/legislacion-mx/Tres_Poderes/2025-11-28_Ley_LEY-ORGÁNICA-DEL-PODER-JUDICIAL-DE-LA-FEDERACIÓN_legal.docx  (*)
./Axiomas/legislacion-mx/basic/
./Axiomas/legislacion-mx/basic/1917-02-05_Constitucion-Politica_Constitucion-Politica-de-los-Estados-Unidos-Mexicanos_legal.docx  (*)
./Axiomas/legislacion-mx/basic/1931-08-14_Codigo_Codigo-Penal-Federal_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2015-06-12_Ley-Federal_Ley-Federal-del-Trabajo_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2015-06-12_Ley-Federal_Ley-Federal-del-Trabajo_legal.docx:Zone.Identifier  (*)
./Axiomas/legislacion-mx/basic/2017-02-05_Constitucion-Politca_Constitucion-Politica-de-la-Ciudad-de-Mexico_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2019-05-27_Ley-Nacional_Ley-Nacional-Sobre-el-Uso-de-la-Fuerza_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2025-07-16_Ley-General_Ley-General-del-Sistema-Nacional-de-Seguridad-Publica_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2025-10-03_Reglamento-Interior_Reglamento-Interior-de-la-Secretaria-de-Educacion-Publica_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2025-10-03_Reglamento-Interior_Reglamento-Interior-de-la-Secretaria-de-Educacion-Publica_legal.docx:Zone.Identifier  (*)
./Axiomas/legislacion-mx/basic/2026-01-15_Ley-Federal_LEY-FEDERAL-DE-LOS-TRABAJADORES-AL-SERVICIO-DEL-ESTADO_legal.docx  (*)
./Axiomas/legislacion-mx/basic/2026-01-15_Ley-Federal_LEY-FEDERAL-DE-LOS-TRABAJADORES-AL-SERVICIO-DEL-ESTADO_legal.docx:Zone.Identifier  (*)
./Axiomas/legislacion-mx/segob/
./Axiomas/legislacion-mx/segob/2018-05-18_Ley_LEY-GENERAL-DE-MEJORA-REGULATORIA_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2024-04-01_Ley_LEY GENERAL DE COMUNICACIÓN SOCIAL_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2024-12-17_Ley_LEY-DE-PARTICIPACIÓN-CIUDADANA-DE-LA-CIUDAD-DE-MÉXICO_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2025-03-20_Ley_LEY-GENERAL-DE-TRANSPARENCIA-Y-ACCESO-A-LA-INFORMACIÓN-PÚBLICA_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2025-07-16_Ley_LEY-ORGÁNICA-DE-LA-ADMINISTRACIÓN-PÚBLICA-FEDERAL_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2025-11-14_Ley_LEY-DE-SEGURIDAD-NACIONAL_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2025-11-14_Ley_LEY-GENERAL-DE-PROTECCIÓN-DE-DATOS-PERSONALES-EN-POSESIÓN-DE-SUJETOS-OBLIGADOS_legal.docx  (*)
./Axiomas/legislacion-mx/segob/2025-11-14_Ley_Ley-Federal-de-Procedimiento-Administrativo_legal.docx  (*)
./Axiomas/legislacion-mx/segob/Decretos y Acuerdos/
./Axiomas/legislacion-mx/segob/Decretos y Acuerdos/2025-01-01_Plan-Nacional_PLAN-NACIONAL-DE-DESARROLLO-2025-2030_semantic.docx  (*)
./Axiomas/legislacion-mx/segob/Decretos y Acuerdos/2025-09-03_Decreto_Decreto-Programa-Sectorial-SEGOB-2025-2030_legal.docx  (*)
./Axiomas/legislacion-mx/segob/Particulares/
./Axiomas/legislacion-mx/segob/Particulares/2020-07-02_reglamento_REGLAMENTO-INTERIOR-DE-LA-SECRETARÍA-DE-GOBERNACIÓN_legal.docx  (*)
./Axiomas/legislacion-mx/segob/Particulares/2025-03-21_manual_MANUAL-DE-ORGANIZACIÓN-GENERAL-DE-LA-SECRETARÍA-DE-GOBERNACIÓN_semantic.docx  (*)
./Axiomas/legislacion-mx/segob/Transversal/
./Axiomas/legislacion-mx/segob/Transversal/2021-05-20_Ley_LEY-GENERAL-DEL-SISTEMA-NACIONAL-ANTICORRUPCIÓN_legal.docx  (*)
./Axiomas/legislacion-mx/segob/Transversal/2024-04-01_Ley_LEY-DE-LA-COMISIÓN-NACIONAL-DE-LOS-DERECHOS-HUMANOS_legal.docx  (*)
./Axiomas/legislacion-mx/segob/Transversal/2025-01-02_Ley_LEY-GENERAL-DE-RESPONSABILIDADES-ADMINISTRATIVAS_legal.docx  (*)
./CLAUDE.md  (*)
./CLAUDE.md:Zone.Identifier  (*)
./Dockerfile  (*)
./Dockerfile.base  (*)
./Dockerfile.base:Zone.Identifier  (*)
./Dockerfile:Zone.Identifier  (*)
./GUIA_RAPIDA.sh  (*)
./app - copia.py:Zone.Identifier  (*)
./app.py
./catalogo_axiomas.py
./cloudbuild.yaml
./debug_logica_a.py  (*)
./descargar_modelo.py
./ejecutar_secuencia_embeddings.py  (*)
./init_faiss.py
./inspect_articulos_rapido.py  (*)
./llamada_deepseek.txt  (*)
./logica_a.py
./logica_b.py
./logica_c.py
./orquestador_embe.py  (*)
./rag_app_deepseek.py  (*)
./rag_app_deepseek.py:Zone.Identifier  (*)
./rag_chat_segob_d.py  (*)
./readme.md  (*)
./requirements.txt
./requirements_local.txt
./resultados_validacion_homoclaves_81.csv  (*)
./script_embeddings_3p_55.py
./script_embeddings_basic_55.py
./script_embeddings_excep_mx.py
./script_embeddings_excep_mx.py:Zone.Identifier  (*)
./script_embeddings_fce_55.py
./script_embeddings_listaF.py
./script_embeddings_segob_55.py
./script_embeddings_tramites_2_0.py
./script_embeddings_transp_55.py
./script_legal.py  (*)
./script_semantico.py  (*)
./script_semantico_mog_indice.py  (*)
./startup.sh
./startup.sh:Zone.Identifier  (*)
./test_81_homoclaves_d.py  (*)
./test_logica_a_completo.py  (*)
./test_normalizar.py  (*)
./tramites_secretaria_gobernacion_procesados_rapido.csv  (*)
./utils_rag.py
```

---

## 2. ARCHIVOS DE DESPLIEGUE

Existen: `Dockerfile`, `Dockerfile.base`, `.dockerignore`, `.gcloudignore`, `cloudbuild.yaml`, `startup.sh`.
No existen: `Procfile`, `service.yaml`, `app.yaml`, ni ningún otro archivo de configuración de Cloud Run (no hay definición de memoria, CPU, concurrencia ni timeout del servicio en el repo → **NO DETERMINADO**).

### Dockerfile

```dockerfile
# En lugar de google/cloud-sdk, usamos nuestra propia base ya preparada
FROM gcr.io/alma-juridica-aipp/protocolo01-base:latest

WORKDIR /app

# Solo copiamos el código, que no pesa nada
COPY *.py ./
COPY startup.sh ./
RUN dos2unix startup.sh && chmod +x startup.sh

# Limpiamos el script para evitar errores de formato (Windows/Linux)
RUN dos2unix startup.sh && chmod +x startup.sh

EXPOSE 8080

# Arrancamos con el script que sincroniza datos de GCS
ENTRYPOINT ["./startup.sh"]
```

### Dockerfile.base

```dockerfile
FROM google/cloud-sdk:slim
RUN apt-get update && apt-get install -y python3-pip dos2unix libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
```

### .dockerignore

```
# Excluir bases de datos locales
procesado-mx/
procesado-unam/

# Excluir documentos originales
Axiomas/

# Excluir entornos virtuales y caché
venv/
.env
__pycache__/
*.pyc
.git
.gitignore
```

### .gcloudignore

```
.git
.gcloudignore
# IGNORAR CARPETAS PESADAS LOCALES
modelo_e5/
procesado-mx/
procesado-unam/
venv/
descargar_modelo.py
```

### cloudbuild.yaml

```yaml
steps:
  # PASO 1: Intentar descargar la imagen base previa (Cache)
  - name: 'gcr.io/cloud-builders/docker'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        docker pull gcr.io/$PROJECT_ID/protocolo01-base:latest || exit 0

  # PASO 2: Construir la imagen BASE (Rápido si no hay cambios)
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/protocolo01-base:latest',
      '--cache-from', 'gcr.io/$PROJECT_ID/protocolo01-base:latest',
      '-f', 'Dockerfile.base', '.'
    ]

  # PASO 3: Construir la imagen de la APP (Usando BUILD_ID para evitar errores)
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/protocolo01-app:$BUILD_ID',
      '-t', 'gcr.io/$PROJECT_ID/protocolo01-app:latest',
      '.'
    ]

  # PASO 4: Subir las imágenes (Aquí estaba el error antes)
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'push', 
      'gcr.io/$PROJECT_ID/protocolo01-app:$BUILD_ID'
    ]

# Opcional: También subimos la etiqueta 'latest' para facilitar despliegues
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'push', 
      'gcr.io/$PROJECT_ID/protocolo01-app:latest'
    ]

images:
  - 'gcr.io/$PROJECT_ID/protocolo01-base:latest'
  - 'gcr.io/$PROJECT_ID/protocolo01-app:latest'
```

### startup.sh

```bash
#!/bin/bash
set -e

# 1. Sincronizar la carpeta de Vectores (ChromaDB)
echo "⬇️ Sincronizando carpeta 'procesado-mx'..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-mx ./procesado-mx -r

# 2. CRÍTICO: Sincronizar el Índice de Títulos (FAISS)
# Sin esto, el catálogo y la Lógica A fallarán.
echo "⬇️ Sincronizando carpeta 'faiss-lista'..."
gcloud storage rsync $GCS_BUCKET_PATH/faiss-lista ./faiss-lista -r

# 3. Sincronizar UNAM (Independiente)
echo "⬇️ Sincronizando carpeta 'procesado-unam'..."
gcloud storage rsync $GCS_BUCKET_PATH/procesado-unam ./procesado-unam -r

# 4. Descarga del Modelo de Embeddings (Caché local)
echo "🧠 Descargando modelo de IA..."
gcloud storage rsync $GCS_BUCKET_PATH/modelo_e5 ./modelo_e5 -r

echo "🚀 Iniciando Wall-E Legal 2.0..."
# El flag -u asegura que los logs se vean en tiempo real en Google Cloud
python3 -u app.py
```

### Observaciones literales sobre estos archivos

- `Dockerfile` solo copia `*.py` y `startup.sh` (líneas `COPY *.py ./` y `COPY startup.sh ./`). Una carpeta `web/` **no entraría en la imagen** sin añadir un `COPY`.
- `Dockerfile` repite `RUN dos2unix startup.sh && chmod +x startup.sh` dos veces.
- `Dockerfile` usa la imagen fija `gcr.io/alma-juridica-aipp/protocolo01-base:latest`, mientras `cloudbuild.yaml` construye `gcr.io/$PROJECT_ID/protocolo01-base:latest`. Coinciden solo si `$PROJECT_ID == alma-juridica-aipp` → **NO DETERMINADO**.
- `Axiomas/` está excluido por `.dockerignore`, y el `Dockerfile` tampoco lo copia. Esto importa para `init_faiss.main()` (ver sección 8).
- `.gcloudignore` **no excluye `.env` ni `llamada_deepseek.txt`**. Cuando existe `.gcloudignore`, `gcloud` no aplica `.gitignore` (no hay `#!include:.gitignore`). Por eso `gcloud builds submit` subiría ambos archivos al bucket de código fuente de Cloud Build. Ver la sección 6 sobre `llamada_deepseek.txt`.
- `startup.sh` tiene `set -e` y sincroniza `procesado-unam`. Si esa ruta no existe en el bucket y `gcloud storage rsync` falla, el contenedor no arranca. No se consultó GCS → **NO DETERMINADO**.

---

## 3. CONTRATO DE LAS FUNCIONES DE LÓGICA

Resumen:

| Función | Archivo:línea | Firma | Retorno | Llamadas a DeepSeek por consulta |
|---|---|---|---|---|
| `logica_a_cita_precisa` | `logica_a.py:3` | `(colecciones_legales, embedding_function, query)` | `str` (función normal, sin `yield`) | 1 (extracción de entidades) |
| `logica_b_streaming` | `logica_b.py:3` | `(colecciones_legales, embedding_function, query)` | **generador** de `str`; cada `yield` es el **texto COMPLETO a mostrar** (ACUMULADO durante la redacción) | 2 (entidades + redacción con streaming) |
| `logica_c_avanzada` | `logica_c.py:4` | `(coleccion_segob, coleccion_tramites, embedding_function, query_usuario)` | `str` (función normal, sin `yield`) | 2 (estratega + síntesis) |

Ninguna devuelve diccionario. Ninguna tiene anotaciones de tipo.

### 3.1 `logica_a_cita_precisa`

```python
3	def logica_a_cita_precisa(colecciones_legales, embedding_function, query):
```

Todas las salidas son `return` de un `str`. No hay ningún `yield` en el archivo:

- `logica_a.py:21`: `return "❌ No pude identificar qué ley estás buscando. ..."`
- `logica_a.py:24`: `return "❌ No pude identificar el artículo solicitado. ..."`
- `logica_a.py:40`: `return f"⚠️ No encontré la ley '{titulo_usuario}' en el índice. ..."`
- `logica_a.py:99`: `return respuesta` (éxito; `respuesta` es el f-string de las líneas 87-97)
- `logica_a.py:123`: `return f"⚠️  Encontré la ley '{titulo_exacto}', pero el artículo {articulo_num} no está ..."`

Formato de la respuesta exitosa (`logica_a.py:81-97`):

```python
81	                texto_html = '<div class="contenedor-legal">'
82	                for p in parrafos:
83	                    texto_html += f'<p class="parrafo-legal">{p}</p>'
84	                texto_html += '</div>'
...
87	                respuesta = f"""
88	                ### ⚖️ **EXTRACTO NORMATIVO FORMAL**
...
93	                {texto_html}
...
97	                """
```

Implicaciones verificadas en el código:
- El resultado es **Markdown con HTML incrustado**. Las clases `contenedor-legal` y `parrafo-legal` dependen del CSS de `app.py:211-229`.
- Cada línea del f-string lleva **16 espacios de sangría** porque el texto es literal dentro del bloque indentado. Un parser CommonMark estricto trata 4 o más espacios iniciales como bloque de código. No se ejecutó la app, así que el render actual en Gradio 3.50.2 es **NO DETERMINADO**. El front nuevo debe aplicar dedent o comprobarlo.
- El texto `p` del documento se interpola sin escapar en `<p>` (`logica_a.py:83`).
- Los errores se devuelven como cadenas con prefijo `❌` o `⚠️`. No se lanzan excepciones: las de Chroma se capturan en `logica_a.py:118-120`. Las de `extraer_entidades_con_llm` no se capturan aquí; esa función devuelve `{}` ante error de parseo (`utils_rag.py:126-127`).
- La llamada a DeepSeek ocurre en `logica_a.py:16`, mediante `extraer_entidades_con_llm` y luego `call_deepseek_api` (`utils_rag.py:121`).

### 3.2 `logica_b_streaming` (el punto crítico)

```python
3	def logica_b_streaming(colecciones_legales, embedding_function, query):
```

Es un **generador**: contiene `yield` en las líneas 7, 124, 152, 184 y 188. Llamarla no ejecuta nada hasta iterarla.

**Cada `yield` entrega el texto ACUMULADO, no el fragmento nuevo.** Prueba (`logica_b.py:180-184`):

```python
180	        # Temperatura en 0.0 para máximo determinismo
181	        respuesta_acumulada = ""
182	        for chunk in call_deepseek_api_stream(prompt, temperature=0.2):
183	            respuesta_acumulada += chunk
184	            yield respuesta_acumulada
```

El generador de bajo nivel sí entrega FRAGMENTOS (`utils_rag.py:85-87`):

```python
85	                            delta = json_data['choices'][0]['delta']
86	                            if 'content' in delta:
87	                                yield delta['content'] # Entregamos el fragmento [cite: 80]
```

`logica_b` acumula esos fragmentos y re-emite el total. El consumidor actual lo confirma: **reemplaza** el buffer en cada iteración, no concatena (`app.py:156-159`):

```python
156	            generador = logica_b_streaming(cols_legales, embedding_fn, mensaje)
157	            for fragmento in generador:
158	                buffer_texto = fragmento
159	                yield buffer_texto
```

Secuencia completa de `yield`, en orden de ejecución:

| Línea | Contenido | ¿Prefijo del siguiente? |
|---|---|---|
| `logica_b.py:7` | `"🔍 **Analizando tu consulta y buscando en la normativa mexicana...**"` (estado) | No |
| `logica_b.py:124` | `"❌ No encontré información suficiente ..."` y luego `return` (línea 125) | Fin |
| `logica_b.py:152` | `"⚖️ **Analizando y redactando respuesta...**"` (estado) | No |
| `logica_b.py:184` | `respuesta_acumulada` (crece en cada chunk) | Sí, entre yields de esta línea |
| `logica_b.py:188` | `mensaje_error` (cualquier excepción, `except` de la línea 186) | Fin |

Consecuencias para el endpoint SSE:
- Los dos mensajes de estado (7 y 152) **no son prefijo** de la respuesta final. Por eso el cliente debe tratar cada evento como **reemplazo total**. La otra opción es que el envoltorio calcule el delta solo a partir de la primera emisión de la línea 184, y no puede distinguirla por contenido de forma fiable.
- Si se envía el acumulado completo en cada evento, el tráfico crece de forma cuadrática con la longitud de la respuesta.
- Los errores de la API llegan **dentro del flujo de texto**, no como excepción:
  - Sin clave: `utils_rag.py:55` emite `"ERROR: No se encontró DEEPSEEK_API_KEY."` como si fuera contenido. Esa cadena se acumula y se emite en la línea 184.
  - Fallo de red o HTTP: `utils_rag.py:90-91` emite `f"Error API: {e}"`, que se **concatena** al texto ya acumulado.
- El generador captura toda `Exception` (líneas 186-188), así que no propaga errores al llamador.
- `extraer_entidades_con_llm(query)` (línea 10) es una llamada **bloqueante** a DeepSeek que ocurre entre el primer `yield` y el segundo.

### 3.3 `logica_c_avanzada`

```python
4	def logica_c_avanzada(coleccion_segob, coleccion_tramites, embedding_function, query_usuario):
```

Función normal sin `yield`. Retorna `str`:
- `logica_c.py:10`: `return "⚠️ Error: Las bases de datos especializadas (SEGOB/Trámites) no están listas."`
- `logica_c.py:111`: `return call_deepseek_api(prompt_final, temperature=0.1)`. `call_deepseek_api` está anotada `-> str` (`utils_rag.py:93`). Ante error devuelve las cadenas `"ERROR: No se encontró DEEPSEEK_API_KEY."` (`utils_rag.py:97`) o `f"Error API: {e}"` (`utils_rag.py:111`), sin lanzar excepción.

Hace dos llamadas a DeepSeek: `logica_c.py:46` (estratega) y `logica_c.py:111` (síntesis).
Los nombres de los parámetros difieren de `CLAUDE.md` (`col_segob, col_tramites, ..., query`), pero el orden posicional coincide.
El llamador actual muestra un estado previo propio, ajeno a `logica_c` (`app.py:168`: `yield "⏳ Procesando solicitud de trámites..."`).

---

## 4. ESTADO DE LOS DATOS LOCALES

| Carpeta | ¿Existe? | Tamaño (`du -sh`) | Subcarpetas de primer nivel |
|---|---|---|---|
| `procesado-mx/` | Sí | 36M | `basic-mx` **(solo esa)** |
| `faiss-lista/` | Sí | 240K | (ninguna) |
| `modelo_e5/` | Sí | 2.2G | `1_Pooling`, `2_Normalize` |
| `procesado-unam/` | **No** | — | — |

Detalle de `procesado-mx/basic-mx/`: `chroma_db_basic` (32M), `mapa_basic.json`, `metadata_basic.json` (4.2M) y `sincro_basic.json`.

**Faltan en local** las rutas que `app.py:76-81` espera:
- `procesado-mx/segob-mx/chroma_db_segob`
- `procesado-mx/transp-mx/chroma_db_transp`
- `procesado-mx/3p-mx/chroma_db_3p`
- `procesado-mx/fce-mx/chroma_db_fce`
- `procesado-mx/tramites-mx/chroma_db_tramites_mx`

En local, por tanto, `FCE` y `Trámites SEGOB` devolverían el error de "no se encontraron bases" (`app.py:142-148`). Cita Precisa, Razonamiento y la futura base General solo consultarían `basic`.

Contenido de `faiss-lista/` (listado con `ls -la`, sin abrir archivos):

| Archivo | Bytes | Fecha |
|---|---|---|
| `indice_titulos_leyes.faiss` | 176173 | Mar 10 2026 — **presente** |
| `metadata_titulos_leyes.pkl` | 14943 | Mar 10 2026 — **presente** |
| `inspeccion_base_datos.json` | 44562 | Mar 10 2026 (extra, lo genera `init_faiss.py:33`) |

Archivos de primer nivel en `modelo_e5/`: `README.md`, `config.json`, `config_sentence_transformers.json`, `model.safetensors`, `modules.json`, `sentence_bert_config.json`, `special_tokens_map.json`, `tokenizer.json` y `tokenizer_config.json`.

---

## 5. ENTORNO

- Python del sistema: `Python 3.12.3` (`/usr/bin/python3`).
- Entorno virtual: **`venv/`** (no `.venv/`), creado con `/usr/bin/python3 -m venv .../venv`, Python 3.12.3, `include-system-site-packages = false`.
- Versiones instaladas en `venv/` (`venv/bin/pip list`):

| Paquete | Versión |
|---|---|
| gradio | 3.50.2 |
| gradio_client | 0.6.1 |
| chromadb | 1.4.0 |
| faiss-cpu | 1.13.2 |
| langchain-huggingface | 1.2.0 |
| fastapi | 0.128.0 |
| uvicorn | 0.40.0 |
| starlette | 0.50.0 |
| pysqlite3-binary | 0.5.4.post2 |
| sentence-transformers | 5.2.0 |

- `fastapi` y `uvicorn` **no** aparecen en `requirements.txt` ni en `requirements_local.txt`. Están instalados como dependencias de `gradio` (`pip show gradio` → `Requires: ... fastapi ... uvicorn ...`). En la imagen de producción sus versiones quedan sin fijar → **NO DETERMINADO**.
- No se verificó qué versiones se instalan en la imagen de Cloud Run (`Dockerfile.base` hace `pip3 install -r requirements.txt` sin pins, salvo `gradio==3.50.2`) → **NO DETERMINADO**.
- Variables definidas en `.env` (solo nombres): **`DEEPSEEK_API_KEY`**. Es la única línea no vacía del archivo. `GCS_BUCKET_PATH` y `PORT` **no** están en `.env`.

---

## 6. GIT

- Rama actual: `master`
- Últimos commits (`git log --oneline -10`; el historial solo tiene 3):

```
bc50d0e Wall-E Legal 2.0; Primera versión #Laisha
1614ca0 readme.md: Agregando documentación de instalación y modelo local
e25bb55 Primer Commit: morado, negro, blanco / Botón "FCE" con "principal-mx" y "excep-mx"
```

- Cambios sin commitear (`git status --porcelain`):

```
 M .gitignore
 M catalogo_axiomas.py
 D script_embeddings_dual_unam.py
 D script_embeddings_eva_5_2.py
 D script_embeddings_eva_5_5.py
 D script_embeddings_eva_SEGOB.py
 M startup.sh
?? CLAUDE.md
?? CLAUDE.md:Zone.Identifier
?? Dockerfile.base:Zone.Identifier
?? Dockerfile:Zone.Identifier
?? "app - copia.py:Zone.Identifier"
?? llamada_deepseek.txt
?? startup.sh:Zone.Identifier
```

  `git diff --stat` (solo los archivos rastreados):

```
 .gitignore                     |  41 ++--
 catalogo_axiomas.py            | 164 ++++++-------
 script_embeddings_dual_unam.py | 311 -----------------------
 script_embeddings_eva_5_2.py   | 484 ------------------------------------
 script_embeddings_eva_5_5.py   | 541 -----------------------------------------
 script_embeddings_eva_SEGOB.py | 364 ---------------------------
 startup.sh                     |  18 +-
 7 files changed, 107 insertions(+), 1816 deletions(-)
```

  Nota: aparece `app - copia.py:Zone.Identifier`, pero `app - copia.py` no existe en disco.

- Contenido de `.gitignore`:

```
# Dependencias (Súper pesadas)
node_modules/
bin/
obj/

# Entornos virtuales de Python (Muy comunes en Backend)
venv/
.venv/
env/
__pycache__/
*.pyc

# Archivos de configuración sensible
.env

# Archivos grandes de datos o logs
*.log
*.sqlite3
data/
temp/

# Archivos de sistema
.DS_Store
Thumbs.db

#Carpetas del proyecto
Axiomas
faiss-lista
modelo_e5
procesado-mx

# Classic
Llamar_deepseek.txt
```

**Hallazgo de seguridad:** `llamada_deepseek.txt` (700 bytes, sin rastrear) contiene **2 cadenas con el patrón de una clave de API** (`sk-` seguido de 10 o más caracteres alfanuméricos; no se imprimieron sus valores). `.gitignore:33` ignora `Llamar_deepseek.txt`, que **no coincide** con `llamada_deepseek.txt` (`git check-ignore` no lo reporta). Un `git add .` lo versionaría. Además, `.gcloudignore` no lo excluye (ver sección 2). Si la clave es real, conviene rotarla y corregir la regla de ignore.

---

## 7. FRONTEND EXISTENTE

- `web/`, `static/`, `templates/`, `assets/`: **ninguna existe**.
- Archivos `.html` / `.htm` / `.css` / `.js` fuera de `venv/`, `.git/`, `modelo_e5/` y `procesado-*`: **ninguno**.

### CSS personalizado en `app.py` (líneas 189-230, íntegro)

```python
189	tema = gr.themes.Soft(primary_hue="orange", secondary_hue="blue")
190	css = """
191	.gradio-container {background-color: #FFFDF7;}
192	footer {display: none !important;}
193	
194	/* Estilo para el bloque de texto legal */
195	blockquote {
196	    border-left: 4px solid #E65100; /* Naranja profundo */
197	    background-color: #FFF3E0;
198	    padding: 15px;
199	    margin: 10px 0;
200	    line-height: 1.6; /* Mejora la lectura de párrafos largos */
201	    color: #212121;
202	}
203	
204	/* Resaltado de los números de párrafo */
205	blockquote strong {
206	    color: #1565C0;
207	    font-variant: small-caps;
208	}
209	
210	/* Centrar el contenedor del texto dentro de la caja de Gradio */
211	.contenedor-legal {
212	    width: 90%;            /* Ocupa el 90% del ancho para dejar márgenes */
213	    margin: 20px auto;     /* Centra el bloque horizontalmente */
214	    padding: 15px;
215	    background-color: #ffffff;
216	    border: 1px solid #e0e0e0;
217	    border-radius: 4px;
218	}
219	
220	/* Estilo para cada párrafo: Justificado y con Sangría Sencilla */
221	.parrafo-legal {
222	    text-align: justify;   /* Texto Justificado */
223	    text-indent: 40px;     /* Sangría en la primera línea */
224	    margin-bottom: 1.2em;  /* Espacio entre párrafos */
225	    line-height: 1.5;      /* Interlineado cómodo para lectura legal */
226	    color: #1a1a1a;
227	    font-family: 'Times New Roman', serif; /* Opcional: fuente más tradicional */
228	    user-select: text;
229	}
230	"""
```

### HTML personalizado

- `app.py` no contiene HTML literal. El único HTML de la interfaz lo genera `logica_a.py:81-84` con las clases `contenedor-legal` y `parrafo-legal`, definidas en el CSS de arriba (`app.py:211-229`).
- `app.py:255` asigna `elem_classes="buffer-container"`, pero esa clase **no tiene regla CSS** en `app.py`.
- Encabezado de la interfaz en `app.py:233`: `gr.Markdown("# ⚖️🔶 Wall-E Legal 2.0")`.
- Encabezado del catálogo en `catalogo_axiomas.py:56`: `"## 🏛️ Acervo Documental del Juez Scharseinegger\n"`.

---

## 8. RIESGOS PARA MIGRAR A FASTAPI

1. **`app.py` tiene efectos secundarios al importarse.** Importarlo desde `main.py`, por ejemplo para reutilizar `obtener_colecciones_por_modo`, ejecuta todo esto:
   - el parche SQLite (`app.py:6-12`);
   - `load_dotenv()` (`app.py:25`);
   - `init_faiss.main()` (`app.py:32-37`);
   - la construcción completa del `gr.Blocks` (`app.py:232-337`);
   - `generar_catalogo()` (`app.py:271`), que abre el `.pkl`.

   `obtener_colecciones_por_modo`, `get_db_collection`, `get_embedding_function` y `RECURSOS_CACHE` viven en `app.py`, no en un módulo aparte.
2. **`init_faiss.main()` puede regenerar el índice al arrancar.** Si faltan los archivos de `faiss-lista/` (`init_faiss.py:211`), llama a `generar_indices_faiss()`. Esa función carga un segundo modelo con `SentenceTransformer` (`init_faiss.py:154`) y escribe en `faiss-lista/` (`init_faiss.py:191-193`). Necesita `Axiomas/`, que no está en la imagen Docker (`.dockerignore`), así que en Cloud Run fallaría y solo dejaría avisos.
3. **`init_faiss.py:17-21` hace `sys.exit(1)` al importarse si falta `faiss`.** `SystemExit` no hereda de `Exception`, así que el `except Exception` de `app.py:35` **no lo captura** y el proceso termina. Además, `init_faiss.py:23` importa `sentence_transformers` a nivel de módulo.
4. **Parche pysqlite3.** Debe ejecutarse antes de cualquier `import chromadb`, directo o transitivo, en el nuevo punto de entrada. Verificado: `logica_a.py`, `logica_b.py`, `logica_c.py`, `utils_rag.py` y `catalogo_axiomas.py` **no importan chromadb**. Por eso `main.py` puede importarlos sin riesgo, siempre que el parche vaya antes de `import chromadb`. `pysqlite3-binary` también está instalado en local, así que en local el parche se aplica.
5. **Singletons perezosos sin lock.**
   - `RECURSOS_CACHE` (`app.py:40-69`) y `CACHE_FAISS` (`utils_rag.py:132-136`, carga en `195-196`) se inicializan en la primera petición, con un `if ... is None` sin sincronización.
   - Con FastAPI, los endpoints `def` corren en un threadpool. Dos peticiones simultáneas en frío pueden cargar el modelo de ~2.2 G dos veces.
   - Conviene precargar ambos en el `lifespan`.
6. **Hoy el código nunca ha corrido en concurrencia.**
   - `app.py:340` usa `demo.queue()` sin `concurrency_count`. En Gradio 3.x el valor por defecto es 1, así que `stream_response` se ejecuta de forma serializada. Este valor por defecto viene de la documentación de Gradio 3.x y no se verificó ejecutando.
   - No está verificado si `HuggingFaceEmbeddings.embed_query` y las consultas a un mismo `chromadb.PersistentClient` son seguros entre hilos con estas versiones → **NO DETERMINADO**.
7. **Ruta del modelo relativa al CWD, no a `BASE_DIR`.**
   - `app.py:49` usa `model_name="./modelo_e5"`. Si uvicorn se lanza desde otro directorio, la carga falla y el `except:` desnudo de `app.py:51` hace que se descargue `intfloat/multilingual-e5-large` desde Hugging Face Hub (`app.py:52-54`): red más ~2 G en tiempo de ejecución, en silencio.
   - El resto de las rutas sí usa `__file__`/`BASE_DIR`: `app.py:26` y `75-82`, `utils_rag.py:148`, `catalogo_axiomas.py:5-7` e `init_faiss.py:26-29`.
   - `startup.sh` sincroniza en `./`, relativo al CWD; en la imagen es `WORKDIR /app`.
8. **La caché de colecciones usa solo la ruta como clave y crea colecciones vacías.**
   - `get_db_collection` (`app.py:57-69`) guarda en caché por `path_str` (línea 58), sin tener en cuenta `collection_name`, y usa `get_or_create_collection` (línea 62).
   - Para Trámites, la primera llamada con `"tramites_gob_mx"` (`app.py:108`) **crea una colección vacía en disco** si no existe, y la devuelve. El fallback a `"langchain"` (`app.py:109-110`) nunca se ejecuta.
   - Es comportamiento actual; un endpoint nuevo lo heredaría.
9. **E/S bloqueante.** `requests.post(..., timeout=90)` en `utils_rag.py:72-73` y `107` es síncrono, y el embedding también.
   - Si los endpoints se declaran `async def` y llaman directamente a la lógica, bloquean el event loop.
   - Hay que usar endpoints `def` o `run_in_threadpool`.
   - Un `StreamingResponse` con generador síncrono lo itera Starlette en el threadpool.
10. **Los errores llegan como texto, no como excepciones.** Las tres funciones devuelven o emiten cadenas de error. Los prefijos que aparecen son `❌`, `⚠️`, `ERROR:` y `Error API:`.
    - Sin lógica extra en el envoltorio, el endpoint respondería HTTP 200 también en errores.
    - Ver los detalles en la sección 3.
11. **Semántica del streaming.** `logica_b_streaming` emite el texto acumulado y mensajes de estado que no son prefijo de la respuesta (sección 3.2). El SSE debe definir el reemplazo total como contrato, o calcular deltas en el envoltorio.
12. **Dependencias del ciclo de vida de Gradio.**
    - El historial vive en el componente `gr.Chatbot` del cliente con el formato `[[pregunta, respuesta]]` (`app.py:116-124`, `175-185`). No hay estado de sesión en el servidor.
    - Las funciones de lógica son de un solo turno: solo reciben `query`.
    - El enrutado por modo, la validación de colecciones y el mensaje previo de Trámites están en `stream_response` (`app.py:126-173`). No son reutilizables sin importar `app.py` (riesgo 1).
13. **Mapeo modo→colección incompleto para el front nuevo.**
    - `obtener_colecciones_por_modo` no tiene rama `"General"` (`app.py:88-110`); un modo desconocido devuelve listas vacías.
    - El modo `"FCE"` usa hoy `logica_b_streaming` (`app.py:161-165`), no `logica_a`.
    - El código no define qué debe hacer la combinación pestaña × base. Por ejemplo, Cita Precisa con base FCE o Razonamiento con base Trámites, cuando `logica_c` no distingue modo → **NO DETERMINADO**; es decisión de diseño.
14. **El render del HTML exige saneamiento.** La respuesta de Cita Precisa incrusta texto del documento sin escapar (`logica_a.py:83`), y la de Razonamiento es Markdown generado por el LLM. El front tendrá que renderizar Markdown con HTML y sanearlo. Eso implica, probablemente, una librería JS nueva que hoy no existe.
15. **Montar Gradio en `/legacy`.** Coexisten gradio 3.50.2, fastapi 0.128.0 y starlette 0.50.0 en `venv/`. No está verificado que `gr.mount_gradio_app` funcione con estas versiones → **NO DETERMINADO**.
16. **Varios workers multiplican la memoria.** `uvicorn --workers N` carga el modelo y el índice FAISS en cada proceso. La memoria configurada en Cloud Run no está en el repo → **NO DETERMINADO**.
17. **Despliegue.**
    - `Dockerfile` no copia `web/`.
    - `startup.sh` termina en `python3 -u app.py`.
    - `PORT` se lee en `app.py:342`, y el nuevo arranque debe respetarlo.
    - `procesado-unam` falta en local, y `startup.sh` lo sincroniza con `set -e` (sección 2).
