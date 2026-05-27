from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    app_title: str = "Supermercado Analytics API"
    app_version: str = "1.0.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Paths (relative to project root; override via env vars for Docker)
    data_root: Path = Path("data")

    @property
    def processed_root(self) -> Path:
        return self.data_root / "processed"

    @property
    def transactions_long_path(self) -> Path:
        return self.processed_root / "transactions_long"

    @property
    def transactions_basket_path(self) -> Path:
        return self.processed_root / "transactions_basket"

    @property
    def catalog_path(self) -> Path:
        return self.processed_root / "catalog"

    @property
    def models_root(self) -> Path:
        return self.data_root / "models"

    @property
    def kmeans_model_path(self) -> Path:
        return self.models_root / "kmeans"

    @property
    def association_rules_path(self) -> Path:
        return self.models_root / "association_rules.parquet"

    @property
    def customer_clusters_path(self) -> Path:
        return self.processed_root / "customer_clusters.parquet"

    # Raw dataset (already extracted)
    @property
    def raw_dataset_path(self) -> Path:
        return self.data_root / "DataSet"


settings = Settings()