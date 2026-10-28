import customtkinter as ctk
import threading
import ollama
import pyttsx3
import speech_recognition as sr
import pyaudio
import subprocess
import webbrowser
import datetime
import requests
import xml.etree.ElementTree as ET
import pyautogui
import psutil
import pyjokes
import os
import difflib

# -----------------------------
# YOUR IDENTITY (edit this!)
# -----------------------------
DEVELOPER_NAME = "Zedaan "          # <-- change this to your actual name
DEFAULT_CITY = "Pune"           # <-- change this to your city
# MIC: leave None for auto. If Jarvis picks the wrong mic, run test_mic_list.py,
# find your real mic number, and set MIC_INDEX to that number, e.g. MIC_INDEX = 1
MIC_INDEX = 1  # 1 = Microphone Array (Realtek) from your test list. Try 6, then 12, then 18 if this one is silent.

# -----------------------------
# FIND WORKING MIC (WASAPI + native sample rate)
# -----------------------------
# FIX 1 - MIC: auto-pick, but allow manual override, and never crash on start.
mic_device_index = MIC_INDEX
mic_sample_rate = 16000
try:
    if mic_device_index is None:
        p = pyaudio.PyAudio()
        wasapi_index = None
        for i in range(p.get_host_api_count()):
            info = p.get_host_api_info_by_index(i)
            if "WASAPI" in info["name"]:
                wasapi_index = i
                break
        if wasapi_index is not None:
            mic_device_index = p.get_host_api_info_by_index(wasapi_index)["defaultInputDevice"]
            device_info = p.get_device_info_by_index(mic_device_index)
            mic_sample_rate = int(device_info["defaultSampleRate"])
        else:
            mic_device_index = p.get_default_input_device_info()["index"]
            mic_sample_rate = int(p.get_default_input_device_info()["defaultSampleRate"])
        p.terminate()
except Exception as e:
    print(f"Mic auto-detect failed, will try default mic at listen time. Error: {e}")
    mic_device_index = MIC_INDEX

# -----------------------------
# SETTINGS
# -----------------------------
MODEL = "llama3.2"

recognizer = sr.Recognizer()
recognizer.pause_threshold = 1
recognizer.energy_threshold = 200

conversation = [
    {
        "role": "system",
        "content": (
            f"You are Jarvis, an intelligent AI assistant. "
            f"You were built and are maintained by {DEVELOPER_NAME}, who is your developer and creator. "
            f"Always treat {DEVELOPER_NAME} with respect as your developer. "
            f"Be helpful, concise, friendly, and conversational. If the user asks to open an app or website, do not refuse for safety - just say you will open it."
        ),
    }
]

# -----------------------------
# TEXT TO SPEECH
# -----------------------------
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()
    engine.stop()

# -----------------------------
# SPEECH RECOGNITION
# -----------------------------
def listen():
    # FIX 1 continued - MIC: use default mic if auto-detect failed, listen longer,
    # and use en-IN for Indian English accents. Print the real reason on failure.
    try:
        mic = sr.Microphone(device_index=mic_device_index, sample_rate=mic_sample_rate, chunk_size=1024) if mic_device_index is not None else sr.Microphone()
    except Exception as e:
        print(f"Could not open mic: {e}")
        return None
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening... speak now, loud and clear, close to the mic.")
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("Mic timeout: no speech heard in 10 seconds.")
            return None
    for lang in ["en-IN", "en-US"]:
        try:
            text = recognizer.recognize_google(audio, language=lang)
            print(f"Heard ({lang}): {text}")
            return text.lower()
        except sr.UnknownValueError:
            print(f"Could not understand with {lang}, trying next language...")
            continue
        except sr.RequestError as e:
            print(f"Google speech service failed (check internet): {e}")
            return None
    print("Google could not understand the audio - speak louder / closer / less background noise.")
    return None

# -----------------------------
# SKILL: WEATHER (Open-Meteo, free, no API key)
# -----------------------------
def get_weather(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_resp = requests.get(geo_url, timeout=10).json()

        if "results" not in geo_resp:
            return f"Sorry, I couldn't find a place called {city}."

        lat = geo_resp["results"][0]["latitude"]
        lon = geo_resp["results"][0]["longitude"]
        place_name = geo_resp["results"][0]["name"]

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_resp = requests.get(weather_url, timeout=10).json()

        current = weather_resp["current_weather"]
        temp = current["temperature"]
        wind = current["windspeed"]

        return f"The current weather in {place_name} is {temp} degrees Celsius, with wind speed of {wind} kilometers per hour."

    except Exception as e:
        return f"Sorry, I couldn't fetch the weather. Error: {e}"

# -----------------------------
# SKILL: NEWS HEADLINES (BBC RSS, free, no API key)
# -----------------------------
def get_news():
    try:
        url = "http://feeds.bbci.co.uk/news/rss.xml"
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.content)

        headlines = []
        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            headlines.append(title)

        if not headlines:
            return "I couldn't find any news headlines right now."

        return "Here are the top headlines: " + ". ".join(headlines)

    except Exception as e:
        return f"Sorry, I couldn't fetch the news. Error: {e}"

