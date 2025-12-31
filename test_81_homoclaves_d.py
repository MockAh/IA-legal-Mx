# test_rag_batch_homoclave.py
import csv
import time
import os
import sys
from pathlib import Path
from tqdm import tqdm
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

# --- Importamos la lógica del Chat ---
try:
    from rag_chat_segob_d import logica_c_avanzada
except ImportError:
    print("❌ ERROR: No se encontró 'rag_chat_segob_d.py'.")
    sys.exit(1)

load_dotenv()

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = "resultados_validacion_homoclaves_81.csv"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large-instruct"
COLLECTION_NAME = "langchain"

# Rutas Específicas
PATH_TRAMITES_DB = BASE_DIR / "procesado-mx" / "tramites-mx" / "chroma_db_tramites_mx"
PATHS_LEGALES_DB = [
    BASE_DIR / "procesado-mx" / "principal-mx" / "chroma_db_mx",
    BASE_DIR / "procesado-mx" / "excep-mx" / "chroma_db_excep_mx"
]

# ==========================================
# 2. DATOS DE PRUEBA (QUERYS vs HOMOCLAVES)
# ==========================================

LISTA_A_QUERYS = [
    "Mi iglesia quiere transmitir una misa especial por televisión, ¿qué permiso necesito para medios no impresos?",
    "¿Qué autorización requiero para vender productos con el escudo nacional en mi tienda?",
    "Nuestra escuela quiere poner su nombre en la bandera nacional, ¿esto se puede?",
    "¿Estoy autorizado para traducir el himno nacional mexicano a una lengua indígena?",
    "Necesito una prórroga de 10 años para el permiso de operación de mi centro de apuestas, ¿qué trámite necesito?",
    "¿Cómo registro mi agrupación religiosa para obtener personalidad jurídica como asociación?",
    "Como apoderado legal, ¿dónde doy el aviso de que abrimos un nuevo templo de nuestra asociación?",
    "Quiero tramitar mi CURP biométrica con fotografía y huellas, ¿en qué módulo lo hago?",
    "Necesito incrementar el número de boletos de un sorteo ya autorizado, ¿cómo pido la modificación?",
    "¿Qué permiso necesito para organizar peleas de gallos y lotería en una feria regional?",
    "¿Cómo puedo consultar e imprimir mi constancia de CURP en línea para un trámite bancario?",
    "¿Cómo informo sobre la venta de acciones de mi empresa permisionaria de juegos y sorteos?",
    "Gané un sorteo pero no me quieren entregar el premio, ¿cómo realizo la reclamación formal?",
    "Nuestra asociación civil de caballos quiere registrarse como órgano técnico de consulta, ¿cuáles son los pasos?",
    "¿Qué trámite debo seguir para obtener el permiso de cruce de apuestas en peleas de gallos temporales?",
    "Voy a realizar una rifa sin venta de boletos en mi empresa, ¿necesito el permiso general de sorteos?",
    "¿Cómo obtengo el permiso para realizar un sorteo con venta de boletos al público?",
    "Como operador de un casino, ¿dónde entrego mis estados financieros trimestrales firmados?",
    "¿Qué permiso se requiere para cantar el himno de otro país en un evento oficial en México?",
    "Me encuentro fuera de mi país por temor a la persecución, ¿cómo solicito el estatus de refugiado?",
    "Quiero cambiar mi trámite de refugio de un estado a otro de la república, ¿cómo pido el traslado?",
    "Soy refugiado y quiero traer a mis hijos a México para vivir conmigo, ¿cómo pido la reunificación?",
    "Necesito apoyo institucional para obtener mi documento de identidad y viaje como refugiado, ¿qué hago?",
    "¿Cómo solicito la recomendación de la COMAR para mi proceso de naturalización ante la SRE?",
    "Soy extranjero con protección complementaria y voy a viajar a mi país, ¿cómo doy el aviso de salida?",
    "¿Es obligatorio avisar a la Secretaría de Gobernación si cambio mi domicilio como refugiado?",
    "He decidido volver a mi país, ¿cómo presento la renuncia formal a mi condición de refugiado?",
    "¿Cómo me inscribo como representante de la sociedad civil en un mecanismo de participación ciudadana?",
    "Ya no puedo ser parte del consejo ciudadano, ¿cómo presento mi renuncia expresa al mecanismo?",
    "¿Qué requisitos debo cumplir para abrir y operar un hipódromo con cruce de apuestas?",
    "Nuestra organización quiere entrar al mecanismo de colaboración con el gobierno para políticas públicas, ¿cómo?",
    "Necesito la constancia de actividades cívicas de mi asociación para ser donataria ante el SAT, ¿dónde la pido?",
    "¿Cómo autorizo un evento promocional con sorteos en mi sitio web de apuestas autorizado?",
    "Necesito actualizar la fianza de los premios no pagados de mi permiso de sorteos, ¿qué trámite es?",
    "¿Cómo solicito una fecha de inspección adicional para un sorteo que voy a realizar?",
    "¿Qué permiso necesito para organizar carreras de caballos con apuestas en un escenario temporal?",
    "Quiero realizar un sorteo de raspadito o instantáneo, ¿qué permiso general de sorteos me corresponde?",
    "Tengo una queja por la mala atención en mi trámite de juegos y sorteos, ¿cómo la presento?",
    "¿Dónde entregan los permisionarios de casinos su reporte mensual de pago de aprovechamientos?",
    "Nuestra pista de carreras quiere iniciar su temporada anual, ¿cómo solicitamos la acreditación oficial?",
    "Tenemos un conflicto legal con otra asociación religiosa, ¿podemos resolverlo mediante arbitraje?",
    "¿Cómo pedimos la designación de un amigable componedor para resolver desavenencias en nuestra iglesia?",
    "¿Cómo inscribo una propiedad que mi asociación religiosa adquirió por herencia o sucesión?",
    "Nuestra agrupación religiosa abrió un templo y queremos acreditar nuestra antigüedad, ¿cómo avisamos?",
    "¿Cómo puedo apostillar mis documentos nacionales para que tengan validez legal en el extranjero?",
    "Necesito legalizar las firmas de mi título para un país que no está en el convenio de la Haya, ¿qué hago?",
    "Cambiamos el domicilio y los estatutos de nuestra asociación religiosa, ¿cómo pido la toma de nota?",
    "¿Cómo obtengo la opinión favorable para que un ministro de culto extranjero tramite su visa?",
    "Queremos incorporar un nuevo inmueble al patrimonio de nuestra asociación religiosa, ¿cómo se hace?",
    "Soy responsable de un religioso extranjero y su documento migratorio va a vencer, ¿cómo lo renuevo?",
    "¿Qué oficio necesito pedir para que un ministro de culto extranjero canjee su FMM por una credencial?",
    "¿Qué permiso general se requiere para realizar adjudicaciones por sorteo en sistemas de comercio?",
    "Tengo dudas sobre los requisitos técnicos para un permiso de juegos, ¿puedo pedir una consulta oficial?",
    "Ya entregamos todos los premios de la rifa y queremos liberar la garantía, ¿cómo pido el finiquito?",
    "Como concesionario de radio, quiero transmitir un material grabado, ¿cómo pido la autorización?",
    "¿Cómo puedo solicitar la publicación de un documento legal en el Diario Oficial de la Federación?",
    "¿Dónde puedo comprar ejemplares impresos del Diario Oficial de la Federación del año 2015?",
    "¿Necesito permiso para usar el himno nacional en una obra de teatro o película comercial?",
    "Mi estación de radio va a transmitir programas en un idioma que no es lengua nacional, ¿qué trámite hago?",
    "¿Cómo solicito el permiso para transmitir en mi canal un programa grabado directamente en el extranjero?",
    "¿Qué autorización necesito para promocionar y transmitir concursos en mi estación de radio?",
    "Soy productor de cine nacional, ¿dónde debo entregar mi informe anual de producción filmada?",
    "Soy dueño de una sala de cine, ¿cómo presento mi informe anual de películas exhibidas?",
    "Trabajo en una distribuidora de películas, ¿dónde valido mi informe anual de operaciones en México?",
    "¿Qué trámite debo hacer para clasificar una película que voy a vender o rentar en DVD?",
    "Necesito copias certificadas de los estatutos que están en el expediente de mi asociación religiosa, ¿cómo?",
    "¿Cómo solicito una certificación que acredite quiénes son los representantes de mi asociación religiosa?",
    "Quiero estrenar una película en cines, ¿quién me da la autorización y clasificación comercial?",
    "Necesito un documento que acredite que soy ministro de culto o una constancia de laicidad, ¿dónde?",
    "¿Cómo obtengo permiso para realizar un homenaje o grabar un video en la Rotonda de las Personas Ilustres?",
    "Nuestra escuela requiere asesoría sobre el protocolo de incineración y honores a la bandera, ¿a quién pido?",
    "¿Cómo solicito que personal de gobernación supervise la legalidad de un concurso en mi canal de TV?",
    "Fui repatriado a México y no tengo identificación, ¿cómo tramito mi CURP temporal con fotografía?",
    "Quiero tramitar la CURP de mi hijo recién nacido mexicano, ¿cuáles son los pasos ante el RENAPO?",
    "Soy extranjero solicitante de refugio en México, ¿cómo me asignan mi clave de CURP?",
    "Me admitieron el trámite de asilo político, ¿cómo obtengo mi CURP temporal de 180 días?",
    "Soy residente permanente extranjero en México, ¿cómo solicito que el INM me asigne mi CURP?",
    "Tengo una estancia de visitante regular en México, ¿dónde tramito mi CURP temporal de 365 días?",
    "Ya tengo mi carta de naturalización mexicana, ¿cómo actualizo mi CURP para que no sea de extranjero?",
    "Necesito una certificación oficial de una copia simple de un Diario Oficial antiguo, ¿dónde se hace?",
    "Estoy en prisión por un delito menor bajo condiciones de pobreza, ¿cómo envío mi solicitud de amnistía?"
]

