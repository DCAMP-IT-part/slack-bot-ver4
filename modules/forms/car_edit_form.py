# modules/forms/car_edit_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_car_edit_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_car_edit_modal_view()
    )
    return "", 200

def get_car_edit_modal_view():
    return {
        "type": "modal",
        "callback_id": "car_edit_form_submit",
        "title": {"type":"plain_text","text":"차량 해지/변경"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "old_car_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "old_car_number"
                },
                "label": {"type": "plain_text", "text": "삭제할 차량번호"}
            },
            {
                "type": "input",
                "block_id": "new_car_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "new_car_number"
                },
                "label": {"type": "plain_text", "text": "새로 등록할 차량번호 (없으면 비워둠)"}
            }
        ]
    }

def submit_car_edit_form(payload):
    values = payload["view"]["state"]["values"]
    old_car = values["old_car_block"]["old_car_number"]["value"]
    new_car = values["new_car_block"]["new_car_number"]["value"] or "(미등록)"

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id) 

    msg_text = (
        f"*[차량 해지/변경]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 기존 차량번호: {old_car}\n"
        f"- 새 차량번호: {new_car}\n"
    )
    send_dm_to_admin("주차",msg_text)

    return make_response(json.dumps({"response_action":"clear"}),
                         200, {"Content-Type":"application/json"})
