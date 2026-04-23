"""
Zentrales Logging: ein Format, benannter Logger `openstair`.

- Level: `OPENSTAIR_LOG_LEVEL` > `~/.openstair/app_settings.json` > INFO
"""

from __future__ import annotations

import logging
import sys

from config.app_settings import log_level_for_startup


def setup_logging() -> None:
    level_name = log_level_for_startup()
    try:
        level = getattr(logging, level_name)
    except AttributeError:
        level = logging.INFO

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        logging.getLogger("openstair").setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("openstair").setLevel(level)
