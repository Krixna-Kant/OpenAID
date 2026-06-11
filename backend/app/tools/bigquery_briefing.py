"""Generate field briefings from synced BigQuery tables."""

from __future__ import annotations

from app.config import settings


def build_briefing_query(table: str, region_filter: str | None = None) -> str:
    region_clause = ""
    if region_filter:
        region_clause = f"AND LOWER(CAST(country AS STRING)) LIKE '%{region_filter.lower()}%'"
    return f"""
    SELECT
      COUNT(*) AS row_count,
      COUNT(DISTINCT country) AS countries,
      MAX(_fivetran_synced) AS last_synced
    FROM `{settings.bigquery_project}.{settings.bigquery_dataset}.{table}`
    WHERE 1=1 {region_clause}
    """


def demo_briefing(dataset_title: str, region: str, row_count: int = 0) -> str:
  """Fallback briefing when BigQuery is not configured."""
  return f"""# Field Briefing — {region}

**Dataset:** {dataset_title}
**Status:** Pipeline provisioned and initial sync triggered.

## Summary
- Target region: {region}
- Records available: {row_count or 'pending first sync'}
- Recommendation: Verify medical supply coverage against flood-affected districts before dispatch.

## Next actions
1. Confirm last sync timestamp in Fivetran dashboard
2. Cross-reference with local health ministry contacts
3. Schedule recurring sync every 6 hours during active response
"""
