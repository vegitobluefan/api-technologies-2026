"""Забирает .dill при старте: уже лежит в /models -> используем; иначе скачиваем по MODEL_URL."""
import hashlib, logging, os, time, urllib.request

log = logging.getLogger("model_store")

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _check(path: str, sha256: str):
    if sha256 and _sha256(path).lower() != sha256.lower():
        raise RuntimeError(f"SHA256 модели не совпал: {path}")

def ensure_model(path: str, url: str = "", token: str = "", sha256: str = "", retries: int = 6) -> str:
    if os.path.exists(path):
        _check(path, sha256)
        log.info("модель найдена: %s", path)
        return path
    if not url:
        raise RuntimeError(
            f"Модель не найдена: {path}. Положи файл в ./models/ или задай MODEL_URL в .env")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url)
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            _check(tmp, sha256)
            os.replace(tmp, path)
            log.info("модель скачана: %s", path)
            return path
        except Exception as e:  # сеть/хэш: ждём и пробуем снова
            log.warning("скачивание модели, попытка %d/%d: %s", attempt, retries, e)
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError("Не удалось скачать модель по MODEL_URL")
