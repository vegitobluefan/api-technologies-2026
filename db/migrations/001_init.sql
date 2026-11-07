-- Схема под контракты contracts/*/openapi.yaml и архитектуру ДЗ 1.
-- Применяется только на ПУСТОМ томе Postgres. Новые изменения — отдельными файлами 002_*.sql, потом `make reset`.
-- Поля СПАРК (ogrn, названия и т.п.) сверить с ответом GetCompanyShortReport в WSDL.

-- SCD2: история атрибутов юрлица (пишет Store/Loader)
CREATE TABLE IF NOT EXISTS company_versions (
  id                BIGSERIAL PRIMARY KEY,
  inn               TEXT NOT NULL,
  ogrn              TEXT,
  kpp               TEXT,
  short_name        TEXT,
  full_name         TEXT,
  status            TEXT,            -- ACTIVE | LIQUIDATING | LIQUIDATED
  registration_date DATE,
  legal_address     TEXT,
  director          TEXT,
  okved_code        TEXT,
  okved_name        TEXT,
  group_id          TEXT,
  group_relation    TEXT,            -- PARENT | SUBSIDIARY | AFFILIATE
  attrs_hash        TEXT NOT NULL,   -- хэш бизнес-атрибутов (без id/valid_*/is_current)
  valid_from        TIMESTAMPTZ NOT NULL,
  valid_to          TIMESTAMPTZ,
  is_current        BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_company_current ON company_versions(inn) WHERE is_current;
CREATE INDEX IF NOT EXISTS ix_company_inn ON company_versions(inn, valid_from);
CREATE INDEX IF NOT EXISTS ix_company_group ON company_versions(group_id) WHERE is_current;

-- Группы компаний (текущее состояние; состав = company_versions WHERE is_current AND group_id=...)
CREATE TABLE IF NOT EXISTS company_groups (
  group_id   TEXT PRIMARY KEY,
  group_name TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Служебное состояние загрузки: initial_done, initial_loaded_at, last_sync_at
CREATE TABLE IF NOT EXISTS load_state (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Результат lookup по /abs (пишет Enrichment)
CREATE TABLE IF NOT EXISTS bank_clients (
  inn            TEXT PRIMARY KEY,
  is_bank_client BOOLEAN NOT NULL,
  checked_at     TIMESTAMPTZ NOT NULL
);

-- Актуальный срез для чтения (пишет Enrichment, читают Client Info / Group Companies / Scoring)
CREATE TABLE IF NOT EXISTS company_snapshot (
  inn               TEXT PRIMARY KEY,
  ogrn              TEXT,
  kpp               TEXT,
  short_name        TEXT,
  full_name         TEXT,
  status            TEXT,
  registration_date DATE,
  legal_address     TEXT,
  okved_code        TEXT,
  okved_name        TEXT,
  group_id          TEXT,
  group_name        TEXT,
  group_relation    TEXT,
  is_bank_client    BOOLEAN NOT NULL DEFAULT FALSE,
  data_as_of        TIMESTAMPTZ NOT NULL,
  built_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_snapshot_group ON company_snapshot(group_id);
