import os
import sys
from pathlib import Path

# --- 1. PARCHE CRÍTICO INTELIGENTE (Funciona en Local y Nube) ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("☁️  Parche SQLite aplicado (Entorno Cloud/Linux detected)")
except ImportError:
    print("💻 Modo Local detectado: Usando SQLite nativo (Parche omitido)")

import gradio as gr
import chromadb
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

# --- Módulos Nuevos ---
from logica_a import logica_a_cita_precisa
from logica_b import logica_b_explicacion_juridica
from logica_c import logica_c_avanzada 

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
COLLECTION_NAME = "langchain"

# --- Variables Globales ---
EMBEDDING_FUNCTION = None
COLS_LEGALES = []
COL_TRAMITES = None
COL_SEGOB = None
COL_FCE = None

def cargar_recursos(scope: str):
    """Carga modelos y DBs según el scope seleccionado."""
    global EMBEDDING_FUNCTION, COLS_LEGALES, COL_TRAMITES, COL_SEGOB, COL_FCE
    
    print(f"🔄 Cargando recursos para Scope: {scope}...")
    
    # 1. Cargar Modelo (Solo una vez)
    if EMBEDDING_FUNCTION is None:
        print("🧠 Cargando modelo E5 en CPU...")
        try:
            EMBEDDING_FUNCTION = HuggingFaceEmbeddings(
                model_name="./modelo_e5", 
                model_kwargs={'device': 'cpu'}
            )
        except Exception as e:
            print(f"⚠️ Error cargando modelo local (posiblemente en entorno de prueba): {e}")
            # Fallback para pruebas si no tienes el modelo descargado
            EMBEDDING_FUNCTION = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

    # 2. Definir rutas (AJUSTADAS A TU ESTRUCTURA REAL)
    rutas_legales = []
    ruta_tramites = None
    ruta_segob = None # Inicializamos
    
    if scope.lower() == 'unam':
        rutas_legales = [BASE_DIR / "procesado-unam" / "chroma_db_unam"]
    elif scope.lower() == 'mx':
        # ESTRUCTURA CORREGIDA SEGÚN TU 'ls'
        rutas_legales = [
            BASE_DIR / "procesado-mx" / "principal-mx" / "chroma_db_mx",
            BASE_DIR / "procesado-mx" / "excep-mx" / "chroma_db_excep_mx"
        ]
        # Trámites y Segob viven DENTRO de procesado-mx
        ruta_tramites = BASE_DIR / "procesado-mx" / "tramites-mx" / "chroma_db_tramites_mx"
        
        # OJO AQUÍ: Asumiendo que dentro de segob-mx hay un chroma_db o es la carpeta misma.
        # Ajusta "chroma_db_segob" si tu carpeta interna tiene otro nombre, o quítalo si "segob-mx" es la DB directa.
        ruta_segob = BASE_DIR / "procesado-mx" / "segob-mx" / "chroma_db_segob" 

    # 3. Conectar ChromaDB Legal
    COLS_LEGALES = []
    for ruta in rutas_legales:
        if ruta.exists():
            try:
                client = chromadb.PersistentClient(path=str(ruta))
                COLS_LEGALES.append(client.get_or_create_collection(COLLECTION_NAME))
                print(f"  ✅ Legal cargado: {ruta.name}")
            except Exception as e:
                print(f"  ❌ Error cargando Legal {ruta.name}: {e}")

    # 4. Conectar ChromaDB Trámites (CON DIAGNÓSTICO)
    COL_TRAMITES = None
    if ruta_tramites and ruta_tramites.exists():
        try:
            print(f"  📂 Intentando cargar Trámites desde: {ruta_tramites}")
            client_t = chromadb.PersistentClient(path=str(ruta_tramites))
            
            # --- CHISMOSO: ¿Cómo se llaman las colecciones aquí? ---
            nombres_cols = [c.name for c in client_t.list_collections()]
            print(f"  👀 Colecciones en Trámites: {nombres_cols}")
            
            # Intentamos cargar 'tramites_gob_mx', si falla, probamos 'langchain'
            target_col = "tramites_gob_mx"
            if target_col not in nombres_cols and "langchain" in nombres_cols:
                target_col = "langchain"
            
            COL_TRAMITES = client_t.get_collection(target_col) 
            print(f"  ✅ Trámites cargado correctamente (Colección: {target_col})")
        except Exception as e:
            print(f"  ⚠️ Error cargando trámites: {e}")
    else:
        print(f"  🚫 Ruta Trámites NO encontrada: {ruta_tramites}")

    # 5. Conectar ChromaDB SEGOB (CON DIAGNÓSTICO)
    COL_SEGOB = None
    if ruta_segob and ruta_segob.exists():
        try:
            print(f"  📂 Intentando cargar SEGOB desde: {ruta_segob}")
            client_s = chromadb.PersistentClient(path=str(ruta_segob))
            
            # --- CHISMOSO: ¿Cómo se llaman las colecciones aquí? ---
            nombres_cols_s = [c.name for c in client_s.list_collections()]
            print(f"  👀 Colecciones en SEGOB: {nombres_cols_s}")
            
            COL_SEGOB = client_s.get_or_create_collection("langchain")
            print("  🎖️ Biblioteca SEGOB cargada con éxito.")
        except Exception as e:
            print(f"  ⚠️ Error cargando SEGOB: {e}")
    else:
         print(f"  🚫 Ruta SEGOB NO encontrada: {ruta_segob}")

    # 6. Conectar ChromaDB FCE (principal-mx y excep-mx)
    COL_FCE = []
    rutas_fce = []
    if scope.lower() == 'mx':
        ruta_fce_principal = BASE_DIR / "procesado-mx" / "principal-mx" / "chroma_db_mx"
        ruta_fce_excep = BASE_DIR / "procesado-mx" / "excep-mx" / "chroma_db_excep_mx"
        rutas_fce = [ruta_fce_principal, ruta_fce_excep]
        for ruta_fce in rutas_fce:
            if ruta_fce.exists():
                try:
                    print(f"  📂 Intentando cargar FCE desde: {ruta_fce}")
                    client_fce = chromadb.PersistentClient(path=str(ruta_fce))
                    col_fce = client_fce.get_or_create_collection("langchain")
                    COL_FCE.append(col_fce)
                    print(f"  📚 Base de datos FCE cargada con éxito: {ruta_fce.name}")
                except Exception as e:
                    print(f"  ⚠️ Error cargando FCE: {e}")
            else:
                print(f"  🚫 Ruta FCE NO encontrada: {ruta_fce}")
        print(f"  🟣 Diagnóstico FCE: Se han cargado {len(COL_FCE)} colecciones (esperadas: 2). Rutas: {[str(r) for r in rutas_fce]}")

    return "Recursos Listos"

