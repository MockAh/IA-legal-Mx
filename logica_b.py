from utils_rag import call_deepseek_api_stream, extraer_entidades_con_llm, buscar_titulo_en_faiss, normalizar_titulo

def logica_b_streaming(colecciones_legales, embedding_function, query):
    """Versión streaming con Búsqueda Híbrida (Exacta + Semántica)."""
    
    try:
        yield "🔍 **Analizando tu consulta y buscando en la normativa mexicana...**"
        
        # --- PASO 1 y 2: Extracción de Entidades ---
        entidades = extraer_entidades_con_llm(query)
        articulo_buscado = entidades.get("Articulo")
        titulo_raw = entidades.get("titulo_documento")
        
        print(f"📋 [logica_b] Entidades extraídas: {entidades}")
        print(f"   → Título detectado: {titulo_raw or '(ninguno)'}")
        print(f"   → Artículo detectado: {articulo_buscado or '(ninguno)'}")
        
        # (Opcional) Normalizar el título con FAISS si el usuario lo proporcionó
        titulo_exacto = None
        if titulo_raw:
            check_titulo = normalizar_titulo(titulo_raw)
            if "constitucion" == check_titulo:
                titulo_exacto = 'constitucion politica de los estados unidos mexicanos'
                print(f"🎯 Hardcode aplicado: '{titulo_raw}' -> '{titulo_exacto}'")
            else:
                titulo_faiss = buscar_titulo_en_faiss(titulo_raw, embedding_function, k=1)
                titulo_exacto = normalizar_titulo(titulo_faiss) if titulo_faiss else None
                print(f"   → Título FAISS: {titulo_faiss or '(sin coincidencia)'}")
                print(f"   → Título normalizado para ChromaDB: {titulo_exacto or '(sin coincidencia)'}")

            
        # Construir el diccionario de filtros para ChromaDB
        filtro_exacto = {}
        if articulo_buscado:
            filtro_exacto["Articulo"] = str(articulo_buscado)
        if titulo_exacto:
            filtro_exacto["titulo_documento"] = titulo_exacto

        contexto_compilado = []
        textos_unicos = set()

        print(f"\n{'='*60}")
        print(f"📂 [logica_b] INICIO DE BÚSQUEDA")
        print(f"   Filtro exacto: {filtro_exacto or '(ninguno)'}")
        print(f"   Colecciones a recorrer: {len(colecciones_legales)}")
        print(f"{'='*60}")

        # Iterar sobre las bases de datos disponibles
        for idx_col, collection in enumerate(colecciones_legales):
            col_name = getattr(collection, 'name', f'colección-{idx_col}')
            print(f"\n🗄️  [logica_b] Consultando: {col_name}")
            
            # --- PASO 3.a: BÚSQUEDA EXACTA (Solo si hay entidades detectadas) ---
            if filtro_exacto:
                try:
                    # ChromaDB requiere un formato específico si hay múltiples filtros
                    where_clause = None
                    if len(filtro_exacto) == 1:
                        where_clause = filtro_exacto
                    elif len(filtro_exacto) > 1:
                        where_clause = {"$and": [{k: {"$eq": v}} for k, v in filtro_exacto.items()]}
                        
                    results_exact = collection.query(
                        query_embeddings=[embedding_function.embed_query(query)], 
                        n_results=8, # Traemos los mejores fragmentos de este artículo exacto
                        where=where_clause 
                    )
                    
                    n_exact = len(results_exact['documents'][0]) if results_exact['documents'] else 0
                    print(f"   🎯 Búsqueda EXACTA → {n_exact} chunk(s) recuperados")
                    if results_exact['documents']:
                        for i, (doc, meta) in enumerate(zip(results_exact['documents'][0], results_exact['metadatas'][0])):
                            a = meta.get('Articulo', '')
                            t = meta.get('titulo_documento', 'Doc')
                            preview = doc[:120].replace('\n', ' ')
                            es_art_buscado = articulo_buscado and str(a) == str(articulo_buscado)
                            tag = "✅ MATCH Art." if es_art_buscado else "  "
                            print(f"      [{i+1}] {tag} Art={a} | Doc={t}")
                            print(f"          Texto: \"{preview}...\"")
                            if doc not in textos_unicos:
                                t_title = t.title()
                                fuente = f"{t_title}, Art. {a}" if a and a != '<No aplica>' else t_title
                                # Etiquetamos para que el LLM sepa que esto es literal
                                contexto_compilado.append(f"---\n[🎯 EXTRACCIÓN DIRECTA]\nFuente: [{fuente}]\nTexto: {doc}\n---")
                                textos_unicos.add(doc)
                except Exception as e:
                    print(f"⚠️ Error menor en búsqueda exacta (omitido): {e}")

            # --- PASO 3.b: BÚSQUEDA SEMÁNTICA CLÁSICA ---
            try:
                results_sem = collection.query(
                    query_embeddings=[embedding_function.embed_query(query)], 
                    n_results=10 # Traemos el contexto general
                )
                n_sem = len(results_sem['documents'][0]) if results_sem['documents'] else 0
                print(f"   🧠 Búsqueda SEMÁNTICA → {n_sem} chunk(s) recuperados")
                if results_sem['documents']:
                    for i, (doc, meta) in enumerate(zip(results_sem['documents'][0], results_sem['metadatas'][0])):
                        a = meta.get('Articulo', '')
                        t = meta.get('titulo_documento', 'Doc')
                        preview = doc[:120].replace('\n', ' ')
                        es_art_buscado = articulo_buscado and str(a) == str(articulo_buscado)
                        tag = "✅ MATCH Art." if es_art_buscado else "  "
                        duplicado = "(DUP, omitido)" if doc in textos_unicos else ""
                        print(f"      [{i+1}] {tag} Art={a} | Doc={t} {duplicado}")
                        print(f"          Texto: \"{preview}...\"")
                        if doc not in textos_unicos:
                            t_title = t.title()
                            fuente = f"{t_title}, Art. {a}" if a and a != '<No aplica>' else t_title
                            contexto_compilado.append(f"---\n[🧠 CONTEXTO SEMÁNTICO]\nFuente: [{fuente}]\nTexto: {doc}\n---")
                            textos_unicos.add(doc)
            except Exception as e:
                print(f"⚠️ Error menor en búsqueda semántica (omitido): {e}")

        # --- RESUMEN DE CHUNKS ---
        print(f"\n{'='*60}")
        print(f"📊 [logica_b] RESUMEN: {len(contexto_compilado)} chunk(s) únicos enviados al LLM")
        if articulo_buscado:
            arts_encontrados = [c for c in contexto_compilado if f"Art. {articulo_buscado}" in c]
            print(f"   🔎 Chunks que contienen Art. {articulo_buscado}: {len(arts_encontrados)}")
        print(f"{'='*60}\n")

        if not contexto_compilado:
            yield "❌ No encontré información suficiente en las leyes cargadas para explicar esto."
            return

        contexto_str = "\n".join(contexto_compilado)

        # --- Recopilar fuentes únicas por tipo para la sección de referencias ---
        fuentes_directas = []
        fuentes_semanticas = []
        for chunk_text in contexto_compilado:
            # Extraer la línea "Fuente: [...]" de cada chunk
            for linea in chunk_text.split("\n"):
                if linea.startswith("Fuente: ["):
                    nombre_fuente = linea.replace("Fuente: [", "").rstrip("]")
                    if "EXTRACCIÓN DIRECTA" in chunk_text and nombre_fuente not in fuentes_directas:
                        fuentes_directas.append(nombre_fuente)
                    elif "CONTEXTO SEMÁNTICO" in chunk_text and nombre_fuente not in fuentes_semanticas:
                        fuentes_semanticas.append(nombre_fuente)

        catalogo_fuentes = ""
        if fuentes_directas:
            catalogo_fuentes += "FUENTES PRIMARIAS (Búsqueda Exacta):\n"
            for f in fuentes_directas:
                catalogo_fuentes += f"  - {f}\n"
        if fuentes_semanticas:
            catalogo_fuentes += "FUENTES COMPLEMENTARIAS (Búsqueda Semántica):\n"
            for f in fuentes_semanticas:
                catalogo_fuentes += f"  - {f}\n"

        yield "⚖️ **Analizando y redactando respuesta...**"

        # --- PASO 4: PROMPT REFORZADO ---
        prompt = f"""
        Eres "Aura Legal", experta en derecho mexicano. Tu objetivo: traducir leyes en acciones claras.
        
        CONTEXTO (Verdad Absoluta):
        {contexto_str}

        CATÁLOGO DE FUENTES CONSULTADAS:
        {catalogo_fuentes}

        TAREA:
        Responde a: "{query}" siguiendo estrictamente estas reglas:
        1. **FUERZA DE CONTEXTO:** Usa ÚNICAMENTE la información del CONTEXTO proporcionado. Si el usuario pregunta por un artículo y ves fragmentos con la etiqueta [🎯 EXTRACCIÓN DIRECTA], dales prioridad absoluta. Si la respuesta no está ahí, di: "Lo siento, la normativa cargada no contiene información específica para responder a eso."
        2. **La Lógica en Sencillo:** Explica el porqué de la ley o el artículo. Si los fragmentos son partes de un mismo artículo, únelos lógicamente en tu explicación.
        3. **Pasos a Seguir:** 2-3 estrategias claras basadas en el texto.
        4. **REFERENCIAS (OBLIGATORIO):** Al final de tu respuesta, agrega una sección "📚 **Fuentes consultadas**" con la lista de documentos que usaste, usando el CATÁLOGO DE FUENTES CONSULTADAS de arriba. Reglas:
           a. Prioriza las FUENTES PRIMARIAS (Búsqueda Exacta). Cítalas primero.
           b. Solo incluye FUENTES COMPLEMENTARIAS si realmente las usaste en tu explicación.
           c. Para cada fuente, usa el formato: **Nombre del documento**, Art. N (si aplica).
           d. Dentro del cuerpo de tu respuesta, cuando menciones un dato legal, cítalo inline entre paréntesis: (Nombre del documento, Art. N).

        PROHIBICIÓN: No uses conocimientos externos que no estén en el contexto.

        Genera la respuesta con formato Markdown claro.
        """

        # Temperatura en 0.0 para máximo determinismo
        respuesta_acumulada = ""
        for chunk in call_deepseek_api_stream(prompt, temperature=0.2):
            respuesta_acumulada += chunk
            yield respuesta_acumulada

    except Exception as e:
        mensaje_error = f"❌ **Ocurrió un error inesperado:**\n\n`{str(e)}`\n\nIntenta reformular tu pregunta."
        yield mensaje_error