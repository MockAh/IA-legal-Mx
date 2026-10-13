"""
recursos.py — Capa de recursos compartidos de Wall-E Legal 2.0

Punto de entrada común para el servidor FastAPI y para cualquier script futuro.
NO importa app.py y NO construye interfaz alguna: importarlo es barato y no
dispara la inicialización de FAISS ni la UI de Gradio.

Resuelve cuatro problemas detectados en la auditoría del repo:
  1. El parche de SQLite se aplica aquí, antes de importar chromadb.
  2. La carga perezosa del modelo y de las colecciones queda protegida con lock,
     para que dos peticiones simultáneas no instancien dos modelos de 2 GB.
  3. Las rutas se resuelven contra BASE_DIR, no contra el directorio de arranque.
  4. Las colecciones se ABREN, nunca se crean: si falta el acervo, el sistema lo
     reporta en lugar de fabricar una colección vacía.
"""

import os
import sys
import threading
from pathlib import Path

# --- PARCHE CRÍTICO: debe ejecutarse ANTES de importar chromadb ---
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    print("☁️  Parche SQLite aplicado")
except ImportError:
    print("💻 Modo local detectado (sin parche SQLite)")

import chromadb
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

# app.py cargaba el .env por su cuenta; un punto de entrada nuevo no hereda eso.
# Sin esta línea, DEEPSEEK_API_KEY no existe y la extracción de entidades falla
# en silencio: logica_a concluye que no identificó la ley.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MODELO_LOCAL = BASE_DIR / "modelo_e5"
FAISS_DIR = BASE_DIR / "faiss-lista"
INDICE_FAISS = FAISS_DIR / "indice_titulos_leyes.faiss"
METADATA_FAISS = FAISS_DIR / "metadata_titulos_leyes.pkl"

# ──────────────────────────────────────────────────────────────────────
# Acervos
# ──────────────────────────────────────────────────────────────────────

RUTAS = {
    "basic":    BASE_DIR / "procesado-mx" / "basic-mx"    / "chroma_db_basic",
    "segob":    BASE_DIR / "procesado-mx" / "segob-mx"    / "chroma_db_segob",
    "transp":   BASE_DIR / "procesado-mx" / "transp-mx"   / "chroma_db_transp",
    "3p":       BASE_DIR / "procesado-mx" / "3p-mx"       / "chroma_db_3p",
    "fce":      BASE_DIR / "procesado-mx" / "fce-mx"      / "chroma_db_fce",
    "tramites": BASE_DIR / "procesado-mx" / "tramites-mx" / "chroma_db_tramites_mx",
}

# Nombre de colección por acervo. Se prueban en orden hasta encontrar una.
NOMBRES_COLECCION = {
    "tramites": ("tramites_gob_mx", "langchain"),
}
NOMBRE_POR_DEFECTO = ("langchain",)

ETIQUETAS_ACERVO = {
    "basic":    "Legislación básica",
    "segob":    "Secretaría de Gobernación",
    "transp":   "Transparencia",
    "3p":       "Tres Poderes",
    "fce":      "Fondo de Cultura Económica",
    "tramites": "Trámites gob.mx",
}

# Bases que ofrece el frontend. 'General' es nueva: agrupa lo que antes se
# consultaba de forma implícita dentro de cada modo.
BASES = {
    "GENERAL":        ["basic", "transp", "3p"],
    "FCE":            ["fce"],
    "TRAMITES_SEGOB": ["segob", "tramites"],
}

ETIQUETAS_BASE = {
    "GENERAL":        "General",
    "FCE":            "FCE",
    "TRAMITES_SEGOB": "Trámites SEGOB",
}

# ──────────────────────────────────────────────────────────────────────
# Caché con protección de concurrencia
# ──────────────────────────────────────────────────────────────────────

_LOCK_MODELO = threading.Lock()
_LOCK_COLECCIONES = threading.Lock()
_CACHE = {"modelo": None, "colecciones": {}}


