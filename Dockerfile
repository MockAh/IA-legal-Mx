FROM gcr.io/alma-juridica-aipp/protocolo01-base:latest

WORKDIR /app

# Código y frontend
COPY *.py ./
COPY web/ ./web/
COPY startup.sh ./

# Normaliza saltos de línea (Windows/Linux) y da permisos
RUN dos2unix startup.sh && chmod +x startup.sh

EXPOSE 8080

ENTRYPOINT ["./startup.sh"]