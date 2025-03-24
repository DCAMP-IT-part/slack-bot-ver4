import os
import re
import json
import requests
import openai
import numpy as np
from dotenv import load_dotenv

##############################################################################
# 1) 설정 / 준비
##############################################################################

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APPS_SCRIPT_URL = os.getenv("GOOGLE_APPS_SCRIPT_URL_MEMBERSHIP_ALL", "")
openai.api_key = OPENAI_API_KEY

EMBEDDING_MODEL = "text-embedding-ada-002"
CHAT_MODEL      = "gpt-3.5-turbo"  # 또는 gpt-4(비용↑)

# 유사도 임계값(예시)
SIMILARITY_THRESHOLD = 0.88

##############################################################################
# 2) 데이터 가져오기
##############################################################################

def fetch_sheet_data():
    """
    예: 구글 Apps Script URL에서 JSON 형태 데이터를 가져온다.
    실제 응답은 [{'문의 내용':..., '답변':...}, ...] 형태라고 가정.
    """
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

##############################################################################
# 3) 개인정보 마스킹
##############################################################################

def mask_personal_info(text: str) -> str:
    """
    이메일, 전화번호, 차량번호 등 정규식으로 찾으면 *** 처리.
    필요 시 패턴(정규식) 더 정교화 가능
    """
    # 이메일
    text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+", "***@***.***", text)

    # 전화번호(예: 010-1234-5678, 02-123-4567 등)
    text = re.sub(r"\b\d{2,3}-\d{3,4}-\d{4}\b", "***-****-****", text)

    # 차량번호 예시(간단 패턴)
    text = re.sub(r"\b\d{2,3}[가-힣A-Za-z]\s?\d{4}\b", "*** ****", text)

    return text

##############################################################################
# 4) 임베딩 + 유사도 계산
##############################################################################

def compute_embedding(text: str):
    """
    openai.embedding.create -> text-embedding-ada-002 사용
    """
    try:
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print("[오류] compute_embedding error:", e)
        return None

def cosine_similarity(vecA, vecB):
    if not vecA or not vecB:
        return 0.0
    a = np.array(vecA)
    b = np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

##############################################################################
# 5) 중복(유사) 문서 병합
##############################################################################

def deduplicate_texts(docs, threshold=0.88):
    """
    docs: [{'question':..., 'answer':..., 'embedding':...}, ...]
    유사도가 threshold 이상이면 같은 cluster로 묶어서 대표 문서로 병합 처리.
    (간단히 O(n^2) 방식 예시)
    """
    visited = [False] * len(docs)
    clusters = []

    for i in range(len(docs)):
        if visited[i]:
            continue

        cluster_rep = docs[i].copy()
        cluster_rep_texts = [
            cluster_rep["question"] + "\n" + cluster_rep["answer"]
        ]
        visited[i] = True

        for j in range(i+1, len(docs)):
            if visited[j]:
                continue
            sim = cosine_similarity(docs[i]["embedding"], docs[j]["embedding"])
            if sim >= threshold:
                visited[j] = True
                cluster_rep_texts.append(
                    docs[j]["question"] + "\n" + docs[j]["answer"]
                )
        # 단순히 '\n\n---\n\n'로 구분해 텍스트 합치기
        merged_text = "\n\n---\n\n".join(cluster_rep_texts)
        clusters.append(merged_text)

    return clusters

##############################################################################
# 6) LLM 요약
##############################################################################

def summarize_text(text: str, max_tokens=500) -> str:
    """
    openai.chat_completions.create -> gpt-3.5-turbo
    (openai>=1.0.0 이후 변경된 방식)
    """
    system_prompt = (
        "당신은 '개인정보 마스킹 + 내용 요약' 전문 AI입니다. "
        "아래는 고객들이 작성한 문의 내용과, 관리자 답변 기록입니다.\n"
        "이미 일부 정규식 마스킹이 되었지만, 추가로 남아있는 개인정보가 있다면 전부 '***' 처리 후\n"
        "핵심 정보만 간결하게 요약해 주세요."
    )

    user_prompt = f"다음 텍스트를 요약/정리해 주세요:\n{text}"

    try:
        response = openai.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        print("[오류] summarize_text:", e)
        return "요약 실패"

##############################################################################
# 7) 메인 흐름
##############################################################################

def main():
    # (a) 데이터 로드
    raw_data = fetch_sheet_data()
    if not raw_data:
        print("[안내] 가져올 데이터가 없거나 오류. 종료합니다.")
        return

    # (b) 개인정보 마스킹 + 임베딩
    docs = []
    for row in raw_data:
        question = row.get("문의 내용", "").strip()
        answer   = row.get("답변", "").strip()

        # 질문과 답변 모두 비어있으면 스킵
        if not question and not answer:
            continue

        # 정규식 마스킹
        question_masked = mask_personal_info(question)
        answer_masked   = mask_personal_info(answer)

        doc_text = f"Q: {question_masked}\nA: {answer_masked}"
        emb = compute_embedding(doc_text)
        if emb is None:
            continue

        docs.append({
            "question": question_masked,
            "answer": answer_masked,
            "embedding": emb
        })

    print(f"[INFO] 임베딩 완료 문서 수: {len(docs)}")

    # (c) 유사 문서 중복 제거
    clusters = deduplicate_texts(docs, threshold=SIMILARITY_THRESHOLD)
    print(f"[INFO] 중복제거 후 cluster 개수: {len(clusters)}")

    # (d) 각 클러스터를 요약
    final_texts = []
    for idx, cluster_text in enumerate(clusters, start=1):
        summary = summarize_text(cluster_text, max_tokens=800)
        final_texts.append(f"[Cluster {idx}]\n{summary}\n")

    # (e) 결과 저장
    os.makedirs("data", exist_ok=True)
    output_file = "data/final_summarized.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for txt in final_texts:
            f.write(txt)
            f.write("\n\n")

    print(f"[완료] 최종 요약 결과를 '{output_file}'에 저장했습니다.")

if __name__ == "__main__":
    main()
