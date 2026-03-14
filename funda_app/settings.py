from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    whatsapp_access_token: str = Field(
        validation_alias=AliasChoices("WHATSAPP_ACCESS_TOKEN", "WHATS_APP_TOKEN")
    )
    whatsapp_phone_number_id: str = Field(
        validation_alias=AliasChoices("WHATSAPP_PHONE_NUMBER_ID")
    )
    whatsapp_api_version: str = "v25.0"
    whatsapp_base_url: str = "https://graph.facebook.com"
    whatsapp_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_app_settings() -> AppSettings:
    """
    Loads application settings from the environment.

    Returns:
        AppSettings: Configured application settings.
    """
    return AppSettings()
