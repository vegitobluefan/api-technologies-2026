#!/usr/bin/env python3
"""Проверка настоящего мока СПАРК (в БД ничего не пишет).

    pip install zeep requests
    python scripts/spark_probe.py              # ИНН возьмёт из списка компаний
    python scripts/spark_probe.py 5030357423

Что делает:
  1. печатает операции и параметры из WSDL (сверить с константами в services/loader/app/soap_client.py);
  2. Authenticate, затем список компаний, краткий отчёт, группа, изменения за сутки, неизвестный ИНН;
  3. прогоняет ответы через наш разбор (spark_parse) и показывает, какие поля нашлись, а каких нет.
SPARK_WSDL, SPARK_LOGIN, SPARK_PASSWORD берутся из окружения или из .env. Пароль и SessionId не печатаются.
Вывод можно целиком показывать команде.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from lxml import etree
from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.helpers import serialize_object
from zeep.transports import Transport

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "loader"))
from app import spark_parse as sp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def env(name, default=None):
    if os.environ.get(name):
        return os.environ[name]
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    if default is not None:
        return default
    sys.exit(f"нет {name}: задай переменную окружения или впиши в .env")


def show(obj, limit=2500):
    text = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    return text if len(text) <= limit else text[:limit] + "\n... (обрезано)"


def fault_text(f):
    code = ""
    if getattr(f, "detail", None) is not None:
        for el in f.detail.iter():
            if isinstance(el.tag, str) and el.tag.split("}")[-1] == "ErrorCode":
                code = (el.text or "").strip()
    return f"SOAP Fault code={code or '?'} message={getattr(f, 'message', '')}"


def main():
    wsdl, login, password = env("SPARK_WSDL"), env("SPARK_LOGIN"), env("SPARK_PASSWORD")
    client = Client(wsdl, transport=Transport(session=requests.Session(), timeout=20, operation_timeout=20),
                    settings=Settings(strict=False, xml_huge_tree=True))
    bindings = client.wsdl.bindings
    binding = next((n for n, b in bindings.items() if type(b).__name__ == "Soap11Binding"), next(iter(bindings)))
    ns = env("SPARK_NS", binding[1:binding.index("}")])
    address = env("SPARK_URL", "")
    service = client.create_service(binding, address) if address else client.service

    print("=" * 70, "\nОПЕРАЦИИ ИЗ WSDL (сверь с константами OP_* и P_* в soap_client.py)\n" + "=" * 70)
    for name, op in bindings[binding]._operations.items():
        try:
            print(f"  {name}: {op.input.signature()}")
        except Exception as e:
            print(f"  {name}: (сигнатура недоступна: {e})")
    print(f"\nnamespace SOAP-заголовка: {ns}")

    print("\n" + "=" * 70, "\nAuthenticate\n" + "=" * 70)
    try:
        res = serialize_object(service.Authenticate(Login=login, Password=password), dict)
    except Fault as f:
        sys.exit(fault_text(f))
    sid = res if isinstance(res, str) else sp.pick(res, "SessionId", "Session")
    print("SessionId получен:", bool(sid), "| тип ответа:", type(res).__name__)

    def header():
        el = etree.Element(etree.QName(ns, "SessionId"))
        el.text = str(sid)
        return [el]

    def call(title, op, **params):
        time.sleep(0.25)    # лимит 5 запросов/с
        print("\n" + "-" * 70 + f"\n{title}: {op}({', '.join(f'{k}={v!r}' for k, v in params.items())})\n" + "-" * 70)
        try:
            out = serialize_object(service[op](**params, _soapheaders=header()), dict)
            print(show(out))
            return out
        except Fault as f:
            print(fault_text(f))
        except TypeError as e:
            print(f"TypeError (скорее всего неверное имя параметра, сверь с сигнатурой выше): {e}")
        except Exception as e:
            print(f"{type(e).__name__}: {e}")
        return None

    listing = call("Список компаний (страница 1)", "GetCompanyList", Page=1)
    if listing is None:
        listing = call("Список компаний (без параметров)", "GetCompanyList")
    inns = [i for i in map(sp.inn_of, sp.find_list(listing)) if i] if listing else []
    print(f"\nРазбор списка: найдено ИНН {len(inns)}, первые: {inns[:3]}")
    print("ключи верхнего уровня:", list(listing) if isinstance(listing, dict) else type(listing).__name__)
    for key in ("TotalPages", "PageCount", "Pages", "Total"):
        if isinstance(listing, dict) and sp.pick(listing, key) is not None:
            print(f"  поле {key} = {sp.pick(listing, key)}")

    inn = sys.argv[1] if len(sys.argv) > 1 else (inns[0] if inns else "5030357423")
    print("\nИНН для проверки:", inn)
    report = call("Краткий отчёт", "GetCompanyShortReport", INN=inn)
    group = call("Группа", "GetCompanyGroup", INN=inn)
    changes = call("Изменения за сутки", "GetChangedCompanies", Since=datetime.now(timezone.utc) - timedelta(days=1), Page=1)
    items = sp.find_list(changes)
    print(f"\nРазбор изменений: записей на странице {len(items)}, Total={sp.pick(changes, 'Total')}, "
          f"типы изменений: {sorted({str(sp.pick(i, 'ChangeType')) for i in items})}")
    call("Неизвестный ИНН (ждём COMPANY_NOT_FOUND или INVALID_INN)", "GetCompanyShortReport", INN="0000000000")

    print("\n" + "=" * 70, "\nРАЗБОР spark_parse: что мы поймём из этих ответов\n" + "=" * 70)
    if report is None:
        print("отчёт не получен, разбирать нечего")
        return
    row = sp.to_company_row(report, group, inn)
    print(show(row))
    empty = [k for k, v in row.items() if v in (None, "")]
    print("\nПустые поля:", empty or "нет")
    try:
        sp.check_row(row, report)
        print("обязательные поля (short_name, status, registration_date): ЕСТЬ")
    except Exception as e:
        print("ОШИБКА разбора:", e)
        print("-> добавь нужные имена в pick(...) в services/loader/app/spark_parse.py")
    print("название группы:", sp.group_name_of(group))


if __name__ == "__main__":
    main()
