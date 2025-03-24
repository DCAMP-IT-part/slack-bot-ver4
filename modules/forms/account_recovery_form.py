# modules/forms/account_recovery_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_account_recovery_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_account_recovery_modal_view()
    )
    return "", 200

def get_account_recovery_modal_view():
    return {
        "type": "modal",
        "callback_id": "account_recovery_form_submit",
        "title": {"type": "plain_text", "text": "비밀번호 찾기 문의"},
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
                "label": {"type": "plain_text", "text": "계정 이메일 주소"}
            },
            {
                "type": "input",
                "block_id": "issue_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "issue_description"
                },
                "label": {"type": "plain_text", "text": "상세 문제 (메일이 안 온다 등)"}
            }
        ]
    }

def submit_account_recovery_form(payload):
    values = payload["view"]["state"]["values"]
    email_val  = values["email_block"]["email_value"]["value"]
    issue_desc = values["issue_block"]["issue_description"]["value"]

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id) 

    message_text = (
        f"*[비밀번호 찾기 문의]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 계정 이메일: {email_val}\n"
        f"- 문제 상황: {issue_desc}\n"
    )
    send_dm_to_admin("홈페이지",message_text)

    res = {"response_action": "clear"}
    return make_response(json.dumps(res), 200, {"Content-Type": "application/json"})
