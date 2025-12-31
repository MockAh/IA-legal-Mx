from utils_rag import call_deepseek_api, extraer_entidades_con_llm

def logica_a_cita_precisa(colecciones_legales, embedding_function, query):
    """Busca un documento y artículo exacto en las bases de datos."""
    print("--- Ejecutando Lógica A (Precisa) ---")
    entidades = extraer_entidades_con_llm(query)
    titulo_buscado = entidades.get("titulo_documento")
    articulo_num = entidades.get("Articulo")

    if not titulo_buscado:
        return "No pude identificar qué ley estás buscando. Intenta mencionar el nombre del documento."

    for collection in colecciones_legales:
        # Paso 1: Buscar el documento
        search_results = collection.query(
            query_embeddings=[embedding_function.embed_query(query)],
            n_results=1,
            where={"titulo_documento": {"$eq": titulo_buscado}}
        )
        
        if not search_results['metadatas'] or not search_results['metadatas'][0]:
            continue # No está en esta colección, siguiente.

        # Paso 2: Filtrar por artículo
        metadata_encontrado = search_results['metadatas'][0][0]
        fuente_correcta = metadata_encontrado.get("source")
        
        condiciones = [{"source": {"$eq": fuente_correcta}}, {"Articulo": {"$eq": articulo_num}}]
        # Ajuste para transitorios si la query lo menciona
        tipo_transitorio = "Principal" if "transitorio" not in query.lower() else {"$ne": "Principal"}
        if tipo_transitorio != "Principal": condiciones.append({"Transitorio": tipo_transitorio})
        else: condiciones.append({"Transitorio": {"$eq": "Principal"}})

        results = collection.query(
            query_embeddings=[embedding_function.embed_query(query)],
            where={"$and": condiciones},
            n_results=1
        )

        if results['documents'] and results['documents'][0]:
            doc = results['documents'][0][0]
            meta = results['metadatas'][0][0]
            return f"🏛️ **Cita Encontrada**:\n\n> {doc}\n\n_Fuente: {meta.get('titulo_documento').title()}, Artículo {meta.get('Articulo')}_"

    return f"Encontré la ley '{titulo_buscado}', pero no el artículo '{articulo_num}' específico en las bases de datos."