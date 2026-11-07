"""SOAP-клиент СПАРК (zeep). TODO: изучить WSDL: python -m zeep <wsdl>.

- authenticate() при старте, SessionId в SOAP-заголовке
- перелогин на SESSION_EXPIRED (один повтор)
- RateLimiter перед каждым вызовом, ретраи с backoff на RATE_LIMIT / Fault
- таймаут (zeep Transport(timeout=...)), заголовок X-Mock-Scenario
"""
from .config import settings
from .rate_limiter import RateLimiter

limiter = RateLimiter(settings.rate_limit_rps)

class SparkClient:
    def __init__(self):
        self.session_id = None
        # TODO: self.client = zeep.Client(settings.spark_wsdl, transport=...)

    def authenticate(self): ...
    def get_company_list(self, page=None): ...
    def get_company_short_report(self, inn: str): ...
    def get_company_group(self, inn: str): ...
    def get_changed_companies(self, since): ...
