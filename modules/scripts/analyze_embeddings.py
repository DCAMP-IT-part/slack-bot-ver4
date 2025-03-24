import json
import numpy as np
import matplotlib.pyplot as plt  # pip install matplotlib

def load_embeddings(file_path):
    """membership_all_embeddings.json 로드 -> Python 리스트 반환"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def cosine_similarity(vecA, vecB):
    a = np.array(vecA)
    b = np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def main():
    file_path = "data/membership_all_embeddings.json"  # 실제 경로 확인
    data = load_embeddings("data/membership_all_embeddings.json")

    # 임베딩 벡터 리스트 추출
    embeddings = [d["embedding"] for d in data if "embedding" in d]

    n = len(embeddings)
    if n < 2:
        print("임베딩 데이터가 2개 미만이므로 유사도 계산 불가.")
        return

    print(f"임베딩 개수: {n}")

    # 모든 (i<j) 쌍에 대해 코사인 유사도 계산
    sim_values = []
    for i in range(n):
        for j in range(i+1, n):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            sim_values.append(sim)

    print(f"쌍별 유사도 개수: {len(sim_values)}")

    # 간단 통계
    sim_array = np.array(sim_values)
    print("Min similarity:", sim_array.min())
    print("Max similarity:", sim_array.max())
    print("Mean similarity:", sim_array.mean())
    print("Median similarity:", np.median(sim_array))
    print("90th percentile:", np.percentile(sim_array, 90))
    print("95th percentile:", np.percentile(sim_array, 95))

    # 히스토그램 그리기
    plt.hist(sim_values, bins=50, range=(0,1), alpha=0.75, color='blue')
    plt.title("Cosine Similarity Distribution")
    plt.xlabel("Similarity")
    plt.ylabel("Count")
    plt.show()

if __name__ == "__main__":
    main()
