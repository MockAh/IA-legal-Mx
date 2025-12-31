# -*- coding: utf-8 -*-
"""
rag_chat_segob_1.py (Versión 8.0 - Lógica C Operacional)
Implementa la lógica híbrida: Leyes -> Query Enriquecida -> Trámites.
"""
import os
import argparse
import chromadb
import json
import requests
import torch
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env.
load_dotenv()

# --- 1. CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent
COLLECTION_NAME = "langchain"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large-instruct"

# --- DETECCIÓN DE HARDWARE ---
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
# Nota: Requiere 'import torch' al inicio

# --- 2. MÓDULO REUTILIZABLE PARA LA API (call_deepseek_api) ---
# Estas variables se cargan desde el entorno (asegúrate de que .env esté correcto)
# LLM_API_BASE = os.getenv("LLM_API_BASE")
# LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL")
# LLM_API_KEY = os.getenv("VLLM_API_KEY") 

def call_deepseek_api(prompt: str, temperature: float = 0.0) -> str:
    """
    Función centralizada para hacer llamadas a la API de DeepSeek.
    Maneja la autenticación y la estructura de la petición.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        # api_key = "tu_clave_api_aqui" # Descomentar para pruebas locales
        return "ERROR: No se encontró la clave API de DeepSeek. Configura la variable de entorno DEEPSEEK_API_KEY."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    try:
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"ERROR de conexión con la API de DeepSeek: {e}"
    except (KeyError, IndexError) as e:
        return f"ERROR al procesar la respuesta del LLM: {e}"

# --- 3. LÓGICAS A y B (Omitidas para brevedad, asumiendo que están intactas) ---

def extraer_entidades_con_llm(query: str) -> dict:
    """Usa el LLM para extraer entidades para la Lógica A."""
    print("\n🔍 Usando API de DeepSeek para extraer entidades...")
    
    prompt = f"""
    Analiza la siguiente consulta y extrae las entidades "titulo_documento" y "Articulo" en formato JSON.
    REGLAS ESTRICTAS:
    1. El valor de "titulo_documento" NO DEBE CONTENER ACENTOS.
    2. El valor de "Articulo" debe ser un string que contenga únicamente el número o identificador ordinal/decimal.
    3. Si una entidad no se encuentra, su valor debe ser null.
    EJEMPLO:
    - Consulta: "Qué dice el artículo 1 de la Ley Orgánica de la UNAM"
    - JSON Correcto: {{"titulo_documento": "ley organica de la unam", "Articulo": "1"}}
    TAREA:
    - Consulta: "{query}"
    - JSON Resultante:
    """
    llm_output = call_deepseek_api(prompt)
    
    try:
        print(f"   JSON recibido del LLM: {llm_output}")
        if "```json" in llm_output:
            llm_output = llm_output.split("```json\n")[1].split("```")[0]
        return json.loads(llm_output)
    except (json.JSONDecodeError, TypeError, IndexError):
        print(f"   ❌ ERROR al decodificar la respuesta del LLM.")
        return {}

def logica_a_cita_por_metadatos(colecciones_legales: list[chromadb.Collection], embedding_function, query: str):
    """
    Lógica A (v5 - Multi-DB): Itera sobre una lista de colecciones para encontrar
    la cita precisa que el usuario solicita.
    """
    print("\n--- Ejecutando Lógica A (v5 Multi-DB) ---")

    print("\nPASO 1: Extrayendo entidades clave (documento y artículo)...")
    entidades = extraer_entidades_con_llm(query)
    titulo_buscado = entidades.get("titulo_documento")
    articulo_num = entidades.get("Articulo")

    if not titulo_buscado:
        print("\n🚫 El LLM no pudo identificar un 'titulo_documento'. No se puede continuar.")
        return

    texto_chunk_final = None
    metadata_final = None

    for i, collection in enumerate(colecciones_legales):
        print(f"\n🔎 Buscando en la base de datos #{i+1} (Colección: {collection.name})...")
        
        try:
            search_results = collection.query(
                query_embeddings=[embedding_function.embed_query(query)],
                n_results=1,
                where={"titulo_documento": {"$eq": titulo_buscado}}
            )
            
            if not search_results.get('metadatas') or not search_results['metadatas'][0]:
                print(f"  - No se encontró el documento '{titulo_buscado}' en esta DB.")
                continue

            metadata_encontrado = search_results['metadatas'][0][0]
            fuente_correcta = metadata_encontrado.get("source")
            print(f"  ✅ Documento encontrado: '{metadata_encontrado.get('titulo_documento')}' (Fuente: {fuente_correcta})")

            if not articulo_num:
                print("  ⚠️ El LLM no identificó un número de artículo. Se mostrará el chunk más relevante del documento.")
                texto_chunk_final = search_results['documents'][0][0]
                metadata_final = search_results['metadatas'][0][0]
                break 

            condiciones_filtro = [{"source": {"$eq": fuente_correcta}}, {"Articulo": {"$eq": articulo_num}}]
            if "transitorio" in query.lower():
                condiciones_filtro.append({"Transitorio": {"$ne": "Principal"}})
            else:
                condiciones_filtro.append({"Transitorio": {"$eq": "Principal"}})
            
            filtro_preciso = {"$and": condiciones_filtro}
            
            results = collection.query(
                query_embeddings=[embedding_function.embed_query(query)],
                where=filtro_preciso,
                n_results=1
            )
            if results.get('documents') and results['documents'][0]:
                texto_chunk_final = results['documents'][0][0]
                metadata_final = results['metadatas'][0][0]
                print(f"  ✅ ¡Artículo '{articulo_num}' encontrado en esta DB!")
                break
            else:
                print(f"  - No se encontró el artículo '{articulo_num}' en este documento.")

        except Exception as e:
            print(f"\n❌ ERROR durante la búsqueda en la colección {collection.name}: {e}")
            continue
    
    if texto_chunk_final and metadata_final:
        print("\n" + "="*25 + " ¡VICTORIA! CITA RECUPERADA " + "="*24)
        print(f'\n"{texto_chunk_final}"\n\n---')
        print(f"🔖 Metadatos: Fuente: {metadata_final.get('source', 'N/A')}, Título: {metadata_final.get('titulo_documento', 'N/A')}, Artículo: {metadata_final.get('Articulo', 'N/A')}, Tipo: {metadata_final.get('Transitorio', 'N/A')}")
        print("="*78)
    else:
        print("\n🚫 Búsqueda finalizada. No se pudo encontrar la cita precisa en ninguna de las bases de datos disponibles.")

def logica_b_explicacion_juridica(colecciones_legales: list[chromadb.Collection], embedding_function, query: str):
    """
    Lógica B (v5 - Citas Duales): Recupera chunks con sus metadatos y los formatea
    para que el LLM pueda citar documentos de tipo 'legal' (con Artículo) y
    'semantic' (sin Artículo) de forma precisa.
    """
    print("\n--- Ejecutando Lógica B (v5 - Citas Duales) ---")
    
    # --- PASO 1: Buscar contexto y metadatos en todas las fuentes ---
    print("\n🧠 PASO 1: Buscando contexto y metadatos en todas las fuentes...")
    contexto_compilado = []
    textos_unicos = set()

    for i, collection in enumerate(colecciones_legales):
        try:
            print(f"  - Consultando base de datos #{i+1} (Colección: {collection.name})...")
            results_legal = collection.query(
                query_embeddings=[embedding_function.embed_query(query)],
                n_results=7,
                include=["metadatas", "documents"]
            )
            if results_legal and results_legal['documents'][0]:
                docs = results_legal['documents'][0]
                metadatas = results_legal['metadatas'][0]
                
                for doc, meta in zip(docs, metadatas):
                    if doc not in textos_unicos:
                        contexto_compilado.append({'texto': doc, 'metadata': meta})
                        textos_unicos.add(doc)
                
                print(f"    ➡️  Recuperados {len(docs)} chunks. Total únicos: {len(contexto_compilado)}")
        except Exception as e:
            print(f"    ❌ ERROR en la búsqueda de legislación en la colección {collection.name}: {e}")

    if not contexto_compilado:
        print("\n🚫 No se encontró suficiente contexto legal para generar una explicación.")
        return

    # --- PASO 2: Formatear el contexto para el LLM con fuentes explícitas ---
    print("\n📑 PASO 2: Formateando contexto para el LLM con fuentes explícitas...")
    contexto_formateado_parts = []
    for item in contexto_compilado:
        meta = item['metadata']
        titulo = meta.get('titulo_documento', 'Documento sin título').title()
        # Se recupera el artículo. Puede ser un número o la etiqueta "<No aplica>".
        articulo = meta.get('Articulo', '<No aplica>')
        
        # --- INICIO DE LA MODIFICACIÓN ---
        # Lógica condicional para construir la fuente basándose en el metadato 'Articulo'
        if articulo and articulo.lower() != '<no aplica>':
            # Si hay un artículo válido (no es la etiqueta por defecto), se incluye.
            fuente_str = f"Fuente: [Título del Documento: {titulo}], [Artículo: {articulo}]"
        else:
            # Si es un chunk semántico, solo se usa el título.
            fuente_str = f"Fuente: [Título del Documento: {titulo}]"
        # --- FIN DE LA MODIFICACIÓN ---

        chunk_str = f"---\n{fuente_str}\nTexto: {item['texto']}\n---"
        contexto_formateado_parts.append(chunk_str)
    
    contexto_final_para_llm = "\n\n".join(contexto_formateado_parts)
    print(f"✅ Contexto final formateado con {len(contexto_compilado)} chunks únicos.")
    
    # --- PASO 3: Generación de la explicación con el LLM y el nuevo prompt ---
    print("\n💬 PASO 3: Usando API de DeepSeek para generar la explicación ciudadana...")
    
    # --- INICIO DE LA MODIFICACIÓN DEL PROMPT ---
    prompt_explicacion = f"""
