# modules/forms/ip_fix_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_ip_fix_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_ip_fix_modal_view()
    )
    return "", 200

def get_ip_fix_modal_view():
    return {
        "type": "modal",
        "callback_id": "ip_fix_form_submit",
        "title": {"type":"plain_text","text":"IP 고정 요청"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "pc_mac_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "mac_address"
                },
                "label": {"type": "plain_text", "text": "PC MAC 주소"}
            },
            {
                "type": "input",
                "block_id": "ip_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "preferred_ip"
                },
                "label": {"type": "plain_text", "text": "원하는 고정 IP (없으면 비워둠)"}
            }
        ]
    }

def submit_ip_fix_form(payload):
    values = payload["view"]["state"]["values"]
    mac_addr = values["pc_mac_block"]["mac_address"]["value"]
    pref_ip   = values["ip_block"]["preferred_ip"]["value"] or "(미지정)"

    # 1) Slack User ID 추출
    slack_user_id = payload["user"]["id"]  # 보통 이 경로로 user.id 존재

    # 2) Slack Display Name(또는 Real Name) 조회
    slack_user_name = get_slack_user_name(slack_user_id)  # (아래에서 정의)


    msg_text = (
        f"*[IP 고정 요청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- MAC 주소: {mac_addr}\n"
        f"- 희망 IP: {pref_ip}\n"
    )
    send_dm_to_admin("네트워크",msg_text)


    res = {"response_action":"clear"}
    return make_response(json.dumps({"response_action":"clear"}),
                         200, {"Content-Type":"application/json"})
