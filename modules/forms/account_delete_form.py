# modules/forms/account_delete_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_account_delete_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_account_delete_modal_view()
    )
    return "", 200

def get_account_delete_modal_view():
    return {
        "type": "modal",
        "callback_id": "account_delete_form_submit",
        "title": {"type": "plain_text", "text": "계정 탈퇴 신청"},
        "submit": {"type": "plain_text", "text": "제출"},
        "close":  {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "email_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "email_value"
                },
                "label": {"type": "plain_text", "text": "현재 로그인 이메일"}
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason_value"
                },
                "label": {"type": "plain_text", "text": "탈퇴 사유"}
            }
        ]
    }

def submit_account_delete_form(payload):
    values = payload["view"]["state"]["values"]
    email_val  = values["email_block"]["email_value"]["value"]
    reason_val = values["reason_block"]["reason_value"]["value"]

    slack_user_id = payload["user"]["id"]  
    slack_user_name = get_slack_user_name(slack_user_id)
    

    msg_text = (
        f"*[계정 탈퇴 신청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 이메일: {email_val}\n"
        f"- 탈퇴 사유: {reason_val}\n"
    )
    send_dm_to_admin("홈페이지", msg_text)

    res = {"response_action":"clear"}
    return make_response(json.dumps(res), 200, {"Content-Type":"application/json"})