### Personalidad
Eres "Aura Legal", una asistente experta en derecho mexicano diseñada para empoderar a la ciudadanía. Tu propósito no es solo citar leyes, sino **revelar la lógica detrás de ellas y traducirla en acción**. Eres didáctica, clara y usas metáforas brillantes para hacer entendible lo complejo.

### Contexto Informativo
La siguiente información es tu única fuente de verdad. Cada fragmento de texto viene precedido por su `Fuente`, que indica el `Título del Documento` y, a veces, el `Artículo` al que pertenece. Basa todas tus conclusiones EXCLUSIVAMENTE en estos textos.
---
{contexto_final_para_llm}
---

### Tarea Principal
Analiza la pregunta del usuario y el contexto proporcionado para generar una respuesta que cumpla con los siguientes 3 pasos obligatorios:

1.  **La Lógica en Sencillo:** Explica la lógica fundamental de la ley usando una **metáfora o analogía central** que sea fácil de entender.

2.  **Estrategias y Pasos a Seguir:** Sugiere **de 2 a 3 estrategias o caminos de acción** claros y realistas, basados estrictamente en el contexto.

3.  **Cita tus Fuentes (Con Precisión):** Mientras explicas, **DEBES** citar la fuente de tu razonamiento basándote en la línea `Fuente:` que precede a cada texto. Tu formato de cita debe adaptarse a la información disponible:
    * Si la `Fuente` incluye un `Artículo`, usa el formato: `(Referencia, [Título del Documento], Artículo X)`.
    * Si la `Fuente` **NO** incluye un `Artículo` (porque es un documento de tipo semántico), usa el formato: `(Referencia, [Título del Documento])`.
    
    **Ejemplos de Citas Correctas:**
    - Para un archivo 'legal': "...esto se basa en la obligación de la Universidad (Ley Orgánica de la UNAM, Artículo 1)."
    - Para un archivo 'semantic': "...el procedimiento está descrito en la guía oficial (Manual de Procedimientos de la DGAE)."

