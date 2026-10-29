FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/benchmark
WORKDIR /app
COPY app.py ./
COPY backend ./backend
COPY web ./web
RUN mkdir -p /home/benchmark/.ollama_benchmark && chown -R 65534:65534 /home/benchmark && chmod 700 /home/benchmark/.ollama_benchmark
USER 65534:65534
EXPOSE 8765
CMD ["python", "app.py", "--no-browser"]
