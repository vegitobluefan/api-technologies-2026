"""GetChangedCompanies(Since=last_sync_at) -> ShortReport+Group -> SCD2 upsert.
last_sync_at = время НАЧАЛА запроса, а не конца."""

def incremental_load(client): ...
