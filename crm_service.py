import os
from dotenv import load_dotenv

load_dotenv()

mode = os.getenv("CRM_MODE")

if mode == "mock":
    from app.crm_mock import *
else:
    from app.crm_real import *