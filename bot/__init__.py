import logging
import sys
from logging import Logger, StreamHandler
from pathlib import Path

from logmatic import JsonFormatter

logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")


def patch_trace(self: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log 'msg % args' with severity 'TRACE'

    :param self:
    :param msg:
    :param args:
    :param kwargs:
    :return:
    """
    if self.isEnabledFor(logging.TRACE):
        self._log(logging.TRACE, msg, args, **kwargs)


Logger.trace = patch_trace

# Set up logging
logging_handlers = []

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging_handlers.append(StreamHandler(stream=sys.stdout))

json_handler = logging.FileHandler(filename=Path(LOG_DIR, "log.json"), mode="w")
json_handler.formatter = JsonFormatter()
logging_handlers.append(json_handler)

logging.basicConfig(
    format="%(asctime)s Bot: | %(name)33s | %(levelname)8s | %(message)s",
    datefmt="%b %d %H:%M:%S",
    level=logging.TRACE,
    handlers=logging_handlers
)

log = logging.getLogger(__name__)

for key, value in logging.Logger.manager.loggerDict.items():
    # Force all existing loggers to the correct level and handlers
    # This happens long before we instantiate our loggers
    # so those should still have the expected level

    if key == "bot":
        continue

    if not isinstance(value, logging.Logger):
        continue

    value.setLevel(logging.DEBUG)

    for handler in value.handlers.copy():
        value.removeHandler(handler)

    for handler in logging_handlers:
        value.addHandler(handler)

# Silence irrelevant loggers
logging.getLogger("aio_pika").setLevel(logging.ERROR)
logging.getLogger("discord").setLevel(logging.ERROR)
logging.getLogger("websockets").setLevel(logging.ERROR)
