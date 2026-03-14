from types import SimpleNamespace

from google.genai.types import GenerateContentConfig

from funda_app.agents import models


def test_invoke_gemini_returns_response_text(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_generate_content(
        *,
        model: str,
        contents: list[object],
        config: GenerateContentConfig | None,
    ) -> SimpleNamespace:
        captured["model"] = model
        captured["contents"] = contents
        captured["config"] = config
        return SimpleNamespace(text="hello from gemini")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )
    monkeypatch.setattr(
        models,
        "get_app_settings",
        lambda: SimpleNamespace(
            gemini_client_settings=SimpleNamespace(client=fake_client)
        ),
    )

    config = GenerateContentConfig(temperature=0.2)
    response = models.invoke_gemini(
        prompt="Summarize the latest webhook payload.",
        model=models.GeminiModels.GEMINI_3_FLASH_PREVIEW,
        config=config,
    )

    assert response == "hello from gemini"
    assert captured["model"] == "gemini-3-flash-preview"
    assert captured["config"] == config
    assert len(captured["contents"]) == 2


def test_invoke_gemini_returns_none_when_response_has_no_text(
    monkeypatch,
) -> None:
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text=None))
    )
    monkeypatch.setattr(
        models,
        "get_app_settings",
        lambda: SimpleNamespace(
            gemini_client_settings=SimpleNamespace(client=fake_client)
        ),
    )

    response = models.invoke_gemini(prompt="Ping")

    assert response is None
