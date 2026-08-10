from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)

# In-memory storage for demonstration (replace with PostgreSQL/MongoDB in production)
ticket_database = []

# Webhook verification for Meta WhatsApp Cloud API
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    VERIFY_TOKEN = "radiant_secure_token_123"  # Set this in your Meta App dashboard
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Hello from Radiant e Serve Bot Server", 200

# Webhook to receive incoming messages from WhatsApp
@app.route("/webhook", methods=["POST"])
def handle_whatsapp_message():
    data = request.get_json()
    
    try:
        # Extract incoming message details from WhatsApp Payload structure
        if "entry" in data:
            change = data["entry"][0]["changes"][0]["value"]
            if "messages" in change:
                msg = change["messages"][0]
                sender_phone = msg["from"]
                message_body = msg["text"]["body"].strip()
                
                # Process the message through our conversational logic handler
                response_data = process_chat_logic(sender_phone, message_body)
                
                # Here you would normally use the Meta Cloud API to send `response_data` back to `sender_phone`
                print(f"Sending to {sender_phone}: {response_data}")

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# Simple state manager & problem capture function
user_sessions = {}

def process_chat_logic(phone, text):
    # Check if user has an active session, else start one
    if phone not in user_sessions:
        user_sessions[phone] = {"step": "MENU"}
        return "Welcome to Radiant e Serve 🛠️.\n1. Book a Repair\n2. General Support"
    
    state = user_sessions[phone]
    current_step = state["step"]
    
    if current_step == "MENU":
        if text == "1":
            state["step"] = "GET_DEVICE"
            return "What device or appliance needs service? (e.g., Mi Smartphone, LED TV, Home Appliance)"
        else:
            state["step"] = "GET_GENERAL_QUERY"
            return "Please type your general inquiry or problem statement:"
            
    elif current_step == "GET_DEVICE":
        state["device"] = text
        state["step"] = "GET_PROBLEM"
        return "Please describe the problem you are facing with your device:"
        
    elif current_step == "GET_PROBLEM":
        state["problem"] = text
        state["step"] = "DONE"
        
        # Generate Ticket & Store Data
        ticket_id = f"RES-{int(datetime.datetime.now().timestamp())}"
        ticket_payload = {
            "ticket_id": ticket_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "customer_phone": phone,
            "device": state.get("device", "General Inquiry"),
            "problem": state["problem"]
        }
        
        # Save to database
        ticket_database.append(ticket_payload)
        
        # Forward to Radiant e Serve (Trigger internal alert/email here)
        forward_to_radiant_esecreve(ticket_payload)
        
        # Reset session
        del user_sessions[phone]
        
        return f"Thank you! Your issue has been recorded. Ticket ID: {ticket_id}. Our team at Radiant e Serve will reach out soon."

    elif current_step == "GET_GENERAL_QUERY":
        ticket_id = f"RES-GEN-{int(datetime.datetime.now().timestamp())}"
        ticket_payload = {
            "ticket_id": ticket_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "customer_phone": phone,
            "problem": text
        }
        ticket_database.append(ticket_payload)
        forward_to_radiant_esecreve(ticket_payload)
        
        del user_sessions[phone]
        return f"We have received your message (Ticket: {ticket_id}). Support team will contact you shortly!"

def forward_to_radiant_esecreve(ticket):
    # Integration point: Send data via email (using SMTP/SendGrid) or an internal API endpoint 
    print("--- FORWARDING TO RADIANT E SERVE ---")
    print(ticket)
    print("-------------------------------------")

if __name__ == "__main__":
    app.run(port=5000, debug=True)