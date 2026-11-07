"""Преобразование строк company_snapshot в JSON по контрактам (CompanyInfo, CompanyGroup).
Одна реализация на всех: Enrichment кладёт этот JSON в Redis, Client Info и Group Companies отдают его же."""
from datetime import date, datetime, timezone


def iso_utc(dt: datetime) -> str:
    """datetime -> '2026-09-23T06:15:00Z' (UTC, без долей секунды)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_company_info(row: dict) -> dict:
    """row — строка company_snapshot (ключи = имена колонок)."""
    reg = row["registration_date"]
    doc = {
        "inn": row["inn"],
        "ogrn": row["ogrn"],
        "kpp": row.get("kpp"),
        "shortName": row["short_name"],
        "status": row["status"],
        "registrationDate": reg.isoformat() if isinstance(reg, date) else str(reg),
        "legalAddress": row["legal_address"],
        "mainActivity": {"code": row["okved_code"], "name": row["okved_name"]},
        "groupId": row.get("group_id"),
        "isBankClient": bool(row["is_bank_client"]),
        "dataAsOf": iso_utc(row["data_as_of"]),
    }
    if row.get("full_name"):
        doc["fullName"] = row["full_name"]
    return doc


def to_company_group(inn: str, group_id: str | None, group_name: str | None,
                     rows: list[dict], only_bank_clients: bool, data_as_of: datetime) -> dict:
    """rows — все компании группы (включая запрошенную) из company_snapshot.
    Нет группы -> передай group_id=None, rows=[]."""
    members = [{
        "inn": r["inn"],
        "shortName": r["short_name"],
        "status": r["status"],
        "relation": r["group_relation"],
        "isBankClient": bool(r["is_bank_client"]),
    } for r in rows]
    if only_bank_clients:
        members = [m for m in members if m["isBankClient"]]
    return {
        "inn": inn,
        "groupId": group_id,
        "groupName": group_name,
        "members": members,
        "totalMembers": len(members),
        "dataAsOf": iso_utc(data_as_of),
    }
