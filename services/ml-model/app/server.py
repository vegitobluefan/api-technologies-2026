"""gRPC ML Model: грузит .dill, строит DataFrame по meta["features"], отдаёт predict_proba[:,1]."""
import logging, os
from concurrent import futures

import dill
import grpc
import pandas as pd

import scoring_pb2, scoring_pb2_grpc  # генерируются из proto/ при сборке
from .model_store import ensure_model

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ml-model")

class Scoring(scoring_pb2_grpc.CompanyScoringServicer):
    def __init__(self):
        path = ensure_model(
            os.getenv("MODEL_PATH", "/models/company-scoring-v1.dill"),
            url=os.getenv("MODEL_URL", ""),
            token=os.getenv("MODEL_TOKEN", ""),
            sha256=os.getenv("MODEL_SHA256", ""),
        )
        with open(path, "rb") as f:
            art = dill.load(f)
        self.model = art["model"]
        meta = art.get("meta", {})
        if "features" not in meta:
            raise RuntimeError("В meta модели нет 'features': проверь файл и meta['feature_doc']")
        self.features = list(meta["features"])
        self.version = str(meta.get("version", "company-scoring-v1"))
        log.info("модель готова, признаки: %s", self.features)

    def GetInfo(self, request, context):
        return scoring_pb2.ModelInfo(features=self.features, model_version=self.version)

    def Predict(self, request, context):
        row, missing = {}, []
        for name in self.features:
            if name in request.numeric:
                row[name] = request.numeric[name]
            elif name in request.categorical:
                row[name] = request.categorical[name]
            else:
                missing.append(name)
        if missing:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"missing features: {missing}")
        df = pd.DataFrame([row], columns=self.features)
        score = float(self.model.predict_proba(df)[0, 1])
        return scoring_pb2.PredictResponse(score=score, model_version=self.version)

def serve():
    servicer = Scoring()  # порт открываем только после загрузки модели -> healthcheck честный
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    scoring_pb2_grpc.add_CompanyScoringServicer_to_server(servicer, server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("gRPC слушает :50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
