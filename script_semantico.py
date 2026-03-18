# script_semantico.py
# === LÓGICA SEMÁNTICA "CAMALEÓN" ===
# Adapta la estrategia de corte según el contenido: Histórico, Ético o Administrativo.

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. DEFINICIÓN DE PATRONES (El "Cerebro" del Clasificador)
# [cite: 31-50]
PATRONES_SEMANTICOS = {
    'historico': [
        r'\b(19|20)\d{2}\b',                     # Años (1900-2099)
        r'(?:fue|se realizó|se creó|inauguró)',  # Verbos pasivos históricos
        r'(?:durante|años después|posteriormente)', 
        r'^[A-ZÁÉÍÓÚÑ\s]+:$'                     # Encabezados tipo "RESEÑA:"
    ],
    'etico_politico': [
        r'(?:Misión|Visión|Valores|Objetivo\s+General)',
        r'creación.*lectores|impulso.*cultura',
        r'inclusión.*vulnerables|sentido\s+social',
        r'^[A-Z][a-záéíóúñ]+\s*$'                # Encabezados cortos
    ],
    'administrativo': [
        r'Nombre del Puesto|Departamento de',
        r'^\d+\.\s',                             # Listas numeradas
        r'(?:Coordinar|Supervisar|Controlar|Ejecutar|Administrar)',
        r'Funciones|Responsabilidades|Atribuciones'
    ]
}

def clasificar_tipo_texto(texto: str) -> str:
    """
    Escanea el texto y decide qué estrategia de chunking usar.
    Retorna: 'historico', 'etico_politico', 'administrativo' o 'mixto'.
    [cite: 26-61]
    """
    puntajes = {tipo: 0 for tipo in PATRONES_SEMANTICOS}

    for tipo, patrones in PATRONES_SEMANTICOS.items():
        for patron in patrones:
            # Buscamos coincidencias en todo el bloque
            matches = re.findall(patron, texto, re.IGNORECASE | re.MULTILINE)
            puntajes[tipo] += len(matches)

    # Determinar ganador
    max_puntos = max(puntajes.values())
    if max_puntos == 0:
        return "mixto"

    tipos_dominantes = [t for t, p in puntajes.items() if p == max_puntos]
    # Si hay empate o ganador claro, devolvemos el primero
    return tipos_dominantes[0]

def obtener_separadores_por_tipo(tipo: str) -> list[str]:
    """
    Define DÓNDE CORTAR el texto según su naturaleza.
    Esta es la clave para no romper ideas importantes.
    [cite: 272-283]
    """
    separadores_base = ["\n\n", "\n", ". ", " ", ""]
    
    if tipo == 'historico':
        # Prioridad: Cortar antes de una fecha (nuevo evento)
        return [r'(?=\b(?:19|20)\d{2}\b)'] + separadores_base
        
    elif tipo == 'etico_politico':
        # Prioridad: Cortar antes de conceptos clave
        return [r'(?=Misión)', r'(?=Visión)', r'(?=Valores)', r'(?=Objetivo)'] + separadores_base
        
    elif tipo == 'administrativo':
        # Prioridad: Cortar antes de Puestos o Funciones
        return [
            r'(?=Nombre del Puesto:)', 
            r'(?=Departamento)', 
            r'(?=Funciones:)', 
            r'(?=^\d+\.\s)' # Antes de un número de lista
        ] + separadores_base
        
    else: # Mixto
        return separadores_base

def enriquecer_metadatos_estandar(chunk_texto: str, tipo_detectado: str, meta_base: dict) -> dict:
    """
    Genera un diccionario de metadatos 100% compatible con el esquema Legal.
    """
    # 1. Copia base
    meta_final = meta_base.copy()
    
    # 2. Campos Semánticos (Propios)
    meta_final["tipo_contenido"] = tipo_detectado
    
    # Subtipo
    subtipo = "general"
    if re.search(r'procedimiento|manual|protocolo', chunk_texto, re.IGNORECASE): subtipo = "procedimiento"
    elif re.search(r'recursos humanos|personal|contratación', chunk_texto, re.IGNORECASE): subtipo = "recursos_humanos"
    elif re.search(r'presupuesto|financiero|contable', chunk_texto, re.IGNORECASE): subtipo = "financiero"
    meta_final["subtipo"] = subtipo
    
    # Fechas Referencia
    fechas_str = ""
    if tipo_detectado == 'historico':
        anios = re.findall(r'\b(19|20)(\d{2})\b', chunk_texto)
        if anios: fechas_str = ", ".join([f"{s}{d}" for s, d in anios])
    meta_final["fechas_referencia"] = fechas_str

    # 3. CAMPOS LEGALES (RELLENO OBLIGATORIO)
    # Deben existir aunque estén vacíos para evitar errores de esquema en Chroma
    # INICIALIZACIÓN COMPLETA para garantizar consistencia con script_legal.py
    meta_final.update({
        "Decreto": meta_final.get("Decreto", "<No aplica>"),
        "Libro": meta_final.get("Libro", "<No aplica>"), 
        "Titulo": meta_final.get("Titulo", "<No aplica>"), 
        "Capitulo": meta_final.get("Capitulo", "<No aplica>"), 
        "Seccion": meta_final.get("Seccion", "<No aplica>"), 
        "Articulo": meta_final.get("Articulo", "<No aplica>"), 
        # ARMONIZACIÓN: Usar valor por defecto Principal si no viene especificado
        "Transitorio": meta_final.get("Transitorio", "Principal"),
        # Propagar estructura para trazabilidad
        "estructura": meta_final.get("estructura", "semantic")
    })
    
    return meta_final

def algoritmo_semantico(lista_de_parrafos: list[str], metadatos_base: dict) -> list[dict]:
    """Algoritmo Semántico Inteligente y Estandarizado."""
    print(f"     🧠 [Semántico] Analizando contexto de {len(lista_de_parrafos)} párrafos...")
    
    texto_completo = "\n\n".join(lista_de_parrafos)
    tipo_contenido = clasificar_tipo_texto(texto_completo)
    separadores_inteligentes = obtener_separadores_por_tipo(tipo_contenido)
    
    print(f"        -> Detectado: {tipo_contenido.upper()}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=900, chunk_overlap=150,
        separators=separadores_inteligentes, is_separator_regex=True 
    )
    
    chunks_texto = text_splitter.split_text(texto_completo)
    
    chunks_finales = []
    for i, txt in enumerate(chunks_texto):
        # Re-evaluación local del tipo
        tipo_chunk = clasificar_tipo_texto(txt) if len(chunks_texto) > 1 else tipo_contenido
        
        # Enriquecimiento ESTANDARIZADO
        meta_final = enriquecer_metadatos_estandar(txt, tipo_chunk, metadatos_base)
        
        # Campos de Sistema (chunk_index local, será ajustado por orquestador si es necesario)
        meta_final["chunk_index"] = i + 1
        meta_final["chunk_index_local"] = i + 1  # Preservar índice local para trazabilidad
        meta_final["texto_chunk"] = txt.strip()
        
        chunks_finales.append(meta_final)
        
    return chunks_finales
