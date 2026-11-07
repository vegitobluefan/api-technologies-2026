"""Доступ к данным Client Info (владелец: Савелий)."""


def get_company_info(inn: str) -> dict | None:
    """cache-aside:
      1) Redis GET company:{inn} -> JSON (уже в формате CompanyInfo) -> вернуть;
      2) промах: SELECT * FROM company_snapshot WHERE inn=%s -> platform_common.mapping.to_company_info(row);
      3) SET company:{inn} с TTL settings.cache_ttl_seconds, вернуть.
    Нет компании -> None. Redis недоступен -> идти в БД, а не падать."""
    raise NotImplementedError
