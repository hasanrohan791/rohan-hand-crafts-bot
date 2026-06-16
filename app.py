import os
import json
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# ========================================
# Environment Variables থেকে নেওয়া হবে
# ========================================
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "rohan_hand_crafts_2024")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Groq AI সেটআপ
client = Groq(api_key=GROQ_API_KEY)

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
৯. কক্ষ Gift Box - দাম: ২৫০ টাকা - স্টক: আছে
১০. C Shell - দাম: ৬০ টাকা - স্টক: আছে
১১. Lotus জিপসাম - দাম: ১০০ টাকা - স্টক: আছে
"""

# Chat History মেমরি
chat_history = {}

def get_ai_reply(sender_id, user_message):
    history = chat_history.get(sender_id, [])
    is_first_time = len(history) == 0

    system_prompt = তুমি Rohan Hand Crafts এর AI সহকারী। 
আমাদের shop ফরিদপুরে অবস্থিত।
সবসময় বাংলায় উত্তর দেবে।
নিজে থেকে কোনো তথ্য বানাবে না।
শুধু নিচের product list থেকে তথ্য দেবে।
কাস্টমারের সাথে ইউজার ফ্রেন্ডলি, মিষ্টি ও ছোট উত্তর দেবে।
{"প্রথম message তাই আসসালামু আলাইকুম দিয়ে শুরু করবে।" if is_first_time else "আগে সালাম দেওয়া হয়েছে তাই আর সালাম দেবে না, সরাসরি উত্তর দেবে।"}
কখনো নমস্কার বা অন্য ভাষার শুভেচ্ছা ব্যবহার করবে না।

আমাদের প্রোডাক্ট লিস্ট:
{PRODUCTS}

নির্দেশনা:
- বানান ভুল হলেও কাছাকাছি প্রোডাক্ট বুঝে উত্তর দেবে
- দাম জিজ্ঞেস করলে সঠিক দাম বলবে
- অর্ডার করতে চাইলে নাম, ঠিকানা ও ফোন নম্বর চাইবে
- কাস্টমার ছবি পাঠালে বলবে কোন প্রোডাক্ট সম্পর্কে জানতে চান"""

    messages = [{"role": "system", "content": system_prompt}]

    # আগের history যোগ করো
    for h in history[-5:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["bot"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return "দুঃখিত, এখন একটু সমস্যা হচ্ছে। একটু পরে আবার চেষ্টা করুন। 😊"

def send_message(recipient_id, message_text):
    url = "https://graph.facebook.com/v18.0/me/messages"
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
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Verification failed', 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                page_id = messaging['recipient']['id']

                if sender_id == page_id:
                    continue

                if 'message' in messaging:
                    message = messaging['message']

                    if message.get('is_echo'):
                        continue

                    if 'text' in message:
                        user_text = message['text']
                    elif 'attachments' in message:
                        user_text = "[কাস্টমার একটি ছবি পাঠিয়েছে]"
                    else:
                        continue

                    ai_reply = get_ai_reply(sender_id, user_text)

                    if sender_id not in chat_history:
                        chat_history[sender_id] = []
                    chat_history[sender_id].append({
                        "user": user_text,
                        "bot": ai_reply
                    })

                    send_message(sender_id, ai_reply)

    return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    return "Rohan Hand Crafts Bot চালু আছে! ✅"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
