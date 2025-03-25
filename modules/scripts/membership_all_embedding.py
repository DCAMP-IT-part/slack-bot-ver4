import os
import json
import requests
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_APPS_SCRIPT_URL_DATA_ALL = os.getenv("GOOGLE_APPS_SCRIPT_URL_DATA_ALL", "")

openai.api_key = OPENAI_API_KEY


def fetch_sheet_data():
    """
    하나의 Apps Script Web App(DCAMP_WEB_SCRIPT_URL)에서
    dcamp, slack 데이터를 구분하여 반환한다고 가정.
    예: 
    {
      "dcamp": [
        { "문의 내용": "디캠프 질문1", "답변": "디캠프 답변1" },
        ...
      ],
      "slack": [
        { "메인 메시지": "슬랙 메시지", "스레드 댓글": ["...", ...] },
        ...
      ]
    }
    """
    if not GOOGLE_APPS_SCRIPT_URL_DATA_ALL:
        print("[오류] Apps Script URL이 설정되지 않았습니다.")
        return {}

    try:
        resp = requests.get(GOOGLE_APPS_SCRIPT_URL_DATA_ALL, timeout=15)
        if resp.status_code != 200:
            print(f"[오류] HTTP {resp.status_code}: {resp.text}")
            return {}

        data = resp.json()
        if not isinstance(data, dict):
            print("[오류] JSON 응답이 dict(객체) 형태가 아님:", data)
            return {}
        return data

    except Exception as e:
        print("[예외] fetch_sheet_data() 예외:", e)
        return {}


def process_dcamp(dcamp_rows):
    """
    dcamp 시트 구조: [ { "문의 내용": "...", "답변": "..." }, ... ]
    => 임베딩 대상이 될 (question, answer) 형태의 리스트로 변환
    """
    results = []
    for row in dcamp_rows:
        question = row.get("문의 내용", "").strip()
        answer   = row.get("답변", "").strip()

        # 둘 다 비어 있으면 스킵
        if not question and not answer:
            continue

        results.append((question, answer))
    return results


def process_slack(slack_rows):
    """
    슬랙 시트 구조: 
    [ 
      { "메인 메시지": "슬랙 메시지", "스레드 댓글": ["댓글A","댓글B",...] }, 
      ...
    ]
    => (question, answer) 형태의 리스트로 변환
    """
    results = []
    for row in slack_rows:
        question = row.get("메인 메시지", "").strip()

        # 스레드 댓글은 배열일 수도 있고, 경우에 따라 없을 수도 있음
        thread_comments = row.get("스레드 댓글", [])
        if isinstance(thread_comments, list):
            # 여러 댓글을 \n 로 이어붙임
            answer = "\n".join(c.strip() for c in thread_comments)
        else:
            # 혹시 문자열로 올 수도 있으니 대응
            answer = str(thread_comments).strip()

        if not question and not answer:
            continue

        results.append((question, answer))
    return results


def compute_embedding(text: str):
    """
    OpenAI의 text-embedding-ada-002 모델로
    문자열을 벡터(list[float])로 변환
    """
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print("[오류] compute_embedding error:", e)
        return None


def main():
    # 1) Apps Script에서 데이터 받아옴
    data = fetch_sheet_data()
    if not data:
        print("[안내] 가져올 데이터가 없거나 오류. 종료합니다.")
        return

    # 2) dcamp/slack 각 시트의 레코드 가져오기
    dcamp_rows = data.get("dcamp", [])
    slack_rows = data.get("slack", [])

    # 3) 시트별 전처리
    dcamp_pairs = process_dcamp(dcamp_rows)   # -> [(question, answer), ...]
    slack_pairs = process_slack(slack_rows)   # -> [(question, answer), ...]

    # 4) 통합
    all_pairs = dcamp_pairs + slack_pairs
    if not all_pairs:
        print("[안내] 임베딩할 항목이 없습니다. 종료합니다.")
        return

    # 5) 임베딩 + 결과 구조화
    result_list = []
    for (q, a) in all_pairs:
        text = f"Q: {q}\nA: {a}"
        emb = compute_embedding(text)
        if emb is None:
            continue
        result_list.append({
            "question": q,
            "answer": a,
            "embedding": emb
        })

    # 6) 결과를 JSON으로 저장
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "combined_slack_dcamp_embeddings.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False)

    print(f"[완료] 임베딩 {len(result_list)}건 -> {output_file}")


if __name__ == "__main__":
    main()
