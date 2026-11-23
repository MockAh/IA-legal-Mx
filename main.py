"""
main.py — Servidor FastAPI de Wall-E Legal 2.0

Sirve el frontend de web/ y expone la lógica existente por HTTP. No reimplementa
nada: importa logica_a, logica_b y logica_c tal como están.

No importa app.py a propósito: hacerlo dispararía init_faiss (cuyo sys.exit(1)
tumbaría el proceso) y construiría la interfaz de Gradio sin necesidad.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8080
"""

import json
from pathlib import Path
from typing import Iterator, Optional

# recursos.py aplica el parche de SQLite al importarse. Va antes que todo lo demás.
import recursos

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from logica_a import logica_a_cita_precisa
from logica_b import logica_b_streaming
from logica_c import logica_c_avanzada
from catalogo_datos import obtener_catalogo

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Wall-E Legal 2.0", docs_url="/api/docs", redoc_url=None)

if (WEB_DIR / "app.css").exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


# ──────────────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────────────

# logica_b emite estos avisos de progreso antes de la respuesta real. No son el
# inicio del texto final, así que el cliente los muestra aparte.
PREFIJOS_ESTADO = ("🔍 **Analizando tu consulta", "⚖️ **Analizando y redactando")


def _desangrar(texto: str) -> str:
    """Quita la sangría de 16 espacios que logica_a arrastra de su f-string.

    Sin esto, cualquier lector de Markdown interpreta la respuesta como bloque
    de código y el HTML del extracto nunca se renderiza.
    """
    return "\n".join(linea.strip() for linea in texto.splitlines()).strip()


def _sse(tipo: str, contenido) -> str:
    """Un evento Server-Sent Events con carga JSON."""
    return "data: " + json.dumps({"tipo": tipo, "contenido": contenido}, ensure_ascii=False) + "\n\n"


class Consulta(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    base: str = Field("GENERAL")

    def base_normalizada(self) -> str:
        return self.base.strip().upper().replace(" ", "_").replace("Á", "A")


# ──────────────────────────────────────────────────────────────────────
# Frontend
# ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def inicio():
    indice = WEB_DIR / "index.html"
    if not indice.exists():
        return {"error": "Falta web/index.html. Copia la carpeta web/ al lado de main.py."}
    return FileResponse(str(indice))


# ──────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────

@app.get("/api/estado")
def estado():
    """Qué acervos están realmente en disco. El front deshabilita lo que falte."""
    return recursos.estado_acervo()


@app.get("/api/catalogo")
def catalogo():
    """Inventario del índice FAISS agrupado por materia."""
    return obtener_catalogo()


@app.post("/api/consulta")
def consulta_cita_precisa(peticion: Consulta):
    """Modo Cita Precisa: recuperación literal, respuesta completa de una vez.

    Definida como 'def' y no 'async def': FastAPI la corre en el threadpool, que
    es lo correcto para una función bloqueante que llama a DeepSeek y a Chroma.
    """
    base = peticion.base_normalizada()

    if base not in recursos.BASES:
        return {"ok": False, "error": f"Base desconocida: '{peticion.base}'."}

    # En Cita Precisa, Trámites SEGOB significa el corpus normativo de SEGOB:
    # logica_c es un flujo de razonamiento operativo, no de cita literal.
    claves = ["segob"] if base == "TRAMITES_SEGOB" else recursos.BASES[base]
    colecciones = [c for c in (recursos.obtener_coleccion(k) for k in claves) if c is not None]

    if not colecciones:
        return {
            "ok": False,
            "error": f"La base '{recursos.ETIQUETAS_BASE[base]}' no está disponible en este servidor.",
            "faltantes": claves,
        }

    try:
        bruto = logica_a_cita_precisa(colecciones, recursos.obtener_modelo(), peticion.query)
        return {"ok": True, "base": base, "markdown": _desangrar(bruto)}
    except Exception as e:
        return {"ok": False, "error": f"Error al procesar la consulta: {e}"}


@app.post("/api/consulta/stream")
def consulta_razonamiento(peticion: Consulta):
    """Modo Razonamiento Jurídico: respuesta progresiva por SSE.

    Cada evento 'texto' trae el contenido ACUMULADO, no el fragmento nuevo:
    el cliente reemplaza, no concatena. Así lo entrega logica_b_streaming.
    """
    base = peticion.base_normalizada()

    def flujo() -> Iterator[str]:
        if base not in recursos.BASES:
            yield _sse("error", f"Base desconocida: '{peticion.base}'.")
            return

        try:
            modelo = recursos.obtener_modelo()
        except Exception as e:
            yield _sse("error", f"No se pudo cargar el modelo de embeddings: {e}")
            return

        # Trámites SEGOB tiene su propio flujo: cruza el corpus normativo con el
        # operativo. No es streaming, así que se anuncia y se entrega completo.
        if base == "TRAMITES_SEGOB":
            col_segob, col_tramites = recursos.colecciones_tramites()
            if col_segob is None or col_tramites is None:
                faltan = [n for n, c in (("segob", col_segob), ("tramites", col_tramites)) if c is None]
                yield _sse("error", f"Acervos no disponibles en este servidor: {', '.join(faltan)}.")
                return
            yield _sse("estado", "Cruzando normativa y catálogo de trámites…")
            try:
                texto = logica_c_avanzada(col_segob, col_tramites, modelo, peticion.query)
                yield _sse("texto", _desangrar(texto))
            except Exception as e:
                yield _sse("error", f"Error en el flujo de trámites: {e}")
            yield _sse("fin", None)
            return

        colecciones = recursos.colecciones_de_base(base)
        if not colecciones:
            yield _sse("error", f"La base '{recursos.ETIQUETAS_BASE[base]}' no está disponible en este servidor.")
            return

        try:
            for fragmento in logica_b_streaming(colecciones, modelo, peticion.query):
                if fragmento.startswith(PREFIJOS_ESTADO):
                    yield _sse("estado", fragmento)
                else:
                    yield _sse("texto", fragmento)
        except Exception as e:
            yield _sse("error", f"Error durante la redacción: {e}")

        yield _sse("fin", None)

    return StreamingResponse(
        flujo(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        workers=1,          # un solo worker: el modelo pesa 2 GB en RAM
    )
