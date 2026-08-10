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
            
            # Check if the user typed text OR clicked an interactive list option
            user_text = ""
            if "text" in message:
                user_text = message["text"]["body"].strip().lower()
            elif "interactive" in message:
                # Extracts the ID of the list option they clicked (e.g., "opt_1", "opt_2.1")
                interactive_type = message["interactive"]["type"]
                if interactive_type == "list_reply":
                    user_text = message["interactive"]["list_reply"]["id"]

            # Handle choices based on button/list IDs or typed text
            if user_text in ["opt_1", "1"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Installation / Demo related",
                    "Please choose an option:",
                    [
                        {"id": "opt_1_1", "title": "New Installation", "description": "Setup a new appliance"},
                        {"id": "opt_1_2", "title": "Demo Request", "description": "Book a product demo"}
                    ]
                )
            elif user_text == "opt_1_1":
                send_whatsapp_message(recipient_phone, "Please share your appliance name, address, and preferred date for the new installation.")
            elif user_text == "opt_1_2":
                send_whatsapp_message(recipient_phone, "Please share your appliance name and preferred time slot for a product demo.")

            elif user_text in ["opt_2", "2"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Repair Related",
                    "Please choose your appliance for repair:",
                    [
                        {"id": "opt_2_1", "title": "AC Repair", "description": "Cooling or power issues"},
                        {"id": "opt_2_2", "title": "Refrigerator Repair", "description": "Freezing or cooling problems"},
                        {"id": "opt_2_3", "title": "Washing Machine", "description": "Drum, spin or water issues"},
                        {"id": "opt_2_4", "title": "Microwave Repair", "description": "Heating or panel issues"}
                    ]
                )
            elif user_text == "opt_2_1":
                send_whatsapp_message(recipient_phone, "Please share your AC brand name, issue description, and service address.")
            elif user_text == "opt_2_2":
                send_whatsapp_message(recipient_phone, "Please share your Refrigerator brand name, issue, and location.")
            elif user_text == "opt_2_3":
                send_whatsapp_message(recipient_phone, "Please share your Washing Machine brand name, error code, and location.")
            elif user_text == "opt_2_4":
                send_whatsapp_message(recipient_phone, "Please share your Microwave brand name, issue, and location.")

            elif user_text in ["opt_3", "3"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Maintenance Related",
                    "Please choose an option:",
                    [
                        {"id": "opt_3_1", "title": "AMC Plans", "description": "Annual Maintenance Contracts"},
                        {"id": "opt_3_2", "title": "General Checkup", "description": "Routine maintenance service"}
                    ]
                )
            elif user_text == "opt_3_1":
                send_whatsapp_message(recipient_phone, "Our team will reach out with AMC pricing plans and coverage details.")
            elif user_text == "opt_3_2":
                send_whatsapp_message(recipient_phone, "Please provide your appliance details to schedule a routine checkup.")

            elif user_text in ["opt_4", "4"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Parts Related Queries",
                    "Please choose an option:",
                    [
                        {"id": "opt_4_1", "title": "Filter Replacement", "description": "Water purifier filters/cartridges"},
                        {"id": "opt_4_2", "title": "Spare Parts Inquiry", "description": "General parts lookup"}
                    ]
                )
            elif user_text == "opt_4_1":
                send_whatsapp_message(recipient_phone, "Please share your water purifier or appliance model name.")
            elif user_text == "opt_4_2":
                send_whatsapp_message(recipient_phone, "Please mention the exact spare part name or model number.")

            elif user_text in ["menu", "hi", "hello", "back"]:
                send_main_menu(recipient_phone)
            else:
                send_main_menu(recipient_phone)

    except Exception as e:
        print(f"Error processing webhook: {e}")

    return jsonify({"status": "success"}), 200

def send_main_menu(phone_number):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Radiant E Serve"},
            "body": {"text": "Dear Customer, thank you for messaging Radiant E Serve, a Reliance Authorised Service Partner. Kindly select your query below:"},
            "footer": {"text": "Service Support Bot"},
            "action": {
                "button": "Select Query",
                "sections": [{
                    "title": "Main Options",
                    "rows": [
                        {"id": "opt_1", "title": "1. Installation/Demo", "description": "New setup or demo request"},
                        {"id": "opt_2", "title": "2. Repair Related", "description": "AC, Fridge, Washing Machine, etc."},
                        {"id": "opt_3", "title": "3. Maintenance", "description": "AMC and routine servicing"},
                        {"id": "opt_4", "title": "4. Parts Queries", "description": "Filters and spare parts"}
                    ]
                }]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

def send_interactive_submenu(phone_number, title, body_text, options):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    rows = [{"id": opt["id"], "title": opt["title"], "description": opt["description"]} for opt in options]
    # Add a back to menu option
    rows.append({"id": "menu", "title": "Main Menu", "description": "Go back to start"})

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": title},
            "body": {"text": body_text},
            "footer": {"text": "Radiant E Serve"},
            "action": {
                "button": "Choose Option",
                "sections": [{"title": "Choices", "rows": rows}]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

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
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)