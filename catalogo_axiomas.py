import os
from pathlib import Path

# Configuración de rutas según tu estructura
BASE_DIR = Path(__file__).resolve().parent
# Ahora apuntamos directamente a la médula del proyecto
PROCESADO_DIR = BASE_DIR / "Axiomas" / "legislacion-mx"

# 1. Definición de Headliners Principales (Categorías Nivel 1)
HEADLINERS = {
    "FCE": "✒️ Fondo de Cultura Económica",
    "Transparencia": "🛡️ Transparencia y Acceso a la Información",
    "Tres_Poderes": "🏛️ Los Tres Poderes",
    "basic": "⚖️ Legislación Básica",
    "segob": "🧱 Secretaría de Gobernación (SEGOB)"
}

# 2. Mapeo de subcarpetas (Nivel 2 o inferior)
SUB_NOMBRES = {
    "1_comercializacion": "Comercialización",
    "2_editorial": "Área Editorial",
    "3_mercadotecnia": "Mercadotecnia",
    "sustantiva": "Normatividad Sustantiva",
    "General-Juridica": "General Jurídica",
    "estatuto_organico": "Estatuto Orgánico"
}

TIPOS_PROCESAMIENTO = {
    "legal": "[legal]",
    "semantic": "[semántico]",
    "excep": "[excepción]",
}

def _nombre_legible(archivo: Path) -> str:
    """Parsea el nombre del archivo para la interfaz."""
    nombre_raw = archivo.stem
    partes = nombre_raw.split("_")
    
    if len(partes) < 3:
        return f"📄 {nombre_raw.replace('-', ' ')}"

    fecha = partes[0]
    tipo_key = partes[-1].lower()
    # Extraer el título (lo que está entre la fecha/clave y el tipo)
    titulo_raw = " ".join(partes[2:-1]) if len(partes) > 3 else partes[1]
    
    titulo = titulo_raw.replace("-", " ").title()
    etiqueta = TIPOS_PROCESAMIENTO.get(tipo_key, "📄")

    return f"{etiqueta} {titulo} *({fecha})*"

def generar_catalogo() -> str:
    """Genera el catálogo Markdown respetando la jerarquía solicitada."""
    if not PROCESADO_DIR.exists():
        return f"⚠️ No se encontró la ruta: `{PROCESADO_DIR}`"

    lineas = [
        "## 🏛️ Acervo Documental del Juez Scharseinegger\n",
        "Selecciona un documento para referencia o consulta su estado actual en la base de datos.\n",
        "---"
    ]

    # Iteramos sobre los headliners en el orden definido
    for carpeta_id, titulo_headliner in HEADLINERS.items():
        ruta_categoria = PROCESADO_DIR / carpeta_id
        
        if not ruta_categoria.exists():
            continue

        # Título Principal (H2)
        lineas.append(f"\n## {titulo_headliner}")
        
        # Escaneamos la carpeta del headliner
        # Usamos rglob para capturar archivos en la raíz del headliner y en subcarpetas
        archivos_encontrados = False
        
        # Agrupamos por subcarpeta para mantener el orden
        for raiz, dirs, archivos in sorted(os.walk(ruta_categoria)):
            # Filtrar solo .docx válidos
            docs = sorted([f for f in archivos if f.endswith(".docx") and "Zone.Identifier" not in f])
            
            if not docs:
                continue
            
            archivos_encontrados = True
            ruta_actual = Path(raiz)
            
            # Si estamos en una subcarpeta (no en la raíz del headliner), ponemos un subtítulo
            if ruta_actual != ruta_categoria:
                nombre_sub = SUB_NOMBRES.get(ruta_actual.name, ruta_actual.name.replace("_", " ").title())
                lineas.append(f"\n### 📁 {nombre_sub}")
            
            # Listar los documentos
            for doc in docs:
                lineas.append(f"- {_nombre_legible(Path(doc))}")

        if not archivos_encontrados:
            lineas.append("_No hay documentos procesados en esta sección._")

    return "\n".join(lineas)

if __name__ == "__main__":
    print(generar_catalogo())