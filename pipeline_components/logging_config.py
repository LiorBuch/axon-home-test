import logging

DEFAULT_FORMAT = "%(asctime)s [%(processName)s] %(levelname)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging for the current process.

    Each pipeline process runs in its own interpreter (especially under the
    Windows 'spawn' start method), so logging must be configured inside every
    process rather than relying on inheritance from the parent.
    """
    logging.basicConfig(level=level, format=DEFAULT_FORMAT, datefmt="%H:%M:%S")
