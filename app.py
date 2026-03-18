import os
import sys
import time
from pathlib import Path

# --- 1. PARCHE CRÍTICO ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("☁️  Parche SQLite aplicado")
except ImportError:
    print("💻 Modo Local detectado")

import gradio as gr
import chromadb
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

# --- Módulos Lógicos ---
from logica_a import logica_a_cita_precisa
from logica_b import logica_b_streaming
from logica_c import logica_c_avanzada
from catalogo_axiomas import generar_catalogo

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

# --- INICIALIZACIÓN FAISS ---
print("\n" + "="*60)
print("🔧 Inicializando índices FAISS...")
print("="*60)
try:
    import init_faiss
    init_faiss.main()
except Exception as e:
    print(f"⚠️  Advertencia al inicializar FAISS: {e}")
    print("   La búsqueda semántica de títulos podría no estar disponible.")

# --- 2. GESTIÓN DE RECURSOS (Singleton para Concurrencia) ---
RECURSOS_CACHE = {
    "modelo": None,
    "clientes_chroma": {}
}

def get_embedding_function():
    if RECURSOS_CACHE["modelo"] is None:
        try:
            RECURSOS_CACHE["modelo"] = HuggingFaceEmbeddings(
                model_name="./modelo_e5", model_kwargs={'device': 'cpu'}
            )
        except:
            RECURSOS_CACHE["modelo"] = HuggingFaceEmbeddings(
                model_name="intfloat/multilingual-e5-large"
            )
    return RECURSOS_CACHE["modelo"]

def get_db_collection(path_str, collection_name="langchain"):
    if path_str not in RECURSOS_CACHE["clientes_chroma"]:
        if os.path.exists(path_str):
            try:
                client = chromadb.PersistentClient(path=path_str)
                col = client.get_or_create_collection(collection_name)
                RECURSOS_CACHE["clientes_chroma"][path_str] = col
            except Exception as e:
                print(f"Error cargando DB {path_str}: {e}")
                return None
        else:
            return None
    return RECURSOS_CACHE["clientes_chroma"].get(path_str)

def obtener_colecciones_por_modo(modo):
    """Retorna las colecciones específicas según el modo seleccionado."""
    
    # Rutas relativas a BASE_DIR
    rutas = {
        "basic_mx": BASE_DIR / "procesado-mx" / "basic-mx" / "chroma_db_basic",
        "segob_mx": BASE_DIR / "procesado-mx" / "segob-mx" / "chroma_db_segob",
        "transp_mx": BASE_DIR / "procesado-mx" / "transp-mx" / "chroma_db_transp",
        "3p_mx": BASE_DIR / "procesado-mx" / "3p-mx" / "chroma_db_3p",
        "fce_mx": BASE_DIR / "procesado-mx" / "fce-mx" / "chroma_db_fce",
        "tramites_mx": BASE_DIR / "procesado-mx" / "tramites-mx" / "chroma_db_tramites_mx",
    }
    
    cols_legales = []
    col_tramites = None
    col_segob = None
    
    if modo == "Cita Precisa":
        # Incluye todas las colecciones legales disponibles
        for key in ["basic_mx", "segob_mx", "transp_mx", "3p_mx", "fce_mx"]:
            c = get_db_collection(str(rutas[key]))
            if c: cols_legales.append(c)
    
    elif modo == "Razonamiento Jurídico":
        # Solo: basic-mx, segob-mx, transp-mx, 3p-mx
        for key in ["basic_mx", "segob_mx", "transp_mx", "3p_mx"]:
            c = get_db_collection(str(rutas[key]))
            if c: cols_legales.append(c)
    
    elif modo == "FCE":
        # Solo: fce-mx
        c = get_db_collection(str(rutas["fce_mx"]))
        if c: cols_legales.append(c)
    
    elif modo == "Trámites SEGOB":
        # Para este modo, retorna segob + tramites
        col_segob = get_db_collection(str(rutas["segob_mx"]))
        col_tramites = get_db_collection(str(rutas["tramites_mx"]), "tramites_gob_mx")
        if not col_tramites:
            col_tramites = get_db_collection(str(rutas["tramites_mx"]), "langchain")
    
    return cols_legales, col_tramites, col_segob

