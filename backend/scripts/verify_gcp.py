#!/usr/bin/env python3
"""Verify GCP / Vertex AI setup for Phase 1.

Usage (from backend/):
  python scripts/verify_gcp.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.gcp_runtime import configure_gcp_runtime, gemini_backend
from app.tools.gemini_reason import interpret_mission


async def main() -> int:
    configure_gcp_runtime()

    print("=== OpenAid Phase 1 — GCP / Vertex check ===\n")
    print(f"gemini_backend:      {gemini_backend()}")
    print(f"gemini_configured:   {settings.gemini_configured}")
    print(f"use_vertex_ai:       {settings.use_vertex_ai}")
    print(f"gcp_project:         {settings.google_cloud_project or '(not set)'}")
    print(f"gcp_location:        {settings.google_cloud_location}")
    print(f"gemini_model:        {settings.gemini_model}")
    print()

    if not settings.gemini_configured:
        print("FAIL: Gemini not configured.")
        print("Set GOOGLE_CLOUD_PROJECT + USE_VERTEX_AI=true, or GOOGLE_API_KEY.")
        print("See docs/GCP_FREE_TRIAL_SETUP.md")
        return 1

    if settings.use_vertex_ai and not settings.google_cloud_project:
        print("FAIL: USE_VERTEX_AI=true but GOOGLE_CLOUD_PROJECT is empty.")
        return 1

    print("Calling interpret_mission (Vertex or API key)...")
    try:
        result = await interpret_mission(
            "We need medical supply data for flooded regions in Kenya."
        )
    except Exception as exc:
        print(f"\nFAIL: Gemini call failed: {exc}")
        if settings.use_vertex_ai:
            print("\nTry:")
            print("  gcloud auth application-default login")
            print("  gcloud services enable aiplatform.googleapis.com")
        return 1

    print("\nOK — Gemini reasoning works")
    print(f"  intent:    {result.intent}")
    print(f"  region:    {result.region}")
    print(f"  hdx_query: {result.hdx_query}")
    print(f"  summary:   {result.summary[:100]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
