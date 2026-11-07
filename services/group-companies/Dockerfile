FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app:/app/libs/common
COPY services/group-companies/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY libs/common ./libs/common
COPY services/group-companies/app ./app
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8005"]
