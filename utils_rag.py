import os
import json
import requests

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