# --- 3. LÓGICA DE INTERFAZ (NUEVA ARQUITECTURA) ---

def user_submit(mensaje, historial):
    """
    1. Agrega mensaje del usuario al historial.
    2. Limpia el input.
    3. Retorna historial actualizado y input vacío.
    """
    if not mensaje:
        return "", historial
    return "", historial + [[mensaje, None]]

def stream_response(historial, modo):
    """
    Generador que alimenta el 'Buffer de Streaming' (Markdown)
    NO toca el historial del chatbot.
    """
    if not historial:
        yield "..."
        return

    mensaje = historial[-1][0]
    embedding_fn = get_embedding_function()
    cols_legales, col_tramites, col_segob = obtener_colecciones_por_modo(modo)
    
    buffer_texto = ""

    # Validación según el modo
    if modo in ["Cita Precisa", "Razonamiento Jurídico", "FCE"] and not cols_legales:
        yield "❌ Error: No se encontraron bases de datos para este modo."
        return
    
    if modo == "Trámites SEGOB" and (not col_segob or not col_tramites):
        yield "❌ Error: Colecciones de SEGOB o Trámites no disponibles."
        return

    try:
        if modo == "Cita Precisa":
            buffer_texto = logica_a_cita_precisa(cols_legales, embedding_fn, mensaje)
            yield buffer_texto
        
        elif modo == "Razonamiento Jurídico":
            generador = logica_b_streaming(cols_legales, embedding_fn, mensaje)
            for fragmento in generador:
                buffer_texto = fragmento
                yield buffer_texto
        
        elif modo == "FCE":
            generador = logica_b_streaming(cols_legales, embedding_fn, mensaje)
            for fragmento in generador:
                buffer_texto = fragmento
                yield buffer_texto
        
        elif modo == "Trámites SEGOB":
            yield "⏳ Procesando solicitud de trámites..."
            buffer_texto = logica_c_avanzada(col_segob, col_tramites, embedding_fn, mensaje)
            yield buffer_texto

    except Exception as e:
        yield f"❌ Error: {str(e)}"

def consolidar_respuesta(historial, buffer_final):
    """
    Al final del streaming, toma el texto del buffer y lo 'graba'
    en el historial permanente del chatbot. Limpia el buffer.
    """
    if not historial:
        return historial, ""
    
    # Actualizamos el último mensaje (que era None) con la respuesta final
    historial[-1][1] = buffer_final
    return historial, "" # Retorna historial lleno y buffer vacío

# --- 4. INTERFAZ GRÁFICA ---

tema = gr.themes.Soft(primary_hue="orange", secondary_hue="blue")
css = """
.gradio-container {background-color: #FFFDF7;}
footer {display: none !important;}

/* Estilo para el bloque de texto legal */
blockquote {
    border-left: 4px solid #E65100; /* Naranja profundo */
    background-color: #FFF3E0;
    padding: 15px;
    margin: 10px 0;
    line-height: 1.6; /* Mejora la lectura de párrafos largos */
    color: #212121;
}

/* Resaltado de los números de párrafo */
blockquote strong {
    color: #1565C0;
    font-variant: small-caps;
}

/* Centrar el contenedor del texto dentro de la caja de Gradio */
.contenedor-legal {
    width: 90%;            /* Ocupa el 90% del ancho para dejar márgenes */
    margin: 20px auto;     /* Centra el bloque horizontalmente */
    padding: 15px;
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}

/* Estilo para cada párrafo: Justificado y con Sangría Sencilla */
.parrafo-legal {
    text-align: justify;   /* Texto Justificado */
    text-indent: 40px;     /* Sangría en la primera línea */
    margin-bottom: 1.2em;  /* Espacio entre párrafos */
    line-height: 1.5;      /* Interlineado cómodo para lectura legal */
    color: #1a1a1a;
    font-family: 'Times New Roman', serif; /* Opcional: fuente más tradicional */
    user-select: text;
}
"""

