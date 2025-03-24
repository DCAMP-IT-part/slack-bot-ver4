# my_slack_bot/modules/dept_service.py
import requests
import numpy as np
from modules.config import GOOGLE_APPS_SCRIPT_URL, SHEET_NAME_DEPT, SECRET_TOKEN
from modules.openai_service import compute_embedding


def fetch_dept_data():
    """
    시트 데이터 + 임베딩을 로드하여 list[dict] 형태로 반환
    ex) [
      {
        "종류": "대관",
        "담당부서": "총무",
        "주요 담당자": "엄아영",
        "상세내용": "...",
        "SlackUserID": "U088BGU32PM"
      },
      ...
    ]
    """
    if not GOOGLE_APPS_SCRIPT_URL:
        print("No GOOGLE_APPS_SCRIPT_URL provided.")
        return []

    local_data = []
    try:
        params = {
            "sheet": SHEET_NAME_DEPT,
            "secret": SECRET_TOKEN
        }
        resp = requests.get(GOOGLE_APPS_SCRIPT_URL, params=params, timeout=15)
        if resp.status_code == 200:
            print("fetch_dept_data: status_code=200")
            print("fetch_dept_data: resp.text =", resp.text)

            local_data = resp.json()  # [{...,"SlackUserID":"U0XXX"}, ...]
            

            # 상세내용 임베딩
            for row in local_data:
                detail_text = row.get("상세내용", "")
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
    return float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)))

def classify_by_detail(user_text, dept_data, threshold=0.5):
    """
    user_text와 dept_data(시트 전체) 비교 후, 가장 유사한 '종류' 반환
    """
    if not dept_data:
        return "기타"

    user_emb = compute_embedding(user_text)
    if not user_emb:
        return "기타"

    best_score = 0.0
    best_cat   = "기타"
    for row in dept_data:
        detail_emb = row.get("detail_embedding")
        if not detail_emb:
            continue
        score = cosine_similarity(user_emb, detail_emb)
        #디버그용 추후 삭제
        print(f"[DEBUG] {row['종류']} => score={score}")
        if score > best_score:
            best_score = score
            best_cat   = row.get("종류","기타")

    if best_score < threshold:
        best_cat = "기타"

    return best_cat

def match_dept_info(category, dept_data):
    for row in dept_data:
        if row.get("종류","") == category:
            dept = row.get("담당부서","기타")
            # mgr  = row.get("주요 담당자","기타 담당자")
            slack_name = row.get("SlackName","")
            return f"{dept} 부서 [{slack_name}]"
        
        
    return f"{dept} 부서 [{slack_name}]"


def get_slack_user_id(category, dept_data):
    """
    dept_data를 순회하여, '종류'가 category인 행의 SlackUserID를 반환.
    없으면 ""(빈 문자열) 반환.
    """
    for row in dept_data:
        if row.get("종류","") == category:
            return row.get("SlackUserID","")
    return ""