# my_slack_bot/modules/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN      = os.getenv("SLACK_BOT_TOKEN")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")

# ADMIN_USER_ID        = os.getenv("ADMIN_USER_ID")
GOOGLE_APPS_SCRIPT_URL = os.getenv("GOOGLE_APPS_SCRIPT_URL", "")
SHEET_NAME_DEPT      = os.getenv("SHEET_NAME_DEPT", "담당자시트")

SECRET_TOKEN = os.getenv("SECRET_TOKEN")

