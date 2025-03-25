# my_slack_bot/modules/slack_events.py

import re
from flask import current_app
# send_dm_to_admin 함수를 포함해 임포트
from modules.slack_utils import send_message, send_blocks, send_dm_to_admin, get_channel_name
from modules.faq_embedding import search_similar_faqs
from modules.openai_service import generate_chat_completion
from modules.dept_service import classify_by_detail, match_dept_info

# 이미 처리된 메시지(중복) 추적
processed_keys = set()

def register_slack_events(slack_events_adapter):
    @slack_events_adapter.on("message")
    def handle_message(event_data):
        dept_data = current_app.config.get("DEPT_DATA", [])
        event = event_data.get("event", {})

        # return #데이터 수집을 위해 return 입력 추후 삭제!

        # (1) 스레드 내 메시지는 무시
        event_ts = event.get("ts")
        thread_ts = event.get("thread_ts")
        if thread_ts and thread_ts != event_ts:
            return

        subtype = event.get("subtype", "")
        if event.get("bot_id") or subtype in (
            "bot_message",
            "message_changed",
            "message_deleted",
            "thread_broadcast",
        ):
            return

        channel_id    = event.get("channel")
        user_id       = event.get("user")
        text          = event.get("text", "")
        msg_ts        = event.get("ts", "")
        client_msg_id = event.get("client_msg_id")

        channel_name = get_channel_name(channel_id)

        # 메시지 유효성 체크
        if not channel_id or not user_id or not msg_ts:
            return

        # 동일 메시지(중복) 처리 방지
        unique_key = (channel_id, client_msg_id) if client_msg_id else (channel_id, msg_ts)
        if unique_key in processed_keys:
            return
        processed_keys.add(unique_key)

        # 부서 데이터 유무 검사
        if not dept_data:
            parent_ts = event.get("thread_ts", msg_ts)
            send_message(channel_id, "담당자 시트 데이터를 불러오지 못했습니다.", thread_ts=parent_ts)
            return

        # (2) 사용자 입력 언어 감지
        lang = detect_language(text)

        # (3) FAQ 검색
        top_faqs = search_similar_faqs(text)
        
        if not top_faqs:
            # FAQ가 전혀 없으면 cat="기타"
            cat = "기타"
            # 이 경우, 채널에는 답변하지 않고 담당자 DM만
        else:
            # FAQ가 존재하면 부서 분류
            cat = classify_by_detail(text, dept_data)
            print(f"[DEBUG] classify_by_detail -> cat={cat}")

        # (4) 만약 cat == "기타"라면 (FAQ 없음 or 분류 결과 기타)
        # => 채널 답변 없이 DM만 보내고 끝낸다
        if cat == "기타":
            dm_text = (
                f"[{channel_name}] 채널에 문의가 들어왔습니다.\n"
                f"카테고리를 특정할 수 없어 '기타'로 분류되었습니다.\n"
                f"사용자 ID: <@{user_id}>\n"
                f"문의 내용: {text}"
            )
            send_dm_to_admin(cat, dm_text)
            # 함수 종료 (채널에는 답글 X)
            return

        # 여기에 왔다는 것은 '기타'가 아닌 카테고리가 분류된 상태
        # => ChatCompletion 호출하여 답변 생성
        # top_faqs[0]을 사용
        best_faq = top_faqs[0]
        for faq in top_faqs:
            faq.pop("embedding", None)  # embedding 제거 (불필요)

        system_prompt = build_system_prompt(lang)
        user_prompt = f"""User query: {text}

FAQ Question: {best_faq['question']}
FAQ Answer: {best_faq['answer']}
"""
        raw_answer = generate_chat_completion(system_prompt, user_prompt) or ""
        answer_body = post_process(raw_answer)

        # (5) 최종 메시지 구성
        if lang == "ko":
            final_msg = (
                f"{answer_body}\n\n"
                "잠시만 기다려주시면, 유관 부서 담당자가 댓글을 남겨 드릴 것입니다."
            )
        else:
            final_msg = (
                f"{answer_body}\n\n"
                "Please wait a moment, the relevant department will post a reply soon."
            )

        # 채널(스레드)로 답글 전송
        parent_ts = event.get("thread_ts", msg_ts)
        blocks = build_category_blocks(cat, final_msg)
        if blocks:
            send_blocks(channel_id, blocks, thread_ts=parent_ts, fallback_text=f"{cat} 안내")
        else:
            send_message(channel_id, final_msg, thread_ts=parent_ts)

        # (6) 유관 부서 담당자에게 DM 보내기
        dm_text = (
            f"[{channel_name}] 채널에 문의가 들어왔습니다.\n"
            f"문의 내용 기반으로 <{cat}>카테고리로 분류되었습니다.\n"
            f"사용자 ID: <@{user_id}>\n"
            f"문의 내용: {text}"
        )
        send_dm_to_admin(cat, dm_text)


def build_category_blocks(cat: str, final_msg: str):
    combined_text = (
        f"{final_msg}\n\n"
        "아래 버튼에서 해당하는 항목을 선택하여 정보를 입력해 주세요.\n"
        "적절한 항목이 없다면, 담당자가 곧 댓글을 남길테니 기다려주세요"
    )

    base_block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": combined_text
        }
    }

    if cat == "주차":
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "주차 등록"},
                    "action_id": "open_parking_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "차량 해지/변경"},
                    "action_id": "open_car_edit_modal"
                }
            ]
        }
        return [base_block, actions_block]

    elif cat == "시설/비품":
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "엘리베이터 소음/충격"},
                    "action_id": "open_elevator_noise_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "서랍 비번 초기화"},
                    "action_id": "open_desk_drawer_modal"
                }
            ]
        }
        return [base_block, actions_block]

    elif cat == "네트워크":
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "사이트 느림/접속 불가"},
                    "action_id": "open_network_issue_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "공인/내부 IP 고정"},
                    "action_id": "open_ip_fix_modal"
                }
            ]
        }
        return [base_block, actions_block]

    elif cat == "홈페이지":
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "비밀번호 찾기 문의"},
                    "action_id": "open_account_recovery_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "아이디 변경"},
                    "action_id": "open_id_change_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "계정 탈퇴"},
                    "action_id": "open_account_delete_modal"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "회사/URL 정보 수정"},
                    "action_id": "open_company_info_modal"
                }
            ]
        }
        return [base_block, actions_block]

    # 매칭 안 되는 카테고리 (기타 등)
    return None


