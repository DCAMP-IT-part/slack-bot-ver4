# modules/forms/company_info_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_company_info_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_company_info_modal_view()
    )
    return "", 200

def get_company_info_modal_view():
    return {
        "type": "modal",
        "callback_id": "company_info_form_submit",
        "title": {"type":"plain_text","text":"회사/서비스/URL 수정"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "which_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "which_info"
                },
                "label": {"type": "plain_text", "text": "수정하려는 항목 (회사명/URL 등)"}
            },
            {
                "type": "input",
                "block_id": "content_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "desired_content"
                },
                "label": {"type": "plain_text", "text": "수정 내용 (어떻게 바꾸고 싶은지)"}
            }
        ]
    }

def submit_company_info_form(payload):
    values = payload["view"]["state"]["values"]
    which_info = values["which_block"]["which_info"]["value"]
    desired    = values["content_block"]["desired_content"]["value"]
    
    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id) 

    msg_text = (
        f"*[회사/서비스/URL 수정 요청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 수정 항목: {which_info}\n"
        f"- 변경 내용: {desired}\n"
    )
    send_dm_to_admin("홈페이지",msg_text)

    return make_response(json.dumps({"response_action":"clear"}),
                         200, {"Content-Type":"application/json"})
