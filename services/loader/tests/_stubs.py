"""Заглушки zeep и pydantic_settings: подставляются ТОЛЬКО если библиотек нет в окружении
(например, на машине, где тесты гоняют без pip install). Если библиотеки есть, используются настоящие."""
import os
import sys
import types


def install_env():
    for k, v in {"SPARK_URL": "http://localhost/spark", "SPARK_WSDL": "http://localhost/spark?wsdl",
                 "SPARK_LOGIN": "login", "SPARK_PASSWORD": "secret", "DATABASE_URL": "postgresql://x/y",
                 "RATE_LIMIT_RPS": "100000", "SPARK_NS": "urn:test:spark"}.items():
        os.environ.setdefault(k, v)


def install_stubs():
    try:
        import zeep  # noqa: F401
    except ImportError:
        class Fault(Exception):
            def __init__(self, message, code=None, actor=None, detail=None, subcodes=None):
                super().__init__(message)
                self.message, self.code, self.actor, self.detail, self.subcodes = message, code, actor, detail, subcodes

        class TransportError(Exception):
            def __init__(self, message=None, status_code=0, content=None):
                super().__init__(message)
                self.message, self.status_code, self.content = message, status_code, content

        class Transport:
            def __init__(self, **kw):
                pass

            def post(self, *a, **k):
                raise NotImplementedError

        zeep = types.ModuleType("zeep")
        zeep.Client = object
        mods = {
            "zeep": zeep,
            "zeep.exceptions": types.SimpleNamespace(Fault=Fault, TransportError=TransportError),
            "zeep.helpers": types.SimpleNamespace(serialize_object=lambda r, t=None: r),
            "zeep.transports": types.SimpleNamespace(Transport=Transport),
            "zeep.cache": types.SimpleNamespace(InMemoryCache=lambda: None),
        }
        sys.modules.update(mods)

    try:
        import pydantic_settings  # noqa: F401
    except ImportError:
        class BaseSettings:
            def __init__(self):
                for name, typ in getattr(type(self), "__annotations__", {}).items():
                    raw = os.environ.get(name.upper())
                    default = getattr(type(self), name, None)
                    if raw is None:
                        value = default
                    elif typ is bool:
                        value = raw.lower() in ("1", "true", "yes")
                    else:
                        value = typ(raw)
                    setattr(self, name, value)

        sys.modules["pydantic_settings"] = types.SimpleNamespace(BaseSettings=BaseSettings)
