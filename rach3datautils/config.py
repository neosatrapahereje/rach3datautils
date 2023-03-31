import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("RACH3DATAUTILS_DEBUG", "False")
if DEBUG == "False":
    DEBUG = False
elif DEBUG == "True":
    DEBUG = True
