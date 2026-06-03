import os
import json
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# ========================================
# এখানে তোমার তথ্য বসাও
# ========================================
PAGE_ACCESS_TOKEN = "এখানে_তোমার_Facebook_Page_Access_Token_বসাও"
VERIFY_TOKEN = "rohan_hand_crafts_2024"
GEMINI_API_KEY = "এখানে_তোমার_Gemini_API_Key_বসাও"
# ========================================

# Gemini AI সেটআপ
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# প্রোডাক্ট লিস্ট
PRODUCTS = """
১. Pumpkin Candle 1 - দাম: ১৮০ টাকা - স্টক: আছে
২. Pumpkin Candle 2 - দাম: ১৮০ টাকা - স্টক: আছে
৩. Sun Candle - দাম: ৫০ টাকা - স্টক: আছে
৪. Bubble Candle - দাম: ৫০ টাকা - স্টক: আছে
৫. Love (জিপসাম) - দাম: ৫০ টাকা - স্টক: আছে
৬. Love Candle - দাম: ১০০ টাকা - স্টক: আছে
৭. Peony Candle - দাম: ৫০ টাকা - স্টক: আছে
৮. Heart Shaped Candle - দাম: ৫০ টাকা - স্টক: আছে
৯. কক্ষ (Gift Box) - দাম: ২৫০ টাকা - স্টক: আছে
১০. C Shell - দাম: ৬০ টাকা - স্টক: আছে
১১. Lotus (জিপসাম) - দাম: ১০০ টাকা - স্টক: আছে
"""

# Chat History সংরক্ষণ (memory)
chat_history = {}

def get_ai_reply(sender_id, user_message):
    """Gemini AI দিয়ে reply তৈরি করো"""
    
    # এই user এর আগের history নাও
    history = chat_history.get(sender_id, [])
    history_text = ""
    if history:
        last_5 = history[-5:]  # শেষ ৫টা message
        for h in last_5:
            history_text += f"কাস্টমার: {h['user']}\nBot: {h['bot']}\n"
    
    # প্রথমবার কিনা চেক করো
    is_first_time = len(history) == 0
    
    prompt = f"""তুমি Rohan Hand Crafts এর AI সহকারী। বাংলায় উত্তর দেবে।
কাস্টমারের সাথে ইউজার ফ্রেন্ডলি, মিষ্টি ও ছোট উত্তর দেবে।
{"প্রথম message তাই 'আসসালামু আলাইকুম' দিয়ে শুরু করবে।" if is_first_time else "আগে সালাম দেওয়া হয়েছে তাই আর সালাম দেবে না, সরাসরি উত্তর দেবে।"}
কখনো 'নমস্কার' বা অন্য ভাষার শুভেচ্ছা ব্যবহার করবে না।

আমাদের প্রোডাক্ট লিস্ট:
{PRODUCTS}

⚠️ নির্দেশনা:
- বানান ভুল হলেও কাছাকাছি প্রোডাক্ট বুঝে উত্তর দেবে
- দাম জিজ্ঞেস করলে সঠিক দাম বলবে
- অর্ডার করতে চাইলে নাম, ঠিকানা ও ফোন নম্বর চাইবে
- কাস্টমার ছবি পাঠালে বলবে "ছবিটি দেখেছি, কোন প্রোডাক্ট সম্পর্কে জানতে চান?"

আগের কথোপকথন:
{history_text if history_text else "নতুন কথোপকথন"}

কাস্টমারের নতুন মেসেজ: {user_message}

সুন্দর ও ছোট উত্তর দাও:"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "দুঃখিত, এখন একটু সমস্যা হচ্ছে। একটু পরে আবার চেষ্টা করুন। 😊"

def send_message(recipient_id, message_text):
    """Facebook Messenger এ message পাঠাও"""
    url = f"https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    response = requests.post(url, headers=headers, params=params, json=data)
    return response.json()

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Facebook Webhook Verification"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Verification failed', 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Facebook থেকে message receive করো"""
    data = request.get_json()
    
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                page_id = messaging['recipient']['id']
                
                # Bot এর নিজের message ignore করো
                if sender_id == page_id:
                    continue
                
                # Message আছে কিনা চেক করো
                if 'message' in messaging:
                    message = messaging['message']
                    
                    # Echo ignore করো
                    if message.get('is_echo'):
                        continue
                    
                    # Text message
                    if 'text' in message:
                        user_text = message['text']
                    # ছবি বা অন্য attachment
                    elif 'attachments' in message:
                        user_text = "[কাস্টমার একটি ছবি বা ফাইল পাঠিয়েছে]"
                    else:
                        continue
                    
                    # AI reply নাও
                    ai_reply = get_ai_reply(sender_id, user_text)
                    
                    # History সেভ করো
                    if sender_id not in chat_history:
                        chat_history[sender_id] = []
                    chat_history[sender_id].append({
                        "user": user_text,
                        "bot": ai_reply
                    })
                    
                    # Reply পাঠাও
                    send_message(sender_id, ai_reply)
    
    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    return "Rohan Hand Crafts Bot চালু আছে! ✅"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
