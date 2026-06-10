import os
import json
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

SHEET_ID = os.getenv("SHEET_ID", "")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS)
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def save_registration(user):
    sheet = get_sheet()
    if sheet.cell(1, 1).value != "Дата":
        sheet.insert_row(["Дата", "Имя", "Username", "User ID"], index=1)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    username = "@" + user.get("username", "") if user.get("username") else "—"
    user_id = user.get("id", "")
    sheet.append_row([now, name, username, user_id])

def tg(method, data):
    r = requests.post(f"{TG_API}/{method}", json=data)
    return r.json()

@app.route("/", methods=["GET"])
def index():
    return "Nika bot is running", 200

@app.route("/test", methods=["GET"])
def test():
    try:
        sheet = get_sheet()
        return jsonify({"ok": True, "sheet_title": sheet.title, "rows": sheet.row_count})
    except Exception as e:
        logging.error(f"Test error: {repr(e)}")
        return jsonify({"ok": False, "error": repr(e)}), 500

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True) or {}
    logging.info(f"Update: {update}")

    # Нажатие inline-кнопки
    if "callback_query" in update:
        cq = update["callback_query"]
        user = cq["from"]
        data = cq.get("data", "")

        if data == "register_webinar":
            try:
                save_registration(user)
                # Подтверждение пользователю (всплывающее)
                tg("answerCallbackQuery", {
                    "callback_query_id": cq["id"],
                    "text": "✅ Записала! Пришлю ссылку за час до начала.",
                    "show_alert": True
                })
                # Личное сообщение
                name = user.get("first_name", "")
                tg("sendMessage", {
                    "chat_id": user["id"],
                    "text": (
                        f"Привет, {name}! 🙏\n\n"
                        "Ты записана на вебинар:\n"
                        "📅 *13 июня, 12:00 по Берлину* (13:00 Москва)\n\n"
                        "Тема: «Почему ты не говоришь, даже когда знаешь немецкий»\n\n"
                        "Ссылку на эфир пришлю за час до начала. Не опаздывай — запись только для тех, кто был живьём 🎯"
                    ),
                    "parse_mode": "Markdown"
                })
                logging.info(f"Registered: {name} / {user.get('username')}")
            except Exception as e:
                logging.error(f"Registration error: {repr(e)}")
                tg("answerCallbackQuery", {
                    "callback_query_id": cq["id"],
                    "text": "Что-то пошло не так, напиши @nikatalalova напрямую.",
                    "show_alert": True
                })

    return jsonify({"ok": True})

@app.route("/anketa", methods=["POST"])
def anketa():
    try:
        data = request.get_json(force=True) or {}
        logging.info(f"New anketa: {data.get('name', '?')}")
        sheet = get_sheet()
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        sheet.append_row([
            now,
            data.get("name", ""),
            data.get("telegram", ""),
            data.get("instagram", ""),
            data.get("country", ""),
            data.get("level", ""),
            data.get("goal", ""),
            data.get("problems", ""),
            data.get("urgency", ""),
        ])
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Anketa error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
