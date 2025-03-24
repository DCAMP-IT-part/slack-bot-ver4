# modules/forms/elevator_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_elevator_noise_modal(payload):
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_elevator_noise_modal_view()
    )
    return "", 200

def get_elevator_noise_modal_view():
    return {
        "type": "modal",
        "callback_id": "elevator_noise_form_submit",
        "title": {"type":"plain_text","text":"엘리베이터 소음 신고"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "which_elevator_block",
                "element": {
                    "type": "static_select",
                    "action_id": "which_elevator",
                    "placeholder": {"type":"plain_text","text":"선택"},
                    "options": [
                        {"text":{"type":"plain_text","text":"고층"},"value":"high"},
                        {"text":{"type":"plain_text","text":"저층"},"value":"low"},
                        {"text":{"type":"plain_text","text":"화물"},"value":"cargo"},
                    ]
                },
                "label": {"type": "plain_text", "text": "엘리베이터 종류"}
            },
            {
                "type": "input",
                "block_id": "time_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "time_info"
                },
                "label": {"type":"plain_text","text":"층수/시간대 (구체적으로)"}
            }
        ]
    }

def submit_elevator_noise_form(payload):
    values = payload["view"]["state"]["values"]
    elevator_sel = values["which_elevator_block"]["which_elevator"]["selected_option"]["value"]
    time_info    = values["time_block"]["time_info"]["value"]

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id)

    elevator_label = {"high":"고층","low":"저층","cargo":"화물"}.get(elevator_sel, "기타")
    msg_text = (
        f"*[엘리베이터 소음 신고]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 종류: {elevator_label}\n"
        f"- 층수/시간대: {time_info}\n"
    )
    send_dm_to_admin("시설/비품",msg_text)

    return make_response(
        json.dumps({"response_action":"clear"}),
        200,
        {"Content-Type":"application/json"}
    )