# Lista sincronizada de Homoclaves (Extraída de tu metadata.json)
LISTA_TARGET_HOMOCLAVES = [
    "sgob-04-003", "segob-2019-069-037-a", "sgob-01-013", "sgob-01-011-a", "segob-2023-069-002-a",
    "sgob-04-007", "sgob-04-010-a", "segob-2025-069-010-a", "sgob-01-016", "sgob-01-026",
    "sgob-05-002", "sgob-01-036", "sgob-01-019", "sgob-01-037", "sgob-01-015",
    "sgob-01-009-a", "sgob-01-009-b", "sgob-01-034", "sgob-01-014", "sgob-06-001",
    "sgob-06-002", "sgob-06-003", "sgob-06-004", "sgob-06-005", "sgob-06-006",
    "sgob-06-007", "sgob-06-008", "segob-09-005", "segob-09-006", "sgob-01-038",
    "sgob-07-001", "sgob-07-002", "sgob-01-029", "sgob-01-033", "sgob-01-017",
    "sgob-01-015-c", "sgob-01-009-c", "sgob-01-018", "sgob-01-035", "sgob-01-032",
    "sgob-04-005", "sgob-04-006", "sgob-04-009-b", "sgob-04-010-b", "sgob-01-007",
    "sgob-01-006", "sgob-04-008", "sgob-04-016", "sgob-04-009-a", "segob-2025-069-009-a",
    "segob-2025-069-008-a", "sgob-01-009-d", "sgob-01-020", "sgob-01-030", "sgob-03-001-c",
    "sgob-01-001", "sgob-01-004", "sgob-01-011-b", "sgob-03-001-d", "sgob-03-001-e",
    "sgob-03-001-a", "sgob-03-014-a", "sgob-03-014-c", "sgob-03-014-b", "sgob-03-006-b",
    "segob-2019-069-036-a", "segob-2019-069-035-a", "sgob-03-006-a", "sgob-04-013", "segob-2025-069-007-a",
    "segob-2025-069-006-a", "sgob-03-001-b", "segob-2021-069-004-a", "segob-2021-069-003-a", "segob-2021-069-007-a",
    "segob-2021-069-006-a", "segob-2021-069-009-a", "segob-2021-069-008-a", "segob-2021-069-005-a", "sgob-01-008",
    "segob-2021-069-002-a"
]

