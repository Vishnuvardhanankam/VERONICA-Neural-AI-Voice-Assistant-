# ===================================================
# server.py — Flask API + serves frontend
# ===================================================

import threading
import os
import time
import requests
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import state
from voice import speak, listen
from router import process_command
from config import SERVER_HOST, SERVER_PORT, WAKE_WORD, OLLAMA_URL, OLLAMA_MODEL

app    = Flask(__name__)
CORS(app)
BASE   = os.path.dirname(os.path.abspath(__file__))

# Thread pool for fast command processing (no thread spawn delay)
executor = ThreadPoolExecutor(max_workers=4)


def _is_ollama_cli_installed():
    return shutil.which("ollama") is not None


def _start_ollama_server():
    if not _is_ollama_cli_installed():
        print("[OLLAMA ERROR]: 'ollama' CLI not found in PATH.")
        return False

    try:
        if os.name == "nt":
            subprocess.Popen(
                ["cmd", "/c", "start", "", "ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                shell=False,
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
        print("[OLLAMA]: Attempting to start local Ollama server...")
        return True
    except Exception as e:
        print(f"[OLLAMA START ERROR]: {e}")
        return False


def _wait_for_ollama(timeout=12, interval=2):
    start = time.time()
    while time.time() - start < timeout:
        try:
            res = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": "Health check.", "stream": False},
                timeout=4
            )
            data = res.json()
            if res.status_code == 200 and "response" in data:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def check_ollama_health():
    try:
        res = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": "Health check.", "stream": False},
            timeout=4
        )
        data = res.json()
        return res.status_code == 200 and "response" in data
    except requests.exceptions.ConnectionError:
        if _start_ollama_server():
            print("[OLLAMA]: Waiting for server to become available...")
            return _wait_for_ollama()
        return False
    except Exception:
        return False


def ollama_health_loop():
    while True:
        state.veronica_state["ai_available"] = check_ollama_health()
        time.sleep(5)

# ===================================================
# SERVE FRONTEND
# ===================================================

@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")

@app.route("/style.css")
def css():
    return send_from_directory(BASE, "style.css")

@app.route("/app.js")
def js():
    return send_from_directory(BASE, "app.js")

@app.route("/logo.png")
def logo():
    return send_from_directory(BASE, "logo.png")

# ===================================================
# API ROUTES
# ===================================================

@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(state.veronica_state)

@app.route("/api/command", methods=["POST"])
def receive_command():
    try:
        data    = request.get_json(force=True)
        command = data.get("command", "").lower().strip()
        if not command:
            return jsonify({"error": "Empty command"}), 400

        state.veronica_state["last_command"] = command
        state.add_log("user", command)

        executor.submit(process_command, command)

        return jsonify({"status": "processing", "command": command})
    except Exception as e:
        print(f"[API ERROR]: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/listen", methods=["POST"])
def trigger_listen():
    def _do():
        cmd = listen()
        if cmd:
            process_command(cmd)
        else:
            speak("I did not catch that. Please try again.")

    executor.submit(_do)
    return jsonify({"status": "listening"})

@app.route("/api/log", methods=["GET"])
def get_log():
    return jsonify(state.veronica_state["log"])

@app.route("/api/clear_log", methods=["POST"])
def clear_log():
    state.clear_log()
    return jsonify({"status": "cleared"})

@app.route("/api/stop", methods=["POST"])
def stop_processing():
    """Stop current processing and reset to idle/standby"""
    state.set_status("idle")
    state.veronica_state["last_response"] = "Stopped. Say Veronica to wake me again."
    state.add_log("veronica", "Stopped. Say Veronica to wake me again.")
    # Signal voice loop to stop current action
    state.veronica_state["stop_flag"] = True
    return jsonify({"status": "stopped"})

# ===================================================
# VOICE WAKE WORD LOOP
# ===================================================

def voice_loop():
    speak("Veronica activated. Say Veronica to wake me.")
    while True:
        try:
            print(f"\n[VOICE LOOP]: Waiting for wake word '{WAKE_WORD}'...")
            wake = listen(timeout=10, phrase_limit=4)
            if wake and WAKE_WORD in wake:
                speak("Yes? How can I help you?")
                cmd = listen(timeout=8, phrase_limit=10)
                if cmd:
                    process_command(cmd)
                else:
                    speak("I did not hear a command.")
        except Exception as e:
            print(f"[VOICE LOOP ERROR]: {e}")

# ===================================================
# ENTRY POINT
# ===================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  VERONICA AI ASSISTANT")
    print("="*50)

    # Attempt to start local AI if needed, then start health monitor and voice loop
    state.veronica_state["ai_available"] = check_ollama_health()
    if state.veronica_state["ai_available"]:
        print("[OLLAMA]: Local AI is online.")
    else:
        print("[OLLAMA]: Local AI is offline. Ensure Ollama is installed and the model is available.")

    threading.Thread(target=ollama_health_loop, daemon=True).start()
    threading.Thread(target=voice_loop, daemon=True).start()

    print(f"\n  ✅ Server starting...")
    print(f"  🌐 Open browser → http://127.0.0.1:{SERVER_PORT}")
    print(f"  🎙  Say '{WAKE_WORD}' to activate voice")
    print(f"  ⌨  Or type commands in the UI")
    print("\n" + "="*50 + "\n")

    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )