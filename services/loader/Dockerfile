FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY services/loader/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/loader/app ./app
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8003"]
