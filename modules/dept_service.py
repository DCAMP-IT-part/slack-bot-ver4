# my_slack_bot/modules/dept_service.py

import requests
import numpy as np
from modules.config import GOOGLE_APPS_SCRIPT_URL_DATA_ALL, SECRET_TOKEN
from modules.openai_service import compute_embedding

SHEET_NAME = "manager"

def fetch_dept_data():
    """
    시트("manager")에서 데이터를 가져와서
    - 각 행의 "상세내용" -> 임베딩 => row["detail_embedding"]
    - 단, "기타" 행은 임베딩=None (skip)
    - 반환형: list[dict]
    """
    if not GOOGLE_APPS_SCRIPT_URL_DATA_ALL:
        print("[WARN] No GOOGLE_APPS_SCRIPT_URL_DATA_ALL provided.")
        return []

    local_data = []
    try:
        params = {
            "sheet": SHEET_NAME,
            "secret": SECRET_TOKEN
        }
        resp = requests.get(GOOGLE_APPS_SCRIPT_URL_DATA_ALL, params=params, timeout=15)
        if resp.status_code == 200:
            print("fetch_dept_data: status_code=200")

            json_data = resp.json()
            local_data = json_data.get("manager", [])

            # 임베딩 계산. "기타"는 None 처리
            for row in local_data:
                cat = row.get("종류","")
                detail_text = row.get("상세내용","")
                if cat == "기타":
                    row["detail_embedding"] = None
                else:
                    emb = compute_embedding(detail_text)
                    row["detail_embedding"] = emb
        else:
            print("fetch_dept_data error:", resp.status_code)
            local_data = []

    except Exception as e:
        local_data = []
        print("fetch_dept_data exception:", e)

    return local_data


def cosine_similarity(vecA, vecB):
    if not (vecA and vecB):
        return 0.0
    a = np.array(vecA)
    b = np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def classify_by_detail(user_text, dept_data, threshold=0.7):
    """
    사용자 질문(user_text) 임베딩 vs. dept_data 임베딩 비교,
    - "기타" 행은 임베딩 스킵
    - max 점수가 threshold 미만이면 최종 "기타"
    - 예) "주차", "멤버십", "고정석/자율석/카드키", ...
    """
    if not dept_data:
        return "기타"

    user_emb = compute_embedding(user_text)
    if not user_emb:
        return "기타"

    best_score = 0.0
    best_cat   = "기타"

    for row in dept_data:
        cat = row.get("종류","")
        if cat == "기타":
            continue  # 기타 행은 임베딩 계산 X
        detail_emb = row.get("detail_embedding")
        if not detail_emb:
            continue

        score = cosine_similarity(user_emb, detail_emb)
        print(f"[DEBUG] {cat} => score={score:.6f}")

        if score > best_score:
            best_score = score
            best_cat   = cat

    if best_score < threshold:
        best_cat = "기타"

    return best_cat


def refine_category_by_location(cat: str, channel_name: str) -> str:
    """
    "주차", "멤버십", "고정석/자율석/카드키" 등은 채널명이 "선릉" or "마포"면 cat에 "(선릉)" "(마포)" 붙여줌.
    예: cat='주차', channel_name='선릉-02-문의' => '주차(선릉)'
    """
    # 위치 구분 필요한 카테고리
    location_needed = ["주차", "멤버십", "고정석/자율석/카드키"]

    if cat in location_needed:
        if "선릉" in channel_name:
            return f"{cat}(선릉)"
        elif "마포" in channel_name:
            return f"{cat}(마포)"

    return cat


def match_dept_info(category, dept_data):
    """
    최종 cat(예: "주차(선릉)", "멤버십(마포)", "기타")에 해당하는 시트 행을 찾아,
    '담당부서 부서 [SlackName]' 형태로 반환.
    """
    default_dept       = "기타"
    default_slack_name = "기타 담당자"

    for row in dept_data:
        if row.get("종류","") == category:
            dept       = row.get("담당부서", default_dept)
            slack_name = row.get("SlackName", default_slack_name)
            return f"{dept} 부서 [{slack_name}]"

    return f"{default_dept} 부서 [{default_slack_name}]"


def get_slack_user_id(category, dept_data):
    """
    최종 cat으로 시트 행을 찾아 SlackUserID 반환
    """
    for row in dept_data:
        if row.get("종류","") == category:
            return row.get("SlackUserID","")
    return ""
