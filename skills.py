# ===================================================
# skills.py — All Veronica features
# ===================================================

import webbrowser
import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError
import requests
import time
import os
import re
import subprocess
import shutil
from urllib.parse import quote_plus

from config import WEATHER_API_KEY, OLLAMA_URL, OLLAMA_MODEL
import state

# Lazy import to avoid circular imports
def _speak(text):
    from voice import speak
    speak(text)

def _listen(**kwargs):
    from voice import listen
    return listen(**kwargs)


def _is_ollama_cli_installed():
    return shutil.which("ollama") is not None


def _start_ollama_server():
    """Try to start the local Ollama server in the background."""
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
        print("[OLLAMA]: Starting local Ollama server...")
        return True
    except Exception as e:
        print(f"[OLLAMA START ERROR]: {e}")
        return False


class LocalAIError(Exception):
    pass


class LocalAIServerOffline(LocalAIError):
    pass


class LocalAIModelUnavailable(LocalAIError):
    pass


def _ensure_ollama_server():
    if _is_ollama_cli_installed():
        return _start_ollama_server()
    return False


def _post_ollama(payload, timeout=40):
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError:
        if _ensure_ollama_server():
            time.sleep(4)
            try:
                res = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            except requests.exceptions.ConnectionError:
                raise LocalAIServerOffline("Ollama is not running or cannot be reached.")
            else:
                return _validate_ollama_response(res)
        raise LocalAIServerOffline("Ollama is not running or cannot be reached.")

    return _validate_ollama_response(res)


def _validate_ollama_response(res):
    if res.status_code == 200:
        return res

    error_text = res.text.strip()
    try:
        payload = res.json()
        error_text = payload.get("error") or payload.get("message") or payload.get("detail") or error_text
    except Exception:
        pass

    if "model" in error_text.lower() or "not found" in error_text.lower() or "unavailable" in error_text.lower():
        raise LocalAIModelUnavailable(error_text)

    raise LocalAIError(error_text)


# ===================================================
# LOCAL AI (OLLAMA)
# ===================================================

def ask_ai(prompt):
    state.set_status("thinking")
    try:
        res = _post_ollama(
            {
                "model":  OLLAMA_MODEL,
                "prompt": f"You are Veronica, a voice assistant. Answer in 1-2 short sentences only. User: {prompt}",
                "stream": False
            },
            timeout=40
        )
        data = res.json()
        if "response" in data:
            return data["response"].strip()
        return "I could not get a response from local AI."

    except LocalAIServerOffline:
        print("[AI ERROR]: Ollama server offline")
        webbrowser.open(f"https://www.google.com/search?q={prompt}")
        return "Local AI is offline. I opened Google for you."
    except LocalAIModelUnavailable as e:
        print(f"[AI ERROR]: Model unavailable — {e}")
        return (
            "Local AI is online, but the configured model is unavailable. "
            "Please install the model or update `OLLAMA_MODEL` in config.py."
        )
    except LocalAIError as e:
        print(f"[AI ERROR]: {e}")
        webbrowser.open(f"https://www.google.com/search?q={prompt}")
        return "Local AI returned an error. I opened Google for you."
    except Exception as e:
        print(f"[AI ERROR]: {e}")
        webbrowser.open(f"https://www.google.com/search?q={prompt}")
        return "Something went wrong. I opened Google for you."


# ===================================================
# WEATHER
# ===================================================

def get_weather(city):
    if WEATHER_API_KEY == "YOUR_OPENWEATHER_KEY":
        _speak("Weather API key is not set. Please add your key in config dot py.")
        return
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
        )
        res  = requests.get(url, timeout=5)
        data = res.json()
        if res.status_code == 200:
            temp = data["main"]["temp"]
            feel = data["main"]["feels_like"]
            desc = data["weather"][0]["description"]
            _speak(
                f"In {city}, it is {temp} degrees Celsius, "
                f"feels like {feel}, with {desc}."
            )
        else:
            _speak(f"Sorry, I could not find weather for {city}.")
    except Exception as e:
        print(f"[WEATHER ERROR]: {e}")
        _speak("Unable to fetch weather right now.")


# ===================================================
# GOOGLE / YOUTUBE
# ===================================================

def google_search(query):
    if not query:
        _speak("What should I search on Google?")
        return
    _speak(f"Searching Google for {query}.")
    webbrowser.open(f"https://www.google.com/search?q={query}")

def youtube_search(query):
    if not query:
        _speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")
        return
    _speak(f"Searching YouTube for {query}.")
    webbrowser.open(
        f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    )


