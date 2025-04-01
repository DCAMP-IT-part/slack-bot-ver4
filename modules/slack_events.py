# my_slack_bot/modules/slack_events.py

import re
from flask import current_app
from modules.slack_utils import send_message, send_blocks, send_dm_to_admin, get_channel_name
from modules.data_embedding import search_similar_faqs
from modules.openai_service import generate_chat_completion
from modules.openai_service import compute_embedding  # 임베딩 직접 사용 시
import numpy as np

processed_keys = set()

def register_slack_events(slack_events_adapter):
    @slack_events_adapter.on("message")
    def handle_message(event_data):
        dept_data = current_app.config.get("DEPT_DATA", [])
        event = event_data.get("event", {})

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
            parent_ts = thread_ts or msg_ts
            send_message(channel_id, "담당자 시트 데이터를 불러오지 못했습니다.", thread_ts=parent_ts)
            return

        # (2) 사용자 입력 언어 감지
        lang = detect_language(text)

        # (3) 데이터 검색
        top_faqs = search_similar_faqs(text)
        
        if not top_faqs:
            # 데이터(FAQ)가 전혀 없으면 cat="기타"
            cat = "기타"
        else:
            # 데이터가 있으면 임베딩으로 부서 분류
            cat = classify_by_detail_tiebreak(text, dept_data, channel_name=channel_name)
            print(f"[DEBUG] classify_by_detail -> cat={cat}")

        # (4) 만약 cat == "기타"라면 (FAQ 없음 or threshold 미달)
        # => 채널 답변 없이 DM만 보내고 끝낸다
        if cat == "기타":
            dm_text = (
                f"[{channel_name}] 채널에 문의가 들어왔습니다.\n"
                f"카테고리를 특정할 수 없어 '기타'로 분류되었습니다.\n"
                f"사용자 ID: <@{user_id}>\n"
                f"문의 내용: {text}"
            )
            send_dm_to_admin(cat, dm_text)
            return

        # (5) 데이터 존재 & cat != "기타" -> ChatCompletion 이용해 답변 생성
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

        # (6) 최종 메시지 구성
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

        # (7) 블록 빌드 시에는 cat가 "주차(선릉)" 등일 수 있으므로,
        #     실제 블록은 "주차", "네트워크", "홈페이지" 등 기본값을 써야 매칭 가능
        base_cat = get_base_cat(cat)
        blocks = build_category_blocks(base_cat, final_msg)

        parent_ts = thread_ts or msg_ts
        if blocks:
            send_blocks(channel_id, blocks, thread_ts=parent_ts, fallback_text=f"{cat} 안내")
        else:
            send_message(channel_id, final_msg, thread_ts=parent_ts)

        # (8) 담당자 DM
        dm_text = (
            f"[{channel_name}] 채널에 문의가 들어왔습니다.\n"
            f"문의 내용 기반으로 <{cat}> 카테고리로 분류되었습니다.\n"
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

    # 기타
    return None


def get_base_cat(cat: str) -> str:
    """
    "주차(선릉)" or "주차(마포)", "멤버십(선릉)" 등으로 들어올 수 있으므로
    블록 빌드를 위해 기본값("주차", "멤버십", "네트워크" 등)으로 변환.
    """
    if cat.startswith("주차"):
        return "주차"
    elif cat.startswith("시설/비품"):
        return "시설/비품"
    elif cat.startswith("네트워크"):
        return "네트워크"
    elif cat.startswith("홈페이지"):
        return "홈페이지"
    elif cat.startswith("멤버십"):
        return "멤버십"
    # etc...
    return cat


def detect_language(text: str) -> str:
    ko_chars = re.findall("[가-힣]", text)
    ratio = len(ko_chars) / max(1, len(text))
    return "ko" if ratio >= 0.3 else "en"


def build_system_prompt(lang: str) -> str:
    if lang == "ko":
        return """당신은 내부 서비스에서 작동하는 한국어 전용 AI 어시스턴트입니다. 답변을 작성할 때 다음 지침을 준수하세요.

1) 첫 문장을 ‘안녕하세요, 디캠프 AI봇입니다.’로 시작...
(중략)
"""
    else:
        return """You are an English-only AI assistant operating within an internal service context...
(중략)
"""


def post_process(answer: str) -> str:
    cleaned = answer.replace("[ko]", "").replace("[en]", "")
    cleaned = cleaned.replace("[한국어]", "").replace("[English]", "")
    return cleaned.strip()


###################################
# 아래: 동점 발생 시 채널명으로 분류하는 함수 예시
###################################

def classify_by_detail_tiebreak(user_text: str, dept_data: list, channel_name: str, threshold=0.82) -> str:
    """
    임베딩 점수가 threshold 이상인 항목 중 가장 높은 스코어(동점 포함)를 찾되,
    '선릉' / '마포'가 들어있는 채널인 경우 해당 키워드를 포함한 부서를 우선 결정.
    """
    if not dept_data:
        return "기타"

    user_emb = compute_embedding(user_text)
    if not user_emb:
        return "기타"

    # 스코어 계산
    scored_rows = []
    for row in dept_data:
        detail_emb = row.get("detail_embedding")
        if not detail_emb:
            continue
        score = cosine_similarity(user_emb, detail_emb)
        if score >= threshold:
            scored_rows.append((score, row))

    # threshold 이상이 하나도 없으면 => "기타"
    if not scored_rows:
        return "기타"

    # 스코어 높은 순 정렬
    scored_rows.sort(key=lambda x: x[0], reverse=True)
    top_score = scored_rows[0][0]

    # 1등과 똑같은 스코어(동점)인 항목들 추출
    tied = [(s, r) for (s, r) in scored_rows if abs(s - top_score) < 1e-9]

    if len(tied) == 1:
        # 단독 1등인 경우
        return tied[0][1].get("종류", "기타")

    # 동점이 여러 개라면, 채널명에 "선릉"/"마포"가 있는지 확인
    ch_lower = channel_name.lower()  # 소문자로 변환
    if "선릉" in ch_lower:
        # tied 중에서 "(선릉)"이 들어간 종류를 우선 선택
        for s, r in tied:
            cat_name = r.get("종류", "")
            if "(선릉)" in cat_name:
                return cat_name
    elif "마포" in ch_lower:
        for s, r in tied:
            cat_name = r.get("종류", "")
            if "(마포)" in cat_name:
                return cat_name

    # 그래도 못 찾으면 tied[0]
    return tied[0][1].get("종류", "기타")


def cosine_similarity(vecA, vecB):
    if not (vecA and vecB):
        return 0.0
    a = np.array(vecA)
    b = np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
