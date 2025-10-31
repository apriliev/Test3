# -*- coding: utf-8 -*-
"""
RUBI CHAT PRO v3.0 - ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ STREAMLIT CLOUD
Работает без python-dotenv (использует st.secrets)
"""

import os
import json
import time
from datetime import datetime, timedelta, date
from io import BytesIO
import requests

import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go

# =====================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# =====================

# ✅ ИСПРАВКА: Используем st.secrets вместо .env
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

try:
    BITRIX24_WEBHOOK = st.secrets["BITRIX24_WEBHOOK"]
except (KeyError, FileNotFoundError):
    BITRIX24_WEBHOOK = os.getenv("BITRIX24_WEBHOOK", "")

if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY не найден!")
    st.error("Установите секреты в Settings → Secrets")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# КОНФИГУРАЦИЯ STREAMLIT
# =====================
st.set_page_config(
    page_title="RUBI CHAT PRO v3.0",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# АУТЕНТИФИКАЦИЯ
# =====================
AUTH_KEY = "rubi_chat_pro_auth_v3"

def require_auth():
    if AUTH_KEY not in st.session_state:
        st.session_state[AUTH_KEY] = False
    
    if st.session_state[AUTH_KEY]:
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Вход в RUBI CHAT PRO v3.0")
        st.markdown("**С автоматической загрузкой звонков из Bitrix24**")
        
        with st.form("login_form", clear_on_submit=False):
            login = st.text_input("Логин", value="admin")
            password = st.text_input("Пароль", value="admin", type="password")
            submitted = st.form_submit_button("✅ Войти", use_container_width=True)
            
            if submitted:
                if login == "admin" and password == "admin":
                    st.session_state[AUTH_KEY] = True
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль")
        
        st.markdown("---")
        st.info("📝 Тестовые учетные данные: admin / admin")
    
    return False

# =====================
# ФУНКЦИИ РАБОТЫ С BITRIX24
# =====================

def get_calls_from_bitrix() -> list:
    """Получить записи звонков из Bitrix24"""
    if not BITRIX24_WEBHOOK:
        st.warning("Bitrix24 webhook не настроен")
        return []
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.activity.list.json"
        
        params = {
            "filter[SUBJECT]": "Звонок",
            "filter[TYPE_ID]": "1",
            "select": ["ID", "OWNER_ID", "OWNER_TYPE_ID", "SUBJECT", "CREATED", "DESCRIPTION"],
            "limit": 50
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            st.warning(f"⚠️ Ошибка Bitrix24: {response.status_code}")
            return []
            
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке из Bitrix24: {str(e)}")
        return []

def get_deal_info(deal_id: str) -> dict:
    """Получить информацию о сделке"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.deal.get.json"
        params = {"id": deal_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("result", {})
        else:
            return {}
            
    except Exception as e:
        return {}

def get_call_recording_url(call_id: str) -> str:
    """Получить URL записи звонка"""
    if not BITRIX24_WEBHOOK:
        return ""
    
    try:
        url = f"{BITRIX24_WEBHOOK}telephony.externalcall.finish.json"
        params = {"CALL_ID": call_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "RECORD_URL" in data["result"]:
                return data["result"]["RECORD_URL"]
        
        return ""
        
    except Exception as e:
        return ""

def download_call_recording(record_url: str) -> bytes:
    """Скачать запись звонка"""
    try:
        response = requests.get(record_url, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            return None
            
    except Exception as e:
        st.error(f"❌ Ошибка при скачивании: {str(e)}")
        return None

def save_analysis_to_bitrix(deal_id: str, analysis: dict):
    """Сохранить результаты анализа в Bitrix24"""
    if not BITRIX24_WEBHOOK:
        return False
    
    try:
        note_text = f"""📊 АНАЛИЗ КАЧЕСТВА ЗВОНКА - RUBI CHAT PRO

⭐ Оценка: {analysis.get('total_score', 0)}/20

Критерии:
- 🎤 Вежливость: {analysis.get('scores', {}).get('politeness', 0)}/5
- 👂 Понимание: {analysis.get('scores', {}).get('understanding', 0)}/5
- 💼 Решение: {analysis.get('scores', {}).get('solution', 0)}/5
- ✍️ Закрытие: {analysis.get('scores', {}).get('closing', 0)}/5

😊 Тональность: {analysis.get('sentiment', 'N/A')}

💡 Рекомендации:
{chr(10).join(f"• {rec}" for rec in analysis.get('recommendations', []))}"""
        
        url = f"{BITRIX24_WEBHOOK}crm.activity.add.json"
        
        data = {
            "fields": {
                "OWNER_ID": deal_id,
                "OWNER_TYPE_ID": "2",
                "TYPE_ID": "4",
                "DESCRIPTION": note_text,
                "SUBJECT": "🤖 АНАЛИЗ КАЧЕСТВА ЗВОНКА"
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        return response.status_code == 200
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось сохранить в Bitrix24: {str(e)}")
        return False

# =====================
# ФУНКЦИИ АНАЛИЗА
# =====================

def transcribe_audio_with_whisper(audio_data: bytes) -> str:
    """Транскрибация через OpenAI Whisper"""
    try:
        audio_file = BytesIO(audio_data)
        audio_file.name = "call.mp3"
        
        st.info("🎙️ Транскрибируем звонок...")
        
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
        
        st.success("✅ Транскрибация завершена!")
        return transcript.text
        
    except Exception as e:
        st.error(f"❌ Ошибка при транскрибации: {str(e)}")
        return ""

def analyze_transcript_with_gpt(transcription: str) -> dict:
    """Анализ качества звонка с помощью GPT-4"""
    try:
        st.info("🤖 Анализируем качество звонка...")
        
        prompt = f"""Проанализируй этот телефонный разговор между менеджером и клиентом.
        
Транскрибация:
{transcription}

Дай оценку по следующим критериям (каждый по 5 баллам):
1. ВЕЖЛИВОСТЬ И ПРОФЕССИОНАЛИЗМ
2. ПОНИМАНИЕ ПОТРЕБНОСТЕЙ
3. ПРЕДСТАВЛЕНИЕ РЕШЕНИЯ
4. ЗАКРЫТИЕ СДЕЛКИ

Также определи:
- ТОНАЛЬНОСТЬ (Позитивная/Нейтральная/Негативная)
- КЛЮЧЕВЫЕ МОМЕНТЫ (3-5 ключевых фраз)
- РЕКОМЕНДАЦИИ для улучшения (2-3 пункта)

Ответ дай в JSON:
{{
    "politeness": <0-5>,
    "understanding": <0-5>,
    "solution": <0-5>,
    "closing": <0-5>,
    "sentiment": "<Позитивная/Нейтральная/Негативная>",
    "key_phrases": ["фраза1", "фраза2", "фраза3"],
    "recommendations": ["рекомендация1", "рекомендация2"]
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Ты - эксперт по оценке качества телефонных звонков."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        json_str = response_text[start_idx:end_idx]
        
        analysis = json.loads(json_str)
        
        total = (analysis.get("politeness", 0) + 
                analysis.get("understanding", 0) + 
                analysis.get("solution", 0) + 
                analysis.get("closing", 0))
        
        analysis["total_score"] = total
        
        st.success("✅ Анализ завершен!")
        
        return analysis
        
    except Exception as e:
        st.error(f"❌ Ошибка при анализе: {str(e)}")
        return {}

# =====================
# MOCK ДАННЫЕ
# =====================
MANAGERS_DATA = [
    {"id": 1, "name": "Менеджер Иван", "health": 89, "targets": 1000000, "fact": 850000},
    {"id": 2, "name": "Менеджер Ирина", "health": 65, "targets": 1000000, "fact": 580000},
    {"id": 3, "name": "Менеджер Артем", "health": 74, "targets": 900000, "fact": 430000},
    {"id": 4, "name": "Менеджер Мария", "health": 30, "targets": 660000, "fact": 0},
]

DEALS_DATA = [
    {"id": 1, "title": "ООО Техцентр", "manager": "Иван", "amount": 250000, "stage": "agreement", "days_in_stage": 5, "probability": 85},
    {"id": 2, "title": "ЗАО Промторг", "manager": "Ирина", "amount": 450000, "stage": "presentation", "days_in_stage": 12, "probability": 45},
]

# =====================
# ИНИЦИАЛИЗАЦИЯ SESSION
# =====================
if "selected_module" not in st.session_state:
    st.session_state["selected_module"] = "auto_load"
if "uploaded_calls" not in st.session_state:
    st.session_state["uploaded_calls"] = []
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# =====================
# ГЛАВНЫЙ UI
# =====================
def main():
    if not require_auth():
        st.stop()
    
    with st.sidebar:
        st.markdown("## 🔥 RUBI CHAT PRO v3.0")
        st.markdown("**С автозагрузкой из Bitrix24**")
        st.markdown("---")
        
        st.markdown("### ✅ Статус интеграций")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("🔑 OpenAI:")
        with col2:
            st.success("✅ Подключен") if OPENAI_API_KEY else st.error("❌ Нет")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("📊 Bitrix24:")
        with col2:
            st.success("✅ Подключен") if BITRIX24_WEBHOOK else st.error("❌ Нет")
        
        st.markdown("---")
        
        st.markdown("### 📌 Модули")
        module = st.radio(
            "Выберите модуль:",
            ["auto_load", "manual", "calls", "pulse"],
            format_func=lambda x: {
                "auto_load": "📥 Автозагрузка из Bitrix24",
                "manual": "📁 Загрузка вручную",
                "calls": "📊 История звонков",
                "pulse": "⛵ Пульс сделок",
            }[x],
            key="module_select"
        )
        st.session_state["selected_module"] = module
        
        st.markdown("---")
        if st.button("🚪 Выход", use_container_width=True):
            st.session_state[AUTH_KEY] = False
            st.rerun()
    
    if st.session_state["selected_module"] == "auto_load":
        show_auto_load_module()
    elif st.session_state["selected_module"] == "manual":
        show_manual_load_module()
    elif st.session_state["selected_module"] == "calls":
        show_calls_history_module()
    elif st.session_state["selected_module"] == "pulse":
        show_pulse_module()

def show_auto_load_module():
    """ГЛАВНЫЙ МОДУЛЬ: Автоматическая загрузка звонков из Bitrix24"""
    st.markdown("# 📥 Автоматическая загрузка звонков из Bitrix24")
    
    if not BITRIX24_WEBHOOK:
        st.error("❌ Webhook Bitrix24 не настроен!")
        st.info("📝 Установи BITRIX24_WEBHOOK в Settings → Secrets")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔄 Загруженные звонки из CRM")
    
    with col2:
        if st.button("🔄 Обновить список", use_container_width=True):
            with st.spinner("⏳ Загружаем звонки из Bitrix24..."):
                calls = get_calls_from_bitrix()
                st.session_state["bitrix_calls"] = calls
                st.success(f"✅ Загружено {len(calls)} звонков")
                time.sleep(1)
                st.rerun()
    
    st.markdown("---")
    
    if not hasattr(st.session_state, "bitrix_calls"):
        st.session_state["bitrix_calls"] = []
    
    if st.session_state["bitrix_calls"]:
        calls_to_show = st.session_state["bitrix_calls"][:20]
        
        st.markdown(f"### 📞 Всего найдено: {len(st.session_state['bitrix_calls'])} звонков")
        
        calls_df = pd.DataFrame([
            {
                "🆔 ID": c.get("ID", "N/A")[:10],
                "📌 Тема": c.get("SUBJECT", "Звонок"),
                "📅 Дата": c.get("CREATED", "N/A"),
                "📝 Описание": (c.get("DESCRIPTION", "")[:30] + "...") if c.get("DESCRIPTION") else "N/A"
            }
            for c in calls_to_show
        ])
        
        st.dataframe(calls_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        st.markdown("### 🎙️ Выбери звонок для анализа")
        
        selected_idx = st.selectbox(
            "Доступные звонки:",
            range(len(calls_to_show)),
            format_func=lambda i: f"Звонок {i+1} - {calls_to_show[i].get('SUBJECT', 'N/A')}"
        )
        
        selected_call = calls_to_show[selected_idx]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**ID звонка:** {selected_call.get('ID', 'N/A')}")
            st.markdown(f"**Тема:** {selected_call.get('SUBJECT', 'N/A')}")
        
        with col2:
            st.markdown(f"**Дата:** {selected_call.get('CREATED', 'N/A')}")
            st.markdown(f"**Описание:** {selected_call.get('DESCRIPTION', 'N/A')[:50]}")
        
        st.markdown("---")
        
        if st.button("🚀 Начать анализ этого звонка", use_container_width=True, type="primary"):
            
            st.info("⏳ Получаем информацию о сделке...")
            deal_info = get_deal_info(selected_call.get("OWNER_ID", ""))
            
            st.markdown("### 📊 Информация о сделке")
            if deal_info:
                st.json(deal_info)
            else:
                st.warning("Информация о сделке не найдена")
            
            st.info("⏳ Загружаем запись звонка...")
            record_url = get_call_recording_url(selected_call.get("ID", ""))
            
            if record_url:
                st.success(f"✅ URL записи получен")
                
                audio_data = download_call_recording(record_url)
                
                if audio_data:
                    st.success(f"✅ Запись загружена ({len(audio_data) / 1024 / 1024:.2f} MB)")
                    
                    st.markdown("---")
                    st.markdown("### 📝 Этап 1: Транскрибация")
                    
                    transcription = transcribe_audio_with_whisper(audio_data)
                    
                    if transcription:
                        st.text_area("Полная транскрибация:", transcription, height=150, disabled=True)
                        
                        st.markdown("---")
                        st.markdown("### 🎯 Этап 2: Анализ качества")
                        
                        analysis = analyze_transcript_with_gpt(transcription)
                        
                        if analysis:
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("🎤 Вежливость", f"{analysis.get('politeness', 0)}/5")
                            with col2:
                                st.metric("👂 Понимание", f"{analysis.get('understanding', 0)}/5")
                            with col3:
                                st.metric("💼 Решение", f"{analysis.get('solution', 0)}/5")
                            with col4:
                                st.metric("✍️ Закрытие", f"{analysis.get('closing', 0)}/5")
                            
                            st.markdown("---")
                            
                            total = analysis.get("total_score", 0)
                            if total >= 18:
                                st.success(f"🟢 Оценка: {total}/20 (Отличный звонок)")
                            elif total >= 14:
                                st.warning(f"🟡 Оценка: {total}/20 (Хороший звонок)")
                            else:
                                st.error(f"🔴 Оценка: {total}/20 (Требует улучшения)")
                            
                            st.markdown("---")
                            
                            st.markdown("#### 😊 Тональность и ключевые фразы:")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                sentiment = analysis.get("sentiment", "Нейтральная")
                                emoji = {"Позитивная": "😊", "Нейтральная": "😐", "Негативная": "😞"}.get(sentiment, "❓")
                                st.info(f"{emoji} **{sentiment}**")
                            
                            with col2:
                                st.markdown("#### 🔑 Ключевые фразы:")
                                for phrase in analysis.get("key_phrases", [])[:3]:
                                    st.markdown(f"- {phrase}")
                            
                            st.markdown("#### 💡 Рекомендации:")
                            for rec in analysis.get("recommendations", []):
                                st.markdown(f"- {rec}")
                            
                            st.markdown("---")
                            
                            if st.button("💾 Сохранить анализ в Bitrix24", use_container_width=True, type="primary"):
                                success = save_analysis_to_bitrix(
                                    selected_call.get("OWNER_ID", ""),
                                    {
                                        "total_score": total,
                                        "scores": {
                                            "politeness": analysis.get("politeness", 0),
                                            "understanding": analysis.get("understanding", 0),
                                            "solution": analysis.get("solution", 0),
                                            "closing": analysis.get("closing", 0)
                                        },
                                        "sentiment": sentiment,
                                        "key_phrases": analysis.get("key_phrases", []),
                                        "recommendations": analysis.get("recommendations", [])
                                    }
                                )
                                
                                if success:
                                    st.success("✅ Анализ сохранён в Bitrix24!")
                                else:
                                    st.info("ℹ️ Результаты сохранены локально")
                else:
                    st.error("❌ Не удалось загрузить запись")
            else:
                st.warning("⚠️ URL записи не найден в Bitrix24")
    else:
        st.info("📭 Звонков не найдено. Нажми кнопку 'Обновить список'")

def show_manual_load_module():
    """Загрузка вручную"""
    st.markdown("# 📁 Загрузить звонок вручную")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Выберите MP3, WAV, OGG или M4A файл", type=["mp3", "wav", "ogg", "m4a"])
    
    with col2:
        manager_select = st.selectbox("Менеджер:", [m["name"] for m in MANAGERS_DATA])
    
    if uploaded_file is not None:
        st.success(f"✅ Файл загружен: {uploaded_file.name}")
        
        client_name = st.text_input("Имя клиента / Компания:", "ООО Клиент")
        call_date = st.date_input("Дата звонка:", datetime.now())
        
        if st.button("🚀 Начать анализ", use_container_width=True, type="primary"):
            audio_data = uploaded_file.read()
            
            transcription = transcribe_audio_with_whisper(audio_data)
            
            if transcription:
                st.text_area("Полная транскрибация:", transcription, height=150, disabled=True)
                
                st.markdown("---")
                
                analysis = analyze_transcript_with_gpt(transcription)
                
                if analysis:
                    total = analysis.get("total_score", 0)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🎤 Вежливость", f"{analysis.get('politeness', 0)}/5")
                    with col2:
                        st.metric("👂 Понимание", f"{analysis.get('understanding', 0)}/5")
                    with col3:
                        st.metric("💼 Решение", f"{analysis.get('solution', 0)}/5")
                    with col4:
                        st.metric("✍️ Закрытие", f"{analysis.get('closing', 0)}/5")

def show_calls_history_module():
    """История звонков"""
    st.markdown("# 📊 История анализированных звонков")
    
    if st.session_state["uploaded_calls"]:
        calls_df = pd.DataFrame([
            {
                "👤 Менеджер": c.get("manager", "N/A"),
                "🏢 Клиент": c.get("client", "N/A")[:20],
                "📅 Дата": c.get("date", "N/A"),
                "⭐ Оценка": f"{c.get('quality', 0)}/20",
            }
            for c in st.session_state["uploaded_calls"]
        ])
        
        st.dataframe(calls_df, use_container_width=True, hide_index=True)
    else:
        st.info("📭 История пуста")

def show_pulse_module():
    """Пульс сделок"""
    st.markdown("# ⛵ Пульс сделок")
    
    for deal in DEALS_DATA:
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### 💼 {deal['title']}")
                st.markdown(f"**Менеджер:** {deal['manager']} | **Сумма:** {deal['amount']:,} ₽".replace(",", " "))
            
            with col2:
                st.markdown(f"**Стадия:** {deal['stage']}")
                st.markdown(f"**Вероятность:** {deal['probability']}%")

if __name__ == "__main__":
    main()
