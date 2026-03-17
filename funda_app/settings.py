from functools import cached_property

from google import genai
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict


class FirestoreClientSettings(BaseModel):
    """
    Configuration for the Firestore client.

    Attributes:
        client: Initialized Firestore client instance (via cached_property).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @cached_property
    def client(self) -> firestore.Client:
        """
        Returns initialized Firestore client.

        Returns:
            firestore.Client: Configured Firestore client instance.
        """
        return firestore.Client()


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
