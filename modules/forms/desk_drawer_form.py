# modules/forms/desk_drawer_form.py
import json
from flask import make_response
from modules.slack_utils import slack_client, send_dm_to_admin, get_slack_user_name

def open_desk_drawer_modal(payload):
    """
    열려는 모달을 정의하고, SlackClient.views_open으로 띄우는 함수
    """
    trigger_id = payload["trigger_id"]
    slack_client.views_open(
        trigger_id=trigger_id,
        view=get_desk_drawer_modal_view()
    )
    return "", 200

def get_desk_drawer_modal_view():
    """
    실제 모달 레이아웃 (blocks)을 반환
    """
    return {
        "type": "modal",
        "callback_id": "desk_drawer_form_submit",
        "title": {"type": "plain_text", "text": "서랍 해제 요청"},
        "submit": {"type": "plain_text", "text": "제출"},
        "close":  {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "location_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "desk_location"
                },
                "label": {"type": "plain_text", "text": "서랍 위치 (층/번호)"}
            },
            {
                "type": "input",
                "block_id": "reason_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason"
                },
                "label": {"type": "plain_text", "text": "기타 요청 사항"}
            }
        ]
    }

def submit_desk_drawer_form(payload):
    """
    제출 후 처리 로직
    """
    values = payload["view"]["state"]["values"]
    location_value = values["location_block"]["desk_location"]["value"]
    reason_value   = values["reason_block"]["reason"]["value"] or "(없음)"

    slack_user_id = payload["user"]["id"]
    slack_user_name = get_slack_user_name(slack_user_id) 

    msg_text = (
        f"*[서랍 비번 해제 요청]*\n"
        f"작성자: {slack_user_name}\n"
        f"- 위치(층/번호): {location_value}\n"
        f"- 요청 사항: {reason_value}\n"
    )
    send_dm_to_admin("시설/비품", msg_text)  # 관리자 DM으로 보내거나, 다른 처리 로직

    # 모달 닫기
    res_body = {"response_action": "clear"}
    return make_response(json.dumps(res_body), 200, {"Content-Type": "application/json"})