# -----------------------------
# SKILL: DATE & TIME
# -----------------------------
def get_datetime_reply():
    now = datetime.datetime.now()
    return f"It's currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."

# -----------------------------
# SKILL: GOOGLE MAPS
# -----------------------------
def open_maps(place):
    url = f"https://www.google.com/maps/search/{place.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Opening Google Maps for {place}."

# -----------------------------
# SKILL: WIKIPEDIA (free public REST API, no key)
# -----------------------------
def get_wikipedia_summary(topic):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        headers = {"User-Agent": "JarvisAssistant/1.0 (personal project; contact@example.com)"}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return f"Sorry, I couldn't find anything about {topic} on Wikipedia."

        data = resp.json()

        if "extract" not in data:
            return f"Sorry, I couldn't find anything about {topic} on Wikipedia."

        extract = data["extract"]
        sentences = extract.split(". ")
        short_version = ". ".join(sentences[:3])
        return short_version

    except Exception as e:
        return f"Sorry, I couldn't reach Wikipedia. Error: {e}"

# -----------------------------
# SKILL: SCREENSHOT (offline, no key)
# -----------------------------
def take_screenshot():
    try:
        folder = os.path.join(os.path.expanduser("~"), "Desktop", "jarvis", "screenshots")
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"screenshot_{timestamp}.png")

        img = pyautogui.screenshot()
        img.save(filepath)

        return f"Screenshot saved to {filepath}."
    except Exception as e:
        return f"Sorry, I couldn't take a screenshot. Error: {e}"

# -----------------------------
# SKILL: SYSTEM INFO (offline, no key)
# -----------------------------
def get_system_info():
    try:
        battery = psutil.sensors_battery()
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent

        parts = [f"CPU usage is {cpu} percent", f"RAM usage is {ram} percent"]

        if battery:
            plugged = "plugged in" if battery.power_plugged else "on battery"
            parts.append(f"battery is at {battery.percent} percent, {plugged}")

        return ". ".join(parts) + "."
    except Exception as e:
        return f"Sorry, I couldn't get system info. Error: {e}"

# -----------------------------
# SKILL: JOKE (fully offline, no key)
# -----------------------------
def tell_joke():
    try:
        return pyjokes.get_joke()
    except Exception as e:
        return f"Sorry, I couldn't think of a joke. Error: {e}"

# -----------------------------
# SKILL: OPEN WEBSITE (offline, no key)
# -----------------------------
def open_website(site):
    site = site.strip()
    known_sites = {
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "reddit": "https://reddit.com",
        "whatsapp": "https://web.whatsapp.com",
    }
    # Typo tolerance: "ytoutbe" -> "youtube", "gogle" -> "google"
    if site not in known_sites:
        close = difflib.get_close_matches(site, known_sites.keys(), n=1, cutoff=0.6)
        if close:
            site = close[0]
    if site in known_sites:
        url = known_sites[site]
    elif "." in site:
        url = "https://" + site
    else:
        url = f"https://{site}.com"

    webbrowser.open(url)
    return f"Opening {site}."

