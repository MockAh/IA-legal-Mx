import os
import json
import pickle
import requests
import numpy as np
from typing import Generator, Optional, Tuple # <--- Agrega esto
from functools import lru_cache # <--- Para la optimización de caché (Paso 3)
from pathlib import Path

try:
    import faiss
except ImportError:
    faiss = None
import unicodedata

# ===== FUNCIÓN DE NORMALIZACIÓN DE TÍTULOS =====

def normalizar_titulo(titulo: str) -> str:
    """
    Normaliza un título para que coincida con el formato de ChromaDB.
    
    Transformaciones:
    1. Convierte a minúsculas
    2. Elimina acentos y caracteres especiales
    3. Reemplaza guiones por espacios
    
    Ejemplos:
    - "Constitucion-Politica-de-los-Estados-Unidos-Mexicanos" 
      -> "constitucion politica de los estados unidos mexicanos"
    """
    if not titulo:
        return ""
    
    # Convertir a minúsculas
    titulo = titulo.lower()
    
    # Eliminar acentos y caracteres diacríticos
    titulo_nfd = unicodedata.normalize('NFD', titulo)
    titulo_sin_acentos = ''.join(char for char in titulo_nfd if unicodedata.category(char) != 'Mn')
    
    # Reemplazar guiones por espacios
    titulo_normalizado = titulo_sin_acentos.replace('-', ' ')
    
    # Limpiar espacios múltiples
    titulo_normalizado = ' '.join(titulo_normalizado.split())
    
    return titulo_normalizado


# AGREGA ESTA NUEVA FUNCIÓN AL FINAL DEL ARCHIVO
def call_deepseek_api_stream(prompt: str, temperature: float = 0.0) -> Generator[str, None, None]:
    """Versión streaming de la API que devuelve fragmentos en tiempo real."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        yield "ERROR: No se encontró DEEPSEEK_API_KEY."
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": True  # <--- CRÍTICO: Activar streaming [cite: 63]
    }

    try:
        # Timeout un poco más alto para streams largos
        with requests.post("https://api.deepseek.com/chat/completions", 
                          headers=headers, json=payload, stream=True, timeout=90) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]  # Remover "data: "
                        if data == '[DONE]':
                            break
                        try:
                            json_data = json.loads(data)
                            delta = json_data['choices'][0]['delta']
                            if 'content' in delta:
                                yield delta['content'] # Entregamos el fragmento [cite: 80]
                        except:
                            continue
    except Exception as e:
        yield f"Error API: {e}"

def call_deepseek_api(prompt: str, temperature: float = 0.0) -> str:
    """Función maestra para consultar al LLM."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "ERROR: No se encontró DEEPSEEK_API_KEY."

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
    except Exception as e:
        return f"Error API: {e}"

def extraer_entidades_con_llm(query: str) -> dict:
    """Extrae Título y Artículo para la Lógica A."""
    prompt = f"""
    Analiza la consulta: "{query}".
    Extrae en JSON: "titulo_documento" (sin acentos) y "Articulo" (solo número).
    Si no existe, usa null.
    Responde SOLO con el JSON.
    """
    llm_output = call_deepseek_api(prompt)
    try:
        if "```json" in llm_output:
            llm_output = llm_output.split("```json\n")[1].split("```")[0]
        return json.loads(llm_output)
    except:
        return {}


# ===== NUEVAS FUNCIONES PARA BÚSQUEDA SEMÁNTICA DE TÍTULOS =====

CACHE_FAISS = {
    "index": None,
    "metadata": None,
    "embedding_model": None
}


def cargar_indice_faiss(base_dir: Optional[str] = None) -> Tuple[Optional[object], Optional[list]]:
    """
    Carga el índice FAISS y metadatos generados por init_faiss.py.
    Los archivos se leen desde la carpeta 'faiss-lista'.
    
    Retorna:
        (index, metadata) - Índice FAISS y lista de metadatos
    """
    if base_dir is None:
        base_dir = str(Path(__file__).resolve().parent)
    
    indice_path = os.path.join(base_dir, "faiss-lista", "indice_titulos_leyes.faiss")
    metadata_path = os.path.join(base_dir, "faiss-lista", "metadata_titulos_leyes.pkl")
    
    if not os.path.exists(indice_path) or not os.path.exists(metadata_path):
        print(f"⚠️  Índices FAISS no encontrados en {os.path.join(base_dir, 'faiss-lista')}")
        print("   Ejecuta init_faiss.py primero para generar los índices.")
        return None, None
    
    if faiss is None:
        print("❌ FAISS no está instalado. Instala con: pip install faiss-cpu")
        return None, None
    
    try:
        index = faiss.read_index(indice_path)
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        print(f"✅ Índice FAISS cargado: {index.ntotal} vectores")
        return index, metadata
    except Exception as e:
        print(f"❌ Error cargando índices FAISS: {e}")
        return None, None


def buscar_titulo_en_faiss(titulo_usuario: str, 
                           embedding_function, 
                           k: int = 1) -> Optional[str]:
    """
    Busca semánticamente un título de ley en el índice FAISS.
    
    Flujo:
    1. Convierte el título a vector usando el modelo de embeddings
    2. Busca los k mejores matches en FAISS
    3. Retorna el primer match (más similar)
    
    Args:
        titulo_usuario: Títnombre de ley buscado por el usuario
        embedding_function: Función para generar embeddings
        k: Número de resultados a retornar (default: 1)
    
    Returns:
        Título exacto de la ley del índice, o None si no se encuentra
    """
    global CACHE_FAISS
    
    # Cargar índice si no está en caché
    if CACHE_FAISS["index"] is None:
        CACHE_FAISS["index"], CACHE_FAISS["metadata"] = cargar_indice_faiss()
    
    if CACHE_FAISS["index"] is None or CACHE_FAISS["metadata"] is None:
        return None
    
    index = CACHE_FAISS["index"]
    metadata = CACHE_FAISS["metadata"]
    
    # Generar embedding del título del usuario
    try:
        emb_usuario = embedding_function.embed_query(titulo_usuario)
        emb_usuario = np.array([emb_usuario]).astype('float32')
        
        # Buscar en FAISS (Inner Product para similitud de coseno)
        distancias, indices = index.search(emb_usuario, k=k)
        
        if len(indices) > 0 and indices[0][0] != -1:
            idx_mejor = indices[0][0]
            titulo_exacto = metadata[idx_mejor].get("titulo_extraido")
            similitud = distancias[0][0]
            
            print(f"🔍 Búsqueda FAISS: '{titulo_usuario}' -> '{titulo_exacto}' (similitud: {similitud:.4f})")
            return titulo_exacto
        
        return None
    except Exception as e:
        print(f"❌ Error en búsqueda FAISS: {e}")
        return None