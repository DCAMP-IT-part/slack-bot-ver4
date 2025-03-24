# my_slack_bot/app.py
from flask import Flask, Blueprint
from slackeventsapi import SlackEventAdapter

from modules.config import SLACK_SIGNING_SECRET
from modules.faq_embedding import load_faq_embeddings
from modules.dept_service import fetch_dept_data
from modules.slack_events import register_slack_events
from modules.slack_actions import actions_bp

# #디버깅용 추후 삭제
# print("DEBUG: SLACK_SIGNING_SECRET length:", len(SLACK_SIGNING_SECRET or ""), "value:", repr(SLACK_SIGNING_SECRET))

def create_app():
    app = Flask(__name__)

    # 1) FAQ 임베딩 로드
    load_faq_embeddings()

    # 2) 부서 데이터 로드 후 Flask config에 저장
    dept_data = fetch_dept_data()
    app.config["DEPT_DATA"] = dept_data

    # 추가) "카테고리(=종류)" -> "SlackUserID" 매핑
    cat_map = {}
    for row in dept_data:
        cat = row.get("종류")         # 예: "대관", "주차", ...
        user_id = row.get("SlackUserID")  # "U088BGU32PM" 등
        if cat and user_id:
            cat_map[cat] = user_id
    # Flask config에 저장 (Slack에서 DM 보낼 때 사용)
    app.config["CATEGORY_USER_MAP"] = cat_map


    # 3) Slack 이벤트용 Blueprint + SlackEventAdapter 생성
    events_bp = Blueprint("events_bp", __name__)
    slack_events_adapter = SlackEventAdapter(
        SLACK_SIGNING_SECRET,
        "/slack/events",  # 실제 이벤트 엔드포인트
        events_bp
    )

    # 4) slack_events.py에 정의된 핸들러 등록
    register_slack_events(slack_events_adapter)

    # 5) Flask 앱에 Blueprint 등록
    #    url_prefix="/" 이므로 실제 라우트는 "/slack/events"
    app.register_blueprint(events_bp, url_prefix="/")

    # 6) Slack 액션(Interactive components) Blueprint 등록
    app.register_blueprint(actions_bp, url_prefix="/")

    @app.route("/", methods=["GET"])
    def home():
        return "Slack Bot is running with detail-based classification!", 200

    return app

if __name__ == "__main__":
    flask_app = create_app()
    # 로컬 실행 시
    flask_app.run(port=3000, debug=True)