### Formato de Salida
Estructura tu respuesta de la siguiente manera, usando los títulos exactos:

**[Un Título Creativo para la Explicación]**

**La Lógica en Sencillo**
[Tu explicación clara usando la metáfora central y las citas precisas.]

**Estrategias y Pasos a Seguir**
[Tus estrategias numeradas, con citas precisas.]

**Importante:**
[Concluye con la advertencia legal estándar.]

### Pregunta del Usuario
{query}
"""
    # --- FIN DE LA MODIFICACIÓN DEL PROMPT ---
    
    explicacion = call_deepseek_api(prompt_explicacion)
    
    print("\n" + "="*23 + " EXPLICACIÓN JURÍDICA GENERADA " + "="*23)
    print(explicacion)
    print("="*78)

# --- 4. ✨ LÓGICA C: TRÁMITES CON ENRIQUECIMIENTO LEGAL ---

def logica_c_avanzada(colecciones_legales: list, coleccion_tramites, embedding_function, query_usuario: str):
    """
    Lógica C (Doble Paso - Anti-Alucinación):
    Exploración -> Queries Refinadas (X/Y) -> Búsqueda Dual -> Síntesis Estricta.
    """
    print("\n--- 🛡️ Ejecutando Lógica C (Avanzada - Strict Mode) ---")
    
    # =========================================================================
    # PASO i y ii: Primera búsqueda "Raw" (Exploración)
    # =========================================================================
    print("\n🔍 PASO 1: Exploración Legal Inicial (Top 6)...")
    
    # Aplicamos prefijo E5 a la query original
    query_raw_embeddings = embedding_function.embed_query(f"query: {query_usuario}")
    
    contexto_legal_inicial = []
    # Recolectamos de todas las colecciones legales disponibles
    for col in colecciones_legales:
        try:
            results = col.query(
                query_embeddings=[query_raw_embeddings],
                n_results=3 
            )
            if results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    ref = f"Doc: {meta.get('titulo_documento')} (Art. {meta.get('Articulo', 'N/A')})"
                    contexto_legal_inicial.append(f"- [{ref}]: {doc}")
        except Exception: pass

    # Nos quedamos con los Top 6 para dar contexto al LLM
    contexto_legal_inicial = contexto_legal_inicial[:6]
    texto_contexto_raw = "\n".join(contexto_legal_inicial)

    # =========================================================================
    # PASO iii: Primera Llamada al LLM (El Estratega)
    # =========================================================================
    print("\n🧠 PASO 2: LLM definiendo estrategia de búsqueda (Query X y Y)...")
    
    prompt_estratega = f"""
    Eres un experto en investigación jurídica.
    Duda del Usuario: "{query_usuario}"
    Contexto Preliminar:
    {texto_contexto_raw}
    
    INSTRUCCIONES:
    Genera un JSON con dos claves para profundizar la investigación:
    - "query_x": Búsqueda técnica para la LEY (usa términos jurídicos vistos en el contexto).
    - "query_y": Búsqueda operativa para el TRÁMITE (usa términos como requisitos, licencia, permiso, formato).
    """
    
    response_json_str = call_deepseek_api(prompt_estratega)
    
    # Limpieza y Parsing del JSON
    query_x = query_usuario 
    query_y = query_usuario 
    
    try:
        if "```json" in response_json_str:
            response_json_str = response_json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in response_json_str:
            response_json_str = response_json_str.split("```")[1].split("```")[0].strip()
        
        queries_dict = json.loads(response_json_str)
        query_x = queries_dict.get("query_x", query_usuario)
        query_y = queries_dict.get("query_y", query_usuario)
        print(f"   🔹 Query X (Ley): {query_x}")
        print(f"   🔸 Query Y (Trámite): {query_y}")
    except:
        print("   ⚠️ Usando queries por defecto.")

    # =========================================================================
    # PASO iv y v: Ejecución de Búsquedas Refinadas
    # =========================================================================
    print("\n🚀 PASO 3: Ejecutando búsquedas especializadas...")
    
    # --- Ejecutar Query X (Normativa) ---
    chunks_legales_finales = []
    emb_x = embedding_function.embed_query(f"query: {query_x}")
    
    for col in colecciones_legales:
        try:
            res_x = col.query(query_embeddings=[emb_x], n_results=3)
            if res_x['documents']:
                for doc, meta in zip(res_x['documents'][0], res_x['metadatas'][0]):
                    # FORMATEO ESTRICTO PARA CITAS LEGALES
                    fuente_clean = meta.get('titulo_documento', 'Ley desconocida').replace('_', ' ').title()
                    articulo_clean = meta.get('Articulo', 'N/A')
                    # Preparamos el string para que el LLM lo pueda citar fácilmente
                    chunks_legales_finales.append(f"[[FUENTE: {fuente_clean}, ARTÍCULO: {articulo_clean}]]\nTEXTO: {doc}")
        except: pass
    
    # --- Ejecutar Query Y (Trámites) ---
    chunks_tramites_finales = []

    # 1. Crea una lista para guardar las homoclaves detectadas
    homoclaves_debug_list = []

    if coleccion_tramites:
        # 1. ¿Cuántos hay?
        conteo = coleccion_tramites.count()
        print(f"🔍 [DEBUG] Registros totales en la colección: {conteo}")
        
        if conteo == 0:
            print("❌ LA COLECCIÓN ESTÁ VACÍA. Revisa el nombre de la colección o el path.")
            return # O maneja el error
        
        emb_y = embedding_function.embed_query(f"query: {query_y}")
        try:
            res_y = coleccion_tramites.query(
                query_embeddings=[emb_y], 
                n_results=3
            )

            # # --- INICIO DEL BLOQUE DE DEBUG ---
            # print(f"\n--- DEBUG TRÁMITES ---")
            # print(f"🔍 Query Y utilizada: {query_y}")
            # print(f"📊 Cantidad de documentos devueltos: {len(res_y['documents'][0]) if res_y['documents'] else 0}")
            # if res_y['metadatas'] and res_y['metadatas'][0]:
            #     print(f"🏷️ Metadatos del primer resultado: {res_y['metadatas'][0][0]}")
            # else:
            #     print("⚠️ No se recuperaron metadatos. Posible error de filtro 'where' o BD vacía.")
            # print(f"----------------------\n")
            # # --- FIN DEL BLOQUE DE DEBUG ---

            if res_y['documents']:
                for doc, meta in zip(res_y['documents'][0], res_y['metadatas'][0]):
                    # FORMATEO ESTRICTO PARA CITAS DE TRÁMITES
                    nombre_tramite = meta.get('nombre', 'Trámite sin nombre').title()
                    homoclave = meta.get('homoclave', 'S/N') # En trámites usamos 'Articulo' para guardar la Homoclave/ID

                    # 2. AGREGA ESTA LÍNEA: Guardar homoclave para el test
                    homoclaves_debug_list.append(str(homoclave).strip())

                    chunks_tramites_finales.append(f"[[TRÁMITE: {nombre_tramite}, HOMOCLAVE: {homoclave}]]\nDETALLES OFICIALES: {doc}")
        except Exception as e:
            print(f"   ❌ Error trámites: {e}")
    
    # Unimos los contextos
    contexto_legal_str = "\n\n".join(chunks_legales_finales[:5])
    contexto_tramites_str = "\n\n".join(chunks_tramites_finales[:3]) if chunks_tramites_finales else "No se encontraron trámites registrados en la base de datos."

    # print("/////////////////////////")
    # print(contexto_legal_str)
    # print("/////////////////////////")
    # print(contexto_tramites_str)
    # print("/////////////////////////")
    # print(chunks_tramites_finales)
    # print("/////////////////////////")

    # =========================================================================
    # PASO vi: Segunda Llamada al LLM (Síntesis Final Estricta)
    # =========================================================================
    print("\n💬 PASO 4: Generando Respuesta Final (Modo Estricto)...")
    
    prompt_final = f"""
    Actúa como un "Analista de Cumplimiento Normativo y Procedimental".
    
    OBJETIVO:
    Responder a la pregunta del usuario basándote ÚNICA Y EXCLUSIVAMENTE en los fragmentos proporcionados abajo. 
    Tienes prohibido inventar requisitos, pasos o leyes que no aparezcan en el texto.

    --- INICIO DE LOS DATOS ---
    
    [SECCIÓN A: FUNDAMENTO LEGAL ENCONTRADO]
    {contexto_legal_str}
    
    [SECCIÓN B: TRÁMITES ADMINISTRATIVOS ENCONTRADOS]
    {contexto_tramites_str}
    
    --- FIN DE LOS DATOS ---

    PREGUNTA DEL USUARIO: "{query_usuario}"

    INSTRUCCIONES DE RESPUESTA:
    
    1. **Diagnóstico Legal (Contexto):**
       - Explica brevemente qué dice la normativa sobre el tema.
       - **REGLA DE CITA:** Cada afirmación debe terminar con su referencia exacta entre paréntesis. 
       - Ejemplo: "El uso del escudo requiere autorización (Ley sobre el Escudo..., Art. 6)."
    
    2. **Ruta de Acción (El Trámite):**
       - Describe el trámite encontrado en la [SECCIÓN B].
       - **REGLA DE FIDELIDAD:** Solo menciona requisitos, costos o pasos que estén explícitamente escritos en "DETALLES OFICIALES". Si el texto no menciona el costo, NO lo inventes.
       - Cita siempre la **Homoclave** del trámite.
       - Cita siempre el **nombre** del trámite.
       - Si en [SECCIÓN B] dice "No se encontraron trámites", indícalo claramente y sugiere acudir a la dependencia mencionada en la ley.

    3. **Conclusión:**
       - Un resumen de una línea sobre qué hacer.

    Genera la respuesta ahora:
    """
    
    # Usamos temperatura baja para evitar alucinaciones
    respuesta_final = call_deepseek_api(prompt_final)
    
    print("\n" + "="*30 + " RESPUESTA FINAL (STRICT MODE) " + "="*30)
    print(respuesta_final)
    print("="*85)
    
    return respuesta_final

    # DEBUG
    # return respuesta_final, homoclaves_debug_list

# --- 5. CARGA DE RECURSOS (MODIFICADA: Separación Estratégica) ---

def cargar_recursos(scope: str):
    """
    Carga recursos separando:
    1. Leyes Generales (Para Lógica A/B)
    2. Leyes SEGOB (Exclusiva Lógica C) -> procesado-mx/segob-mx
    3. Trámites (Exclusiva Lógica C) -> procesado-mx/tramites-mx/chroma_db_tramites_mx
    """
    print(f"🧠 Cargando modelo: '{EMBEDDING_MODEL_NAME}'...")
    try:
        embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME, model_kwargs={'device': 'cpu'})
    except Exception as e:
        print(f"  ❌ Error carga modelo: {e}")
        return None, [], [], None 

    # Listas separadas
    cols_generales = []
    cols_segob = []
    col_tramites = None
    
    paths_generales = []
    path_segob = None
    path_tramites = None

    if scope == 'mx':
        # 1. Rutas Generales
        paths_generales.append(BASE_DIR / "procesado-mx" / "principal-mx" / "chroma_db_mx")
        paths_generales.append(BASE_DIR / "procesado-mx" / "excep-mx" / "chroma_db_excep_mx")
        
        # 2. Ruta SEGOB (Lógica C)
        path_segob = BASE_DIR / "procesado-mx" / "segob-mx"
        
        # 3. Ruta Trámites (Lógica C) - CORREGIDA AQUI
        # Debe apuntar a la subcarpeta que contiene los archivos .sqlite3 y .bin
        path_tramites = BASE_DIR / "procesado-mx" / "tramites-mx" / "chroma_db_tramites_mx"

    # --- CARGA 1: Leyes Generales ---
    for p in paths_generales:
        if os.path.exists(p):
            try:
                client = chromadb.PersistentClient(path=str(p))
                col = client.get_or_create_collection(name=COLLECTION_NAME)
                cols_generales.append(col)
                print(f"  ✅ [General] Cargada: {p.name}")
            except Exception as e: print(f"  ❌ Error General ({p.name}): {e}")

    # --- CARGA 2: Leyes SEGOB ---
    if path_segob and os.path.exists(path_segob):
        try:
            client_s = chromadb.PersistentClient(path=str(path_segob))
            col_s = client_s.get_or_create_collection(name=COLLECTION_NAME)
            cols_segob.append(col_s)
            print(f"  ✅ [SEGOB] Cargada biblioteca especializada: {path_segob.name}")
        except Exception as e: print(f"  ❌ Error SEGOB ({path_segob.name}): {e}")

    # --- CARGA 3: Trámites ---
    if path_tramites and os.path.exists(path_tramites):
        try:
            client_t = chromadb.PersistentClient(path=str(path_tramites))
            # Aquí usamos el nombre específico que me mostraste en tu script
            col_tramites = client_t.get_collection(name="tramites_gob_mx")
            print(f"  ✅ [Trámites] Cargada: {path_tramites.name}")
        except Exception as e: 
            print(f"  ❌ Error Trámites ({path_tramites.name}): {e}")
    else:
         print(f"  ⚠️ No se encontró la ruta Trámites: {path_tramites}")

    return embedding_function, cols_generales, cols_segob, col_tramites

# --- 6. MAIN ---
if __name__ == "__main__":
    # 1. Configuración de Argumentos
    parser = argparse.ArgumentParser(description="Aura: Asistente Legal y de Trámites")
    parser.add_argument("query", type=str, help="La consulta del usuario.")
    parser.add_argument("--modo", type=str, choices=['A', 'B', 'C'], default='C')
    parser.add_argument("--scope", type=str, choices=['unam', 'mx'], default='mx')

    args = parser.parse_args()

    print(f"\n🔵 Iniciando Aura en MODO={args.modo} | SCOPE={args.scope}")
    print(f"📝 Query recibida: '{args.query}'")

    # 2. Carga de Recursos
    emb_fn, cols_gen, cols_seg, col_tram = cargar_recursos(args.scope)

    # Validación de Seguridad
    if not emb_fn:
        print("\n❌ ERROR CRÍTICO: No se pudo cargar el modelo de Embeddings.")
        exit(1)
    
    # 3. Enrutador de Lógica
    try:
        if args.modo == 'C':
            # Verificación específica para Modo C
            if cols_seg and col_tram:
                logica_c_avanzada(cols_seg, col_tram, emb_fn, args.query)
            else:
                print("\n⚠️ ERROR MODO C: Faltan recursos.")
                print(f"   - Colección SEGOB cargada: {'✅' if cols_seg else '❌'}")
                print(f"   - Colección TRÁMITES cargada: {'✅' if col_tram else '❌'}")
                print("   Revisa las rutas en 'cargar_recursos'.")

        elif args.modo == 'B':
            if cols_gen:
                logica_b_explicacion_juridica(cols_gen, emb_fn, args.query)
            else:
                print("❌ No hay leyes generales cargadas para el Modo B.")

        elif args.modo == 'A':
            if cols_gen:
                logica_a_cita_por_metadatos(cols_gen, emb_fn, args.query)
            else:
                print("❌ No hay leyes generales cargadas para el Modo A.")

    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado durante la ejecución: {e}")