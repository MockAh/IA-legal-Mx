# script_semantico.py
# === MÓDULO DE PROCESAMIENTO SEMÁNTICO PARA ÍNDICES ===
# Especializado en parsear y estructurar documentos tipo "Manual de Organización"

import re
from typing import List, Dict, Any, Tuple

def algoritmo_semantico(lista_de_parrafos: List[str], metadatos_base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Procesa documentos con estructura de ÍNDICE como el "Manual de Organización".
    
    Estrategia:
    1. Identifica dónde comienza el ÍNDICE
    2. Parse cada línea del índice extrayendo: número de capítulo, título, subcapítulos y páginas
    3. Estructura jerárquicamente para preservar relaciones padre-hijo
    4. Crea chunks semánticos para cada entrada del índice
    
    Args:
        lista_de_parrafos: Lista de párrafos del documento
        metadatos_base: Metadatos base del documento
        
    Returns:
        Lista de chunks estructurados para ChromaDB
    """
    
    print(f"🔍 [SEMÁNTICO] Procesando {len(lista_de_parrafos)} párrafos del documento: {metadatos_base.get('source', 'desconocido')}")
    
    # 1. Encontrar el inicio del ÍNDICE
    indice_start = -1
    for i, parrafo in enumerate(lista_de_parrafos):
        # Buscar "ÍNDICE" o variantes
        if re.search(r'^ÍNDICE\b', parrafo.strip(), re.IGNORECASE):
            indice_start = i
            print(f"   📖 Índice encontrado en párrafo {i}: '{parrafo[:50]}...'")
            break
    
    if indice_start == -1:
        print("   ⚠️  No se encontró marcador de ÍNDICE, procesando todo como contenido")
        indice_start = 0
    
    # 2. Extraer líneas del índice (omitir párrafos antes del índice)
    lineas_indice = lista_de_parrafos[indice_start:]
    
    # 3. Parsear el índice
    chunks = parsear_indice_estructurado(lineas_indice, metadatos_base)
    
    # 4. Si no se encontró estructura de índice, fallback a procesamiento por párrafos
    if not chunks:
        print("   ⚠️  No se pudo parsear como índice, usando fallback semántico básico")
        chunks = fallback_semantico_basico(lista_de_parrafos, metadatos_base)
    
    print(f"   ✅ Generados {len(chunks)} chunks semánticos")
    return chunks


def parsear_indice_estructurado(lineas_indice: List[str], metadatos: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse específico para índices de manuales organizacionales.
    
    Maneja:
    - Capítulos numerados: "1. GLOSARIO"
    - Subcapítulos con viñetas: "• Dirección General"
    - Números de página al final
    - Jerarquía padre-hijo
    """
    
    chunks = []
    cap_actual = None
    contexto_actual = {}
    chunk_index = 1
    
    # Patrones de regex
    patron_capitulo = re.compile(r'^(\d+)\.\s+(.+?)\s*(?:\.{2,}|\s+)?(\d+)$')
    patron_subcapitulo = re.compile(r'^[•\-]\s+(.+?)\s*(?:\.{2,}|\s+)?(\d+)$')
    patron_seccion_sin_numero = re.compile(r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+)\s+(\d+)$')
    patron_solo_pagina = re.compile(r'^(\d+)$')
    
    for i, linea in enumerate(lineas_indice):
        linea_limpia = linea.strip()
        if not linea_limpia or len(linea_limpia) < 2:
            continue
        
        # Debug: mostrar qué se está procesando
        if i < 10:  # Solo primeros 10 para debug
            print(f"      📄 Línea {i}: '{linea_limpia[:80]}...'")
        
        # 1. ¿Es un capítulo numerado?
        match_cap = patron_capitulo.match(linea_limpia)
        if match_cap:
            num_cap = match_cap.group(1)
            titulo_cap = match_cap.group(2).strip()
            pagina_cap = match_cap.group(3)
            
            # Crear chunk para el capítulo
            cap_actual = {
                "numero": num_cap,
                "titulo": titulo_cap,
                "pagina": pagina_cap,
                "subcapitulos": []
            }
            
            # Chunk principal del capítulo
            chunk = crear_chunk_indice(
                texto=f"Capítulo {num_cap}: {titulo_cap}",
                detalle=f"Este capítulo abarca desde la página {pagina_cap} del documento.",
                tipo="capitulo",
                jerarquia={"nivel": 1, "capitulo": num_cap},
                metadatos=metadatos,
                pagina=pagina_cap,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1
            
            contexto_actual = {"capitulo": titulo_cap, "numero_cap": num_cap}
            continue
        
        # 2. ¿Es un subcapítulo con viñeta?
        match_sub = patron_subcapitulo.match(linea_limpia)
        if match_sub:
            titulo_sub = match_sub.group(1).strip()
            pagina_sub = match_sub.group(2)
            
            # Determinar si es parte de un capítulo o de una sección
            if cap_actual:
                # Agregar al capítulo actual
                if "subcapitulos" not in cap_actual:
                    cap_actual["subcapitulos"] = []
                cap_actual["subcapitulos"].append({
                    "titulo": titulo_sub,
                    "pagina": pagina_sub
                })
            
            # Chunk para el subcapítulo
            chunk = crear_chunk_indice(
                texto=titulo_sub,
                detalle=f"Subsección ubicada en la página {pagina_sub}. Parte de: {contexto_actual.get('capitulo', 'Documento principal')}",
                tipo="subcapitulo",
                jerarquia={
                    "nivel": 2,
                    "capitulo": contexto_actual.get("numero_cap", ""),
                    "capitulo_titulo": contexto_actual.get("capitulo", "")
                },
                metadatos=metadatos,
                pagina=pagina_sub,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1
            continue
        
        # 3. ¿Es una sección sin número (como "INTRODUCCIÓN")?
        match_seccion = patron_seccion_sin_numero.match(linea_limpia)
        if match_seccion:
            titulo_seccion = match_seccion.group(1).strip()
            pagina_seccion = match_seccion.group(2)
            
            chunk = crear_chunk_indice(
                texto=titulo_seccion,
                detalle=f"Sección principal del documento en página {pagina_seccion}",
                tipo="seccion_principal",
                jerarquia={"nivel": 1, "seccion": "inicial"},
                metadatos=metadatos,
                pagina=pagina_seccion,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1
            continue
        
        # 4. ¿Es solo un número de página? (líneas que solo contienen número)
        match_pagina = patron_solo_pagina.match(linea_limpia)
        if match_pagina:
            # Esto podría ser el número de página de la línea anterior sin formato adecuado
            # Lo ignoramos por ahora, ya que debería estar adjunto al título
            continue
        
        # 5. Fallback: línea no reconocida, crear chunk genérico
        if len(linea_limpia) > 10:  # Solo si tiene contenido significativo
            chunk = crear_chunk_indice(
                texto=linea_limpia[:100],
                detalle="Elemento del índice del documento",
                tipo="elemento_indice",
                jerarquia={"nivel": 0},
                metadatos=metadatos,
                pagina="desconocida",
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1
    
    # 6. Crear chunk resumen de la estructura
    if cap_actual or chunks:
        estructura_resumen = extraer_estructura_completa(chunks)
        chunk_resumen = crear_chunk_indice(
            texto=f"Estructura del Documento: {metadatos.get('titulo_documento', 'Manual')}",
            detalle=estructura_resumen,
            tipo="resumen_estructura",
            jerarquia={"nivel": 0, "tipo": "resumen"},
            metadatos=metadatos,
            pagina="multiple",
            chunk_index=chunk_index
        )
        chunks.append(chunk_resumen)
    
    return chunks


def crear_chunk_indice(texto: str, detalle: str, tipo: str, jerarquia: Dict, 
                       metadatos: Dict[str, Any], pagina: str, chunk_index: int) -> Dict[str, Any]:
    """
    Crea un chunk estructurado para ChromaDB.
    """
    
    # Texto completo para embedding
    texto_completo = f"{texto}\n\n{detalle}"
    
    # Metadatos enriquecidos
    metadata = metadatos.copy()
    metadata.update({
        "tipo_contenido": "indice",
        "subtipo": tipo,
        "pagina_referencia": pagina,
        "jerarquia": jerarquia,
        "chunk_index": chunk_index,
        "chunk_index_local": chunk_index,
        "texto_chunk": texto_completo,
        "fuente": "parseador_indice",
        "longitud_texto": len(texto_completo)
    })
    
    return {
        "texto_chunk": texto_completo,
        "metadata": metadata
    }


def extraer_estructura_completa(chunks: List[Dict]) -> str:
    """
    Extrae una descripción de la estructura completa del documento.
    """
    capitulos = []
    subcapitulos_count = 0
    
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        subtipo = metadata.get("subtipo", "")
        
        if subtipo == "capitulo":
            capitulos.append(metadata.get("texto_chunk", "Capítulo desconocido")[:100])
        elif subtipo == "subcapitulo":
            subcapitulos_count += 1
    
    estructura = f"Documento organizado en {len(capitulos)} capítulos principales"
    if subcapitulos_count > 0:
        estructura += f" con {subcapitulos_count} subsecciones"
    
    if capitulos:
        estructura += ":\n- " + "\n- ".join(capitulos[:5])  # Primeros 5 capítulos
        if len(capitulos) > 5:
            estructura += f"\n... y {len(capitulos) - 5} capítulos más"
    
    return estructura


def fallback_semantico_basico(parrafos: List[str], metadatos: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fallback: procesamiento semántico básico por párrafos.
    Se usa cuando no se detecta estructura de índice.
    """
    
    chunks = []
    
    for i, parrafo in enumerate(parrafos):
        if len(parrafo.strip()) < 20:  # Ignorar párrafos muy cortos
            continue
        
        chunk = {
            "texto_chunk": parrafo,
            "metadata": {
                **metadatos,
                "tipo_contenido": "contenido_general",
                "subtipo": "parrafo_semantico",
                "parrafo_numero": i + 1,
                "chunk_index": i + 1,
                "chunk_index_local": i + 1,
                "longitud_texto": len(parrafo)
            }
        }
        chunks.append(chunk)
    
    return chunks


# --- FUNCIÓN DE PRUEBA PARA TESTING LOCAL ---
if __name__ == "__main__":
    # Simular el contenido del índice para pruebas
    contenido_ejemplo = [
        "ÍNDICE",
        "PÁG",
        "INTRODUCCIÓN 1",
        "1. GLOSARIO 2",
        "2. RESEÑA HISTÓRICA DEL FONDO DE CULTURA ECONÓMICA 4",
        "3. MISIÓN, VISIÓN Y OBJETIVOS 15",
        "4. MARCO NORMATIVO 15",
        "5. SERVICIOS QUE PROPORCIONA EL FCE 20",
        "6. ORGANIGRAMA GENERAL 21",
        "• Dirección General 22",
        "• Gerencia Editorial 23",
        "• Coordinación de Obras para Niños y Jóvenes y Formación Lectora 24",
        "7. ESTRUCTURA ORGÁNICA Y DESCRIPCIÓN DE PUESTOS 33",
        "8. CÓDIGO DE ÉTICA DE LA ADMINISTRACIÓN PÚBLICA FEDERAL Y CÓDIGO DE CONDUCTA 220",
        "9. POLÍTICA GENERAL 231"
    ]
    
    metadatos_prueba = {
        "source": "2024-03-22_Indice_MANUAL-DE-ORGANIZACIÓN_semantic.docx",
        "titulo_documento": "Manual de Organización General del Fondo de Cultura Económica",
        "estructura": "semantic",
        "dominio": "organizacional",
        "sub_dominio": "manuales"
    }
    
    print("🧪 Ejecutando prueba del parseador de índices...")
    resultados = algoritmo_semantico(contenido_ejemplo, metadatos_prueba)
    
    print(f"\n📊 Resultados de la prueba:")
    print(f"   Total chunks generados: {len(resultados)}")
    
    for i, chunk in enumerate(resultados[:3]):  # Mostrar primeros 3
        metadata = chunk.get("metadata", {})
        print(f"\n   Chunk {i+1}:")
        print(f"     Tipo: {metadata.get('subtipo', 'desconocido')}")
        print(f"     Texto: {chunk['texto_chunk'][:80]}...")
        print(f"     Página: {metadata.get('pagina_referencia', 'N/A')}")
    
    print("\n✅ Prueba completada. El script está listo para integrarse con el orquestador.")