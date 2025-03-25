import pytest
from unittest.mock import patch
from slack_sdk.errors import SlackApiError

# 우리가 실제로 테스트할 대상 함수:
from modules.slack_utils import send_message, get_slack_user_name

@patch("modules.slack_utils.slack_client.chat_postMessage")
def test_send_message_success(mock_post):
    """
    send_message가 정상적으로 chat_postMessage를 호출하는지 검증한다.
    """
    # 실행
    send_message(channel_id="C123", reply_text="Hello, Slack!", thread_ts="165.123")

    # 검증: mock_post가 특정 파라미터로 한번만 호출되었는지
    mock_post.assert_called_once_with(
        channel="C123",
        text="Hello, Slack!",
        mrkdwn=True,
        thread_ts="165.123"
    )

@patch("modules.slack_utils.slack_client.chat_postMessage")
def test_send_message_empty_text(mock_post):
    """
    reply_text가 빈 경우, 메시지를 보내지 않도록 했다. 
    실제로 chat_postMessage가 호출되지 않아야 한다.
    """
    send_message(channel_id="C123", reply_text=None)
    mock_post.assert_not_called()

@patch("modules.slack_utils.slack_client.users_info")
def test_get_slack_user_name_success(mock_users_info):
    """
    Slack API 응답이 정상일 때, display_name을 최우선 반환하는지 확인.
    """
    # 모의 응답
    mock_users_info.return_value = {
        "ok": True,
        "user": {
            "profile": {
                "display_name": "TestDisplay",
                "real_name": "TestReal"
            }
        }
    }
    user_name = get_slack_user_name("U999")
    assert user_name == "TestDisplay"  # display_name 우선

@patch("modules.slack_utils.slack_client.users_info")
def test_get_slack_user_name_no_display(mock_users_info):
    """
    display_name이 없으면 real_name을 사용해야 한다.
    """
    mock_users_info.return_value = {
        "ok": True,
        "user": {
            "profile": {
                "display_name": "",
                "real_name": "TestReal"
            }
        }
    }
    user_name = get_slack_user_name("U999")
    assert user_name == "TestReal"

@patch("modules.slack_utils.slack_client.users_info")
def test_get_slack_user_name_error(mock_users_info):
    """
    SlackApiError가 발생하거나 ok=False인 경우, "Unknown User"를 반환해야 한다.
    """
    # 1) ok=False 케이스
    mock_users_info.return_value = {"ok": False}
    assert get_slack_user_name("U999") == "Unknown User"

    # 2) SlackApiError 발생
    mock_users_info.side_effect = SlackApiError("Error", response={"ok": False, "error": "something_wrong"})
    assert get_slack_user_name("U999") == "Unknown User"
