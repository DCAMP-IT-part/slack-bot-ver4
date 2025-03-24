import os
import json
import requests
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APPS_SCRIPT_URL = os.getenv("GOOGLE_APPS_SCRIPT_URL_MEMBERSHIP_ALL_MASKING", "")

openai.api_key = OPENAI_API_KEY

def fetch_sheet_data():
    """구글 Apps Script URL에서 FAQ 데이터(문의/답변) JSON 형태로 가져오기"""
    if not APPS_SCRIPT_URL:
        print("[오류] Apps Script URL이 설정되지 않았습니다.")
        return []

    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=15)
        if resp.status_code != 200:
            print(f"[오류] HTTP {resp.status_code}: {resp.text}")
            return []
        data = resp.json()
        if not isinstance(data, list):
            print("[오류] JSON 응답이 리스트 형태가 아님:", data)
            return []
        return data
    except Exception as e:
        print("[예외] fetch_sheet_data() 예외:", e)
        return []

def compute_embedding(text: str):
    """OpenAI Embedding API (>=1.0.0) - 객체 기반 응답 처리"""
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        # ✔️ 변경 지점: 딕셔너리(subscript)가 아닌 객체 접근
        return response.data[0].embedding
    except Exception as e:
        print("[오류] compute_embedding error:", e)
        return None

def main():
    faq_data = fetch_sheet_data()
    if not faq_data:
        print("[안내] 가져올 데이터가 없거나 오류. 종료합니다.")
        return

    result_list = []
    for row in faq_data:
        question = row.get("문의 내용", "").strip()
        answer   = row.get("답변", "").strip()

        if not question and not answer:
            continue

        text = f"Q: {question}\nA: {answer}"
        emb = compute_embedding(text)
        if emb is None:
            continue

        result_list.append({
            "question": question,
            "answer": answer,
            "embedding": emb
        })
        
    # 결과를 JSON으로 저장할 data 폴더 생성 (없으면 생성)
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)

    # 결과를 JSON으로 저장
    output_file = os.path.join(output_dir, "membership_all_embeddings.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False)

    print(f"[완료] 임베딩 {len(result_list)}건 -> {output_file}")

if __name__ == "__main__":
    main()
