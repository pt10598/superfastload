
import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageMessage, QuickReply, QuickReplyButton, MessageAction, TextSendMessage

app = Flask(__name__)

# 優先從環境變數讀取 LINE Bot 的金鑰 (Heroku 推薦做法)
# 如果環境變數不存在，則使用預設值 (僅作備份)
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "slsFpJ3Uy4qzyPwQlhWVxLVqNW+NMARoozhWBsXJycYumR1EcTri9jmB1+I34PZZPdO5+d911KGQ3fr0RjtU+MkZYrdUAg3cor6bqhYhR7S/5D8FJ8BL5AVq0eDh7ZS8TuqHoU7T9ZxLkUamZtd5HAdB04t89/1O/w1cDnyilFU=")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "1a35e9f4d632526902b819a11049dabc")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 用於儲存用戶狀態和資料的字典
user_states = {}
user_data = {}

# 定義用戶狀態
STATE_START = "start"
STATE_ASK_NAME = "ask_name"
STATE_ASK_PHONE = "ask_phone"
STATE_ASK_LINE_ID = "ask_line_id"
STATE_ASK_ID_NUMBER = "ask_id_number"
STATE_ASK_BIRTHDAY = "ask_birthday"
STATE_ASK_REG_ADDR = "ask_reg_addr"
STATE_ASK_RES_ADDR = "ask_res_addr"
STATE_ASK_CONTACT1 = "ask_contact1"
STATE_ASK_CONTACT2 = "ask_contact2"
STATE_UPLOAD_ID_FRONT = "upload_id_front"
STATE_UPLOAD_ID_BACK = "upload_id_back"
STATE_ASK_CONSENT = "ask_consent"
STATE_ASSESSING = "assessing"
STATE_CANCELLED = "cancelled"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel secret.")
        abort(400)
    except LineBotApiError as e:
        app.logger.error(f"LineBotApiError: {e.status_code} - {e.message}")
        abort(500)
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        abort(500)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    current_state = user_states.get(user_id, STATE_START)
    app.logger.info(f"User {user_id} in state {current_state} sent: {text}")

    try:
        if text == "開始評估額度" and current_state == STATE_START:
            user_states[user_id] = STATE_ASK_NAME
            user_data[user_id] = {}
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="好的，我們將開始進行額度評估。\n請輸入您的姓名：")
            )
        elif current_state == STATE_ASK_NAME:
            user_data[user_id]["姓名"] = text
            user_states[user_id] = STATE_ASK_PHONE
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的手機號碼：")
            )
        elif current_state == STATE_ASK_PHONE:
            user_data[user_id]["手機號碼"] = text
            user_states[user_id] = STATE_ASK_LINE_ID
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的 LINE ID：")
            )
        elif current_state == STATE_ASK_LINE_ID:
            user_data[user_id]["LINE ID"] = text
            user_states[user_id] = STATE_ASK_ID_NUMBER
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的身分證字號：")
            )
        elif current_state == STATE_ASK_ID_NUMBER:
            user_data[user_id]["身分證字號"] = text
            user_states[user_id] = STATE_ASK_BIRTHDAY
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的生日 (例如：1990/01/01)：")
            )
        elif current_state == STATE_ASK_BIRTHDAY:
            user_data[user_id]["生日"] = text
            user_states[user_id] = STATE_ASK_REG_ADDR
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的戶籍地址：")
            )
        elif current_state == STATE_ASK_REG_ADDR:
            user_data[user_id]["戶籍地址"] = text
            user_states[user_id] = STATE_ASK_RES_ADDR
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入您的居住地址：")
            )
        elif current_state == STATE_ASK_RES_ADDR:
            user_data[user_id]["居住地址"] = text
            user_states[user_id] = STATE_ASK_CONTACT1
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="好的，請輸入第一位聯絡人的姓名與電話 (例如：王小明 0912345678)：")
            )
        elif current_state == STATE_ASK_CONTACT1:
            user_data[user_id]["聯絡人1"] = text
            user_states[user_id] = STATE_ASK_CONTACT2
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入第二位聯絡人的姓名與電話 (例如：陳大華 0987654321)：")
            )
        elif current_state == STATE_ASK_CONTACT2:
            user_data[user_id]["聯絡人2"] = text
            user_states[user_id] = STATE_UPLOAD_ID_FRONT
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請上傳您的身分證正面照片：")
            )
        elif current_state == STATE_ASK_CONSENT:
            if text == "同意":
                user_states[user_id] = STATE_ASSESSING
                app.logger.info(f"Assessment Complete for {user_id}: {user_data[user_id]}")
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="感謝您的同意！我們已收到您的資料，將開始進行額度評估。\n稍後會有專人與您聯繫。")
                )
                del user_states[user_id]
                del user_data[user_id]
            elif text == "不同意":
                user_states[user_id] = STATE_CANCELLED
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="您已取消本次申請，資料將作廢。如有需要請再次申請。")
                )
                del user_states[user_id]
                del user_data[user_id]
            else:
                send_consent_message(event.reply_token)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您好，歡迎使用極速貸！請點選「開始評估額度」以啟動服務。")
            )
    except LineBotApiError as e:
        app.logger.error(f"LineBotApiError during reply: {e.status_code} - {e.message}")

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    current_state = user_states.get(user_id)

    if current_state == STATE_UPLOAD_ID_FRONT:
        user_data[user_id]["身分證正面照片"] = f"image_id_{event.message.id}"
        user_states[user_id] = STATE_UPLOAD_ID_BACK
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="身分證正面照片已收到。\n請上傳您的身分證反面照片：")
        )
    elif current_state == STATE_UPLOAD_ID_BACK:
        user_data[user_id]["身分證反面照片"] = f"image_id_{event.message.id}"
        user_states[user_id] = STATE_ASK_CONSENT
        send_consent_message(event.reply_token)
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="目前不接受圖片上傳，請依照指示操作。")
        )

def send_consent_message(reply_token):
    quick_reply = QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="同意", text="同意")),
            QuickReplyButton(action=MessageAction(label="不同意", text="不同意"))
        ]
    )
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="請閱讀以下個資使用同意書內容：\n\n[個資使用同意書內容範本]\n\n本人同意極速貸及其合作夥伴，得於所列特定目的範圍內，蒐集、處理及利用本人所提供之個人資料。\n\n您是否同意上述個資使用條款？", quick_reply=quick_reply)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
