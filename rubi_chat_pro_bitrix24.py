# -*- coding: utf-8 -*-
"""
RUBI CHAT PRO v3.0 - С АВТОМАТИЧЕСКОЙ ЗАГРУЗКОЙ ЗВОНКОВ ИЗ BITRIX24
Полный аналог RUBI Chat с транскрибацией звонков через OpenAI Whisper
Платформа AI для управления отделом продаж
ГОТОВО К РАЗВЕРТЫВАНИЮ НА GITHUB + STREAMLIT CLOUD
"""

import os
import json
import time
from datetime import datetime, timedelta, date
from pathlib import Path
import requests
from dotenv import load_dotenv
from io import BytesIO
import threading
from queue import Queue

import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go

# =====================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# =====================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BITRIX24_WEBHOOK = os.getenv("BITRIX24_WEBHOOK", "")

if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY не найден в переменных окружения!")
    st.stop()

if not BITRIX24_WEBHOOK:
    st.warning("⚠️ BITRIX24_WEBHOOK не установлен. Автозагрузка звонков недоступна.")

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

@st.cache_resource
def get_bitrix_client():
    """Получить клиент Bitrix24"""
    if not BITRIX24_WEBHOOK:
        return None
    return BITRIX24_WEBHOOK

def get_calls_from_bitrix() -> list:
    """
    Получить записи звонков из Bitrix24
    API: crm.activity.list
    """
    if not BITRIX24_WEBHOOK:
        st.warning("Bitrix24 webhook не настроен")
        return []
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.activity.list.json"
        
        params = {
            "filter[SUBJECT]": "Звонок",
            "filter[TYPE_ID]": "1",  # Phone call
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
        
        params = {
            "id": deal_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("result", {})
        else:
            return {}
            
    except Exception as e:
        return {}

def get_call_recording_url(call_id: str) -> str:
    """
    Получить URL записи звонка из Bitrix24
    """
    if not BITRIX24_WEBHOOK:
        return ""
    
    try:
        url = f"{BITRIX24_WEBHOOK}telephony.externalcall.finish.json"
        
        # Получаем информацию о звонке
        params = {
            "CALL_ID": call_id
        }
        
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
    """Сохранить результаты анализа в Bitrix24 как примечание"""
    if not BITRIX24_WEBHOOK:
        return False
    
    try:
        note_text = f"""
        📊 АНАЛИЗ КАЧЕСТВА ЗВОНКА - RUBI CHAT PRO
        
        ⭐ Оценка: {analysis.get('total_score', 0)}/20
        
        Критерии:
        - 🎤 Вежливость: {analysis.get('scores', {}).get('politeness', 0)}/5
        - 👂 Понимание: {analysis.get('scores', {}).get('understanding', 0)}/5
        - 💼 Решение: {analysis.get('scores', {}).get('solution', 0)}/5
        - ✍️ Закрытие: {analysis.get('scores', {}).get('closing', 0)}/5
        
        😊 Тональность: {analysis.get('sentiment', 'N/A')}
        
        💡 Рекомендации:
        {chr(10).join(f"• {rec}" for rec in analysis.get('recommendations', []))}
        """
        
        url = f"{BITRIX24_WEBHOOK}crm.activity.add.json"
        
        data = {
            "fields": {
                "OWNER_ID": deal_id,
                "OWNER_TYPE_ID": "2",  # Deal
                "TYPE_ID": "4",  # Note
                "DESCRIPTION": note_text,
                "SUBJECT": "🤖 АНАЛИЗ КАЧЕСТВА ЗВОНКА"
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        return response.status_code == 200
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось сохранить анализ в Bitrix24: {str(e)}")
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
                    "content": "Ты - эксперт по оценке качества телефонных звонков в sales."
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
    {
        "id": 1, "title": "ООО Техцентр", "manager": "Иван", "amount": 250000,
        "stage": "agreement", "days_in_stage": 5, "probability": 85,
        "health_pos": ["Может быть в статусе ещё 18 дней", "Есть контакт"],
        "health_neg": []
    },
    {
        "id": 2, "title": "ЗАО Промторг", "manager": "Ирина", "amount": 450000,
        "stage": "presentation", "days_in_stage": 12, "probability": 45,
        "health_pos": [],
        "health_neg": ["Задача просрочена на 2 дня"]
    },
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
if "bitrix_calls" not in st.session_state:
    st.session_state["bitrix_calls"] = []

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
        
        # Статус API
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
        
        # Выбор модуля
        st.markdown("### 📌 Модули")
        module = st.radio(
            "Выберите модуль:",
            ["auto_load", "manual", "calls", "pulse", "assistant"],
            format_func=lambda x: {
                "auto_load": "📥 Автозагрузка из Bitrix24",
                "manual": "📁 Загрузка вручную",
                "calls": "📊 История звонков",
                "pulse": "⛵ Пульс сделок",
                "assistant": "🤖 AI Ассистент"
            }[x],
            key="module_select"
        )
        st.session_state["selected_module"] = module
        
        st.markdown("---")
        st.markdown("### 📊 Статистика")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📞 Всего звонков", len(st.session_state["uploaded_calls"]) + len(st.session_state["bitrix_calls"]))
        with col2:
            if st.session_state["uploaded_calls"] or st.session_state["bitrix_calls"]:
                all_calls = st.session_state["uploaded_calls"] + st.session_state["bitrix_calls"]
                avg_score = np.mean([c.get("quality", 10) for c in all_calls])
                st.metric("⭐ Средняя оценка", f"{avg_score:.1f}/20")
        
        st.markdown("---")
        if st.button("🚪 Выход", use_container_width=True):
            st.session_state[AUTH_KEY] = False
            st.rerun()
    
    # ОСНОВНОЙ КОНТЕНТ
    if st.session_state["selected_module"] == "auto_load":
        show_auto_load_module()
    elif st.session_state["selected_module"] == "manual":
        show_manual_load_module()
    elif st.session_state["selected_module"] == "calls":
        show_calls_history_module()
    elif st.session_state["selected_module"] == "pulse":
        show_pulse_module()
    elif st.session_state["selected_module"] == "assistant":
        show_assistant_module()

def show_auto_load_module():
    """ГЛАВНЫЙ МОДУЛЬ: Автоматическая загрузка звонков из Bitrix24"""
    st.markdown("# 📥 Автоматическая загрузка звонков из Bitrix24")
    
    if not BITRIX24_WEBHOOK:
        st.error("❌ Webhook Bitrix24 не настроен!")
        st.info("Установи BITRIX24_WEBHOOK в файле .env")
        return
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
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
    
    with col3:
        if st.button("⚙️ Настройки", use_container_width=True):
            st.session_state["show_settings"] = not st.session_state.get("show_settings", False)
    
    st.markdown("---")
    
    # Таблица загруженных звонков
    if st.session_state["bitrix_calls"]:
        calls_to_show = st.session_state["bitrix_calls"][:20]
        
        st.markdown(f"### 📞 Всего найдено: {len(st.session_state['bitrix_calls'])} звонков")
        
        calls_df = pd.DataFrame([
            {
                "🆔 ID": c.get("ID", "N/A")[:10],
                "📌 Тема": c.get("SUBJECT", "Звонок"),
                "📅 Дата": c.get("CREATED", "N/A"),
                "👤 Тип": c.get("OWNER_TYPE_ID", "2"),
                "📝 Описание": c.get("DESCRIPTION", "")[:30] + "..."
            }
            for c in calls_to_show
        ])
        
        st.dataframe(calls_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Выбор звонка для анализа
        st.markdown("### 🎙️ Выбери звонок для анализа")
        
        selected_idx = st.selectbox(
            "Доступные звонки:",
            range(len(calls_to_show)),
            format_func=lambda i: f"Звонок {i+1} - {calls_to_show[i].get('SUBJECT', 'N/A')} ({calls_to_show[i].get('CREATED', 'N/A')})"
        )
        
        selected_call = calls_to_show[selected_idx]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**ID звонка:** {selected_call.get('ID', 'N/A')}")
            st.markdown(f"**Тема:** {selected_call.get('SUBJECT', 'N/A')}")
        
        with col2:
            st.markdown(f"**Дата:** {selected_call.get('CREATED', 'N/A')}")
            st.markdown(f"**Описание:** {selected_call.get('DESCRIPTION', 'N/A')}")
        
        st.markdown("---")
        
        if st.button("🚀 Начать анализ этого звонка", use_container_width=True, type="primary"):
            
            st.info("⏳ Получаем информацию о сделке...")
            deal_info = get_deal_info(selected_call.get("OWNER_ID", ""))
            
            st.markdown("### 📊 Информация о сделке")
            st.json(deal_info)
            
            st.info("⏳ Загружаем запись звонка...")
            record_url = get_call_recording_url(selected_call.get("ID", ""))
            
            if record_url:
                st.success(f"✅ URL записи: {record_url[:50]}...")
                
                audio_data = download_call_recording(record_url)
                
                if audio_data:
                    st.success(f"✅ Запись загружена ({len(audio_data) / 1024 / 1024:.2f} MB)")
                    
                    # ТРАНСКРИБАЦИЯ
                    st.markdown("---")
                    st.markdown("### 📝 Этап 1: Транскрибация")
                    
                    transcription = transcribe_audio_with_whisper(audio_data)
                    
                    if transcription:
                        st.text_area("Полная транскрибация:", transcription, height=150, disabled=True)
                        
                        st.markdown("---")
                        
                        # АНАЛИЗ
                        st.markdown("### 🎯 Этап 2: Анализ качества")
                        
                        analysis = analyze_transcript_with_gpt(transcription)
                        
                        if analysis:
                            # Оценки
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
                            
                            # Общая оценка
                            total = analysis.get("total_score", 0)
                            if total >= 18:
                                st.success(f"🟢 Оценка: {total}/20 (Отличный звонок)")
                            elif total >= 14:
                                st.warning(f"🟡 Оценка: {total}/20 (Хороший звонок)")
                            else:
                                st.error(f"🔴 Оценка: {total}/20 (Требует улучшения)")
                            
                            st.markdown("---")
                            
                            # Тональность
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                sentiment = analysis.get("sentiment", "Нейтральная")
                                emoji = {"Позитивная": "😊", "Нейтральная": "😐", "Негативная": "😞"}.get(sentiment, "❓")
                                st.info(f"{emoji} **{sentiment}**")
                            
                            # Ключевые фразы
                            with col2:
                                st.markdown("#### 🔑 Ключевые фразы:")
                                for phrase in analysis.get("key_phrases", [])[:3]:
                                    st.markdown(f"- {phrase}")
                            
                            # Рекомендации
                            with col3:
                                st.markdown("#### 💡 Рекомендации:")
                                for rec in analysis.get("recommendations", []):
                                    st.markdown(f"- {rec}")
                            
                            st.markdown("---")
                            
                            # Сохранить в Bitrix24
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
                                
                                # Добавить в историю
                                call_record = {
                                    "id": len(st.session_state["uploaded_calls"]) + 1,
                                    "file": selected_call.get("ID", ""),
                                    "manager": "Из Bitrix24",
                                    "client": deal_info.get("TITLE", "N/A"),
                                    "date": selected_call.get("CREATED", ""),
                                    "quality": total,
                                    "sentiment": sentiment,
                                    "transcription": transcription,
                                    "scores": {
                                        "politeness": analysis.get("politeness", 0),
                                        "understanding": analysis.get("understanding", 0),
                                        "solution": analysis.get("solution", 0),
                                        "closing": analysis.get("closing", 0)
                                    }
                                }
                                
                                st.session_state["uploaded_calls"].append(call_record)
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
        uploaded_file = st.file_uploader(
            "Выберите MP3, WAV, OGG или M4A файл",
            type=["mp3", "wav", "ogg", "m4a"]
        )
    
    with col2:
        manager_select = st.selectbox(
            "Менеджер:",
            [m["name"] for m in MANAGERS_DATA]
        )
    
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
                    
                    st.markdown("---")
                    
                    if st.button("💾 Сохранить анализ", use_container_width=True, type="primary"):
                        call_record = {
                            "id": len(st.session_state["uploaded_calls"]) + 1,
                            "file": uploaded_file.name,
                            "manager": manager_select,
                            "client": client_name,
                            "date": call_date.strftime("%Y-%m-%d"),
                            "quality": total,
                            "sentiment": analysis.get("sentiment", "Нейтральная"),
                            "transcription": transcription,
                            "scores": {
                                "politeness": analysis.get("politeness", 0),
                                "understanding": analysis.get("understanding", 0),
                                "solution": analysis.get("solution", 0),
                                "closing": analysis.get("closing", 0)
                            }
                        }
                        
                        st.session_state["uploaded_calls"].append(call_record)
                        st.success("✅ Анализ сохранён!")

def show_calls_history_module():
    """История звонков"""
    st.markdown("# 📊 История анализированных звонков")
    
    all_calls = st.session_state["uploaded_calls"] + st.session_state["bitrix_calls"]
    
    if all_calls:
        calls_df = pd.DataFrame([
            {
                "🎙️ Источник": "Ручная загрузка" if c in st.session_state["uploaded_calls"] else "Bitrix24",
                "👤 Менеджер": c.get("manager", "N/A"),
                "🏢 Клиент": c.get("client", "N/A")[:20],
                "📅 Дата": c.get("date", "N/A"),
                "⭐ Оценка": f"{c.get('quality', 0)}/20",
                "😊 Тональность": c.get("sentiment", "N/A")
            }
            for c in all_calls
        ])
        
        st.dataframe(calls_df, use_container_width=True, hide_index=True)
        
        # Статистика
        st.markdown("---")
        st.markdown("### 📈 Статистика")
        
        avg_score = np.mean([c.get("quality", 10) for c in all_calls])
        positive_count = sum(1 for c in all_calls if "Позитивная" in c.get("sentiment", ""))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⭐ Средняя оценка", f"{avg_score:.1f}/20")
        with col2:
            st.metric("😊 Позитивные", f"{positive_count}/{len(all_calls)}")
        with col3:
            st.metric("📞 Всего звонков", len(all_calls))
    else:
        st.info("📭 История пуста")

def show_pulse_module():
    """Пульс сделок"""
    st.markdown("# ⛵ Пульс сделок")
    
    for deal in DEALS_DATA:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"### 💼 {deal['title']}")
                st.markdown(f"**Менеджер:** {deal['manager']} | **Сумма:** {deal['amount']:,} ₽".replace(",", " "))
            
            with col2:
                st.markdown(f"**Стадия:** {deal['stage']}")
                st.markdown(f"**Вероятность:** {deal['probability']}%")
            
            with col3:
                if deal['probability'] > 70:
                    st.success(f"✅ Здоровье: {deal['days_in_stage']} дней")
                else:
                    st.warning(f"⚠️ Здоровье: {deal['days_in_stage']} дней")

def show_assistant_module():
    """AI Ассистент"""
    st.markdown("# 🤖 AI Ассистент")
    
    for message in st.session_state["chat_history"]:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
    
    user_input = st.chat_input("Напишите вашу задачу...")
    
    if user_input:
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("⏳ Обработка..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": user_input}],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    response_text = response.choices[0].message.content
                    st.markdown(response_text)
                    
                    st.session_state["chat_history"].append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    main()
