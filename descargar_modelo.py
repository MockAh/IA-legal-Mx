from sentence_transformers import SentenceTransformer
print("⏳ Descargando modelo... esto puede tardar unos minutos...")
# Descargamos el modelo exacto que usa tu app
model = SentenceTransformer('intfloat/multilingual-e5-large-instruct')
# Lo guardamos en una carpeta local llamada 'modelo_e5'
model.save('./modelo_e5')
print("✅ ¡Modelo descargado y guardado en la carpeta './modelo_e5'!")