def obtener_modelo():
    """Devuelve la función de embeddings. Se instancia una sola vez.

    Prefiere el modelo cacheado en ./modelo_e5 (ruta absoluta). Si no está,
    avisa en consola antes de descargar ~2 GB de Hugging Face, para que nadie
    se sorprenda con la espera.
    """
    if _CACHE["modelo"] is not None:
        return _CACHE["modelo"]

    with _LOCK_MODELO:
        if _CACHE["modelo"] is not None:       # otra petición ganó la carrera
            return _CACHE["modelo"]

        if MODELO_LOCAL.is_dir():
            print(f"🧠 Cargando modelo local: {MODELO_LOCAL}")
            _CACHE["modelo"] = HuggingFaceEmbeddings(
                model_name=str(MODELO_LOCAL), model_kwargs={"device": "cpu"}
            )
        else:
            print(f"⚠️  No existe {MODELO_LOCAL}.")
            print("   Se descargará 'intfloat/multilingual-e5-large' (~2 GB).")
            print("   Para evitarlo, ejecuta: python3 descargar_modelo.py")
            _CACHE["modelo"] = HuggingFaceEmbeddings(
                model_name="intfloat/multilingual-e5-large",
                model_kwargs={"device": "cpu"},
            )
        return _CACHE["modelo"]


def obtener_coleccion(clave: str):
    """Abre una colección existente. Devuelve None si el acervo no está en disco.

    Usa get_collection (no get_or_create): si falta el acervo queremos saberlo,
    no terminar con una colección vacía que responde cero resultados.
    """
    if clave in _CACHE["colecciones"]:
        return _CACHE["colecciones"][clave]

    ruta = RUTAS.get(clave)
    if ruta is None or not ruta.is_dir():
        _CACHE["colecciones"][clave] = None
        return None

    with _LOCK_COLECCIONES:
        if clave in _CACHE["colecciones"] and _CACHE["colecciones"][clave] is not None:
            return _CACHE["colecciones"][clave]

        coleccion = None
        try:
            cliente = chromadb.PersistentClient(path=str(ruta))
            for nombre in NOMBRES_COLECCION.get(clave, NOMBRE_POR_DEFECTO):
                try:
                    coleccion = cliente.get_collection(nombre)
                    print(f"✅ Acervo '{clave}' abierto (colección: {nombre})")
                    break
                except Exception:
                    continue
            if coleccion is None:
                print(f"⚠️  '{clave}': la carpeta existe pero no tiene colección utilizable.")
        except Exception as e:
            print(f"❌ Error abriendo el acervo '{clave}': {e}")

        _CACHE["colecciones"][clave] = coleccion
        return coleccion


def colecciones_de_base(base: str) -> list:
    """Colecciones disponibles para una base del frontend, en orden."""
    claves = BASES.get(base, [])
    abiertas = [obtener_coleccion(c) for c in claves]
    return [c for c in abiertas if c is not None]


def colecciones_tramites():
    """Par (segob, tramites) para logica_c_avanzada. Cualquiera puede ser None."""
    return obtener_coleccion("segob"), obtener_coleccion("tramites")


# ──────────────────────────────────────────────────────────────────────
# Diagnóstico
# ──────────────────────────────────────────────────────────────────────

def estado_acervo() -> dict:
    """Retrato honesto de qué hay en disco. Alimenta /api/estado."""
    acervos = {}
    for clave, ruta in RUTAS.items():
        existe_ruta = ruta.is_dir()
        coleccion = obtener_coleccion(clave) if existe_ruta else None
        documentos = None
        if coleccion is not None:
            try:
                documentos = coleccion.count()
            except Exception:
                documentos = None
        acervos[clave] = {
            "etiqueta": ETIQUETAS_ACERVO.get(clave, clave),
            "ruta": str(ruta.relative_to(BASE_DIR)),
            "disponible": coleccion is not None,
            "documentos": documentos,
        }

    bases = {}
    for base, claves in BASES.items():
        presentes = [c for c in claves if acervos.get(c, {}).get("disponible")]
        faltantes = [c for c in claves if c not in presentes]
        bases[base] = {
            "etiqueta": ETIQUETAS_BASE[base],
            "acervos": claves,
            "disponible": len(presentes) > 0,
            "completa": not faltantes,
            "faltantes": faltantes,
        }

    return {
        "acervos": acervos,
        "bases": bases,
        "faiss": {
            "indice": INDICE_FAISS.exists(),
            "metadata": METADATA_FAISS.exists(),
        },
        "modelo": {
            "cacheado_en_disco": MODELO_LOCAL.is_dir(),
            "cargado_en_memoria": _CACHE["modelo"] is not None,
        },
        "llm": {
            # Nunca el valor, solo si está puesta.
            "clave_configurada": bool(os.getenv("DEEPSEEK_API_KEY")),
        },
    }
