from functools import cached_property

from google import genai
from pydantic import BaseModel, ConfigDict


class GeminiClientSettings(BaseModel):
    """
    Configuration for the Gemini API client (Vertex AI).

    Attributes:
        client: Initialized Gemini client instance (via cached_property).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @cached_property
    def client(self) -> genai.Client:
        """
        Returns initialized Gemini client (Vertex AI).

        Returns:
            genai.Client: Configured Gemini client instance.
        """
        return genai.Client(vertexai=True)