# ==========================================
# 3. FUNCIONES DE CARGA Y EJECUCIÓN
# ==========================================

def cargar_recursos_test():
    """Carga local de recursos."""
    print(f"🧠 Cargando modelo: {EMBEDDING_MODEL_NAME}...")
    try:
        embedding_function = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME, 
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': True}
        )
    except Exception as e:
        print(f"❌ Error modelo: {e}")
        return None, [], None

    cols_legales = []
    col_tramites = None

    # Cargar DBs Legales
    print("📚 Cargando Bases Legales...")
    for p in PATHS_LEGALES_DB:
        if os.path.exists(p):
            try:
                client = chromadb.PersistentClient(path=str(p))
                col = client.get_or_create_collection(name=COLLECTION_NAME)
                cols_legales.append(col)
            except Exception: pass

    # Cargar DB Trámites
    print(f"🗂️ Cargando Base Trámites: {PATH_TRAMITES_DB.name}")
    if os.path.exists(PATH_TRAMITES_DB):
        try:
            client_t = chromadb.PersistentClient(path=str(PATH_TRAMITES_DB))

            # CAMBIO AQUÍ: Usamos el nombre real detectado en tu terminal
            NOMBRE_COL_TRAMITES = "tramites_gob_mx"

            col_tramites = client_t.get_or_create_collection(name=NOMBRE_COL_TRAMITES)
            print("   ✅ Trámites cargados.")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print(f"   ❌ Ruta no existe: {PATH_TRAMITES_DB}")

    return embedding_function, cols_legales, col_tramites

