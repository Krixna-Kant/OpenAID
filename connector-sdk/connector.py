"""Fivetran Connector SDK template for HDX / humanitarian CSV sources.

Deploy with: fivetran deploy --api-key KEY --api-secret SECRET
"""

from fivetran_connector_sdk import Connector
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk import Operations as op
import csv
import io
import json
import urllib.request

# Configuration is injected at deploy time via configuration.json / secrets
REQUIRED_CONFIG = ["source_url", "table_name"]


def schema(configuration: dict):
    table = configuration.get("table_name", "humanitarian_records")
    return [{"table": table, "primary_key": ["id"]}]


def update(configuration: dict, state: dict):
    source_url = configuration["source_url"]
    table_name = configuration.get("table_name", "humanitarian_records")

    log.info(f"Fetching humanitarian data from {source_url}")
    with urllib.request.urlopen(source_url, timeout=60) as response:
        raw = response.read().decode("utf-8", errors="replace")

    rows = []
    if source_url.lower().endswith(".json"):
        payload = json.loads(raw)
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("data") or payload.get("results") or [payload]
    else:
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)

    for idx, row in enumerate(rows):
        record = dict(row)
        record.setdefault("id", str(idx + 1))
        op.upsert(table=table_name, data=record)

    op.checkpoint(state={"last_sync": "ok", "row_count": len(rows)})
    log.info(f"Synced {len(rows)} records into {table_name}")


connector = Connector(update=update, schema=schema)

if __name__ == "__main__":
    connector.debug()
