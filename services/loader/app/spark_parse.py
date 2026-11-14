"""Разбор ответов СПАРК в словари для SCD2 (владелец: Данияр).

Здесь нет zeep и БД, поэтому модуль легко тестировать.
zeep отдаёт ответ как объекты, soap_client превращает их в обычные dict/list
(zeep.helpers.serialize_object), а дальше работают функции ниже.

Имена полей ищем без учёта регистра и подчёркиваний: "Inn", "INN" и "inn" это один ключ.
Запись компании ищем на любой глубине вложенности (find_record), поэтому обёртки вида
{"ShortReport": {"Company": {...}, "Meta": {...}}} не мешают.
Если в WSDL поле называется иначе, достаточно добавить имя в нужный вызов pick(...).
Если обязательного поля нет, check_row громко падает: пустые строки в БД молча не попадут.
"""
from collections import deque
from datetime import date, datetime, timezone

from .spark_errors import MappingError

# по этим ключам узнаём саму запись компании (общий "Status" или "Name" в обёртке запись не определяют)
IDENTITY_KEYS = ("Inn", "Ogrn", "ShortName", "FullName")
REQUIRED_FIELDS = ("short_name", "status", "registration_date")


def _norm(key) -> str:
    return str(key).lower().replace("_", "")


def pick(d, *names):
    """Первое непустое значение из словаря d по одному из имён."""
    if not isinstance(d, dict):
        return None
    by_norm = {_norm(k): v for k, v in d.items()}
    for name in names:
        value = by_norm.get(_norm(name))
        if value not in (None, ""):
            return value
    return None


def find_record(obj, *keys):
    """Ближайший к корню словарь, где есть хотя бы один из ключей (поиск вширь, заходим и в списки)."""
    wanted = {_norm(k) for k in keys}
    queue = deque([obj])
    while queue:
        cur = queue.popleft()
        if isinstance(cur, dict):
            if any(_norm(k) in wanted and v not in (None, "") for k, v in cur.items()):
                return cur
            queue.extend(v for v in cur.values() if isinstance(v, (dict, list)))
        elif isinstance(cur, list):
            queue.extend(x for x in cur if isinstance(x, (dict, list)))
    return None


def unwrap(d, *keys):
    """Оставлено для совместимости: спускается в единственный вложенный словарь, пока не встретит один из keys."""
    while isinstance(d, dict) and pick(d, *keys) is None:
        inner = [v for v in d.values() if isinstance(v, dict)]
        if len(inner) != 1:
            break
        d = inner[0]
    return d


def _lists(obj):
    """Все списки внутри словаря, вширь: сначала лежащие ближе к корню."""
    queue = deque([obj])
    while queue:
        cur = queue.popleft()
        if isinstance(cur, dict):
            for v in cur.values():
                if isinstance(v, list):
                    yield v
                elif isinstance(v, dict):
                    queue.append(v)


def inn_of(item):
    """ИНН из элемента списка: строка "7700000001", число или словарь {"Inn": "7700000001", ...} (в любой обёртке)."""
    if isinstance(item, dict):
        rec = find_record(item, "Inn")
        value = pick(rec, "Inn") if rec else None
    else:
        value = item
    return str(value).strip() if value not in (None, "") else None


def _is_inn(value) -> bool:
    s = str(value or "").strip()
    return s.isdigit() and len(s) in (10, 12)


