# ===================================================
# router.py — Routes commands to the right skill
# Optimized: fast matching, no unnecessary speak calls
# ===================================================

import re
import time
from voice import speak, listen 
from skills import (
    ask_ai, get_weather, google_search, youtube_search,
    wiki_search, detect_fake_news, get_recipe,
    take_note, read_notes
)


def process_command(command):
    if not command:
        return

    command = command.lower().strip()
    print(f"[ROUTER]: '{command}'")

    # ---- EXIT ----
    if command in ["exit", "quit", "stop", "bye", "goodbye"]:
        speak("Goodbye. Have a great day!")
        return

    # ---- TIME (check before 'what is') ----
    if "what time" in command or "current time" in command or command == "time" or "tell me the time" in command or "what's the time" in command:
        speak(f"The time is {time.strftime('%I:%M %p')}.")
        return

    # ---- DATE ----
    if "what day" in command or "what date" in command or "today" in command or command == "date" or "current date" in command or "tell me the date" in command:
        speak(f"Today is {time.strftime('%A, %B %d, %Y')}.")
        return

    # ---- RECIPE ----
    if any(t in command for t in [
        "recipe for", "recipe of", "how to make", "how do i make",
        "how to cook", "how do i cook", "how to prepare", "give me recipe"
    ]) or command.startswith("recipe"):
        dish = re.sub(
            r"^(give me a? ?recipe (for|of)?|recipe (for|of)?|"
            r"how (to|do i) (make|cook|prepare))\s*", "", command
        ).strip()
        if not dish:
            speak("What dish?")
            dish = listen(timeout=6)
        if dish:
            get_recipe(dish)
        return

    # ---- WEATHER ----
    if "weather" in command:
        match = re.search(r"(?:weather in|weather for|weather at)\s+(.+)", command)
        if match:
            get_weather(match.group(1).strip())
        elif " in " in command:
            get_weather(command.split(" in ")[-1].strip())
        else:
            speak("Which city?")
            city = listen(timeout=5)
            if city:
                get_weather(city)
        return

    # ---- GOOGLE ----
    if command.startswith("google") or "search google" in command:
        query = re.sub(r"^(google|search google for|google search)\s*", "", command).strip()
        google_search(query)
        return

    # ---- YOUTUBE ----
    if (command.startswith("youtube") or "search youtube" in command or
        command.startswith("open youtube") or "search on youtube" in command or
        command.startswith("play on youtube") or command.startswith("play youtube")):
        query = re.sub(
            r"^(youtube|open youtube|search youtube for|search on youtube for|search youtube|search on youtube|play on youtube|play youtube)\s*",
            "",
            command
        ).strip()
        youtube_search(query)
        return

    # ---- WIKIPEDIA ----
    if (command.startswith("who is") or command.startswith("who was") or command.startswith("what is") ):
        query = re.sub(
            r"^(who is|who was|what is|what are|tell me about)\s*", "", command
        ).strip()
        wiki_search(query)
        return

    # ---- NOTES ----
    if any(t in command for t in ["take a note", "write this down", "make a note", "note this"]):
        take_note()
        return

    if any(t in command for t in ["read my note", "read notes", "show notes", "what are my notes"]):
        read_notes()
        return

    # ---- FACT CHECK ----
    if any(t in command for t in [
        "fact check", "is it true", "is this true", "is that true",
        "verify this", "is it fake", "is this fake", "fake news"
    ]):
        claim = re.sub(
            r"^(fact check|is it true that?|is this true|is that true|"
            r"verify this|is it fake that?|is this fake|fake news)\s*",
            "", command
        ).strip()
        if not claim:
            speak("What claim?")
            claim = listen(timeout=10, phrase_limit=20)
        if claim:
            detect_fake_news(claim)
        return

    # ---- FALLBACK: LOCAL AI (no preamble speak = faster) ----
    state_set = __import__('state').set_status
    state_set("thinking")
    reply = ask_ai(command)
    if reply:
        speak(reply)