# -----------------------------
# SKILLS ROUTER
# -----------------------------
def handle_command(command):
    # FIX 2 - YOUTUBE / OPEN: catch this BEFORE the LLM, even with typos like "ytoutbe".
    # The old code only worked for the exact word "youtube", so "ytoutbe" fell through to the LLM,
    # and the LLM refused. Now we catch open/launch + any youtube-like word first.
    if ("open" in command or "launch" in command or "start" in command) and any(
        w in command for w in ["youtube", "ytube", "ytoutbe", "youtub", "utube", "yt "]
    ):
        return open_website("youtube")
    # WhatsApp: can OPEN WhatsApp Web, but CANNOT send a message by contact name.
    # The LLM used to pretend it sent a message - this guard stops that lie.
    if "whatsapp" in command:
        if "message" in command or "send" in command:
            webbrowser.open("https://web.whatsapp.com")
            return "I opened WhatsApp Web for you, but I cannot send a message by name like Prajwal, and I do not have your contacts or WhatsApp login in code. To send, you need to pick the chat in WhatsApp Web and press Send yourself. If you give me a phone number, I can open a pre-filled chat link for that number."
        return open_website("whatsapp")
    if "open chrome" in command:
        subprocess.Popen("start chrome", shell=True)
        return "Opening Chrome."

    elif "open notepad" in command:
        subprocess.Popen("notepad")
        return "Opening Notepad."

    elif "open vs code" in command or "open visual studio code" in command:
        subprocess.Popen("code", shell=True)
        return "Opening VS Code."

    elif "weather" in command:
        if " in " in command:
            city = command.split(" in ")[-1].strip()
        else:
            city = DEFAULT_CITY
        return get_weather(city)

    elif "news" in command or "headline" in command:
        return get_news()

    elif "time" in command or "date" in command:
        return get_datetime_reply()

    elif "map" in command or "directions to" in command or "where is" in command:
        for trigger in ["show map of", "open maps for", "map of", "directions to", "where is"]:
            if trigger in command:
                place = command.split(trigger)[-1].strip()
                return open_maps(place)
        return open_maps(command.replace("map", "").strip())

    elif "who am i" in command or "about me" in command or "who is my developer" in command:
        return (
            f"You are {DEVELOPER_NAME}, my creator and developer. "
            f"You built me from scratch, debugged my microphone drivers, "
            f"and taught me to listen, speak, and help you with real tasks. "
            f"I exist because of your work."
        )

    elif "wikipedia" in command or command.startswith("who is") or command.startswith("what is"):
        for trigger in ["wikipedia", "who is", "what is"]:
            if trigger in command:
                topic = command.split(trigger)[-1].strip()
                if topic:
                    return get_wikipedia_summary(topic)
        return None

    elif "screenshot" in command:
        return take_screenshot()

    elif "system info" in command or "battery" in command or "cpu" in command or "ram" in command:
        return get_system_info()

    elif "joke" in command:
        return tell_joke()

    elif "open" in command and ("website" in command or "youtube" in command or "github" in command or "reddit" in command or "gmail" in command):
        for trigger in ["open website", "open"]:
            if trigger in command:
                site = command.split(trigger)[-1].strip()
                if site:
                    return open_website(site)
        return None

    else:
        return None

# -----------------------------
# CORE: process a message (typed or spoken), return reply text
# -----------------------------
def get_reply(user_input):
    skill_reply = handle_command(user_input)
    if skill_reply:
        return skill_reply

    conversation.append({"role": "user", "content": user_input})
    try:
        response = ollama.chat(model=MODEL, messages=conversation)
        reply = response["message"]["content"]
    except Exception as e:
        return "Sorry, I cannot connect to Ollama. Make sure it's running."

    conversation.append({"role": "assistant", "content": reply})
    return reply

# =====================================================
# GUI
# =====================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Jarvis")
app.geometry("600x700")

chat_box = ctk.CTkTextbox(app, width=560, height=550, font=("Segoe UI", 14))
chat_box.pack(padx=20, pady=(20, 10))
chat_box.configure(state="disabled")

def add_message(sender, text):
    chat_box.configure(state="normal")
    chat_box.insert("end", f"{sender}: {text}\n\n")
    chat_box.configure(state="disabled")
    chat_box.see("end")

def process_and_reply(user_input):
    add_message("You", user_input)
    reply = get_reply(user_input)
    add_message("Jarvis", reply)
    speak(reply)

def on_send():
    text = entry.get().strip()
    if not text:
        return
    entry.delete(0, "end")
    threading.Thread(target=process_and_reply, args=(text,), daemon=True).start()

def on_mic():
    def listen_and_process():
        add_message("System", "Listening...")
        heard = listen()
        if heard is None:
            add_message("System", "Didn't catch that. Speak louder, closer to the mic, and check Windows Sound > Input mic bar moves. Or type it instead.")
            return
        process_and_reply(heard)

    threading.Thread(target=listen_and_process, daemon=True).start()

bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(padx=20, pady=(0, 20), fill="x")

entry = ctk.CTkEntry(bottom_frame, placeholder_text="Type a message...", font=("Segoe UI", 14))
entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
entry.bind("<Return>", lambda event: on_send())

send_button = ctk.CTkButton(bottom_frame, text="Send", width=70, command=on_send)
send_button.pack(side="left", padx=(0, 10))

mic_button = ctk.CTkButton(bottom_frame, text="🎤 Talk", width=90, command=on_mic)
mic_button.pack(side="left")

add_message("Jarvis", f"Online. Hello {DEVELOPER_NAME}, how can I help you?")
threading.Thread(target=speak, args=(f"Jarvis online. Hello {DEVELOPER_NAME}, how can I help you?",), daemon=True).start()

app.mainloop()