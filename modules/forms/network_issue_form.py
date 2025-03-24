# modules/forms/network_issue_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_network_issue_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_network_issue_modal_view()
    )
    return "", 200

def get_network_issue_modal_view():
    return {
        "type": "modal",
        "callback_id": "network_issue_form_submit",
        "title": {"type":"plain_text","text":"네트워크/사이트 느림 문의"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "site_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "site_url"
                },
                "label": {"type": "plain_text", "text": "접속 시도 URL (느린 사이트)"}
            },
            {
                "type": "input",
                "block_id": "time_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "time_info"
                },
                "label": {"type": "plain_text", "text": "발생 시간대/지속 시간"}
            },
            {
                "type": "input",
                "block_id": "mac_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "mac_address"
                },
                "label": {"type": "plain_text", "text": "PC MAC주소 (가능하면)"}
            }
        ]
    }

def submit_network_issue_form(payload):
    values = payload["view"]["state"]["values"]
    site_url = values["site_block"]["site_url"]["value"]
    time_info= values["time_block"]["time_info"]["value"]
    mac_addr = values["mac_block"]["mac_address"]["value"]

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id)

    msg_text = (
        f"*[네트워크 이슈]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 사이트: {site_url}\n"
        f"- 시간대: {time_info}\n"
        f"- MAC주소: {mac_addr}\n"
    )
    send_dm_to_admin("네트워크",msg_text)

    return make_response(json.dumps({"response_action":"clear"}),
                         200, {"Content-Type":"application/json"})
