# catalogo_axiomas.py
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# Apuntamos a donde tu startup.sh descarga los índices
METADATA_PATH = BASE_DIR / "faiss-lista" / "metadata_titulos_leyes.pkl"

# Categorías derivadas de Axiomas/legislacion-mx/<subcarpeta>
CATEGORIAS = {
    "basic":         "📜 Legislación Básica",
    "FCE":           "📘 Fondo de Cultura Económica",
    "segob":         "🏛️ Secretaría de Gobernación",
    "Transparencia": "🔍 Transparencia",
    "Tres_Poderes":  "⚖️ Tres Poderes",
}

MARCADOR_RUTA = "legislacion-mx/"


def _extraer_categoria(ruta: str) -> str:
    """Extrae la subcarpeta principal después de 'legislacion-mx/' en la ruta."""
    idx = ruta.find(MARCADOR_RUTA)
    if idx == -1:
        return "Otros"
    resto = ruta[idx + len(MARCADOR_RUTA):]
    subcarpeta = resto.split("/")[0] if "/" in resto else resto
    return subcarpeta if subcarpeta in CATEGORIAS else "Otros"


def generar_catalogo() -> str:
    """Genera el catálogo Markdown agrupado en 5 subconjuntos leyendo la memoria de FAISS."""

    if not METADATA_PATH.exists():
        return f"⚠️ No se encontró la base de datos de títulos en: `{METADATA_PATH}`. Verifica que 'faiss-lista' exista."

    try:
        with open(METADATA_PATH, 'rb') as f:
            metadata_list = pickle.load(f)

        if not metadata_list:
            return "📭 La biblioteca FAISS está cargada pero no contiene títulos registrados."

        # Agrupar títulos únicos por categoría
        grupos: dict[str, set[str]] = {cat: set() for cat in CATEGORIAS}
        grupos["Otros"] = set()

        for m in metadata_list:
            ruta = m.get("ruta", "")
            titulo = m.get("titulo_extraido", "Documento sin título")
            cat = _extraer_categoria(ruta)
            grupos[cat].add(titulo)

        # Construir Markdown
        lineas = [
            "## 🏛️ Acervo Documental del Juez Scharseinegger\n",
            "Leyes y reglamentos procesados en la memoria semántica (FAISS), organizados por materia.\n",
            "---",
        ]

        total = 0
        for cat_key, cat_label in CATEGORIAS.items():
            titulos = sorted(grupos[cat_key])
            if not titulos:
                continue
            total += len(titulos)
            lineas.append(f"\n### {cat_label} ({len(titulos)})\n")
            for t in titulos:
                nombre_limpio = t.replace("-", " ").title()
                lineas.append(f"- ✅ {nombre_limpio}")

        # Si quedaron documentos sin clasificar
        otros = sorted(grupos["Otros"])
        if otros:
            total += len(otros)
            lineas.append(f"\n### 📁 Otros ({len(otros)})\n")
            for t in otros:
                nombre_limpio = t.replace("-", " ").title()
                lineas.append(f"- ✅ {nombre_limpio}")

        lineas.append(f"\n**Total de leyes indexadas:** {total}")
        return "\n".join(lineas)

    except Exception as e:
        return f"❌ Error al leer la biblioteca FAISS: {str(e)}"