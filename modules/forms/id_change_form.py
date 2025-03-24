# modules/forms/id_change_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_id_change_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_id_change_modal_view()
    )
    return "", 200

def get_id_change_modal_view():
    return {
        "type": "modal",
        "callback_id": "id_change_form_submit",
        "title": {"type": "plain_text", "text": "로그인 이메일 변경"},
        "submit": {"type": "plain_text", "text": "제출"},
        "close":  {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "current_email_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "current_email"
                },
                "label": {"type": "plain_text", "text": "현재 이메일 주소"}
            },
            {
                "type": "input",
                "block_id": "new_email_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "new_email"
                },
                "label": {"type": "plain_text", "text": "변경할 이메일 주소"}
            }
        ]
    }

def submit_id_change_form(payload):
    values = payload["view"]["state"]["values"]
    current_email = values["current_email_block"]["current_email"]["value"]
    new_email     = values["new_email_block"]["new_email"]["value"]

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id)

    msg_text = (
        f"*[아이디 변경 신청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 현재 이메일: {current_email}\n"
        f"- 변경할 이메일: {new_email}\n"
    )
    send_dm_to_admin("홈페이지",msg_text)

    res = {"response_action": "clear"}
    return make_response(json.dumps(res), 200, {"Content-Type": "application/json"})
