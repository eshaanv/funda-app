from functools import cached_property, lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from funda_app.settings import FirestoreClientSettings, GeminiClientSettings


class AppSettings(BaseSettings):
    app_env: Literal["dev", "prod"] = Field(
        default="dev",
        validation_alias=AliasChoices("APP_ENV"),
    )
    whatsapp_access_token: str = Field(
        validation_alias=AliasChoices("WHATSAPP_ACCESS_TOKEN", "WHATS_APP_TOKEN")
    )
    whatsapp_phone_number_id: str = Field(
        validation_alias=AliasChoices("WHATSAPP_PHONE_NUMBER_ID")
    )
    new_member_admin_phone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEW_MEMBER_ADMIN_PHONE"),
    )
    whatsapp_api_version: str = "v25.0"
    whatsapp_base_url: str = "https://graph.facebook.com"
    whatsapp_timeout_seconds: float = 10.0
    attio_api_key_dev: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_API_KEY_DEV"),
    )
    attio_api_key_prod: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_API_KEY_PROD"),
    )
    attio_base_url: str = "https://api.attio.com/v2"
    attio_timeout_seconds: float = 20.0
    attio_founder_lifecycle_list_id_dev: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_FOUNDER_LIFECYCLE_LIST_ID_DEV"),
    )
    attio_founder_lifecycle_list_id_prod: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_FOUNDER_LIFECYCLE_LIST_ID_PROD"),
    )
    attio_workspace_member_id_dev: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_WORKSPACE_MEMBER_ID_DEV"),
    )
    attio_workspace_member_id_prod: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATTIO_WORKSPACE_MEMBER_ID_PROD"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @cached_property
    def firestore_client_settings(self) -> FirestoreClientSettings:
        """
        Returns Firestore client settings with initialized configuration.

        Returns:
            FirestoreClientSettings: Configured Firestore client settings.
        """
        return FirestoreClientSettings()

    @cached_property
    def gemini_client_settings(self) -> GeminiClientSettings:
        """
        Returns Gemini client settings with initialized configuration.

        Returns:
            GeminiClientSettings: Configured Gemini client settings.
        """
        return GeminiClientSettings()

    @property
    def attio_api_key(self) -> str | None:
        """
        Returns the Attio API key for the active environment.

        Returns:
            str | None: Resolved Attio API key.
        """
        if self.app_env == "prod":
            return self.attio_api_key_prod

        return self.attio_api_key_dev

    @property
    def attio_founder_lifecycle_list_id(self) -> str | None:
        """
        Returns the lifecycle list ID for the active environment.

        Returns:
            str | None: Resolved Attio lifecycle list ID.
        """
        if self.app_env == "prod":
            return self.attio_founder_lifecycle_list_id_prod

        return self.attio_founder_lifecycle_list_id_dev

    @property
    def attio_workspace_member_id(self) -> str | None:
        """
        Returns the Attio workspace member ID for the active environment.

        Returns:
            str | None: Resolved Attio workspace member ID.
        """
        if self.app_env == "prod":
            return self.attio_workspace_member_id_prod

        return self.attio_workspace_member_id_dev


@lru_cache
def get_app_settings() -> AppSettings:
    """
    Loads application settings from the environment.

    Returns:
        AppSettings: Configured application settings.
    """
    return AppSettings()
