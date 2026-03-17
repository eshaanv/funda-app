from typing import Literal

from pydantic import BaseModel


class KeyAIEventProcessingState(BaseModel):
    """
    Represents the persisted processing state for a Key.ai webhook event.

    Args:
        should_process (bool): Whether the current worker should process the event.
        attio_done (bool, optional): Whether Attio sync already completed.
            Defaults to False.
        whatsapp_done (bool, optional): Whether WhatsApp dispatch already completed.
            Defaults to False.
    """

    should_process: bool
    attio_done: bool = False
    whatsapp_done: bool = False


class KeyAIEventRecord(BaseModel):
    """
    Represents the stored idempotency record for a Key.ai webhook event.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
        member_id (str): Key.ai member ID.
        event_type (str): Key.ai event name.
        status (Literal["processing", "failed", "completed"]): Processing status.
        attio_done (bool, optional): Whether Attio sync completed.
            Defaults to False.
        whatsapp_done (bool, optional): Whether WhatsApp dispatch completed.
            Defaults to False.
    """

    event_id: str
    member_id: str
    event_type: str
    status: Literal["processing", "failed", "completed"]
    attio_done: bool = False
    whatsapp_done: bool = False
