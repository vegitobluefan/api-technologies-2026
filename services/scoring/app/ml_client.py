"""gRPC-клиент ML Model. Stubs генерируются из proto/scoring.proto (в Docker — при сборке, локально — `python scripts/dev.py proto`)."""
import grpc

import scoring_pb2
import scoring_pb2_grpc
from platform_common.errors import ApiError

from .config import settings

_channel = grpc.insecure_channel(settings.ml_model_addr)   # соединение ленивое: сервис стартует и без ML Model
_stub = scoring_pb2_grpc.CompanyScoringStub(_channel)


def predict(inn: str, numeric: dict, categorical: dict):
    try:
        return _stub.Predict(
            scoring_pb2.PredictRequest(inn=inn, numeric=numeric, categorical=categorical),
            timeout=settings.ml_timeout_sec)
    except grpc.RpcError as e:
        code = e.code()
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise ApiError(504, "UPSTREAM_TIMEOUT", "ML Model не ответила вовремя") from None
        if code == grpc.StatusCode.INVALID_ARGUMENT:   # наш баг: не те признаки
            raise ApiError(500, "INTERNAL_ERROR", "Некорректный набор признаков для модели") from None
        raise ApiError(503, "SERVICE_UNAVAILABLE", "ML Model недоступна") from None
