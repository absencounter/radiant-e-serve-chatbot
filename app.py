import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables from Render
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Your Google Sheets Web App URL
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx2FLbs_CNv2pZ2O7lHGKjoqHaiUDQAwYAEAhB8Aw8rZmn3mUvlAntgMBH-cjHuJyIW/exec"

# In-memory storage for sessions and rate-limiting cooldowns
user_sessions = {}
user_last_action_time = {}

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
            current_time = time.time()

            # --- RATE LIMIT / COOLDOWN CHECK (3 seconds) ---
            if recipient_phone in user_last_action_time:
                if current_time - user_last_action_time[recipient_phone] < 3.0:
                    return jsonify({"status": "rate_limited"}), 200
            
            user_last_action_time[recipient_phone] = current_time

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

            # --- MULTI-STEP FORM FLOW (Model Number Removed) ---
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
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_ADDRESS"
                send_whatsapp_message(recipient_phone, "Please enter your *current address* (6 digit pincode is mandatory):")
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
                    "Choose the appliance:",
                    [
                        {"id": "sub_1_1", "title": "AC Installation/Demo", "description": "Air Conditioner setup"},
                        {"id": "sub_1_2", "title": "Refrigerator Setup", "description": "Fridge installation/demo"},
                        {"id": "sub_1_3", "title": "Washing Machine Setup", "description": "Washing machine setup"},
                        {"id": "sub_1_4", "title": "Microwave Setup", "description": "Microwave demo/setup"},
                        {"id": "sub_1_5", "title": "TV Installation", "description": "Television wall mount/demo"},
                        {"id": "sub_1_6", "title": "Dishwasher Setup", "description": "Dishwasher installation"}
                    ]
                )
            elif user_text in ["opt_2", "2"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Repair Related",
                    "Choose the appliance for repair:",
                    [
                        {"id": "sub_2_1", "title": "AC Repair", "description": "Cooling or power issues"},
                        {"id": "sub_2_2", "title": "Refrigerator Repair", "description": "Freezing or cooling problems"},
                        {"id": "sub_2_3", "title": "Washing Machine Repair", "description": "Drum, spin or water issues"},
                        {"id": "sub_2_4", "title": "Microwave Repair", "description": "Heating or panel issues"},
                        {"id": "sub_2_5", "title": "TV Repair", "description": "Display or sound issues"},
                        {"id": "sub_2_6", "title": "Dishwasher Repair", "description": "Cleaning or draining issues"}
                    ]
                )
            elif user_text in ["opt_3", "3"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Maintenance Related",
                    "Choose the appliance for maintenance:",
                    [
                        {"id": "sub_3_1", "title": "AC Maintenance / AMC", "description": "AC servicing contract"},
                        {"id": "sub_3_2", "title": "Refrigerator Checkup", "description": "Fridge routine service"},
                        {"id": "sub_3_3", "title": "Washing Machine Service", "description": "Washing machine checkup"},
                        {"id": "sub_3_4", "title": "Microwave Service", "description": "Microwave routine checkup"},
                        {"id": "sub_3_5", "title": "TV Maintenance", "description": "Television checkup"},
                        {"id": "sub_3_6", "title": "Dishwasher Service", "description": "Dishwasher maintenance"}
                    ]
                )
            elif user_text in ["opt_4", "4"]:
                send_interactive_submenu(
                    recipient_phone,
                    "Parts Related Queries",
                    "Choose the appliance part:",
                    [
                        {"id": "sub_4_1", "title": "AC Spare Parts", "description": "AC components & filters"},
                        {"id": "sub_4_2", "title": "Refrigerator Parts", "description": "Fridge parts lookup"},
                        {"id": "sub_4_3", "title": "Washing Machine Parts", "description": "Washing machine spares"},
                        {"id": "sub_4_4", "title": "Microwave Parts", "description": "Microwave components"},
                        {"id": "sub_4_5", "title": "TV Spares", "description": "Television accessories/parts"},
                        {"id": "sub_4_6", "title": "Dishwasher Parts", "description": "Dishwasher components"}
                    ]
                )
            elif user_text.startswith("sub_"):
                service_mapping = {
                    # Installation / Demo
                    "sub_1_1": "Installation/Demo > AC",
                    "sub_1_2": "Installation/Demo > Refrigerator",
                    "sub_1_3": "Installation/Demo > Washing Machine",
                    "sub_1_4": "Installation/Demo > Microwave",
                    "sub_1_5": "Installation/Demo > TV",
                    "sub_1_6": "Installation/Demo > Dishwasher",
                    # Repair Related
                    "sub_2_1": "Repair Related > AC Repair",
                    "sub_2_2": "Repair Related > Refrigerator Repair",
                    "sub_2_3": "Repair Related > Washing Machine Repair",
                    "sub_2_4": "Repair Related > Microwave Repair",
                    "sub_2_5": "Repair Related > TV Repair",
                    "sub_2_6": "Repair Related > Dishwasher Repair",
                    # Maintenance Related
                    "sub_3_1": "Maintenance > AC Maintenance",
                    "sub_3_2": "Maintenance > Refrigerator Checkup",
                    "sub_3_3": "Maintenance > Washing Machine Service",
                    "sub_3_4": "Maintenance > Microwave Service",
                    "sub_3_5": "Maintenance > TV Maintenance",
                    "sub_3_6": "Maintenance > Dishwasher Service",
                    # Parts Queries
                    "sub_4_1": "Parts Queries > AC Parts",
                    "sub_4_2": "Parts Queries > Refrigerator Parts",
                    "sub_4_3": "Parts Queries > Washing Machine Parts",
                    "sub_4_4": "Parts Queries > Microwave Parts",
                    "sub_4_5": "Parts Queries > TV Parts",
                    "sub_4_6": "Parts Queries > Dishwasher Parts"
                }
                user_sessions[recipient_phone]["data"]["service"] = service_mapping.get(user_text, "General Request")
                user_sessions[recipient_phone]["state"] = "WAITING_FOR_BILLING_NAME"
                
                send_whatsapp_message(recipient_phone, f"You selected *{user_sessions[recipient_phone]['data']['service']}*.\n\nPlease enter your full *billing name*:")
            else:
                if current_state == "IDLE":
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
                        {"id": "opt_2", "title": "2. Repair Related", "description": "AC, Fridge, TV, Washing Machine, etc."},
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