"""Конвейер загрузки без zeep и без БД: поддельные клиент и хранилище."""
import unittest
from datetime import date, datetime, timezone

from app import loader
from app.incremental import incremental_load
from app.loader import initial_load
from app.spark_errors import AuthFailed, LoadIncomplete, MappingError, SkipCompany
from app.store import DryRunStore

INNS = [f"77000000{i:02d}" for i in range(1, 7)]


def actual(inn):
    return datetime(2026, 10, 1, 12, 0, int(inn[-2:]) % 60, tzinfo=timezone.utc)     # у каждой компании своя ActualDate


def report(inn, name=None, with_group=True):
    rec = {"INN": inn, "ShortName": name or f"Компания {inn}", "Status": "active",
           "RegistrationDate": date(2015, 1, 1), "OGRN": "1" + inn, "OKVED": {"Code": "62.01", "Name": "ПО"},
           "ActualDate": actual(inn), "Revision": 1}
    if with_group:
        rec["GroupId"] = "G1"
    return rec


class FakeClient:
    def __init__(self, inns=INNS, no_report=(), no_group=(), broken=(), bad_report=(), group_fault=()):
        self.inns, self.no_report, self.no_group = list(inns), set(no_report), set(no_group)
        self.broken, self.bad_report, self.group_fault = set(broken), set(bad_report), set(group_fault)
        self.changed, self.names, self.fetched, self.group_calls, self.list_calls = [], {}, [], [], 0

    def get_all_inns(self):
        self.list_calls += 1
        return self.inns

    def get_company_short_report(self, inn):
        self.fetched.append(inn)
        if inn in self.no_report:
            raise SkipCompany("COMPANY_NOT_FOUND")
        if inn in self.broken:
            raise RuntimeError("мок упал")
        if inn in self.bad_report:
            return {"Foo": "bar"}
        return report(inn, self.names.get(inn), with_group=inn not in self.no_group)

    def get_company_group(self, inn):
        self.group_calls.append(inn)
        if inn in self.group_fault:
            raise SkipCompany("COMPANY_NOT_FOUND")
        return {"GroupId": "G1", "GroupName": "Группа", "Members": {"Member": [
            {"INN": inn, "Role": "parent"}, {"INN": "9999999999", "Role": "affiliate"}]}}

    def get_changed_companies(self, since):
        return list(self.changed)


