import json
from utils_rag import call_deepseek_api

def logica_c_avanzada(coleccion_segob, coleccion_tramites, embedding_function, query_usuario):
    """
    Lógica C (Secretario Segob - Avanzada):
    Exploración -> Estrategia (Query X/Y) -> Búsqueda Especializada -> Síntesis Estricta.
    """
    if not coleccion_segob or not coleccion_tramites:
        return "⚠️ Error: Las bases de datos especializadas (SEGOB/Trámites) no están listas."

    print(f"--- 🛡️ Ejecutando Secretario SEGOB (Advanced Mode) para: {query_usuario} ---")

    # =========================================================================
    # PASO 1: Exploración Inicial (Ver qué hay en SEGOB)
    # =========================================================================
    query_raw_embeddings = embedding_function.embed_query(f"query: {query_usuario}")
    contexto_exploracion = []

    try:
        results = coleccion_segob.query(query_embeddings=[query_raw_embeddings], n_results=3)
        if results['documents']:
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                ref = f"Doc: {meta.get('titulo_documento')} (Art. {meta.get('Articulo', 'N/A')})"
                contexto_exploracion.append(f"- [{ref}]: {doc}")
    except Exception as e:
        print(f"Error exploración: {e}")

    texto_contexto_raw = "\n".join(contexto_exploracion)

    # =========================================================================
    # PASO 2: El Estratega (DeepSeek define qué buscar)
    # =========================================================================
    prompt_estratega = f"""
    Eres el estratega de investigación del Secretario de Gobernación.
    Duda del Ciudadano: "{query_usuario}"
    Vistazo preliminar a la ley:
    {texto_contexto_raw}
    
    INSTRUCCIONES:
    Genera un JSON con dos claves para profundizar la investigación:
    - "query_x": Búsqueda técnica para la NORMATIVA INTERNA (usa términos jurídicos de SEGOB).
    - "query_y": Búsqueda operativa para el TRÁMITE (términos como requisitos, formato, homoclave).
    """
    
    response_json = call_deepseek_api(prompt_estratega)
    
    # Parsing robusto del JSON
    query_x, query_y = query_usuario, query_usuario
    try:
        clean_json = response_json.replace("```json", "").replace("```", "").strip()
        queries_dict = json.loads(clean_json)
        query_x = queries_dict.get("query_x", query_usuario)
        query_y = queries_dict.get("query_y", query_usuario)
    except:
        pass # Si falla, usamos la query original

    # =========================================================================
    # PASO 3: Ejecución de Búsquedas Especializadas (X e Y)
    # =========================================================================
    chunks_legales = []
    chunks_tramites = []

    # --- Búsqueda Legal (Query X) en SEGOB ---
    emb_x = embedding_function.embed_query(f"query: {query_x}")
    try:
        res_x = coleccion_segob.query(query_embeddings=[emb_x], n_results=4)
        if res_x['documents']:
            for doc, meta in zip(res_x['documents'][0], res_x['metadatas'][0]):
                fuente = meta.get('titulo_documento', 'Normativa Segob').title()
                chunks_legales.append(f"[[NORMA: {fuente}, ART: {meta.get('Articulo')}]]\n{doc}")
    except: pass

    # --- Búsqueda Trámites (Query Y) ---
    emb_y = embedding_function.embed_query(f"query: {query_y}")
    try:
        res_y = coleccion_tramites.query(query_embeddings=[emb_y], n_results=3)
        if res_y['documents']:
            for doc, meta in zip(res_y['documents'][0], res_y['metadatas'][0]):
                chunks_tramites.append(f"[[TRÁMITE: {meta.get('nombre')}, HOMOCLAVE: {meta.get('homoclave')}]]\n{doc}")
    except: pass

    # =========================================================================
    # PASO 4: Síntesis Final (Secretario de Gobernación)
    # =========================================================================
    contexto_legal_str = "\n".join(chunks_legales) if chunks_legales else "No se encontró normativa específica."
    contexto_tramites_str = "\n".join(chunks_tramites) if chunks_tramites else "No se encontraron trámites relacionados."

    prompt_final = f"""
    Actúa como el **Secretario de Gobernación-IA**. Tu autoridad es técnica y ejecutiva.
    
    OBJETIVO:
    Responder al ciudadano basándote ÚNICAMENTE en la evidencia oficial recuperada.
    
    [EVIDENCIA NORMATIVA (SEGOB)]
    {contexto_legal_str}
    
    [EVIDENCIA ADMINISTRATIVA (TRÁMITES)]
    {contexto_tramites_str}
    
    PREGUNTA: "{query_usuario}"
    
    INSTRUCCIONES:
    1. **Fundamento**: Cita la normativa de gobernación que da sustento al tema (Nombre y Artículo).
    2. **Acción**: Explica el trámite paso a paso según la "Evidencia Administrativa". Menciona costos y requisitos si aparecen.
    3. **Identificación**: Cita obligatoriamente la HOMOCLAVE del trámite y su **NOMBRE**.
    
    Si la información no está en los textos, indícalo con transparencia institucional.
    """
    
    return call_deepseek_api(prompt_final, temperature=0.1)