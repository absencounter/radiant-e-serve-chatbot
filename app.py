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
        if (
            data
            and "entry" in data
            and data["entry"][0]["changes"]
            and "messages" in data["entry"][0]["changes"][0]["value"]
        ):
            value = data["entry"][0]["changes"][0]["value"]
            message = value["messages"][0]
            recipient_phone = message["from"]
            
            user_text = message.get("text", {}).get("body", "").strip()

            # Dynamic multi-level responses with expanded repair options
            if user_text == "1":
                response_message = (
                    "You selected *1. Installation/Demo related*.\n\n"
                    "Please choose an option:\n"
                    "1.1 New Appliance Installation\n"
                    "1.2 Demo Request\n"
                    "Type 'menu' to go back to the main menu."
                )
            elif user_text == "1.1":
                response_message = "Please share your appliance name, address, and preferred date for the new installation."
            elif user_text == "1.2":
                response_message = "Please share your appliance name and preferred time slot for a product demo."
                
            elif user_text == "2":
                response_message = (
                    "You selected *2. Repair related*.\n\n"
                    "Please choose an option:\n"
                    "2.1 AC Repair\n"
                    "2.2 Refrigerator Repair\n"
                    "2.3 Washing Machine Repair\n"
                    "2.4 Microwave Repair\n"
                    "Type 'menu' to go back to the main menu."
                )
            elif user_text == "2.1":
                response_message = "Please share your AC brand name, description of the cooling issue, and your service address."
            elif user_text == "2.2":
                response_message = "Please share your Refrigerator brand name, cooling or electrical issue, and your location."
            elif user_text == "2.3":
                response_message = "Please share your Washing Machine brand name, error code or drum issue, and your location."
            elif user_text == "2.4":
                response_message = "Please share your Microwave brand name, heating or power issue, and your location."

            elif user_text == "3":
                response_message = (
                    "You selected *3. Maintenance related*.\n\n"
                    "Please choose an option:\n"
                    "3.1 Annual Maintenance Contract (AMC)\n"
                    "3.2 General Servicing Checkup\n"
                    "Type 'menu' to go back to the main menu."
                )
            elif user_text == "3.1":
                response_message = "Our team will reach out with AMC pricing plans and coverage details for your appliances."
            elif user_text == "3.2":
                response_message = "Please provide your appliance details to schedule a routine maintenance checkup."

            elif user_text == "4":
                response_message = (
                    "You selected *4. Parts related queries*.\n\n"
                    "Please choose an option:\n"
                    "4.1 Filter / Cartridge Replacement\n"
                    "4.2 General Spare Parts Inquiry\n"
                    "Type 'menu' to go back to the main menu."
                )
            elif user_text == "4.1":
                response_message = "Please share your water purifier or appliance model name to check filter availability."
            elif user_text == "4.2":
                response_message = "Please mention the exact spare part name or model number you are looking for."

            elif user_text.lower() in ["menu", "hi", "hello"]:
                response_message = (
                    "Dear Customer, thank you for messaging Radiant E Serve, a "
                    "Reliance Authorised Service Partner. Kindly let us know your query:\n\n"
                    "1. Installation/Demo related\n"
                    "2. Repair related\n"
                    "3. Maintenance related\n"
                    "4. Parts related queries"
                )
            else:
                response_message = (
                    "Thank you for your message. Type 'menu' anytime to see the main options list."
                )

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