def detect_language(text: str) -> str:
    ko_chars = re.findall("[가-힣]", text)
    ratio = len(ko_chars) / max(1, len(text))
    return "ko" if ratio >= 0.3 else "en"


def build_system_prompt(lang: str) -> str:
    if lang == "ko":
        return """당신은 내부 서비스에서 작동하는 한국어 전용 AI 어시스턴트입니다. 답변을 작성할 때 다음 지침을 준수하세요.

1) **첫 문장을 ‘안녕하세요, 디캠프 AI봇입니다.’라고 시작**하여, 답변자가 AI봇임을 명시합니다.

2) **모든 문단은 빈 줄(\\n\\n)을 사이에 두고 구분**해, 읽기 좋게 작성합니다.

3) **불필요한 쌍따옴표(")**는 쓰지 마세요. 꼭 필요한 인용이나 예시가 아닌 이상, 쌍따옴표 없이 표현합니다.

4) 만약 사용자의 질문에 대해 **적절한 데이터가 전혀 없다면**, 
   해당 질문에 대해 데이터 기반 답변을 드릴 수 없습니다.
   라고만 간단히 안내하세요.
   (과도한 잡담이나 상식, 사적인 표현을 덧붙이지 않습니다)

5) 사용자가 **회사 내부 업무 범위를 벗어난 질문**을 했다면,
   해당 범위 밖이라 답변이 어렵습니다.
   정도로 짧고 정중하게 안내하세요.

6) 사용자의 질문에 대응할 데이터가 있다면, 
   질문 내용을 충분히 공감한 뒤,
   **친절하고 정확하게** 그 데이터를 바탕으로 답변하세요.

7) 이미 사용자는 이 채널(Slack)을 통해 문의하고 있습니다.
   - “문의 게시판에 글을 남기라”거나, “특정 부서(시설팀 등)에 추가 문의를 하라”는 류의 안내 문구는 넣지 않습니다.
   - 필요한 조치가 있다면, 이 채널에서 직접 안내하거나 처리하는 것으로 가정합니다.

8) **예시 (공감 문구)**:
   - 불편을 겪고 계시군요. 빠르게 도와드리겠습니다.
   - 이런 상황은 답답하실 수 있겠어요. 해결 방법을 안내해 드리겠습니다.
   - 도움이 필요하신 것 같네요. 최대한 정확한 정보를 제공해 드리겠습니다.

9) **봇이 “제가 직접 할 수 없습니다”라는 표현은 굳이 쓰지 않아도 됩니다**.
   - 과거 유사 사례나 복잡한 절차 설명도 지양하고,
   - “확인 후 조치해 드리겠습니다” 정도로 간단히 마무리합니다.

10) **민감 정보(IP, MAC 주소 등) 수집 방법에 대해 구체적으로 언급하지 않습니다**.
    - 공개 채널에 남겨 달라거나, DM으로 보내 달라고도 말하지 않습니다.
    - 단지 “추가 정보 확인이 필요하다” 정도로만 간단히 안내하고 넘어갑니다.

이 모든 지침을 지키면서, 최종적으로 한국어로만 답변을 작성하세요.
"""
    else:
        return """You are an English-only AI assistant operating within an internal service context. Please follow these guidelines when composing your answers:

1) Begin your response with the phrase: "Hello, I'm an AI assistant." to clearly indicate that you are an AI bot.

2) Separate paragraphs with a blank line (\\n\\n) to make them more readable.

3) Do not use unnecessary quotation marks ("). Unless absolutely needed for a direct quote or example, avoid them.

4) If you have no relevant data to answer the user's question, reply briefly:
   I cannot provide a data-based answer to this question.
   (No extra commentary or personal remarks)

5) If the question is beyond your scope (unrelated to internal operations),
   politely state This is outside my scope, so I cannot provide an answer.

6) If relevant data exists, start by acknowledging the user's concern with empathy.
   Then provide a clear, accurate answer based on that data.

7) The user is already contacting you via Slack.
   Do not instruct them to visit another inquiry board or contact a separate department (such as facilities) for further questions.
   Assume any needed actions can be handled in this channel.

8) Example empathetic statements:
   - I understand that this issue must be frustrating.
   - It sounds like an inconvenience; let me help you with that.
   - Let me see how I can assist you with clear, data-based information.

9) There's no need to say “I cannot do this directly.” 
   Avoid lengthy past examples or complicated procedures; 
   a concise assurance like “We will look into it and assist” is sufficient.

10) For sensitive data (IP, MAC address, etc.), do not instruct the user to post it here or send it via DM. 
    Simply mention that additional details might be required, without specifying how to share them.

Please adhere to all these instructions, and ensure your final responses are in English only.
"""

def post_process(answer: str) -> str:
    cleaned = answer.replace("[ko]", "").replace("[en]", "")
    cleaned = cleaned.replace("[한국어]", "").replace("[English]", "")
    return cleaned.strip()
