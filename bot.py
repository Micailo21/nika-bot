import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

SHEET_ID = os.getenv("SHEET_ID", "1LVID59lmM68eIim8FhAfGu5xCMaBAmY0OS2OL0N00NA")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "")

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS)
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def save_to_sheet(data):
    sheet = get_sheet()
    # Создаём шапку если таблица пустая
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Дата":
        sheet.insert_row(
            ["Дата", "Имя", "Telegram", "Instagram", "Страна", "Уровень", "Цель", "Проблемы", "Важность"],
            index=1
        )
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

@app.route("/", methods=["GET"])
def index():
    return "Nika bot is running", 200

@app.route("/anketa", methods=["POST"])
def anketa():
    try:
        data = request.get_json(force=True) or {}
        logging.info(f"New anketa: {data.get('name', '?')} / {data.get('telegram', '?')}")
        save_to_sheet(data)
        return jsonify({"ok": True})
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/test", methods=["GET"])
def test():
    try:
        sheet = get_sheet()
        return jsonify({"ok": True, "sheet_title": sheet.title, "rows": sheet.row_count})
    except Exception as e:
        logging.error(f"Test error: {repr(e)}")
        creds_len = len(GOOGLE_CREDENTIALS)
        creds_start = GOOGLE_CREDENTIALS[:30] if GOOGLE_CREDENTIALS else "EMPTY"
        return jsonify({"ok": False, "error": repr(e), "creds_len": creds_len, "creds_start": creds_start}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
