from funda_app.core import sanitize_whatsapp_text


def test_sanitize_whatsapp_text_replaces_newlines_tabs_and_extra_spaces() -> None:
    assert (
        sanitize_whatsapp_text("Hello\nthere\tteam    with\r\nextra   spaces")
        == "Hello there team with extra spaces"
    )
