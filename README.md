# JARVIS - AI Voice Assistant

A desktop AI voice assistant built in Python, with a dark HUD-style window.
Type a message, or press **Talk** and speak. Jarvis answers in text and by voice.

## Demo

- Voice and typed input
- Local LLM chat, no paid chat API
- Weather, news, Wikipedia, time, jokes, maps
- Open YouTube, Google, GitHub, Gmail, Reddit, WhatsApp Web, Chrome, Notepad, VS Code
- Screenshot, CPU / RAM / battery info

## How it works

1. Input: typed text, or microphone audio.
2. Speech-to-text: Google Web Speech via SpeechRecognition, en-IN first, then en-US.
3. Router: `handle_command()` checks fixed commands first with keyword rules + fuzzy matching.
4. Fixed command? Run code (weather API, BBC RSS, Wikipedia, browser, screenshot).
   No fixed command? Send to Ollama, model `llama3.2`, locally on the laptop.
5. Output: answer shown in the chat window and spoken with `pyttsx3` (SAPI5 on Windows).

## Tech stack

Python 3.12.10, CustomTkinter, Ollama + llama3.2, SpeechRecognition + PyAudio (WASAPI),
pyttsx3, requests, psutil, pyautogui, pyjokes, Open-Meteo, BBC RSS, Wikipedia REST API.

## How to run (Windows)

```powershell
# 1. Make sure Ollama is running in the background, and check:
ollama list
# You should see llama3.2:latest. You do NOT need to keep an "ollama run" window open.

# 2. In the project folder, run with the venv312 Python, not plain python:
venv312\Scripts\python.exe jarvis_gui.py
```

Install from scratch (if you need to reinstall):

```powershell
py -3.12 -m venv venv312
venv312\Scripts\python.exe -m pip install -r requirements.txt
ollama pull llama3.2
```

## Commands that work

`what time is it` | `weather in Pune` | `news` | `who is APJ Abdul Kalam` |
`open youtube` | `open whatsapp` | `open chrome` | `take a screenshot` |
`system info` | `tell me a joke` | `explain AI in simple words`
