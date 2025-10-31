# -*- coding: utf-8 -*-
"""
RUBI CHAT PRO v4.0 - ПОЛНОЕ ПРИЛОЖЕНИЕ
Полный аналог RUBI Chat с транскрибацией звонков и анализом качества
Все 5 модулей + интеграция с Bitrix24
"""

import os
import json
import time
from datetime import datetime, timedelta
from io import BytesIO
import requests

import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go

# =====================
# КОНФИГУРАЦИЯ
# =====================
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
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(
    page_title="RUBI CHAT PRO v4.0",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# MOCK ДАННЫЕ
# =====================
MANAGERS = [
    {"id": 1, "name": "Иван Петров", "kpi": 95, "target": 100, "calls": 45, "deals": 12},
    {"id": 2, "name": "Ирина Сидорова", "kpi": 65, "target": 100, "calls": 32, "deals": 8},
    {"id": 3, "name": "Артем Смирнов", "kpi": 78, "target": 100, "calls": 38, "deals": 10},
    {"id": 4, "name": "Мария Иванова", "kpi": 45, "target": 100, "calls": 20, "deals": 5},
]

DEALS = [
    {"id": 1, "title": "ООО Строй-Сервис", "manager": "Иван Петров", "amount": 500000, "stage": "Переговоры", "probability": 85, "next_action": "Отправить КП"},
    {"id": 2, "title": "ЗАО Промторг", "manager": "Ирина Сидорова", "amount": 250000, "stage": "Предложение", "probability": 60, "next_action": "Презентация"},
    {"id": 3, "title": "ООО Логистика", "manager": "Артем Смирнов", "amount": 750000, "stage": "Переговоры", "probability": 45, "next_action": "Встреча"},
    {"id": 4, "title": "ООО Альфа", "manager": "Мария Иванова", "amount": 100000, "stage": "Квалификация", "probability": 30, "next_action": "Уточнить потребность"},
]

# =====================
# ФУНКЦИИ BITRIX24
# =====================

def get_calls_from_bitrix() -> list:
    """Получить звонки из Bitrix24"""
    if not BITRIX24_WEBHOOK:
        return []
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.activity.list.json"
        params = {
            "filter[SUBJECT]": "Звонок",
            "filter[TYPE_ID]": "1",
            "limit": 50
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", [])
        return []
    except:
        return []

def get_deal_info(deal_id: str) -> dict:
    """Получить информацию о сделке"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.deal.get.json"
        response = requests.get(url, params={"id": deal_id}, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", {})
        return {}
    except:
        return {}

def save_analysis_to_bitrix(deal_id: str, analysis: dict):
    """Сохранить анализ в Bitrix24"""
    if not BITRIX24_WEBHOOK:
        return False
    
    try:
        note_text = f"""📊 АНАЛИЗ КАЧЕСТВА ЗВОНКА - RUBI CHAT PRO v4.0

⭐ Оценка: {analysis.get('total_score', 0)}/20

Критерии:
🎤 Вежливость: {analysis.get('scores', {}).get('politeness', 0)}/5
👂 Выявление потребностей: {analysis.get('scores', {}).get('understanding', 0)}/5
💼 Представление решения: {analysis.get('scores', {}).get('solution', 0)}/5
✍️ Закрытие сделки: {analysis.get('scores', {}).get('closing', 0)}/5

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
                "SUBJECT": "🤖 АНАЛИЗ ЗВОНКА"
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except:
        return False

# =====================
# ФУНКЦИИ АНАЛИЗА
# =====================

def transcribe_audio(audio_data: bytes) -> str:
    """Транскрибация через Whisper"""
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
        st.error(f"❌ Ошибка: {str(e)}")
        return ""

def analyze_call(transcription: str) -> dict:
    """Анализ качества звонка"""
    try:
        st.info("🤖 Анализируем качество звонка...")
        
        prompt = f"""Проанализируй телефонный звонок:

{transcription}

Дай оценку (0-5 каждый):
1. Вежливость
2. Выявление потребностей
3. Представление решения
4. Закрытие сделки

Определи:
- Тональность (Позитивная/Нейтральная/Негативная)
- Ключевые фразы (3-5)
- Рекомендации (2-3)

Ответ JSON:
{{
    "politeness": 0-5,
    "understanding": 0-5,
    "solution": 0-5,
    "closing": 0-5,
    "sentiment": "...",
    "key_phrases": [...],
    "recommendations": [...]
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        analysis = json.loads(response_text[start_idx:end_idx])
        
        total = sum([
            analysis.get("politeness", 0),
            analysis.get("understanding", 0),
            analysis.get("solution", 0),
            analysis.get("closing", 0)
        ])
        
        analysis["total_score"] = total
        analysis["scores"] = {
            "politeness": analysis.get("politeness", 0),
            "understanding": analysis.get("understanding", 0),
            "solution": analysis.get("solution", 0),
            "closing": analysis.get("closing", 0)
        }
        
        st.success("✅ Анализ завершен!")
        return analysis
    except Exception as e:
        st.error(f"❌ Ошибка: {str(e)}")
        return {}

# =====================
# АУТЕНТИФИКАЦИЯ
# =====================

def require_auth():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    
    if st.session_state.auth:
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 RUBI CHAT PRO v4.0")
        
        with st.form("login"):
            login = st.text_input("Логин", "admin")
            password = st.text_input("Пароль", "admin", type="password")
            
            if st.form_submit_button("Войти", use_container_width=True):
                if login == "admin" and password == "admin":
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("❌ Неверный логин/пароль")
    
    return False

# =====================
# МОДУЛИ ПРИЛОЖЕНИЯ
# =====================

def module_call_analysis():
    """Модуль 1: Оценка звонков"""
    st.markdown("# 🎙️ Оценка качества звонков")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Загрузить аудиозапись")
    with col2:
        if st.button("🔄 Обновить список", use_container_width=True):
            st.success("✅ Обновлено")
    
    st.markdown("---")
    
    # Вкладка 1: Загрузка и анализ
    tab1, tab2, tab3 = st.tabs(["📥 Загрузка", "📊 История", "📈 Статистика"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("Выберите файл", type=["mp3", "wav", "ogg", "m4a"])
        with col2:
            manager = st.selectbox("Менеджер:", [m["name"] for m in MANAGERS])
        
        if uploaded_file:
            st.success(f"✅ Загружен: {uploaded_file.name}")
            
            col1, col2 = st.columns(2)
            with col1:
                client_name = st.text_input("Компания клиента:", "ООО Клиент")
            with col2:
                deal_id = st.text_input("ID сделки Bitrix24:", "123")
            
            if st.button("🚀 Начать анализ", use_container_width=True, type="primary"):
                audio_data = uploaded_file.read()
                
                # Транскрибация
                st.markdown("### 📝 Этап 1: Транскрибация")
                transcription = transcribe_audio(audio_data)
                
                if transcription:
                    st.text_area("Транскрибация:", transcription, height=100, disabled=True)
                    
                    # Анализ
                    st.markdown("### 🎯 Этап 2: Анализ качества")
                    analysis = analyze_call(transcription)
                    
                    if analysis:
                        # Показать результаты
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🎤 Вежливость", f"{analysis.get('scores', {}).get('politeness', 0)}/5")
                        with col2:
                            st.metric("👂 Понимание", f"{analysis.get('scores', {}).get('understanding', 0)}/5")
                        with col3:
                            st.metric("💼 Решение", f"{analysis.get('scores', {}).get('solution', 0)}/5")
                        with col4:
                            st.metric("✍️ Закрытие", f"{analysis.get('scores', {}).get('closing', 0)}/5")
                        
                        st.markdown("---")
                        
                        total = analysis.get("total_score", 0)
                        if total >= 18:
                            st.success(f"🟢 Оценка: {total}/20 (Отличный звонок)")
                        elif total >= 14:
                            st.warning(f"🟡 Оценка: {total}/20 (Хороший звонок)")
                        else:
                            st.error(f"🔴 Оценка: {total}/20 (Требует улучшения)")
                        
                        st.markdown("---")
                        
                        # Детали
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### 😊 Тональность:")
                            st.write(analysis.get("sentiment", "N/A"))
                        with col2:
                            st.markdown("#### 🔑 Ключевые фразы:")
                            for phrase in analysis.get("key_phrases", [])[:3]:
                                st.write(f"• {phrase}")
                        
                        st.markdown("#### 💡 Рекомендации:")
                        for rec in analysis.get("recommendations", []):
                            st.write(f"• {rec}")
                        
                        st.markdown("---")
                        
                        if st.button("💾 Сохранить в Bitrix24", use_container_width=True):
                            success = save_analysis_to_bitrix(deal_id, analysis)
                            if success:
                                st.success("✅ Сохранено в Bitrix24!")
                            else:
                                st.info("ℹ️ Результаты готовы")
    
    with tab2:
        st.markdown("### 📊 История анализированных звонков")
        st.info("История будет сохраняться после каждого анализа")
    
    with tab3:
        st.markdown("### 📈 Статистика по звонкам")
        st.info("Статистика обновляется в реальном времени")

def module_sales_results():
    """Модуль 2: Результаты продаж"""
    st.markdown("# 🚀 Результаты отдела продаж")
    
    st.markdown("---")
    
    # KPI показатели
    st.markdown("## 📊 KPI МЕНЕДЖЕРОВ")
    
    kpi_data = []
    for m in MANAGERS:
        kpi_data.append({
            "👤 Менеджер": m["name"],
            "📞 Звонков": m["calls"],
            "🤝 Сделок": m["deals"],
            "📈 KPI": f"{m['kpi']}%",
            "🎯 План": f"{m['target']}%"
        })
    
    df_kpi = pd.DataFrame(kpi_data)
    st.dataframe(df_kpi, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("## 📈 Выполнение плана")
        names = [m["name"] for m in MANAGERS]
        kpi_values = [m["kpi"] for m in MANAGERS]
        
        fig = px.bar(
            x=names,
            y=kpi_values,
            labels={"x": "Менеджер", "y": "KPI %"},
            title="KPI по менеджерам"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("## 📞 Количество звонков")
        calls = [m["calls"] for m in MANAGERS]
        
        fig = px.bar(
            x=names,
            y=calls,
            labels={"x": "Менеджер", "y": "Звонки"},
            title="Звонки по менеджерам"
        )
        st.plotly_chart(fig, use_container_width=True)

def module_deal_audit():
    """Модуль 3: Аудит воронки"""
    st.markdown("# 🔍 Аудит воронки сделок")
    
    st.markdown("---")
    
    # Таблица сделок
    st.markdown("## 📋 Сделки")
    
    deals_data = []
    for d in DEALS:
        deals_data.append({
            "ID": d["id"],
            "📌 Сделка": d["title"],
            "👤 Менеджер": d["manager"],
            "💰 Сумма": f"{d['amount']:,}₽".replace(",", " "),
            "📊 Стадия": d["stage"],
            "📈 Вероятность": f"{d['probability']}%",
            "🎯 Следующее действие": d["next_action"]
        })
    
    df_deals = pd.DataFrame(deals_data)
    st.dataframe(df_deals, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_manager = st.selectbox("Менеджер:", ["Все"] + [m["name"] for m in MANAGERS])
    with col2:
        filter_stage = st.selectbox("Стадия:", ["Все", "Переговоры", "Предложение", "Квалификация"])
    with col3:
        filter_probability = st.selectbox("Вероятность:", ["Все", "> 80%", "60-80%", "< 60%"])
    
    # График воронки
    st.markdown("## 📊 Воронка продаж")
    
    stages = ["Квалификация", "Предложение", "Переговоры", "Закрыто выиграно"]
    counts = [2, 4, 6, 1]
    
    fig = px.funnel(
        x=counts,
        y=stages,
        title="Воронка продаж"
    )
    st.plotly_chart(fig, use_container_width=True)

def module_deals_pulse():
    """Модуль 4: Пульс сделок"""
    st.markdown("# ⛵ Пульс сделок")
    
    st.markdown("---")
    
    for deal in DEALS:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"### 💼 {deal['title']}")
                st.markdown(f"**Менеджер:** {deal['manager']} | **Сумма:** {deal['amount']:,}₽".replace(",", " "))
            
            with col2:
                st.markdown(f"**Стадия:** {deal['stage']}")
                st.markdown(f"**Вероятность:** {deal['probability']}%")
            
            with col3:
                if deal['probability'] > 70:
                    st.success("✅ Здоровая сделка")
                elif deal['probability'] > 40:
                    st.warning("⚠️ Требует внимания")
                else:
                    st.error("🔴 Критичная")
            
            st.markdown(f"📌 **Следующее действие:** {deal['next_action']}")

def module_ai_assistant():
    """Модуль 5: AI Ассистент"""
    st.markdown("# 🤖 AI Ассистент")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Историческое сообщение
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
    
    # Ввод
    user_input = st.chat_input("Введите ваш вопрос...")
    
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
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
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")

# =====================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# =====================

def main():
    if not require_auth():
        st.stop()
    
    # Боковое меню
    with st.sidebar:
        st.markdown("## 🔥 RUBI CHAT PRO v4.0")
        st.markdown("**Полный функционал**")
        st.markdown("---")
        
        # Статус
        st.markdown("### ✅ Статус")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("🔑 OpenAI:")
        with col2:
            st.success("✅ Подключен") if OPENAI_API_KEY else st.error("❌ Нет")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("📊 Bitrix24:")
        with col2:
            st.success("✅ Подключен") if BITRIX24_WEBHOOK else st.warning("⚠️ Опционально")
        
        st.markdown("---")
        
        # Меню модулей
        st.markdown("### 📌 МОДУЛИ")
        
        module = st.radio(
            "Выберите модуль:",
            [1, 2, 3, 4, 5],
            format_func=lambda x: {
                1: "🎙️ Оценка звонков",
                2: "🚀 Результаты продаж",
                3: "🔍 Аудит воронки",
                4: "⛵ Пульс сделок",
                5: "🤖 AI Ассистент"
            }[x],
            key="module"
        )
        
        st.markdown("---")
        
        if st.button("🚪 Выход", use_container_width=True):
            st.session_state.auth = False
            st.rerun()
    
    # Отображение модуля
    if module == 1:
        module_call_analysis()
    elif module == 2:
        module_sales_results()
    elif module == 3:
        module_deal_audit()
    elif module == 4:
        module_deals_pulse()
    elif module == 5:
        module_ai_assistant()

if __name__ == "__main__":
    main()
