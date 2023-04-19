import logging
import os
from typing import Literal, Union


try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

LOGLEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOGLEVEL: Union[LOGLEVELS, str] = os.getenv("RACH3DATAUTILS_LOGLEVEL", "INFO")

logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger("rach3datautils")
