import pytest

from funda_app.app_settings import AppSettings
from funda_app.services import attio, attio_schema


def test_app_settings_defaults_to_dev_for_attio_resolution() -> None:
    settings = AppSettings(
        _env_file=None,
        whatsapp_access_token="token",
        whatsapp_phone_number_id="1029270380269800",
        attio_api_key_dev="dev-token",
        attio_api_key_prod="prod-token",
        attio_founder_lifecycle_list_id_dev="dev-list",
        attio_founder_lifecycle_list_id_prod="prod-list",
    )

    assert settings.app_env == "dev"
    assert settings.attio_api_key == "dev-token"
    assert settings.attio_founder_lifecycle_list_id == "dev-list"


def test_app_settings_resolves_prod_attio_credentials() -> None:
    settings = AppSettings(
        _env_file=None,
        app_env="prod",
        whatsapp_access_token="token",
        whatsapp_phone_number_id="1029270380269800",
        attio_api_key_dev="dev-token",
        attio_api_key_prod="prod-token",
        attio_founder_lifecycle_list_id_dev="dev-list",
        attio_founder_lifecycle_list_id_prod="prod-list",
    )

    assert settings.attio_api_key == "prod-token"
    assert settings.attio_founder_lifecycle_list_id == "prod-list"


def test_attio_validation_uses_env_specific_error_names() -> None:
    with pytest.raises(ValueError, match="ATTIO_API_KEY_PROD is required"):
        attio.sync_attio_member(
            sync_request=_sync_request(),
            settings=AppSettings(
                _env_file=None,
                app_env="prod",
                whatsapp_access_token="token",
                whatsapp_phone_number_id="1029270380269800",
                attio_founder_lifecycle_list_id_prod="prod-list",
            ),
        )

    with pytest.raises(
        ValueError, match="ATTIO_FOUNDER_LIFECYCLE_LIST_ID_PROD is required"
    ):
        attio.sync_attio_member(
            sync_request=_sync_request(),
            settings=AppSettings(
                _env_file=None,
                app_env="prod",
                whatsapp_access_token="token",
                whatsapp_phone_number_id="1029270380269800",
                attio_api_key_prod="prod-token",
            ),
        )

    with pytest.raises(ValueError, match="ATTIO_API_KEY_PROD is required"):
        attio_schema.export_attio_schema(
            settings=AppSettings(
                _env_file=None,
                app_env="prod",
                whatsapp_access_token="token",
                whatsapp_phone_number_id="1029270380269800",
            )
        )


def _sync_request():
    from datetime import UTC, datetime

    from funda_app.schemas.crm import AttioLifecycleSyncRequest, AttioPersonSyncPayload
    from funda_app.schemas.webhooks import MemberStatus, MemberWebhookEvent

    return AttioLifecycleSyncRequest(
        event=MemberWebhookEvent.MEMBER_JOINED,
        event_id="event-123",
        occurred_at=datetime(2026, 3, 14, 16, 26, 12, tzinfo=UTC),
        community_id="community-123",
        community_name="funda",
        member_status=MemberStatus.PENDING,
        person=AttioPersonSyncPayload(
            keyai_member_id="member-123",
            email="eshaan@example.com",
            full_name="Eshaan Vipani",
            first_name="Eshaan",
            last_name="Vipani",
        ),
    )