with gr.Blocks(theme=tema, css=css) as demo:
    gr.Markdown("# ⚖️🔶 Wall-E Legal 2.0")

    with gr.Tabs():
        # ========== PESTAÑA 1: AGENTE IA ==========
        with gr.Tab("⚖️ Agente IA"):
            modo_radio = gr.Radio(
                ["Cita Precisa", "Razonamiento Jurídico", "FCE", "Trámites SEGOB"],
                value="Razonamiento Jurídico",
                label="Modo"
            )

            # 1. EL CHATBOT (Estático durante streaming)
            chatbot = gr.Chatbot(
                height=400, 
                label="Historial", 
                bubble_full_width=False,
                show_copy_button=True
            )

            # 2. EL BUFFER DE STREAMING (Aquí ocurre la magia)
            # Visible solo cuando se genera texto
            lbl_status = gr.Markdown("### 🤖 Respuesta en curso:", visible=False)
            buffer_streaming = gr.Markdown(visible=False, elem_classes="buffer-container")
            
            # 3. ENTRADA
            with gr.Row():
                txt_mensaje = gr.Textbox(
                    placeholder="Escribe tu consulta...", 
                    show_label=False,
                    autofocus=True,
                    lines=1,
                    scale=5
                )
                btn_enviar = gr.Button("📤 Enviar", scale=1)

        # ========== PESTAÑA 2: BASE DE DATOS DISPONIBLE ==========
        with gr.Tab("📚 Base de datos disponible"):
            btn_actualizar = gr.Button("🔄 Actualizar catálogo", scale=1)
            catalogo_md = gr.Markdown(value=generar_catalogo())
            btn_actualizar.click(
                fn=generar_catalogo,
                outputs=[catalogo_md]
            )

    # --- FLUJO DE EVENTOS (PIPELINE) ---
    
    # Paso A: Usuario envía -> Limpia input, añade pregunta a Chatbot (Respuesta=None)
    # Ambos (Enter y botón) disparan el mismo flujo
    evento_submit = txt_mensaje.submit(
        fn=user_submit,
        inputs=[txt_mensaje, chatbot],
        outputs=[txt_mensaje, chatbot],
        queue=False
    )
    
    # El botón también dispara el mismo flujo
    btn_click = btn_enviar.click(
        fn=user_submit,
        inputs=[txt_mensaje, chatbot],
        outputs=[txt_mensaje, chatbot],
        queue=False
    )
    
    # Paso B: Activar visibilidad del Buffer (para ambos eventos)
    evento_visibilidad = evento_submit.then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=True, value="⏳ Iniciando análisis...")),
        outputs=[lbl_status, buffer_streaming]
    )
    
    btn_visibilidad = btn_click.then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=True, value="⏳ Iniciando análisis...")),
        outputs=[lbl_status, buffer_streaming]
    )

    # Paso C: STREAMING -> Actualiza SOLO el Buffer Markdown (El Chatbot NO se toca)
    evento_stream = evento_visibilidad.then(
        fn=stream_response,
        inputs=[chatbot, modo_radio],
        outputs=[buffer_streaming]
    )
    
    btn_stream = btn_visibilidad.then(
        fn=stream_response,
        inputs=[chatbot, modo_radio],
        outputs=[buffer_streaming]
    )

    # Paso D: CONSOLIDACIÓN -> Copia Buffer a Chatbot y oculta Buffer
    evento_stream.then(
        fn=consolidar_respuesta,
        inputs=[chatbot, buffer_streaming],
        outputs=[chatbot, buffer_streaming]
    ).then(
        fn=lambda: (gr.update(visible=False), gr.update(visible=False)),
        outputs=[lbl_status, buffer_streaming]
    )
    
    btn_stream.then(
        fn=consolidar_respuesta,
        inputs=[chatbot, buffer_streaming],
        outputs=[chatbot, buffer_streaming]
    ).then(
        fn=lambda: (gr.update(visible=False), gr.update(visible=False)),
        outputs=[lbl_status, buffer_streaming]
    )

if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0", 
        server_port=int(os.environ.get("PORT", 8080))
    )