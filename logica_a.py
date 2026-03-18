from utils_rag import call_deepseek_api, extraer_entidades_con_llm, buscar_titulo_en_faiss, normalizar_titulo

def logica_a_cita_precisa(colecciones_legales, embedding_function, query):
    """
    Lógica A: Búsqueda de Cita Precisa con Validación Semántica de Títulos.
    
    Flujo:
    1. Extrae titulo_documento y num_articulo del query con LLM
    2. Busca semánticamente el titulo_documento en índice FAISS para obtener el título exacto
    3. Busca el num_articulo en ChromaDB filtrando por ley exacta
    4. Retorna cita completa y formateada
    """
    print("--- Ejecutando Lógica A (Cita Precisa con FAISS) ---")
    
    # PASO 1: Extraer entidades de la consulta
    entidades = extraer_entidades_con_llm(query)
    titulo_usuario = entidades.get("titulo_documento")
    articulo_num = str(entidades.get("Articulo")).strip() if entidades.get("Articulo") else None

    if not titulo_usuario:
        return "❌ No pude identificar qué ley estás buscando. Intenta mencionar el nombre del documento."
    
    if not articulo_num:
        return "❌ No pude identificar el artículo solicitado. Intenta mencionar el número del artículo."

    print(f"📝 Consulta procesada: Ley='{titulo_usuario}', Artículo={articulo_num}")

    # PASO 2: Determinación del Título Exacto
    check_titulo = normalizar_titulo(titulo_usuario) if titulo_usuario else ""

    if "constitucion" in check_titulo:
        # Si detectamos la palabra clave, forzamos el nombre del archivo
        titulo_exacto = 'Constitucion-Politica-de-los-Estados-Unidos-Mexicanos'
        print(f"🎯 Hardcode aplicado: '{titulo_usuario}' -> '{titulo_exacto}'")
    else:
        # Si no, usamos la búsqueda semántica de FAISS
        titulo_exacto = buscar_titulo_en_faiss(titulo_usuario, embedding_function, k=1)

    if not titulo_exacto:
        return f"⚠️ No encontré la ley '{titulo_usuario}' en el índice. Verifica el nombre."

    # --- AQUÍ ESTÁ LA CLAVE: Definir la variable para ChromaDB ---
    titulo_normalizado = normalizar_titulo(titulo_exacto)
    print(f"📝 Título normalizado para búsqueda: '{titulo_normalizado}'")

    # PASO 3: Buscar el artículo en ChromaDB usando el título normalizado
    for i, collection in enumerate(colecciones_legales):
        # 🔍 DEBUG 1: Saber qué colección estamos revisando
        print(f"\n--- Revisando Colección {i}: {collection.name} ---")
        
        condiciones = [
            {"titulo_documento": {"$eq": titulo_normalizado}},
            {"Articulo": {"$eq": articulo_num}}
        ]

        # Ajuste para transitorios
        es_transitorio = "transitorio" in query.lower()
        if es_transitorio:
            condiciones.append({"Transitorio": {"$ne": "Principal"}})
        else:
            condiciones.append({"Transitorio": {"$eq": "Principal"}})

        # 🔍 DEBUG 2: Ver el diccionario exacto que se envía a Chroma
        print(f"🔎 Filtros aplicados: {condiciones}")

        try:
            results = collection.query(
                query_embeddings=[embedding_function.embed_query(query)],
                where={"$and": condiciones},
                n_results=1
            )

            if results['documents'] and results['documents'][0]:
                # En logica_a.py, dentro del bloque: if results['documents'] and results['documents'][0]:
                doc = results['documents'][0][0]
                meta = results['metadatas'][0][0] 
                parrafos = [p.strip() for p in doc.split('\n') if p.strip()]

                # Construimos el contenedor HTML para el texto legal
                # Usamos una clase específica 'contenedor-legal' para centrarlo y 'parrafo-legal' para el estilo
                texto_html = '<div class="contenedor-legal">'
                for p in parrafos:
                    texto_html += f'<p class="parrafo-legal">{p}</p>'
                texto_html += '</div>'

                # Tu respuesta final ahora incluirá este bloque HTML
                respuesta = f"""
                ### ⚖️ **EXTRACTO NORMATIVO FORMAL**
                ---
                🏛️ **LEY:** {meta.get('titulo_documento', titulo_exacto).upper()}
                📍 **ARTÍCULO:** {meta.get('Articulo', articulo_num)}

                {texto_html}

                ---
                🔗 **FUENTE:** `{meta.get('source', 'N/A')}`
                """

                return respuesta
        
            else:
                # 🔍 DEBUG 3: Si no hay resultados, investigamos por qué.
                # Hacemos una búsqueda SOLO por título para ver CÓMO están escritos los artículos.
                print(f"❓ No se halló el Art. {articulo_num}. Inspeccionando metadatos de la ley...")
                
                muestreo = collection.get(
                    where={"titulo_documento": titulo_normalizado},
                    limit=3,
                    include=["metadatas"]
                )
                
                if muestreo['metadatas']:
                    ejemplo = muestreo['metadatas'][0]
                    print(f"💡 Ejemplo de metadato en esta ley: Articulo='{ejemplo.get('Articulo')}', Transitorio='{ejemplo.get('Transitorio')}'")
                else:
                    print(f"❌ Ni siquiera encontré la ley con el título: '{titulo_normalizado}'")

        except Exception as e:
            print(f"⚠️  Error consultando colección: {e}")
            continue

    # Si llegamos aquí, no encontramos el artículo en ninguna colección
    return f"⚠️  Encontré la ley '{titulo_exacto}', pero el artículo {articulo_num} no está en las bases de datos textuales."