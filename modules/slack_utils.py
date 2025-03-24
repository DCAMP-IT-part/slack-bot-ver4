# my_slack_bot/modules/slack_utils.py
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import current_app  # for accessing app.config
from modules.config import SLACK_BOT_TOKEN

slack_client = WebClient(token=SLACK_BOT_TOKEN)

def send_message(channel_id, reply_text, thread_ts=None):
    if not reply_text:
        return
    try:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=reply_text,
            mrkdwn=True,
            thread_ts=thread_ts  # 여기서 thread_ts 사용
        )
    except SlackApiError as e:
        print("send_message error:", e.response["error"])

def send_blocks(channel_id, blocks, fallback_text="", thread_ts=None):
    try:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=fallback_text or "Message with blocks",
            blocks=blocks,
            mrkdwn=True,
            thread_ts=thread_ts  # 여기서 thread_ts 사용
        )
    except SlackApiError as e:
        print("send_blocks error:", e.response["error"])


def send_dm_to_admin(category, text):
    """
    'category'와 'text'를 받아,
    Flask config에 저장된 CATEGORY_USER_MAP에서
    SlackUserID를 찾아 DM을 전송한다.

    - category: 시트의 '종류' 값 (예: '주차', '대관', ...)
    - text:     실제 보낼 메시지 내용
    """
    cat_map = current_app.config.get("CATEGORY_USER_MAP", {})
    user_id = cat_map.get(category)

    if not user_id:
        # 카테고리 맵에 해당 키가 없으면 DM 전송 불가
        print(f"[WARN] category='{category}' not found. No DM sent.")
        return

    try:
        resp = slack_client.conversations_open(users=[user_id])
        dm_channel = resp["channel"]["id"]
        slack_client.chat_postMessage(channel=dm_channel, text=text)
    except SlackApiError as e:
        print("send_dm_to_admin error:", e.response["error"])


def get_slack_user_name(user_id: str) -> str:
    """
    Slack Web API (users.info) 호출하여, user_id의 display_name 혹은 real_name 반환
    """
    try:
        response = slack_client.users_info(user=user_id)
        if response["ok"]:
            user_profile = response["user"]["profile"]
            # display_name이 있으면 우선 사용. 없으면 real_name.
            display_name = user_profile.get("display_name") or user_profile.get("real_name") or user_id
            return display_name
        else:
            print("[WARN] users_info failed, not ok:", response)
    except SlackApiError as e:
        print("[ERROR] get_slack_user_name:", e.response["error"])
    return "Unknown User"        

def get_channel_name(channel_id: str) -> str:
    """
    채널 ID로부터 채널 이름(#general 등)을 조회해서 반환합니다.
    실패 시 'Unknown Channel' 리턴
    """
    try:
        response = slack_client.conversations_info(channel=channel_id)
        if response["ok"]:
            return response["channel"]["name"]
    except SlackApiError as e:
        print(f"get_channel_name error: {e.response['error']}")
    return "Unknown Channel"