from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Google Gemini / Vertex AI (Phase 1)
    google_api_key: str = ""
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    # true = Vertex AI via GCP free trial (recommended for hackathon submission)
    use_vertex_ai: bool = True

    # Fivetran REST + MCP (Phase 2–3)
    fivetran_api_key: str = ""
    fivetran_api_secret: str = ""
    fivetran_group_id: str = ""
    fivetran_allow_writes: bool = False
    fivetran_use_mcp: bool = True
    fivetran_mcp_command: str = "uvx"
    fivetran_mcp_args: str = "--from git+https://github.com/fivetran/fivetran-mcp fivetran-mcp"
    fivetran_mcp_timeout: float = 120.0

    # BigQuery briefings (Phase 4)
    bigquery_project: str = ""
    bigquery_dataset: str = ""

    # App
    cors_origins: str = "http://localhost:3000"
    demo_mode: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fivetran_mcp_argv(self) -> list[str]:
        return [a.strip() for a in self.fivetran_mcp_args.split() if a.strip()]

    @property
    def gemini_configured(self) -> bool:
        if self.use_vertex_ai and self.google_cloud_project:
            return True
        return bool(self.google_api_key)

    @property
    def gemini_uses_vertex(self) -> bool:
        return bool(self.use_vertex_ai and self.google_cloud_project)

    @property
    def fivetran_configured(self) -> bool:
        return bool(self.fivetran_api_key and self.fivetran_api_secret and self.fivetran_group_id)

    @property
    def fivetran_mcp_configured(self) -> bool:
        return self.fivetran_configured

    @property
    def bigquery_configured(self) -> bool:
        return bool(self.bigquery_project and self.bigquery_dataset)

    @property
    def live_provisioning_enabled(self) -> bool:
        """True when demo is off and Fivetran writes are explicitly allowed."""
        return not self.demo_mode and self.fivetran_allow_writes and self.fivetran_configured


settings = Settings()
