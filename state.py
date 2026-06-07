# ===================================================
# state.py — Shared live state across all modules
# ===================================================

import time

veronica_state = {
    "status":        "idle",   # idle | listening | thinking | speaking
    "last_command":  "",
    "last_response": "",
    "log":           [],
    "stop_flag":     False,    # set True to abort current action
    "ai_available":  False
}

def check_stop():
    """Returns True if stop was requested, then resets the flag"""
    if veronica_state["stop_flag"]:
        veronica_state["stop_flag"] = False
        set_status("idle")
        return True
    return False

def set_status(s):
    veronica_state["status"] = s

def add_log(role, text):
    veronica_state["log"].append({
        "role": role,
        "text": str(text),
        "time": time.strftime("%H:%M:%S")
    })
    # Keep only last 50 entries
    if len(veronica_state["log"]) > 50:
        veronica_state["log"] = veronica_state["log"][-50:]

def clear_log():
    veronica_state["log"] = []