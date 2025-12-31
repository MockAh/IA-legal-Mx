from utils_rag import call_deepseek_api

def logica_b_explicacion_juridica(colecciones_legales, embedding_function, query):
    """Genera una explicación didáctica basada en contexto legal."""
    contexto_compilado = []
    textos_unicos = set()

    # 1. Recopilar Contexto
    for collection in colecciones_legales:
        results = collection.query(query_embeddings=[embedding_function.embed_query(query)], n_results=5)
        if results['documents']:
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                if doc not in textos_unicos:
                    titulo = meta.get('titulo_documento', 'Doc').title()
                    art = meta.get('Articulo', '')
                    fuente = f"{titulo}, Art. {art}" if art and art != '<No aplica>' else titulo
                    
                    contexto_compilado.append(f"---\nFuente: [{fuente}]\nTexto: {doc}\n---")
                    textos_unicos.add(doc)

    if not contexto_compilado:
        return "No encontré información suficiente en las leyes cargadas para explicar esto."

    contexto_str = "\n".join(contexto_compilado)
    
    # 2. Prompt Aura Legal
    prompt = f"""
    Eres "Aura Legal", experta en derecho mexicano. Tu objetivo: traducir leyes en acciones claras.
    
    CONTEXTO (Verdad Absoluta):
    {contexto_str}

    TAREA:
    Responde a: "{query}" siguiendo estos 3 pasos:
    1. **La Lógica en Sencillo:** Usa una metáfora para explicar el porqué de la ley.
    2. **Pasos a Seguir:** 2-3 estrategias claras.
    3. **Referencias:** Cita las fuentes provistas entre paréntesis (Ej: Ley X, Art 5).

    Genera la respuesta con formato Markdown claro.
    """
    return call_deepseek_api(prompt, temperature=0.5)