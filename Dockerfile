# Dockerfile — Imagen ligera de protocolo01-v2 (código + front)
# Parte de la pesada (dependencias + modelo). Se reconstruye en cada cambio
# de código con cloudbuild.yaml.
ARG IMAGEN_PESADA
FROM ${IMAGEN_PESADA}

WORKDIR /app

# Solo lo que corre en producción (F3-02). Sin scripts de ingesta, pruebas ni prototipos.
COPY main.py recursos.py catalogo_datos.py logica_a.py logica_b.py logica_c.py utils_rag.py ./
COPY web/ ./web/
COPY startup.sh ./

# Saltos de línea de Windows → Linux, y permiso de ejecución
RUN sed -i 's/\r$//' startup.sh && chmod +x startup.sh

ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["./startup.sh"]
