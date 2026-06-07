# ===================================================
# config.py — All settings. Edit only this file.
# ===================================================

# Weather API (free key from openweathermap.org)
WEATHER_API_KEY = "YOUR API KEYS"

# Ollama local AI
OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3"

# Flask server
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

# Voice settings
LISTEN_TIMEOUT      = 6
LISTEN_PHRASE_LIMIT = 8
WAKE_WORD           = "veronica"
