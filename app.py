import os
import json
import requests
import base64
from flask import Flask, request, jsonify
from groq import Groq
import google.generativeai as genai

app = Flask(__name__)

# ========================================
# Environment Variables
# ========================================
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "rohan_hand_crafts_2024")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# AI সেটআপ
groq_client = Groq(api_key=GROQ_API_KEY)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# ========================================
# প্রোডাক্ট লিস্ট
# ========================================
PRODUCTS = """
১. Pumpkin Candle 1 — দাম: ১৮০ টাকা — স্টক: আছে
২. Pumpkin Candle 2 — দাম: ১৮০ টাকা — স্টক: আছে
৩. Sun Candle — দাম: ৫০ টাকা — স্টক: আছে
৪. Bubble Candle — দাম: ৫০ টাকা — স্টক: আছে
৫. Love জিপসাম শোপিস — দাম: ৫০ টাকা — স্টক: আছে
৬. Love Candle — দাম: ১০০ টাকা — স্টক: আছে
৭. Peony Candle — দাম: ৫০ টাকা — স্টক: আছে
৮. Heart Shaped Candle — দাম: ৫০ টাকা — স্টক: আছে
৯. কক্ষ Gift Box — দাম: ২৫০ টাকা — স্টক: আছে
১০. C Shell শোপিস — দাম: ৬০ টাকা — স্টক: আছে
১১. Lotus জিপসাম শোপিস — দাম: ১০০ টাকা — স্টক: আছে
"""

SYSTEM_PROMPT = f"""তুমি Rohan Hand Crafts এর AI সহকারী।

গুরুত্বপূর্ণ তথ্য:
- আমাদের shop ফরিদপুরে অবস্থিত
- আমরা হাতে তৈরি ক্যান্ডেল, জিপসাম শোপিস, পুঁথির শোপিস ও হোম ডেকর বিক্রি করি
- Facebook Page: Rohan Hand Crafts

নিয়মাবলী:
- সবসময় বাংলায় উত্তর দেবে
- ছোট, মিষ্টি ও সহজ ভাষায় কথা বলবে
- নিজে থেকে কোনো মিথ্যা তথ্য বানাবে না
- শুধু নিচের product list থেকে তথ্য দেবে
- বানান ভুল হলেও কাছাকাছি প্রোডাক্ট বুঝে উত্তর দেবে
- কাস্টমার অর্ডার করতে চাইলে নাম, ঠিকানা ও ফোন নম্বর চাইবে
- delivery charge সম্পর্কে জিজ্ঞেস করলে বলবে "আমাদের সাথে যোগাযোগ করুন"

আমাদের প্রোডাক্ট লিস্ট:
{PRODUCTS}"""

# Chat History মেমরি (server চলাকালীন)
chat_history = {}

# ========================================
# Dashboard এর জন্য Log
# ========================================
message_log = []

def log_message(sender_id, user_msg, bot_reply):
    message_log.append({
        "sender": sender_id,
        "user": user_msg,
        "bot": bot_reply,
        "time": str(__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    })
    if len(message_log) > 100:
        message_log.pop(0)

# ========================================
# ছবি বিশ্লেষণ (Gemini Vision)
# ========================================
def analyze_image(image_url):
    if not GEMINI_API_KEY:
        return "[ছবি বিশ্লেষণ করতে পারছি না]"
    try:
        img_response = requests.get(image_url)
        img_data = base64.b64encode(img_response.content).decode('utf-8')
        
        prompt = f"""এই ছবিতে কী আছে বাংলায় বলো। 
        বিশেষভাবে দেখো এটা কি আমাদের এই প্রোডাক্টগুলোর মধ্যে কোনোটা:
        {PRODUCTS}
        যদি match হয় তাহলে বলো কোন প্রোডাক্ট। না হলে বলো ছবিতে কী দেখছো।"""
        
        response = gemini_model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": img_data}
        ])
        return response.text
    except Exception as e:
        print(f"Gemini Vision Error: {e}")
        return "[ছবি বিশ্লেষণে সমস্যা হয়েছে]"

