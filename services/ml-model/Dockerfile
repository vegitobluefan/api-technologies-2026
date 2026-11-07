FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app:/app/gen
COPY services/ml-model/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto ./proto
RUN mkdir -p gen && python -m grpc_tools.protoc -I proto --python_out=gen --grpc_python_out=gen proto/scoring.proto
COPY services/ml-model/app ./app
CMD ["python","-m","app.server"]
