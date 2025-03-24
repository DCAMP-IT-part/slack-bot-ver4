# modules/openai_service.py
from openai import OpenAI
from modules.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def compute_embedding(text, model="text-embedding-ada-002"):
    try:
        # 새 라이브러리에서는 input을 list로 넘겨야 합니다.
        resp = client.embeddings.create(model=model, input=[text])
        # resp는 pydantic 모델
        return resp.data[0].embedding
    except Exception as e:
        print("compute_embedding error:", e)
        return None

def generate_chat_completion(system_prompt, user_prompt, model="gpt-4", temperature=0.3):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=600,
            temperature=temperature
        )
        # chatCompletion 응답도 pydantic 모델s
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("generate_chat_completion error:", e)
        return None
    

    