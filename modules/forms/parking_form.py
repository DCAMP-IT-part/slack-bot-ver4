import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name
from modules.dept_service import get_slack_user_id

def open_parking_modal(payload):
    trigger_id = payload["trigger_id"]
    try:
        slack_client.views_open(
            trigger_id=trigger_id,
            view=get_parking_modal_view()
        )
    except Exception as e:
        print("views_open error:", e)
    return "", 200


def get_parking_modal_view():
    return {
        "type": "modal",
        "callback_id": "parking_form_submit",
        "title": {"type":"plain_text","text":"주차 등록 신청"},
        "submit": {"type":"plain_text","text":"제출"},
        "close":  {"type":"plain_text","text":"취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "email_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "owner_email"
                },
                "label": {"type": "plain_text", "text": "소유주 이메일 주소"}
            },
            {
                "type": "input",
                "block_id": "name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "owner_name"
                },
                "label": {"type": "plain_text", "text": "소유주 성함"}
            },
            {
                "type": "input",
                "block_id": "phone_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "phone_number"
                },
                "label": {"type": "plain_text", "text": "휴대전화 번호"}
            },
            {
                "type": "input",
                "block_id": "car_number_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "car_number"
                },
                "label": {"type": "plain_text", "text": "차량번호"}
            },
            {
                "type": "input",
                "block_id": "car_type_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "car_type"
                },
                "label": {"type": "plain_text", "text": "차종 (예: 소나타, SUV 등)"}
            },
            {
                "type": "input",
                "block_id": "ev_block",
                "element": {
                    "type": "static_select",
                    "action_id": "is_ev",
                    "placeholder": {"type":"plain_text","text":"선택"},
                    "options": [
                        {"text":{"type":"plain_text","text":"예"},"value":"yes"},
                        {"text":{"type":"plain_text","text":"아니오"},"value":"no"}
                    ]
                },
                "label": {"type": "plain_text", "text": "전기차 여부"}
            }
        ]
    }


def submit_parking_form(payload):
    values = payload["view"]["state"]["values"]
    email_value = values["email_block"]["owner_email"]["value"]
    name_value  = values["name_block"]["owner_name"]["value"]
    phone_value = values["phone_block"]["phone_number"]["value"]
    car_number  = values["car_number_block"]["car_number"]["value"]
    car_type    = values["car_type_block"]["car_type"]["value"]
    ev_selection= values["ev_block"]["is_ev"]["selected_option"]["value"]
    ev_label    = "예" if ev_selection=="yes" else "아니오"

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id) 

    message_text = (
        f"*[주차 등록 신청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 이메일: {email_value}\n"
        f"- 성함: {name_value}\n"
        f"- 휴대전화: {phone_value}\n"
        f"- 차량번호: {car_number}\n"
        f"- 차종: {car_type}\n"
        f"- 전기차: {ev_label}"
    )


    send_dm_to_admin("주차", message_text)

    return make_response(
        json.dumps({"response_action":"clear"}),
        200,
        {"Content-Type":"application/json"}
    )
