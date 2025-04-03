# my_slack_bot/modules/faq_embedding.py

import json
import numpy as np
from modules.openai_service import compute_embedding

data_embeddings = []

def load_data_embeddings(data_file_path="data/combined_slack_dcamp_embeddings.json"):
    global data_embeddings
    try:
        with open(data_file_path, "r", encoding="utf-8") as f:
            data_embeddings = json.load(f)
        print(f"[INFO] Loaded {len(data_embeddings)} FAQ embeddings.")
    except Exception as e:
        print("load_data_embeddings error:", e)
        data_embeddings = []

def cosine_similarity(vecA, vecB):
    if not (vecA and vecB):
        return 0.0
    a = np.array(vecA)
    b = np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)))

def search_similar_data(user_query: str, top_n: int = 3, min_sim: float = 0.82):
    """
    user_query: 사용자 질문 (문자열)
    top_n: 반환할 FAQ 최대 개수
    min_sim: 이 값보다 score가 낮으면 FAQ를 반환하지 않음
    
    반환값 예:
    [
      {
        "question": "...",
        "answer": "...",
        "needs_personal_info": "...",
        "embedding": [...],  # 필요시 유지, 불필요하면 제거 가능
        "score": 0.92
      },
      ...
    ]
    """
    if not data_embeddings:
        return []

    user_emb = compute_embedding(user_query)
    if not user_emb:
        return []

    # 모든 FAQ에 대해 유사도(score) 계산
    scored_data = []
    for faq_item in data_embeddings:
        sc = cosine_similarity(user_emb, faq_item["embedding"])
        scored_data.append((sc, faq_item))

    # 점수 높은 순으로 정렬
    scored_data.sort(key=lambda x: x[0], reverse=True)

    if not scored_data:
        return []

    # 1등 점수가 min_sim 미만이면 매칭 없음 처리
    best_score, _ = scored_data[0]
    if best_score < min_sim:
        return []

    # min_sim 이상인 것들 중 상위 top_n만 추출
    filtered = [(sc, item) for (sc, item) in scored_data if sc >= min_sim]
    selected = filtered[:top_n]

    # 결과 목록을 구성 (score 필드 추가)
    results = []
    for sc, item in selected:
        # item을 복사하여 'score' 필드를 추가
        item_copy = dict(item)
        item_copy["score"] = sc  # ← FAQ 유사도 점수
        results.append(item_copy)

    return results