def main():
    print("\n--- 🧪 TEST DE VALIDACIÓN POR HOMOCLAVES ---")
    
    # Validar integridad
    if len(LISTA_A_QUERYS) != len(LISTA_TARGET_HOMOCLAVES):
        print(f"⚠️ ADVERTENCIA: Listas de diferente longitud. Se usará el mínimo común.")

    emb_fn, cols_legales, col_tramites = cargar_recursos_test()
    if not col_tramites: return

    # CSV Headers
    headers = ["id", "query", "homoclave_esperada", "resultado", "tiempo_seg", "respuesta_bot"]
    
    with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"📝 Guardando en: {OUTPUT_CSV}")
    print("\n⚡ EJECUTANDO 81 CONSULTAS...\n")

    aciertos = 0
    errores_sys = 0
    total = min(len(LISTA_A_QUERYS), len(LISTA_TARGET_HOMOCLAVES))

    # Zip para iterar pares
    pairs = list(zip(LISTA_A_QUERYS, LISTA_TARGET_HOMOCLAVES))

    for i, (query, homoclave) in tqdm(enumerate(pairs), total=total, unit="test"):
        start = time.time()
        estado = "FALSE"
        respuesta = ""
        
        try:
            # Ejecutar RAG
            respuesta = logica_c_avanzada(cols_legales, col_tramites, emb_fn, query)
            
            # Validación Estricta
            if homoclave.lower() in respuesta.lower():
                estado = "TRUE"
                aciertos += 1
            else:
                estado = "FALSE"

        except Exception as e:
            estado = "ERROR"
            respuesta = str(e)
            errores_sys += 1
        
        duracion = round(time.time() - start, 2)

        # Guardar
        fila = [i+1, query, homoclave, estado, duracion, respuesta.replace("\n", " | ")]
        with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(fila)

    print("\n" + "="*40)
    print("📊 RESULTADOS FINALES")
    print("="*40)
    print(f"✅ Aciertos (Homoclave Citada): {aciertos}/{total}")
    print(f"❌ Fallos: {total - aciertos - errores_sys}")
    print(f"📈 Precisión: {(aciertos/total)*100:.2f}%")
    print(f"📂 Archivo: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
