# main.py
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

app = Flask(__name__)

# This is the endpoint the instructor will call
@app.route('/api-endpoint', methods=['POST'])
def handle_request():
    print("✅ Request received!")
    data = request.get_json()

    # Verify the secret
    if data.get('secret') != os.getenv("MY_SECRET"):
        print("🚨 ERROR: Invalid secret!")
        return jsonify({"error": "Invalid secret"}), 403 # Forbidden

    print("✅ Secret verified successfully!")
    # TODO: Add the real logic here later.

    return jsonify({"status": "Request received and verified."}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)