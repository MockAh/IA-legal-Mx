# En lugar de google/cloud-sdk, usamos nuestra propia base ya preparada
FROM gcr.io/alma-juridica-aipp/protocolo01-base:latest

WORKDIR /app

# Solo copiamos el código, que no pesa nada
COPY *.py ./
COPY startup.sh ./
RUN dos2unix startup.sh && chmod +x startup.sh

# Limpiamos el script para evitar errores de formato (Windows/Linux)
RUN dos2unix startup.sh && chmod +x startup.sh

EXPOSE 8080

# Arrancamos con el script que sincroniza datos de GCS
ENTRYPOINT ["./startup.sh"]