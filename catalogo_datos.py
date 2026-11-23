"""
catalogo_datos.py — El acervo FAISS como estructura de datos.

catalogo_axiomas.py devuelve Markdown, que sirve para Gradio pero no para una
API. Este módulo lee el mismo .pkl y devuelve datos; el frontend se encarga del
formato. No modifica catalogo_axiomas.py: ambos pueden convivir.

Si más adelante quieres una sola fuente de verdad, catalogo_axiomas.generar_catalogo()
puede reescribirse en seis líneas sobre obtener_catalogo(). El diff está propuesto
en el mensaje que acompaña a este archivo.
"""

import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
METADATA_PATH = BASE_DIR / "faiss-lista" / "metadata_titulos_leyes.pkl"

# Mismas categorías que catalogo_axiomas.py, sin los emojis (el front los pone).
CATEGORIAS = {
    "basic":         "Legislación Básica",
    "FCE":           "Fondo de Cultura Económica",
    "segob":         "Secretaría de Gobernación",
    "Transparencia": "Transparencia",
    "Tres_Poderes":  "Tres Poderes",
}

MARCADOR_RUTA = "legislacion-mx/"


def _extraer_categoria(ruta: str) -> str:
    """Subcarpeta principal después de 'legislacion-mx/' en la ruta del documento."""
    idx = ruta.find(MARCADOR_RUTA)
    if idx == -1:
        return "Otros"
    resto = ruta[idx + len(MARCADOR_RUTA):]
    subcarpeta = resto.split("/")[0] if "/" in resto else resto
    return subcarpeta if subcarpeta in CATEGORIAS else "Otros"


def _embellecer(titulo: str) -> str:
    """'Ley-General-de-Salud' → 'Ley General De Salud'. Igual que el catálogo actual."""
    return titulo.replace("-", " ").title()


def obtener_catalogo() -> dict:
    """Lee la memoria de FAISS y agrupa los títulos únicos por materia.

    Retorna siempre un diccionario con la misma forma, incluso cuando falla:
        {
          "disponible": bool,
          "mensaje": str | None,      # explica por qué no hay datos
          "total": int,
          "materias": [ {clave, etiqueta, total, titulos: [str]} ]
        }
    """
    if not METADATA_PATH.exists():
        return {
            "disponible": False,
            "mensaje": (
                f"No se encontró el índice de títulos en {METADATA_PATH.name}. "
                "Sincroniza la carpeta 'faiss-lista' o ejecuta init_faiss.py."
            ),
            "total": 0,
            "materias": [],
        }

    try:
        with open(METADATA_PATH, "rb") as f:
            metadata_list = pickle.load(f)
    except Exception as e:
        return {
            "disponible": False,
            "mensaje": f"Error al leer la memoria FAISS: {e}",
            "total": 0,
            "materias": [],
        }

    if not metadata_list:
        return {
            "disponible": False,
            "mensaje": "El índice FAISS está cargado pero no contiene títulos registrados.",
            "total": 0,
            "materias": [],
        }

    grupos = {clave: set() for clave in CATEGORIAS}
    grupos["Otros"] = set()

    for m in metadata_list:
        ruta = m.get("ruta", "")
        titulo = m.get("titulo_extraido", "Documento sin título")
        grupos[_extraer_categoria(ruta)].add(titulo)

    materias = []
    total = 0
    orden = list(CATEGORIAS.items()) + [("Otros", "Otros")]

    for clave, etiqueta in orden:
        titulos = sorted(_embellecer(t) for t in grupos[clave])
        if not titulos:
            continue
        total += len(titulos)
        materias.append({
            "clave": clave,
            "etiqueta": etiqueta,
            "total": len(titulos),
            "titulos": titulos,
        })

    return {"disponible": True, "mensaje": None, "total": total, "materias": materias}
