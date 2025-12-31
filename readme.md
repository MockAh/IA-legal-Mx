# ⚖️ Sistema RAG Legal - Juez Scharseinegger 2.0

Sistema de recuperación y generación aumentada (RAG) especializado en legislación mexicana (UNAM, SEGOB, FCE) y trámites gubernamentales.

## 🚀 Instalación y Configuración del Modelo

Este proyecto utiliza un modelo de embeddings local para garantizar privacidad y velocidad. **No se incluye el modelo binario en el repositorio** por su peso, pero se provee el script para autogenerarlo.

### 1. Clonar y preparar entorno
```bash
git clone <URL_DE_TU_REPO>
cd ia-legal-rag
python -m venv venv
source venv/bin/activate  # O en Windows: venv\Scripts\activate
pip install -r requirements-local.txt

### 2. ⚠️ PASO CRÍTICO: Descargar el Modelo Local
El sistema requiere el modelo intfloat/multilingual-e5-large-instruct. Ejecuta este script para descargarlo y guardarlo automáticamente en la carpeta ./modelo_e5:

Bash

python descargar_modelo.py
Este script descargará los tensores necesarios para que el sistema funcione offline.

### 3. Configurar Variables de Entorno
Crea un archivo .env basado en tus proveedores de LLM (DeepSeek, OpenAI, etc.):

DEEPSEEK_API_KEY=tu_clave_aqui

### 4. Indexación de Documentos (Base de Conocimiento)
Para procesar nuevos documentos (PDF/DOCX) y generar la base de datos vectorial (chroma_db), ejecuta los indexadores según el ámbito:

SEGOB/Trámites: python script_embeddings_eva_SEGOB.py

Legislación General: python script_embeddings_eva_5_5.py

### 5. Ejecutar la Interfaz
Bash

python app.py
El sistema detectará si estás en entorno local o nube y aplicará los parches de SQLite necesarios.