FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py ./
COPY backend ./backend
COPY web ./web
USER 65534:65534
EXPOSE 8765
CMD ["python", "app.py", "--no-browser"]
