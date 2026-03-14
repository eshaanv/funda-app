"""
Logging configuration for the Funda App application.
"""

import logging


def setup_logging() -> None:
    """
    Configures logging for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
