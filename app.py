import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables from Render
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    # Meta webhook verification handshake
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Hello World", 200

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    try:
        # Check if the incoming payload has a message
        if (
            data
            and "entry" in data
            and data["entry"][0]["changes"]
            and "messages" in data["entry"][0]["changes"][0]["value"]
        ):
            value = data["entry"][0]["changes"][0]["value"]
            message = value["messages"][0]
            recipient_phone = message["from"]

            # Define your professional menu response
            response_message = (
                "Dear Customer, thank you for messaging Radiant E Serve, a "
                "Reliance Authorised Service Partner. Kindly let us know your query:\n\n"
                "1. Installation/Demo related\n"
                "2. Repair related\n"
                "3. Maintenance related\n"
                "4. Parts related queries"
            )

            # Send the message back via Meta Graph API
            send_whatsapp_message(recipient_phone, response_message)

    except Exception as e:
        print(f"Error processing webhook: {e}")

    return jsonify({"status": "success"}), 200

def send_whatsapp_message(phone_number, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": text},
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"Meta API Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)