def find_list(obj) -> list:
    """Список записей из ответа: [..], {"Companies": [..]}, {"Companies": {"Company": [..]}}.
    Если в ответе несколько списков, берём тот, где лежат ИНН (а не теги, ошибки и т.п.)."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if not isinstance(obj, dict):
        return []
    first = None
    for items in _lists(obj):
        if first is None:
            first = items
        if any(_is_inn(inn_of(i)) for i in items):
            return items
    return first or []


def to_date(value):
    """xsd:date от zeep уже date; строку '2012-03-15' или '2012-03-15T00:00:00' превращаем в date."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def to_datetime(value):
    """'2026-10-30 20:53:39+00:00' (или datetime от zeep) -> datetime с часовым поясом; без пояса считаем UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def actual_date_of(report):
    """ActualDate из краткого отчёта: с этого момента состояние компании актуально (кандидат на valid_from версии SCD2)."""
    rec = find_record(report, *IDENTITY_KEYS) or {}
    try:
        return to_datetime(pick(rec, "ActualDate", "ChangedAt", "UpdatedAt"))
    except ValueError:
        return None


def revision_of(report):
    rec = find_record(report, *IDENTITY_KEYS) or {}
    value = pick(rec, "Revision")
    return int(value) if value not in (None, "") and str(value).isdigit() else None


def has_group(report) -> bool:
    """В отчёте есть GroupId: только тогда имеет смысл звать GetCompanyGroup."""
    rec = find_record(report, *IDENTITY_KEYS) or {}
    return pick(rec, "GroupId") is not None


def _text(value):
    return str(value).strip() if value not in (None, "") else None


def _relation_in_members(group, inn):
    """Если связь с группой записана не у группы, а у участников: ищем участника с нашим ИНН."""
    for items in _lists(group):
        for item in items:
            if isinstance(item, dict) and inn_of(item) == inn:
                rel = pick(item, "Relation", "RelationType", "Role")
                if rel:
                    return rel
    return None


def to_company_row(report, group=None, inn=None) -> dict:
    """Краткий отчёт + данные о группе -> словарь с ключами = колонкам company_versions
    (без id, attrs_hash, valid_from, valid_to, is_current: их ставит scd2.upsert_company).
    Признак isBankClient сюда не входит: его добавляет Enrichment.
    inn: ИНН, по которому делали запрос (подстраховка, если в ответе его нет)."""
    r = find_record(report, *IDENTITY_KEYS) or (report if isinstance(report, dict) else {})

    # ОКВЭД бывает вложенным объектом {"Code": "62.01", "Name": "..."} или двумя плоскими полями
    okved = pick(r, "MainActivity", "Okved", "MainOkved")
    if isinstance(okved, dict):
        okved_code, okved_name = pick(okved, "Code"), pick(okved, "Name")
    else:
        okved_code = okved or pick(r, "OkvedCode", "MainActivityCode")
        okved_name = pick(r, "OkvedName", "MainActivityName")

    status = pick(r, "Status", "State")
    if isinstance(status, dict):          # {"Code": "ACTIVE", "Name": "Действующая"}
        status = pick(status, "Code", "Value")

    director = pick(r, "Director", "Leader", "Manager", "Head")
    if isinstance(director, dict):        # {"Fio": "...", "Position": "..."}
        director = pick(director, "Fio", "Name", "FullName")

    row_inn = _text(pick(r, "Inn")) or inn
    g = find_record(group, "GroupId", "GroupName") or {}
    relation = pick(g, "Relation", "Role", "GroupRelation")
    if relation is None and group and row_inn:
        relation = _relation_in_members(group, row_inn)

    return {
        "inn": row_inn,
        "ogrn": _text(pick(r, "Ogrn")),
        "kpp": _text(pick(r, "Kpp")),
        "short_name": _text(pick(r, "ShortName", "ShortNameRus", "Name")),
        "full_name": _text(pick(r, "FullName", "FullNameRus")),
        "status": _text(status).upper() if status else None,
        "registration_date": to_date(pick(r, "RegistrationDate", "RegDate", "DateFirstReg")),
        "legal_address": _text(pick(r, "LegalAddress", "Address")),
        "director": _text(director),
        "okved_code": _text(okved_code),
        "okved_name": _text(okved_name),
        "group_id": _text(pick(g, "GroupId", "Id")) or _text(pick(r, "GroupId")),   # в отчёте тоже есть GroupId
        "group_relation": _text(relation).upper() if relation else None,
    }


def check_row(row: dict, report=None) -> None:
    """Обязательные поля должны быть. Иначе MappingError: загрузка падает громко, а не пишет пустые версии."""
    missing = [f for f in REQUIRED_FIELDS if row.get(f) in (None, "")]
    if missing:
        keys = list(report)[:15] if isinstance(report, dict) else type(report).__name__
        raise MappingError(f"ИНН {row.get('inn')}: в ответе СПАРК нет {missing}; верхние ключи отчёта: {keys}")


def group_name_of(group):
    g = find_record(group, "GroupId", "GroupName") or {}
    return _text(pick(g, "GroupName", "Name"))