class LoaderTests(unittest.TestCase):
    def test_initial_load_sets_state(self):
        store, client = DryRunStore(), FakeClient()
        initial_load(client, store, workers=4)
        self.assertEqual(store.counts(), {"companies": 6, "versions": 6, "groups": 1})
        s = store.state
        self.assertEqual((s["initial_done"], s["initial_versions"], s["initial_skipped"]), ("true", "6", "0"))
        self.assertEqual(s["last_sync_at"], s["initial_loaded_at"])
        self.assertEqual(store.rows[INNS[0]]["group_relation"], "PARENT")       # Role из списка участников
        self.assertEqual(store.rows[INNS[0]]["status"], "ACTIVE")

    def test_company_without_group_skips_group_request(self):
        """Нет GroupId в отчёте: компания загружена без группы, GetCompanyGroup не вызываем."""
        store, client = DryRunStore(), FakeClient(no_group=[INNS[1], INNS[2]])
        initial_load(client, store)
        self.assertEqual(len(store.rows), 6)
        self.assertIsNone(store.rows[INNS[1]]["group_id"])
        self.assertEqual(store.counts()["groups"], 1)
        self.assertNotIn(INNS[1], client.group_calls)
        self.assertEqual(len(client.group_calls), 4)

    def test_group_fault_does_not_lose_company(self):
        """Отчёт знает группу, а GetCompanyGroup ответил COMPANY_NOT_FOUND: компанию всё равно загружаем."""
        store = DryRunStore()
        initial_load(FakeClient(group_fault=[INNS[0]]), store)
        self.assertEqual(len(store.rows), 6)
        self.assertEqual(store.rows[INNS[0]]["group_id"], "G1")      # GroupId берём из отчёта
        self.assertIsNone(store.rows[INNS[0]]["group_relation"])

    def test_unknown_company_is_skipped_not_fatal(self):
        store = DryRunStore()
        initial_load(FakeClient(no_report=[INNS[0]]), store)
        self.assertEqual(len(store.rows), 5)
        self.assertEqual(store.state["initial_skipped"], "1")
        self.assertEqual(store.state["initial_done"], "true")

    def test_failure_blocks_done_and_names_inn(self):
        store = DryRunStore()
        with self.assertRaises(LoadIncomplete) as ctx:
            initial_load(FakeClient(broken=[INNS[2]]), store)
        self.assertIn(INNS[2], str(ctx.exception))
        self.assertIsNone(store.get_state("initial_done"))
        self.assertEqual(len(store.rows), 5)           # остальные загружены

    def test_resume_loads_only_missing_and_keeps_start_time(self):
        store = DryRunStore()
        with self.assertRaises(LoadIncomplete):
            initial_load(FakeClient(broken=[INNS[2]]), store)
        first_start = store.state["initial_started_at"]
        fixed = FakeClient()
        initial_load(fixed, store)
        self.assertEqual(fixed.fetched, [INNS[2]])
        self.assertEqual(store.state["initial_loaded_at"], first_start)
        self.assertEqual(store.state["initial_done"], "true")

    def test_second_run_adds_no_versions(self):
        store = DryRunStore()
        client = FakeClient()
        initial_load(client, store)
        client.fetched.clear()
        initial_load(client, store)
        self.assertEqual(client.fetched, [])            # всё уже есть, ничего не качаем

    def test_missing_required_fields_fail_loudly(self):
        store = DryRunStore()
        with self.assertRaises(LoadIncomplete) as ctx:
            initial_load(FakeClient(bad_report=[INNS[0]]), store)
        self.assertIn("нет", str(ctx.exception))
        self.assertNotIn(INNS[0], store.rows)           # пустую строку в БД не записали

    def test_empty_company_list_is_error(self):
        with self.assertRaises(RuntimeError):
            initial_load(FakeClient(inns=[]), DryRunStore())

    def test_auth_failed_aborts(self):
        class Bad(FakeClient):
            def get_company_short_report(self, inn):
                raise AuthFailed("неверный логин")
        with self.assertRaises(AuthFailed):
            initial_load(Bad(), DryRunStore())

    def test_valid_from_is_actual_date_by_default(self):
        class Rec(DryRunStore):
            def __init__(self):
                super().__init__()
                self.stamps = {}

            def save(self, row, group_name, now):
                self.stamps[row["inn"]] = now
                return super().save(row, group_name, now)
        store = Rec()
        initial_load(FakeClient(), store)
        self.assertEqual({i: store.stamps[i] for i in INNS}, {i: actual(i) for i in INNS})

    def test_valid_from_can_be_load_time(self):
        class Rec(DryRunStore):
            def __init__(self):
                super().__init__()
                self.stamps = set()

            def save(self, row, group_name, now):
                self.stamps.add(now)
                return super().save(row, group_name, now)
        store = Rec()
        initial_load(FakeClient(), store, valid_from_actual=False)
        self.assertEqual(len(store.stamps), 1)                       # одно время на всю загрузку
        self.assertEqual(store.stamps.pop().isoformat(), store.state["initial_started_at"])

    def test_incremental_counts_only_real_changes(self):
        store, client = DryRunStore(), FakeClient()
        initial_load(client, store)
        before = store.state["last_sync_at"]
        client.changed = [INNS[0], INNS[1]]
        client.names[INNS[0]] = "Новое название"        # изменилась только одна
        result = incremental_load(client, store)
        self.assertEqual((result["changed"], result["created"]), (2, 1))
        self.assertNotEqual(store.state["last_sync_at"], before)
        self.assertEqual(__import__("json").loads(store.state["changed_inns"]), [INNS[0]])

    def test_incremental_failure_keeps_cursor_but_remembers_created(self):
        store, client = DryRunStore(), FakeClient()
        initial_load(client, store)
        before = store.state["last_sync_at"]
        client.changed = [INNS[0], INNS[1]]
        client.names[INNS[0]] = "Новое название"
        client.broken = {INNS[1]}
        with self.assertRaises(LoadIncomplete):
            incremental_load(client, store)
        self.assertEqual(store.state["last_sync_at"], before)
        self.assertIn(INNS[0], store.state["changed_inns"])

    def test_incremental_before_initial(self):
        with self.assertRaises(LoadIncomplete):
            incremental_load(FakeClient(), DryRunStore())


if __name__ == "__main__":
    unittest.main()
