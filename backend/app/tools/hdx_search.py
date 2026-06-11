"""Search humanitarian datasets on HDX (CKAN API)."""

from __future__ import annotations

import httpx

HDX_API = "https://data.humdata.org/api/3/action/package_search"


async def search_hdx_datasets(query: str, rows: int = 5) -> list[dict]:
    """Return HDX datasets matching a natural-language style query."""
    params = {"q": query, "rows": rows, "sort": "metadata_modified desc"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(HDX_API, params=params)
        response.raise_for_status()
        payload = response.json()

    if not payload.get("success"):
        raise RuntimeError(payload.get("error", {}).get("message", "HDX search failed"))

    results: list[dict] = []
    for item in payload.get("result", {}).get("results", []):
        resources = [
            {
                "name": r.get("name"),
                "format": r.get("format"),
                "url": r.get("url"),
                "last_modified": r.get("last_modified"),
            }
            for r in item.get("resources", [])
            if r.get("url")
        ]
        results.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "title": item.get("title"),
                "notes": (item.get("notes") or "")[:500],
                "organization": item.get("organization", {}).get("title"),
                "metadata_modified": item.get("metadata_modified"),
                "tags": [t.get("name") for t in item.get("tags", [])],
                "resources": resources[:5],
            }
        )
    return results


def pick_best_dataset(datasets: list[dict]) -> dict | None:
    """Heuristic: prefer CSV/JSON resources with recent modification."""
    if not datasets:
        return None

    def score(ds: dict) -> tuple[int, str]:
        formats = {r.get("format", "").upper() for r in ds.get("resources", [])}
        fmt_score = 2 if "CSV" in formats else 1 if "JSON" in formats else 0
        return (fmt_score, ds.get("metadata_modified") or "")

    return sorted(datasets, key=score, reverse=True)[0]
