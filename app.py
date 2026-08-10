import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables from Render
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Your updated Google Sheets Web App URL for Radiant E Serve Leads V2
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx2FLbs_CNv2pZ2O7lHGKjoqHaiUDQAwYAEAhB8Aw8rZmn3mUvlAntgMBH-cjHuJyIW/exec"

# In-memory storage for collecting user details step-by-step
user_sessions = {}

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
            
            # Extract user text or interactive response ID
            user_text = ""
            if "text" in message:
                user_text = message["text"]["body"].strip()
            elif "interactive" in message:
                interactive_type = message["interactive"]["type"]
                if interactive_type == "list_reply":
                    user_text = message["interactive"]["list_reply"]["id"]

            # Initialize session if not exists
            if recipient_phone not in user_sessions:
                user_sessions[recipient_phone] = {"state": "IDLE", "data": {}}

            current_state = user_sessions[recipient_phone]["state"]

            # Reset or Menu triggers
            if user_text.lower() in ["menu", "hi", "hello", "back"]:
                user_sessions[recipient_phone] = {"state": "IDLE", "data": {}}
                send_main_menu(recipient_phone)
                return jsonify({"status": "success"}), 200

            # --- MULTI-STEP FORM FLOW ---
            if current_state == "WAITING_FOR_BILLING_NAME":
                user_sessions[recipient_phone]["data"]["billing_name"] = user_text
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_REG_PHONE"
                send_whatsapp_message(recipient_phone, "Please enter your *registered phone number* (the number given while purchasing):")
                return jsonify({"status": "success"}), 200

            elif current_state == "WAITING_FOR_REG_PHONE":
                user_sessions[recipient_phone]["data"]["reg_phone"] = user_text
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_BRAND"
                send_whatsapp_message(recipient_phone, "Please enter the appliance *brand name* (e.g., Voltas, LG, Samsung):")
                return jsonify({"status": "success"}), 200

            elif current_state == "WAITING_FOR_BRAND":
                user_sessions[recipient_phone]["data"]["brand"] = user_text
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_MODEL"
                send_whatsapp_message(recipient_phone, "Please enter the appliance *model number*:")
                return jsonify({"status": "success"}), 200

            elif current_state == "WAITING_FOR_MODEL":
                user_sessions[recipient_phone]["data"]["model"] = user_text
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_ADDRESS"
                send_whatsapp_message(recipient_phone, "Please enter your *current address with pincode*:")
                return jsonify({"status": "success"}), 200

            elif current_state == "WAITING_FOR_ADDRESS":
                user_sessions[recipient_phone]["data"]["address"] = user_text
                
                # Grab the full collected data dictionary
                lead_data = user_sessions[recipient_phone]["data"]
                
                # Save lead data to Google Sheet automatically
                try:
                    requests.post(GOOGLE_SHEET_WEB_APP_URL, json=lead_data, timeout=5)
                except Exception as e:
                    print(f"Failed to save to Google Sheet: {e}")

                # Finalize submission summary
                summary = (
                    "✅ *Request Submitted Successfully!*\n\n"
                    f"📌 *Service Type:* {lead_data.get('service')}\n"
                    f"👤 *Billing Name:* {lead_data.get('billing_name')}\n"
                    f"📞 *Registered Phone:* {lead_data.get('reg_phone')}\n"
                    f"🏷️ *Brand:* {lead_data.get('brand')}\n"
                    f"🔢 *Model Number:* {lead_data.get('model')}\n"
                    f"📍 *Address:* {lead_data.get('address')}\n\n"
                    "Our support executive will contact you shortly. Type 'menu' to start over."
                )
                send_whatsapp_message(recipient_phone, summary)
                
                # Reset session state
                user_sessions[recipient_phone] = {"state": "IDLE", "data": {}}
                return jsonify({"status": "success"}), 200

            # --- INITIAL MENU SELECTIONS ---
            if user_text in ["opt_1", "1"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Installation / Demo related",
                    "Please choose an option:",
                    [
                        {"id": "sub_1_1", "title": "New Installation", "description": "Setup a new appliance"},
                        {"id": "sub_1_2", "title": "Demo Request", "description": "Book a product demo"}
                    ]
                )
            elif user_text in ["opt_2", "2"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Repair Related",
                    "Please choose your appliance for repair:",
                    [
                        {"id": "sub_2_1", "title": "AC Repair", "description": "Cooling or power issues"},
                        {"id": "sub_2_2", "title": "Refrigerator Repair", "description": "Freezing or cooling problems"},
                        {"id": "sub_2_3", "title": "Washing Machine", "description": "Drum, spin or water issues"},
                        {"id": "sub_2_4", "title": "Microwave Repair", "description": "Heating or panel issues"}
                    ]
                )
            elif user_text in ["opt_3", "3"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Maintenance Related",
                    "Please choose an option:",
                    [
                        {"id": "sub_3_1", "title": "AMC Plans", "description": "Annual Maintenance Contracts"},
                        {"id": "sub_3_2", "title": "General Checkup", "description": "Routine maintenance service"}
                    ]
                )
            elif user_text in ["opt_4", "4"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Parts Related Queries",
                    "Please choose an option:",
                    [
                        {"id": "sub_4_1", "title": "Filter Replacement", "description": "Water purifier filters/cartridges"},
                        {"id": "sub_4_2", "title": "Spare Parts Inquiry", "description": "General parts lookup"}
                    ]
                )
            elif user_text.startswith("sub_"):
                service_map = {
                    "sub_1_1": "New Appliance Installation",
                    "sub_1_2": "Product Demo Request",
                    "sub_2_1": "AC Repair",
                    "sub_2_2": "Refrigerator Repair",
                    "sub_2_3": "Washing Machine Repair",
                    "sub_2_4": "Microwave Repair",
                    "sub_3_1": "Annual Maintenance Contract (AMC)",
                    "sub_3_2": "General Servicing Checkup",
                    "sub_4_1": "Filter / Cartridge Replacement",
                    "sub_4_2": "General Spare Parts Inquiry"
                }
                user_sessions[recipient_phone]["data"]["service"] = service_map.get(user_text, "General Request")
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_BILLING_NAME"
                
                send_whatsapp_message(recipient_phone, f"You selected *{user_sessions[recipient_phone]['data']['service']}*.\n\nPlease enter your full *billing name*:")
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