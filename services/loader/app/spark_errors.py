"""Исключения Loader. Отдельный файл без внешних зависимостей: тесты и loader.py не требуют zeep."""


class SparkError(Exception):
    pass


class AuthFailed(SparkError):
    """Неверный логин или пароль СПАРК. Повторять бессмысленно."""


class SkipCompany(SparkError):
    """COMPANY_NOT_FOUND / INVALID_INN: по этому ИНН данных не будет, запись пропускаем."""


class SparkBadRequest(SparkError):
    """INVALID_REQUEST / UNKNOWN_OPERATION: ошибка в нашем запросе (имя операции или параметра). Повторять бессмысленно."""


class SparkUnavailable(SparkError):
    """Мок не ответил нормально за все попытки."""


class MappingError(SparkError):
    """В ответе СПАРК нет обязательных полей (формат ответа не тот, что ждёт spark_parse)."""


class LoadIncomplete(SparkError):
    """Часть компаний не загрузилась. Загрузка продолжится со следующей попытки с места остановки."""
