FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app:/app/libs/common:/app/gen
COPY services/scoring/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY libs/common ./libs/common
COPY proto ./proto
RUN mkdir -p gen && python -m grpc_tools.protoc -I proto --python_out=gen --grpc_python_out=gen proto/scoring.proto
COPY services/scoring/app ./app
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002"]
