# -*- coding: utf-8 -*-
"""
rag_app_deepseek.py (Versión 6.0 - Citas Precisas en Modo B; Implementación de "legal" y "semantic")

Esta versión mejora la "Lógica B" para que el contexto enviado al LLM incluya
los metadatos de cada chunk. Esto permite al LLM generar citas mucho más
precisas, incluyendo el título del documento fuente.
"""
import os
import argparse
import chromadb
import json
import requests
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings

# --- 1. CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent
COLLECTION_NAME = "langchain"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large-instruct"


# --- 2. MÓDULO REUTILIZABLE PARA LA API ---

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

# --- 3. LÓGICAS DE RAG (MODIFICADAS PARA CITAS PRECISAS) ---

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

def logica_a_cita_por_metadatos(collections: list[chromadb.Collection], embedding_function, query: str):
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

    for i, collection in enumerate(collections):
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

def logica_b_explicacion_juridica(collections: list[chromadb.Collection], embedding_function, query: str):
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

    for i, collection in enumerate(collections):
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
    
    explicacion = call_deepseek_api(prompt_explicacion, temperature=0.5)
    
    print("\n" + "="*23 + " EXPLICACIÓN JURÍDICA GENERADA " + "="*23)
    print(explicacion)
    print("="*78)


# --- 4. CARGA DE RECURSOS Y PUNTO DE ENTRADA ---
def cargar_recursos(scope: str):
    """Carga el modelo de embeddings y conecta a la(s) base(s) de datos correcta(s)."""
    
    print(f"🧠 Cargando modelo de embeddings: '{EMBEDDING_MODEL_NAME}'...")
    try:
        embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME, model_kwargs={'device': 'cpu'})
        print("  ✅ Modelo cargado exitosamente.")
    except Exception as e:
        print(f"  ❌ ERROR FATAL al cargar el modelo de embeddings: {e}")
        return None, None

    db_paths = []
    if scope == 'unam':
        db_paths.append(str(BASE_DIR / "procesado-unam" / "chroma_db_unam"))
    elif scope == 'mx':
        db_paths.append(str(BASE_DIR / "procesado-mx" / "principal-mx" / "chroma_db_mx"))
        db_paths.append(str(BASE_DIR / "procesado-mx" / "excep-mx" / "chroma_db_excep_mx"))
    else:
        print(f"  ❌ ERROR: El scope '{scope}' no es válido.")
        return None, None

    collections = []
    for path in db_paths:
        print(f"🔌 Intentando conectar a la base de datos en: '{path}'")
        try:
            client = chromadb.PersistentClient(path=path)
            collection = client.get_or_create_collection(name=COLLECTION_NAME)
            print(f"  ✅ Conexión exitosa. Colección '{collection.name}' cargada con {collection.count()} documentos.")
            collections.append(collection)
        except Exception as e:
            print(f"  ❌ ERROR al conectar con ChromaDB en '{path}': {e}")
            continue
    
    if not collections:
        print("  ❌ ERROR FATAL: No se pudo cargar ninguna base de datos.")
        return None, None

    return embedding_function, collections

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IA Legal (v5.0 - Citas Precisas) - Interfaz de Consulta por Terminal.")
    parser.add_argument("query", type=str, help="La pregunta a consultar.")
    parser.add_argument("--modo", type=str, choices=['A', 'B'], default='B', help="A=Cita Precisa, B=Explicación Semántica")
    parser.add_argument("--scope", type=str, choices=['unam', 'mx'], default='mx', help="Elige la base de datos a consultar: 'unam' o 'mx' (federal).")
    
    args = parser.parse_args()

    embedding_function, collections = cargar_recursos(scope=args.scope)
    
    if collections and embedding_function:
        if args.modo == 'A':
            logica_a_cita_por_metadatos(collections, embedding_function, args.query)
        else:
            logica_b_explicacion_juridica(collections, embedding_function, args.query)