# ========================================
# AI Reply (Groq)
# ========================================
def get_ai_reply(sender_id, user_message, is_first_time):
    history = chat_history.get(sender_id, [])
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if is_first_time:
        messages[0]["content"] += "\n\nএটা কাস্টমারের প্রথম message। 'আসসালামু আলাইকুম' দিয়ে শুরু করো।"
    else:
        messages[0]["content"] += "\n\nআগে সালাম দেওয়া হয়েছে। আর সালাম দেবে না, সরাসরি উত্তর দেবে।"
    
    for h in history[-5:]:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["bot"]})
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return "দুঃখিত, এখন একটু সমস্যা হচ্ছে। একটু পরে আবার চেষ্টা করুন। 😊"

# ========================================
# Facebook Message পাঠানো
# ========================================
def send_message(recipient_id, message_text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    try:
        response = requests.post(url, params=params, json=data)
        return response.json()
    except Exception as e:
        print(f"Send Message Error: {e}")

# ========================================
# Webhook Verification
# ========================================
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Verification failed', 403

# ========================================
# Webhook Message Handler
# ========================================
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
                    
                    is_first_time = sender_id not in chat_history
                    
                    # ছবি পাঠালে
                    if 'attachments' in message:
                        attachments = message['attachments']
                        for attachment in attachments:
                            if attachment['type'] == 'image':
                                image_url = attachment['payload']['url']
                                image_analysis = analyze_image(image_url)
                                user_text = f"[কাস্টমার একটি ছবি পাঠিয়েছে। ছবিতে দেখা যাচ্ছে: {image_analysis}]"
                            else:
                                user_text = "[কাস্টমার একটি ফাইল পাঠিয়েছে]"
                    elif 'text' in message:
                        user_text = message['text']
                    else:
                        continue
                    
                    ai_reply = get_ai_reply(sender_id, user_text, is_first_time)
                    
                    if sender_id not in chat_history:
                        chat_history[sender_id] = []
                    chat_history[sender_id].append({
                        "user": user_text,
                        "bot": ai_reply
                    })
                    
                    log_message(sender_id, user_text, ai_reply)
                    send_message(sender_id, ai_reply)
    
    return jsonify({"status": "ok"}), 200

# ========================================
# Dashboard
# ========================================
@app.route('/')
def home():
    return "Rohan Hand Crafts Bot চালু আছে! ✅"

@app.route('/dashboard')
def dashboard():
    total = len(message_log)
    unique_users = len(set([m['sender'] for m in message_log]))
    
    html = f"""
    <html>
    <head>
        <title>Rohan Hand Crafts Bot Dashboard</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial; padding: 20px; background: #f0f2f5; }}
            h1 {{ color: #1877f2; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat {{ background: white; padding: 20px; border-radius: 10px; text-align: center; }}
            .stat h2 {{ font-size: 40px; color: #1877f2; margin: 0; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; }}
            th {{ background: #1877f2; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #eee; }}
            tr:hover {{ background: #f0f2f5; }}
        </style>
    </head>
    <body>
        <h1>🤖 Rohan Hand Crafts Bot Dashboard</h1>
        <div class="stats">
            <div class="stat"><h2>{total}</h2><p>মোট মেসেজ</p></div>
            <div class="stat"><h2>{unique_users}</h2><p>মোট কাস্টমার</p></div>
        </div>
        <table>
            <tr><th>সময়</th><th>কাস্টমার ID</th><th>কাস্টমার বলেছে</th><th>Bot বলেছে</th></tr>
    """
    
    for m in reversed(message_log[-50:]):
        user_short = m['user'][:50] + "..." if len(m['user']) > 50 else m['user']
        bot_short = m['bot'][:80] + "..." if len(m['bot']) > 80 else m['bot']
        html += f"<tr><td>{m['time']}</td><td>{m['sender'][-6:]}</td><td>{user_short}</td><td>{bot_short}</td></tr>"
    
    html += "</table></body></html>"
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
