# my_slack_bot/modules/slack_actions.py
import json
from flask import Blueprint, request
from modules.slack_utils import slack_client, send_dm_to_admin

# import 10개 폼
from modules.forms.account_recovery_form import open_account_recovery_modal, submit_account_recovery_form
from modules.forms.id_change_form import open_id_change_modal, submit_id_change_form
from modules.forms.account_delete_form import open_account_delete_modal, submit_account_delete_form
from modules.forms.company_info_form import open_company_info_modal, submit_company_info_form
from modules.forms.network_issue_form import open_network_issue_modal, submit_network_issue_form
from modules.forms.ip_fix_form import open_ip_fix_modal, submit_ip_fix_form
from modules.forms.parking_form import open_parking_modal, submit_parking_form
from modules.forms.car_edit_form import open_car_edit_modal, submit_car_edit_form
from modules.forms.elevator_form import open_elevator_noise_modal, submit_elevator_noise_form
from modules.forms.desk_drawer_form import open_desk_drawer_modal, submit_desk_drawer_form

actions_bp = Blueprint("actions_bp", __name__)

@actions_bp.route("/slack/actions", methods=["POST"])
def handle_interaction():
    payload_str = request.form.get("payload","")
    if not payload_str:
        return "", 200

    payload = json.loads(payload_str)
    # print("Interaction payload:", payload)

    if payload["type"] == "block_actions":
        action = payload["actions"][0]
        act_id = action["action_id"]
        
        # match action_id
        if act_id == "open_account_recovery_modal":
            return open_account_recovery_modal(payload)
        elif act_id == "open_id_change_modal":
            return open_id_change_modal(payload)
        elif act_id == "open_account_delete_modal":
            return open_account_delete_modal(payload)
        elif act_id == "open_company_info_modal":
            return open_company_info_modal(payload)
        elif act_id == "open_network_issue_modal":
            return open_network_issue_modal(payload)
        elif act_id == "open_ip_fix_modal":
            return open_ip_fix_modal(payload)
        elif act_id == "open_parking_modal":
            return open_parking_modal(payload)
        elif act_id == "open_car_edit_modal":
            return open_car_edit_modal(payload)
        elif act_id == "open_elevator_noise_modal":
            return open_elevator_noise_modal(payload)
        elif act_id == "open_desk_drawer_modal":
            return open_desk_drawer_modal(payload)
        return "", 200

    elif payload["type"] == "view_submission":
        callback_id = payload["view"].get("callback_id","")
        
        # match callback_id
        if callback_id == "account_recovery_form_submit":
            return submit_account_recovery_form(payload)
        elif callback_id == "id_change_form_submit":
            return submit_id_change_form(payload)
        elif callback_id == "account_delete_form_submit":
            return submit_account_delete_form(payload)
        elif callback_id == "company_info_form_submit":
            return submit_company_info_form(payload)
        elif callback_id == "network_issue_form_submit":
            return submit_network_issue_form(payload)
        elif callback_id == "ip_fix_form_submit":
            return submit_ip_fix_form(payload)
        elif callback_id == "parking_form_submit":
            return submit_parking_form(payload)
        elif callback_id == "car_edit_form_submit":
            return submit_car_edit_form(payload)
        elif callback_id == "elevator_noise_form_submit":
            # 파일명만 변경, callback_id 그대로
            return submit_elevator_noise_form(payload)
        elif callback_id == "desk_drawer_form_submit":
            return submit_desk_drawer_form(payload)

        return "", 200

    return "", 200
