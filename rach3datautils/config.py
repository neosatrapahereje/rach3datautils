import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = bool(os.getenv("RACH3DATAUTILS_DEBUG", False))
