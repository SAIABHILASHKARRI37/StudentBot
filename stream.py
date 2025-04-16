import streamlit as st
import sqlite3
import google.generativeai as genai
from gtts import gTTS
import os
from textwrap import wrap
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import speech_recognition as sr
import re
import tempfile

# Configure Gemini API
genai.configure(api_key="AIzaSyCa5LqygtZkpVTYGpsqfCQK6xGTwlR4cSY")

LABELS = {
    "en": {"user": "You", "bot": "Bot"},
    "hi": {"user": "आप", "bot": "बॉट"},
    "te": {"user": "మీరు", "bot": "బాట్"},
    "es": {"user": "Tú", "bot": "Bot"},
    "fr": {"user": "Vous", "bot": "Bot"},
    "de": {"user": "Du", "bot": "Bot"},
    "it": {"user": "Tu", "bot": "Bot"},
    "ja": {"user": "あなた", "bot": "ボット"},
    "zh-CN": {"user": "你", "bot": "机器人"},
    "zh-TW": {"user": "你", "bot": "機器人"},
    "ru": {"user": "Вы", "bot": "Бот"},
}

LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Telugu": "te",
    "Italian": "it",
    "Japanese": "ja",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Russian": "ru",
}

SUBJECTS = ["Telugu", "Hindi", "Mathematics", "Science", "English", "Social Studies", "Computer Science", "General Knowledge"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]

conn = sqlite3.connect("chat_history.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        language TEXT,
        sender TEXT,
        message TEXT
    )
""")
conn.commit()

def get_vidyaai_response(user_input, language_code, subject, level):
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
You are an expert teacher in {subject}. 
The student is at a {level} level of understanding in this subject.
You must explain clearly, slowly, and using simple terms.

Speak in the selected language ({language_code}).
Your role is an AI education assistant based on India's NEP 2020, guiding underprivileged school students.

Student's Question: {user_input}
Answer:"""
    response = model.generate_content(prompt)
    return response.text

def clean_text_for_tts(text):
    # Remove hashtags like #math or #hello_world
    text = re.sub(r'#\w+', '', text)
    # Remove any extra whitespace
    return re.sub(r'\s+', ' ', text).strip()

def text_to_speech(text, language, filename="response.mp3"):
    clean_text = clean_text_for_tts(text)
    tts = gTTS(text=clean_text, lang=language)
    tts.save(filename)
    return filename

def generate_pdf(text):
    filename = "Response_Report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    x_margin, y_margin = 50, 50
    y_position = height - 80

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y_position, "🧠 VidyaAI++ Response Report")
    y_position -= 30

    wrapped_text = wrap(clean_text_for_tts(text), 90)
    c.setFont("Helvetica", 12)

    for line in wrapped_text:
        if y_position < y_margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - y_margin
        c.drawString(x_margin, y_position, line)
        y_position -= 20

    c.save()
    return filename

def listen_for_input(language_code):
    fs = 16000  # Sample rate
    duration = 5  # seconds

    st.session_state.listening_status = "🎙 Listening..."
    st.session_state.update()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            write(temp_wav.name, fs, audio)

            st.session_state.listening_status = "🧠 Processing..."
            st.session_state.update()

            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_wav.name) as source:
                audio_data = recognizer.record(source)
                if language_code == "te":
                    language_code = "te-IN"
                text = recognizer.recognize_google(audio_data, language=language_code)
                st.session_state.listening_status = f"✅ Recognized: {text}"
                return text
    except sr.UnknownValueError:
        st.session_state.listening_status = "❌ Couldn't understand."
    except sr.RequestError:
        st.session_state.listening_status = "⚠ Request error."
    return None

def main():
    st.set_page_config(page_title="VidyaAI++", page_icon="🧠")

    st.markdown("""
        <style>
            .chat-box {
                margin: 10px 0; padding: 15px; border-radius: 16px;
                max-width: 70%; transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                color: black;
            }
            .user-msg {
                background: linear-gradient(to right, #a1ffce, #faffd1);
                align-self: flex-end; border-left: 6px solid #00b894;
            }
            .bot-msg {
                background: linear-gradient(to right, #f8f9fa, #dbe6f6);
                align-self: flex-start; border-left: 6px solid #0984e3;
            }
            .chat-container {
                display: flex; flex-direction: column; gap: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center;'>🧠 VidyaAI++ Multilingual Chatbot</h1>", unsafe_allow_html=True)

    language = st.selectbox("🌐 Select your language:", list(LANGUAGES.keys()))
    lang_code = LANGUAGES[language]

    subject = st.selectbox("📚 Subject:", SUBJECTS)
    level = st.radio("📈 Proficiency Level:", LEVELS, horizontal=True)

    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    history = c.execute("SELECT sender, message FROM history WHERE language = ?", (language,)).fetchall()
    labels = LABELS.get(lang_code, {"user": "You", "bot": "Bot"})
    for sender, msg in history:
        msg_class = "user-msg" if sender == "user" else "bot-msg"
        label = labels['user'] if sender == "user" else labels['bot']
        st.markdown(f"<div class='chat-box {msg_class}'><b>{label}:</b> {msg}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 10, 1])
        with col1:
            mic_pressed = st.form_submit_button("🎙")
        with col2:
            user_input = st.text_input("", placeholder="Type or use mic...", label_visibility="collapsed", key="chat_input")
        with col3:
            send_pressed = st.form_submit_button("📨")

    final_input = None
    if mic_pressed:
        final_input = listen_for_input(lang_code)

    if 'listening_status' in st.session_state:
        st.markdown(f"<p style='color: grey;'>{st.session_state.listening_status}</p>", unsafe_allow_html=True)

    if send_pressed or final_input:
        final_input = final_input if final_input else user_input
        if final_input:
            c.execute("INSERT INTO history (language, sender, message) VALUES (?, ?, ?)", (language, "user", final_input))
            response = get_vidyaai_response(final_input, lang_code, subject, level)
            c.execute("INSERT INTO history (language, sender, message) VALUES (?, ?, ?)", (language, "bot", response))
            conn.commit()
            audio_path = text_to_speech(response, lang_code)
            st.audio(audio_path, format="audio/mp3")
            if lang_code == "en":
                pdf_file = generate_pdf(response)
                with open(pdf_file, "rb") as pdf:
                    st.download_button("📄 Download PDF", pdf, file_name="VidyaAI_Response.pdf")

if __name__ == "__main__":
    main()