# ===================================================
# WIKIPEDIA
# ===================================================

def wiki_search(query):
    if not query:
        _speak("What would you like to know about?")
        return
    try:
        wikipedia.set_rate_limiting(False)
        result = wikipedia.summary(query, sentences=2, auto_suggest=False)
        _speak(result)
    except DisambiguationError as e:
        # Try the first option
        try:
            result = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
            _speak(result)
        except:
            _speak("Multiple results found. Please be more specific.")
    except PageError:
        _speak(f"I could not find a Wikipedia page for {query}.")
    except Exception as e:
        print(f"[WIKI ERROR]: {e}")
        _speak("Wikipedia search failed.")


# ===================================================
# FAKE NEWS DETECTOR
# ===================================================

def detect_fake_news(claim):
    if not claim:
        _speak("Please provide a claim to fact check.")
        return
    try:
    
        prompt = f"""Fact-check this claim. Reply ONLY in this format, no extra text:
VERDICT: [LIKELY TRUE/LIKELY FALSE/MISLEADING/UNVERIFIABLE]
CONFIDENCE: [HIGH/MEDIUM/LOW]
EXPLANATION: One sentence.
ADVICE: One sentence.
Claim: {claim}"""

        res  = _post_ollama(
            {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        data = res.json()

        if "response" in data:
            result_text = data["response"].strip()

            # Save to file
            os.makedirs("fact_checks", exist_ok=True)
            safe = re.sub(r"[^a-z0-9]+", "_", claim[:40].lower()).strip("_")
            filepath = os.path.join("fact_checks", f"{safe}.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Claim: {claim}\n{'='*40}\n\n{result_text}")

            print(f"\n[FACT CHECK]\n{result_text}\nSaved: {filepath}\n")

            # Speak only key lines
            lines  = result_text.splitlines()
            spoken = [l for l in lines if any(l.startswith(k) for k in ("VERDICT","CONFIDENCE","EXPLANATION","ADVICE"))]
            _speak(" ".join(spoken) if spoken else result_text)
        else:
            _speak("Fact check failed. No response from AI.")

    except requests.exceptions.ConnectionError:
        _speak("Local AI is offline. Cannot fact check right now.")
    except Exception as e:
        print(f"[FACT CHECK ERROR]: {e}")
        _speak("Sorry, fact check failed.")


# ===================================================
# RECIPE
# ===================================================

def get_recipe(name):
    if not name:
        _speak("What recipe would you like?")
        return
    try:
    
        prompt = f"""Give a recipe for {name}. Format:
INGREDIENTS: (dash list)
INSTRUCTIONS: (numbered)
TIME: total cooking time
TIPS: one tip"""

        res  = _post_ollama(
            {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=90
        )
        data = res.json()

        if "response" in data:
            recipe_text = data["response"].strip()

            os.makedirs("recipes", exist_ok=True)
            safe     = name.strip().lower().replace(" ", "_")
            filepath = os.path.join("recipes", f"{safe}.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Recipe: {name}\n{'='*40}\n\n{recipe_text}")

            print(f"\n[RECIPE]\n{recipe_text}\nSaved: {filepath}\n")
            _speak(f"Recipe for {name} is ready and saved. " + recipe_text[:200])
        else:
            _speak("Recipe generation failed.")

    except requests.exceptions.ConnectionError:
        _speak("Local AI is offline. Cannot generate recipe.")
    except Exception as e:
        print(f"[RECIPE ERROR]: {e}")
        _speak("Sorry, could not generate the recipe.")


# ===================================================
# NOTES
# ===================================================

def take_note():
    _speak("What should I write down?")
    note = _listen(timeout=12, phrase_limit=20)

    if not note:
        _speak("I did not hear anything. Note not saved.")
        return

    os.makedirs("notes", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join("notes", f"note_{timestamp}.txt")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n{note}")
        _speak("Note saved successfully.")
        print(f"[NOTE SAVED]: {filepath}")
    except Exception as e:
        print(f"[NOTE ERROR]: {e}")
        _speak("Failed to save note.")


def read_notes():
    if not os.path.exists("notes"):
        _speak("You have no saved notes.")
        return

    notes = sorted([f for f in os.listdir("notes") if f.endswith(".txt")])
    if not notes:
        _speak("You have no saved notes.")
        return

    filepath = os.path.join("notes", notes[-1])
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        _speak(f"Reading your latest note. {content}")
    except Exception as e:
        print(f"[READ NOTE ERROR]: {e}")
        _speak("Could not read the note.")