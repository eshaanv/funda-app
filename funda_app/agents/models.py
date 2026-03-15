import logging
import time
from enum import StrEnum

from google.genai import types
from google.genai.types import GenerateContentConfig

from funda_app.app_settings import get_app_settings

logger = logging.getLogger(__name__)


class GeminiModels(StrEnum):
    GEMINI_FLASH_LATEST = "gemini-flash-latest"
    GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"
    GEMINI_3_PRO_PREVIEW = "gemini-3-pro-preview"


def invoke_gemini(
    prompt: str,
    model: GeminiModels = GeminiModels.GEMINI_FLASH_LATEST,
    config: GenerateContentConfig | None = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> str | None:
    """
    Invokes Gemini with simple retry behavior.

    Args:
        prompt (str): Text prompt to send to Gemini.
        model (GeminiModels, optional): Gemini model to use.
            Defaults to GeminiModels.GEMINI_FLASH_LATEST.
        config (GenerateContentConfig | None, optional): Generation settings.
            Defaults to None.
        max_retries (int, optional): Maximum retry attempts.
            Defaults to 3.
        initial_delay (float, optional): Initial retry delay in seconds.
            Defaults to 1.0.

    Returns:
        str | None: Generated response text, or None if generation fails.
    """
    contents = [
        types.Content(
            parts=[types.Part.from_text(text=prompt)],
            role="user",
        ),
        types.Content(
            parts=[types.Part.from_text(text="I'll begin writing my response now.")],
            role="model",
        ),
    ]

    client = get_app_settings().gemini_client_settings.client
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model.value,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.error(
                    "Gemini API call failed after %s attempts: %s",
                    max_retries,
                    exc,
                )
                return None

            logger.warning(
                "Gemini API call failed (attempt %s/%s): %s. Retrying in %.1fs...",
                attempt + 1,
                max_retries,
                exc,
                delay,
            )
            time.sleep(delay)
            delay *= 2
            continue

        if response is None or not hasattr(response, "text") or response.text is None:
            return None

        return response.text

    return None
