"""Configure Google Cloud / Vertex AI runtime for ADK agents.

Uses Application Default Credentials (ADC) from:
  gcloud auth application-default login

See docs/GCP_FREE_TRIAL_SETUP.md for the full free-trial walkthrough.
"""

from __future__ import annotations

import os

from app.config import settings


def configure_gcp_runtime() -> None:
    """Apply env vars so google-genai + ADK use Vertex AI when configured."""
    if settings.use_vertex_ai and settings.google_cloud_project:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.google_cloud_project
        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.google_cloud_location
        # Vertex + ADC: do not force AI Studio key into the process.
        return

    if settings.google_api_key:
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)


def gemini_backend() -> str:
    """Return active Gemini backend: vertex | api_key | none."""
    if settings.use_vertex_ai and settings.google_cloud_project:
        return "vertex"
    if settings.google_api_key:
        return "api_key"
    return "none"
