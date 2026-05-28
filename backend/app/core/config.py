from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    app_title: str = "Supermercado Analytics API"
    app_version: str = "1.0.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Paths
    data_root: Path = Path("data")

    project_root_override: Path | None = None

    def _resolve_data_root(self) -> Path:
        """Resuelve data_root contra project_root si es relativa (desarrollo local)."""
        if self.data_root.is_absolute():
            return self.data_root
        return self.project_root / self.data_root

    @property
    def processed_root(self) -> Path:
        return self._resolve_data_root() / "processed"

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
        return self._resolve_data_root() / "models"

    @property
    def kmeans_model_path(self) -> Path:
        return self.models_root / "kmeans"

    @property
    def association_rules_path(self) -> Path:
        return self.models_root / "association_rules.parquet"

    @property
    def customer_clusters_path(self) -> Path:
        return self.processed_root / "customer_clusters.parquet"

    @property
    def raw_dataset_path(self) -> Path:
        return self._resolve_data_root() / "DataSet"

    @property
    def project_root(self) -> Path:
        if self.project_root_override is not None:
            return self.project_root_override
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def hadoop_home(self) -> Path:
        return Path("C:/hadoop")

settings = Settings()