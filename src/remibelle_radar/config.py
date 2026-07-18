from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: Path = Path("data/remibelle.db")
    google_spreadsheet_id: str | None = None
    google_service_account_json: Path | None = None
    x_bearer_token: str | None = None
    enable_paid_x_api: bool = False
    instagram_access_token: str | None = None
    instagram_user_id: str | None = None
    instagram_graph_api_version: str = "v23.0"
    instagram_hashtags: str = "アイドル志望,アイドルオーディション,元アイドル,被写体,コンカフェ"
    radar_timezone: str = "Asia/Tokyo"
    public_profile_seeds: Path = Path("seeds/public_profiles.json")
    request_timeout_seconds: float = 20
    max_results_per_radar: int = 30

    @field_validator("radar_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value
