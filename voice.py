# ===================================================
# voice.py — Speak (TTS) and Listen (STT)
# Optimized for minimum latency
# ===================================================

import speech_recognition as sr
import time
import os
import uuid
import threading
import queue
from gtts import gTTS
import pygame

import state
from config import LISTEN_TIMEOUT, LISTEN_PHRASE_LIMIT

# ---- Init pygame mixer once globally ----
pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
pygame.mixer.init()

# ---- Recognizer with fast settings ----
recognizer = sr.Recognizer()
recognizer.energy_threshold        = 300
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold          = 0.6   # faster end-of-speech detection
recognizer.non_speaking_duration    = 0.4   # shorter silence before cutoff
recognizer.phrase_threshold         = 0.3

# ---- TTS cache: avoid re-generating identical phrases ----
_tts_cache = {}
_CACHE_MAX  = 20  # keep last 20 phrases cached

# ---- Pre-generate common phrases at startup ----
COMMON_PHRASES = [
    "How can I help you?",
    "Let me think about that.",
    "I did not catch that. Please try again.",
    "Stopped. Say Veronica to wake me again.",
    "Yes? How can I help you?",
]

def _generate_audio(text):
    """Generate MP3 bytes for text, use cache if available"""
    if text in _tts_cache:
        return _tts_cache[text]

    filename = f"voice_{uuid.uuid4().hex}.mp3"
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(filename)

    # Read bytes into memory and delete file
    with open(filename, 'rb') as f:
        audio_bytes = f.read()
    os.remove(filename)

    # Cache it
    if len(_tts_cache) >= _CACHE_MAX:
        # Remove oldest entry
        oldest = next(iter(_tts_cache))
        del _tts_cache[oldest]
    _tts_cache[text] = audio_bytes
    return audio_bytes


def _prewarm_cache():
    """Pre-generate audio for common phrases in background at startup"""
    def _do():
        for phrase in COMMON_PHRASES:
            try:
                _generate_audio(phrase)
                print(f"[TTS CACHE]: Prewarmed — '{phrase[:30]}'")
            except Exception as e:
                print(f"[TTS CACHE ERROR]: {e}")
    t = threading.Thread(target=_do, daemon=True)
    t.start()


def speak(text):
    """Convert text to speech — fast path with cache"""
    if not text:
        return

    text = str(text).strip()
    # Truncate very long responses to first 3 sentences for speed
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) > 3:
        text = '. '.join(sentences[:3]) + '.'

    print(f"\n[VERONICA]: {text}")

    state.set_status("speaking")
    state.veronica_state["last_response"] = text
    state.add_log("veronica", text)

    if state.check_stop():
        print("[SPEAK]: Stopped before speaking.")
        state.set_status("idle")
        return

    try:
        # Get audio bytes (from cache or generate)
        audio_bytes = _generate_audio(text)

        # Write to temp file for pygame
        tmp = f"play_{uuid.uuid4().hex}.mp3"
        with open(tmp, 'wb') as f:
            f.write(audio_bytes)

        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.04)
            if state.check_stop():
                pygame.mixer.music.stop()
                print("[SPEAK]: Stopped mid-speech.")
                break

        pygame.mixer.music.unload()

        if os.path.exists(tmp):
            os.remove(tmp)

    except Exception as e:
        print(f"[SPEAK ERROR]: {e}")

    state.set_status("idle")


def listen(timeout=LISTEN_TIMEOUT, phrase_limit=LISTEN_PHRASE_LIMIT):
    """Listen from mic — returns recognized text as lowercase string"""
    state.set_status("listening")
    print("[VERONICA]: Listening...")

    try:
        with sr.Microphone() as source:
            # Shorter noise adjustment = faster response
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )

        text = recognizer.recognize_google(audio)
        text = text.lower().strip()
        print(f"[YOU]: {text}")

        state.veronica_state["last_command"] = text
        state.add_log("user", text)
        state.set_status("thinking")
        return text

    except sr.WaitTimeoutError:
        print("[LISTEN]: Timeout")
    except sr.UnknownValueError:
        print("[LISTEN]: Could not understand")
    except sr.RequestError as e:
        print(f"[LISTEN ERROR]: {e}")
    except Exception as e:
        print(f"[LISTEN ERROR]: {e}")

    state.set_status("idle")
    return ""


# Pre-warm TTS cache when this module is imported
_prewarm_cache()