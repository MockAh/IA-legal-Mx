# script_legal.py
# === LÓGICA LEGAL (ESTANDARIZADA) ===
import re

def algoritmo_eva_mx(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """
    Algoritmo Jerárquico - Módulo Legal.
    Genera metadatos compatibles con el esquema universal.
    """
    
    # 1. ESTADO INICIAL (ESQUEMA UNIVERSAL)
    # Definimos TODAS las claves aquí para garantizar consistencia con el semántico
    estado_actual = {
        # --- Jerarquía Legal ---
        "Decreto": "<No aplica>",
        "Libro": "<No aplica>", 
        "Titulo": "<No aplica>", 
        "Capitulo": "<No aplica>", 
        "Seccion": "<No aplica>", 
        "Articulo": "<No aplica>", 
        "Transitorio": "Principal", # Valor por defecto correcto para legal
        
        # --- Campos Semánticos (Valores por defecto para Legal) ---
        "tipo_contenido": "legal",      # Valor fijo para todo lo que salga de este script
        "subtipo": "normativo",         # Valor genérico para leyes
        "fechas_referencia": ""         # Vacío por defecto
    }

    parrafos_etiquetados = []
    
    print(f"     ⚖️  [Legal] Escaneando jerarquía en {len(lista_de_parrafos)} párrafos...")

    for i, p in enumerate(lista_de_parrafos):
        p_clean = p.strip().lstrip('\ufeff') 
        
        # B. Detección Jerárquica (Resetea niveles inferiores)
        if m := re.match(r'DECRETO\s*(.*)', p_clean, re.IGNORECASE):
            texto_decreto = m.group(1).strip() or "Decreto"
            estado_actual.update({
                "Decreto": texto_decreto, 
                "Libro": "<No aplica>", "Titulo": "<No aplica>", 
                "Capitulo": "<No aplica>", "Seccion": "<No aplica>", 
                "Articulo": "<No aplica>"
            })

        elif m := re.match(r'LIBRO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Libro": m.group(1).strip(), "Titulo": "<No aplica>", "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'T[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Titulo": m.group(1).strip(), "Capitulo": "<No aplica>", "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'CAP[ÍI]TULO\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Capitulo": m.group(1).strip(), "Seccion": "<No aplica>", "Articulo": "<No aplica>"})
            
        elif m := re.match(r'SECCI[ÓO]N\s+(.*)', p_clean, re.IGNORECASE):
            estado_actual.update({"Seccion": m.group(1).strip(), "Articulo": "<No aplica>"})
        
        # C. Detección de Artículos
        elif match := re.match(r'(?:ART[ÍI]?CULO|ART\.?)\s+([\w°º.-]+)', p_clean, re.IGNORECASE):
            id_articulo_raw = match.group(1).strip()
            LIMPIEZA_SIMBOLOS_FIN = r'[º.:;\s"\'\’-]+$'
            id_limpio = re.sub(LIMPIEZA_SIMBOLOS_FIN, '', id_articulo_raw).strip() 

            if id_limpio and id_limpio[0].isdigit():
                match_num = re.match(r'^(\d+)', id_limpio)
                id_articulo_final = match_num.group(1) if match_num else id_limpio
            else:
                id_articulo_final = id_limpio
            
            estado_actual["Articulo"] = id_articulo_final
            
            # Gestión de Transitorios dentro de artículos
            if estado_actual["Transitorio"] == "Transitorio_Encabezado":
                estado_actual["Transitorio"] = "Transitorio_Detectado"
        
        elif re.match(r'(?:ART[ÍI]CULOS\s+)?TRANSITORIOS\b', p_clean, re.IGNORECASE):
            estado_actual.update({
                "Libro": "<No aplica>", "Titulo": "Artículos Transitorios", 
                "Capitulo": "<No aplica>", "Articulo": "<No aplica>", 
                "Transitorio": "Transitorio_Encabezado"
            })

        # D. Asignación (Usamos copy para evitar referencia circular)
        parrafos_etiquetados.append({
            "texto": p, 
            "etiquetas": estado_actual.copy()
        })

    # --- FASE 2: FUSIÓN (CHUNKING) ---
    chunks_fusionados = []
    if not parrafos_etiquetados: return []

    buffer_actual = parrafos_etiquetados[0]
    
    for item in parrafos_etiquetados[1:]:
        # IMPORTANTE: Comparamos etiquetas completas (incluyendo tipo_contenido)
        if item["etiquetas"] == buffer_actual["etiquetas"]:
            buffer_actual["texto"] += "\n" + item["texto"]
        else:
            chunks_fusionados.append(buffer_actual)
            buffer_actual = item
    
    chunks_fusionados.append(buffer_actual)

    # --- FASE 3: FORMATO FINAL ---
    resultado_final = []
    for i, chunk in enumerate(chunks_fusionados):
        # Fusión segura de diccionarios
        meta_final = {**metadatos_base, **chunk["etiquetas"]}
        
        # Corrección de seguridad final
        if not meta_final.get("Articulo"): 
            meta_final["Articulo"] = "<No aplica>"

        meta_final["chunk_index"] = i + 1
        meta_final["chunk_index_local"] = i + 1  # Preservar índice local para trazabilidad
        meta_final["texto_chunk"] = chunk["texto"].strip()
        # Asegurar que estructura se propaga
        meta_final["estructura"] = meta_final.get("estructura", "legal")
        resultado_final.append(meta_final)

    return resultado_final