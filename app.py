
import os
import sys
import json
import requests # 用於發送 HTTP 請求到 GAS

from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 優先從環境變數讀取 LINE Bot 的金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
GAS_URL = os.environ.get("GAS_URL") # Google Apps Script 網址

# 檢查必要的環境變數
if not all([LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, GAS_URL]):
    app.logger.error("Missing environment variables. Please check LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, and GAS_URL.")
    # 在 Heroku 上，我們不希望程式直接崩潰，而是記錄錯誤
    # sys.exit(1)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/liff")
def liff_page():
    try:
        return open("liff_form.html", encoding="utf-8").read()
    except Exception as e:
        app.logger.error(f"Error reading liff_form.html: {e}")
        return "Internal Server Error", 500

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    
    app.logger.info(f"Webhook Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel secret.")
        abort(400)
    except LineBotApiError as e:
        app.logger.error(f"LineBotApiError: {e.status_code} - {e.message}")
        abort(500)
    except Exception as e:
        app.logger.error(f"Unexpected error in callback: {e}", exc_info=True)
        abort(500)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    app.logger.info(f"User {user_id} sent text: {text}")

    if text == "開始評估額度":
        # 填入您的實際 LIFF URL
        liff_url = "https://liff.line.me/2010163577-4275Ob9E"
        
        flex_message = {
            "type": "flex",
            "altText": "請點擊填寫額度評估申請表",
            "contents": {
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=1000&auto=format&fit=crop", # 專業金融背景圖
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "極速貸額度評估",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#4B0082"
                        },
                        {
                            "type": "text",
                            "text": "請點擊下方按鈕，填寫您的申請資料，我們將盡快為您評估。",
                            "wrap": True,
                            "margin": "md",
                            "size": "sm",
                            "color": "#666666"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "color": "#4B0082",
                            "action": {
                                "type": "uri",
                                "label": "填寫申請表",
                                "uri": liff_url
                            }
                        }
                    ]
                }
            }
        }
        try:
            line_bot_api.reply_message(
                event.reply_token,
                messages=[flex_message]
            )
        except Exception as e:
            app.logger.error(f"Error sending Flex Message: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"請點擊下方連結填寫申請表：\n{liff_url}")
            )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="您好，歡迎使用極速貸！請點選「開始評估額度」以啟動服務。")
        )

@app.route("/submit_liff_form", methods=["POST"])
def submit_liff_form():
    try:
        data = request.get_json()
        user_id = request.headers.get("X-Line-User-ID")

        if not user_id:
            app.logger.error("X-Line-User-ID header is missing.")
            return jsonify({"status": "error", "message": "LINE User ID is required."}), 400

        app.logger.info(f"Received LIFF form submission from user {user_id}.")
        
        # 將 LINE User ID 和用戶填寫的 LINE ID 都加入資料中，一起發送到 GAS
        data["lineUserId"] = user_id # LIFF 提供的 LINE User ID
        # data["lineIdInput"] 已經從表單中獲取

        # 將資料發送到 Google Apps Script
        gas_response = requests.post(GAS_URL, json=data)
        gas_response.raise_for_status()
        
        app.logger.info(f"Data sent to GAS. Response: {gas_response.text}")

        # 推送成功訊息給用戶
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text="✅ 您的申請已成功提交！\n系統正在審核資料評估回覆額度，請稍後5~10分鐘。\n謝謝!")
        )

        return jsonify({"status": "success"}), 200

    except Exception as e:
        app.logger.error(f"Error in submit_liff_form: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