def chat_interface(mensaje, historial, modo, scope):
    # Asegurar carga de recursos si cambió el scope o es el inicio
    cargar_recursos(scope)
    
    if not COLS_LEGALES:
        respuesta = "❌ Error: No se cargaron bases de datos legales."
        historial.append([mensaje, respuesta])
        return "", historial

    respuesta = ""
    try:
        if modo == "Cita Precisa":
            respuesta = logica_a_cita_precisa(COLS_LEGALES, EMBEDDING_FUNCTION, mensaje)

        elif modo == "Razonamiento Jurídico":
            # 1. Creamos una lista combinada con las Leyes Generales
            fuentes_para_b = COLS_LEGALES.copy() 
            
            # 2. Si existe la base de SEGOB (y estamos en Scope MX), la agregamos
            if COL_SEGOB:
                fuentes_para_b.append(COL_SEGOB)
            
            # 3. La Lógica B ahora buscará en AMBOS lugares
            respuesta = logica_b_explicacion_juridica(fuentes_para_b, EMBEDDING_FUNCTION, mensaje)
        
        elif modo == "FCE":
            # Búsqueda en principal-mx y excep-mx (FCE)
            if COL_FCE and len(COL_FCE) > 0:
                respuesta = logica_b_explicacion_juridica(COL_FCE, EMBEDDING_FUNCTION, mensaje)
            else:
                respuesta = "❌ Las bases de datos FCE no están disponibles. Asegúrate de que 'principal-mx' y 'excep-mx' estén correctamente cargadas."
        
        elif modo == "Trámites (SEGOB)":
            respuesta = logica_c_avanzada(COL_SEGOB, COL_TRAMITES, EMBEDDING_FUNCTION, mensaje)
        else:
            respuesta = "⚠️ La base de datos de Trámites no está disponible en este Scope (solo 'MX'). Cambiando a explicación legal:\n\n" 
            respuesta += logica_b_explicacion_juridica(COLS_LEGALES, EMBEDDING_FUNCTION, mensaje)
        
    except Exception as e:
        respuesta = f"❌ Error interno: {str(e)}"

    # Agregar al historial en formato compatible con Gradio Chatbot (lista de tuplas)
    historial.append([mensaje, respuesta])
    return "", historial

# --- Tema Personalizado: Morado, Negro y Blanco ---
tema_personalizado = gr.themes.Soft(
    primary_hue="purple",
    secondary_hue="slate"
)

# --- Interfaz ---
with gr.Blocks(theme=tema_personalizado, css="""
    footer {visibility: hidden}
    .gradio-container {background-color: #FFFFFF;}
    h1 {color: #5B21B6; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);}
""") as demo:
    gr.Markdown("# 🚨⚖️ Juez Scharseinegger 2.0")
    
    with gr.Row():
        modo_radio = gr.Radio(
            ["Cita Precisa", "Razonamiento Jurídico", "FCE", "Trámites (SEGOB)"],
            value="Razonamiento Jurídico",
            label="Modo de Respuesta"
        )
        scope_radio = gr.Radio(["UNAM", "MX"], value="MX", label="Ámbito (Scope)")

    chatbot = gr.Chatbot(height=500)
    txt_mensaje = gr.Textbox(placeholder="Escribe tu consulta legal o de trámite...")

    txt_mensaje.submit(chat_interface, [txt_mensaje, chatbot, modo_radio, scope_radio], [txt_mensaje, chatbot])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 8080)))