# -*- coding: utf-8 -*-
"""
RUBI CHAT PRO v1.0
Полный аналог RUBI Chat с интегрированной транскрибацией звонков
Платформа AI для управления отделом продаж с анализом качества звонков
"""

import os
import json
import time
from datetime import datetime, timedelta, date
from pathlib import Path
import base64
import io

import numpy as np
import pandas as pd
import streamlit as st
import requests

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

# =====================
# КОНФИГУРАЦИЯ
# =====================
st.set_page_config(
    page_title="RUBI CHAT PRO",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# АУТЕНТИФИКАЦИЯ
# =====================
AUTH_KEY = "rubi_chat_pro_auth"

def require_auth():
    if AUTH_KEY not in st.session_state:
        st.session_state[AUTH_KEY] = False
    
    if st.session_state[AUTH_KEY]:
        return True
    
    # Login page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Вход в RUBI CHAT PRO")
        with st.form("login_form", clear_on_submit=False):
            login = st.text_input("Логин", value="")
            password = st.text_input("Пароль", value="", type="password")
            submitted = st.form_submit_button("Войти", use_container_width=True)
            
            if submitted:
                if login == "admin" and password == "admin":
                    st.session_state[AUTH_KEY] = True
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль")
    
    return False

# =====================
# MOCK ДАННЫЕ
# =====================
MANAGERS_DATA = [
    {"id": 1, "name": "Менеджер Иван", "health": 89, "status": "potential", "targets": 1000000, "fact": 850000},
    {"id": 2, "name": "Менеджер Ирина", "health": 65, "status": "cold", "targets": 1000000, "fact": 580000},
    {"id": 3, "name": "Менеджер Артем", "health": 74, "status": "potential", "targets": 900000, "fact": 430000},
    {"id": 4, "name": "Менеджер Мария", "health": 30, "status": "optimism", "targets": 660000, "fact": 0},
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
        "health_neg": ["Задача просрочена на 2 дня", "Нет компании в карточке"]
    },
    {
        "id": 3, "title": "ИП Стройсервис", "manager": "Артем", "amount": 180000,
        "stage": "tender", "days_in_stage": 7, "probability": 60,
        "health_pos": ["Есть контакт"],
        "health_neg": ["Задача просрочена на 5 дней"]
    },
]

CALLS_DATA = [
    {
        "id": 1, "file": "call_001.mp3", "manager": "Иван", "date": "2025-10-31",
        "duration": "12:45", "quality": 18, "sentiment": "positive",
        "transcription": "Менеджер: Добрый день! Менеджер РУБИ ЧАТ. Как дела? Клиент: Здравствуйте. Менеджер: Звоню по вашему запросу...",
        "scores": {"politeness": 5, "understanding": 5, "solution": 4, "closing": 4}
    },
]

# =====================
# ИНИЦИАЛИЗАЦИЯ SESSION
# =====================
if "selected_module" not in st.session_state:
    st.session_state["selected_module"] = "results"
if "uploaded_calls" not in st.session_state:
    st.session_state["uploaded_calls"] = CALLS_DATA.copy()
if "selected_manager_filter" not in st.session_state:
    st.session_state["selected_manager_filter"] = "Все менеджеры"
if "selected_period" not in st.session_state:
    st.session_state["selected_period"] = "Месяц"
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# =====================
# ФУНКЦИИ АНАЛИЗА
# =====================
def analyze_call_quality(transcription: str) -> dict:
    """Симулирование анализа качества звонка с помощью AI"""
    # В реальной системе здесь будет вызов к API (OpenAI Whisper, AssemblyAI, Google Speech-to-Text)
    
    transcription_lower = transcription.lower()
    
    # Эмулирование оценок
    politeness_score = 4 if "спасибо" in transcription_lower or "пожалуйста" in transcription_lower else 3
    understanding_score = 4 if "потребность" in transcription_lower or "проблем" in transcription_lower else 3
    solution_score = 3 if "решение" in transcription_lower or "предлаг" in transcription_lower else 2
    closing_score = 3 if "согласи" in transcription_lower or "договор" in transcription_lower else 2
    
    total_score = politeness_score + understanding_score + solution_score + closing_score
    
    # Определение тональности
    positive_words = ["хорошо", "отлично", "спасибо", "согласен", "интересно", "нравится"]
    negative_words = ["проблем", "сложно", "не", "нельзя", "скучно", "плохо"]
    
    pos_count = sum(1 for word in positive_words if word in transcription_lower)
    neg_count = sum(1 for word in negative_words if word in transcription_lower)
    
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    return {
        "total_score": total_score,
        "politeness": politeness_score,
        "understanding": understanding_score,
        "solution": solution_score,
        "closing": closing_score,
        "sentiment": sentiment
    }

def extract_key_phrases(text: str) -> list:
    """Извлечение ключевых фраз из транскрибации"""
    phrases = [
        "автоматизирует контроль", "воронка продаж", "80% времени", "анализ CRM",
        "менеджер", "аудит", "прогноз", "рекомендации", "KPI", "сделки"
    ]
    found = [p for p in phrases if p in text.lower()]
    return found[:5]

def identify_speakers(text: str) -> list:
    """Определение спикеров (Менеджер/Клиент)"""
    lines = text.split(".")
    speakers = []
    for line in lines:
        if "Менеджер:" in line:
            speakers.append({"speaker": "Менеджер", "text": line.replace("Менеджер:", "").strip()})
        elif "Клиент:" in line:
            speakers.append({"speaker": "Клиент", "text": line.replace("Клиент:", "").strip()})
    return speakers

# =====================
# ГЛАВНЫЙ UI
# =====================
def main():
    # Проверка аутентификации
    if not require_auth():
        st.stop()
    
    # Боковая панель
    with st.sidebar:
        st.markdown("## 🎯 RUBI CHAT PRO")
        st.markdown("---")
        
        # Выбор модуля
        st.markdown("### 📌 Модули")
        module = st.radio(
            "Выберите модуль:",
            ["results", "audit", "calls", "pulse", "assistant"],
            format_func=lambda x: {
                "results": "🚀 Результаты ОП",
                "audit": "🔍 Аудит воронки",
                "calls": "☔ Оценка звонков",
                "pulse": "⛵ Пульс сделок",
                "assistant": "🤖 AI Ассистент"
            }[x],
            key="module_select"
        )
        st.session_state["selected_module"] = module
        
        st.markdown("---")
        st.markdown("### ⚙️ Фильтры")
        
        # Фильтры
        manager_filter = st.selectbox(
            "Менеджер:",
            ["Все менеджеры"] + [m["name"] for m in MANAGERS_DATA],
            key="manager_filter"
        )
        st.session_state["selected_manager_filter"] = manager_filter
        
        period = st.selectbox(
            "Период:",
            ["День", "Неделя", "Месяц", "Квартал", "Год"],
            key="period_select"
        )
        st.session_state["selected_period"] = period
        
        st.markdown("---")
        st.markdown("### 📊 Информация")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Менеджеров", len(MANAGERS_DATA))
        with col2:
            st.metric("Сделок", len(DEALS_DATA))
        
        st.markdown("---")
        if st.button("🚪 Выход", use_container_width=True):
            st.session_state[AUTH_KEY] = False
            st.rerun()
    
    # ОСНОВНОЙ КОНТЕНТ
    if st.session_state["selected_module"] == "results":
        show_results_module()
    elif st.session_state["selected_module"] == "audit":
        show_audit_module()
    elif st.session_state["selected_module"] == "calls":
        show_calls_module()
    elif st.session_state["selected_module"] == "pulse":
        show_pulse_module()
    elif st.session_state["selected_module"] == "assistant":
        show_assistant_module()

def show_results_module():
    """Модуль 'Результаты ОП'"""
    st.markdown("# 🚀 Результаты отдела продаж")
    
    # KPI в начале
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("План", "3,560,000 ₽", delta=None)
    with col2:
        st.metric("Факт", "1,860,000 ₽", delta="-1,700,000", delta_color="inverse")
    with col3:
        st.metric("Потенциал", "1,250,000 ₽", delta=None)
    with col4:
        st.metric("% Плана", "52%", delta="-28%", delta_color="inverse")
    
    st.markdown("---")
    
    # Таблица менеджеров
    st.markdown("### 👥 Результаты менеджеров")
    
    managers_df = pd.DataFrame([
        {
            "👤 Менеджер": m["name"],
            "Здоровье": f"{m['health']}%",
            "Цель": f"{m['targets']:,} ₽".replace(",", " "),
            "Факт": f"{m['fact']:,} ₽".replace(",", " "),
            "% Выполнения": f"{int((m['fact']/m['targets'])*100)}%"
        }
        for m in MANAGERS_DATA
    ])
    
    st.dataframe(managers_df, use_container_width=True, hide_index=True)
    
    # Визуализация
    st.markdown("### 📈 Динамика по дням")
    
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    values = np.random.randint(1000000, 2000000, 30)
    
    df_chart = pd.DataFrame({"Дата": dates, "Выручка": values})
    
    if px:
        fig = px.area(df_chart, x="Дата", y="Выручка", title="Динамика выручки")
        fig.update_layout(hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(df_chart.set_index("Дата"))
    
    # Статистика по сделкам
    st.markdown("### 📊 Статистика по сделкам")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Сделок без задач", "38", delta=None)
    with col2:
        st.metric("Просроченные задачи", "46", delta=None)
    with col3:
        st.metric("Застрявшие сделки", "0", delta=None)
    with col4:
        st.metric("Потерянные сделки", "29", delta=None)

def show_audit_module():
    """Модуль 'Аудит воронки'"""
    st.markdown("# 🔍 Аудит воронки")
    
    # Фильтры
    col1, col2 = st.columns(2)
    
    with col1:
        stage_filter = st.multiselect(
            "Стадии сделок:",
            ["agreement", "presentation", "tender", "lost"],
            default=["agreement", "presentation", "tender"]
        )
    
    with col2:
        prob_range = st.slider("Диапазон вероятности:", 0, 100, (0, 100))
    
    # Таблица сделок
    deals_filtered = [d for d in DEALS_DATA if d["stage"] in stage_filter and prob_range[0] <= d["probability"] <= prob_range[1]]
    
    deals_df = pd.DataFrame([
        {
            "Сделка": d["title"],
            "Менеджер": d["manager"],
            "Сумма": f"{d['amount']:,} ₽".replace(",", " "),
            "Стадия": d["stage"],
            "Дней на стадии": d["days_in_stage"],
            "Вероятность": f"{d['probability']}%",
            "Здоровье": "✅" if len(d["health_pos"]) > len(d["health_neg"]) else "⚠️" if len(d["health_neg"]) > 0 else "❌"
        }
        for d in deals_filtered
    ])
    
    st.dataframe(deals_df, use_container_width=True, hide_index=True)
    
    # Детали выбранной сделки
    st.markdown("### 📋 Детали сделки")
    
    if deals_filtered:
        selected_deal = st.selectbox("Выберите сделку:", [d["title"] for d in deals_filtered])
        deal = [d for d in deals_filtered if d["title"] == selected_deal][0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Менеджер:** {deal['manager']}")
            st.markdown(f"**Сумма:** {deal['amount']:,} ₽".replace(",", " "))
        
        with col2:
            st.markdown(f"**Стадия:** {deal['stage']}")
            st.markdown(f"**Вероятность:** {deal['probability']}%")
        
        with col3:
            st.markdown(f"**Дней на стадии:** {deal['days_in_stage']}")
            st.markdown(f"**Здоровье:** {'✅ Хорошее' if len(deal['health_pos']) > 0 else '❌ Плохое'}")
        
        st.markdown("#### ✅ Позитивные факторы")
        for factor in deal["health_pos"]:
            st.markdown(f"- ✓ {factor}")
        
        st.markdown("#### ⚠️ Негативные факторы")
        for factor in deal["health_neg"]:
            st.markdown(f"- ✗ {factor}")

def show_calls_module():
    """Модуль 'Оценка звонков' - ГЛАВНЫЙ НОВЫЙ МОДУЛЬ"""
    st.markdown("# ☔ Оценка качества звонков")
    
    tabs = st.tabs(["📁 Загрузка", "📊 История", "📈 Статистика"])
    
    with tabs[0]:
        st.markdown("## Загрузка и анализ звонков")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📤 Загрузить аудиофайл")
            uploaded_file = st.file_uploader(
                "Выберите MP3 или WAV файл",
                type=["mp3", "wav", "ogg", "m4a"]
            )
        
        with col2:
            manager_select = st.selectbox(
                "Менеджер:",
                [m["name"] for m in MANAGERS_DATA]
            )
        
        if uploaded_file is not None:
            st.success(f"✅ Файл загружен: {uploaded_file.name}")
            
            col1, col2 = st.columns(2)
            with col1:
                duration = st.text_input("Длительность (мин:сек):", "12:45")
            with col2:
                client_name = st.text_input("Имя клиента:", "ООО Клиент")
            
            st.markdown("---")
            
            # ТРАНСКРИБАЦИЯ
            st.markdown("### 🎙️ Транскрибация звонка")
            
            with st.spinner("⏳ Обработка аудио и транскрибация..."):
                time.sleep(2)  # Имитация обработки
                
                transcription = "Менеджер: Добрый день! Это компания РУБИ ЧАТ. Как дела? Клиент: Здравствуйте, спасибо, всё хорошо. Менеджер: Я звоню по вашему запросу о нашем сервисе управления продажами. Клиент: Да, мне интересно узнать подробнее. Менеджер: Наш AI-сервис автоматизирует контроль вашей воронки продаж, экономит 80% времени руководителя на анализ CRM. Клиент: Это очень интересно. Менеджер: Мы работаем с Bitrix24 и AmoCRM. Клиент: У нас есть Bitrix24. Менеджер: Отлично! Интеграция займет один день. Клиент: А стоимость? Менеджер: От 50 тысяч в месяц за трех пользователей. Клиент: Можно нам предложение? Менеджер: Конечно, отправлю КП сегодня же."
                
                st.text_area(
                    "Полная транскрибация:",
                    transcription,
                    height=150,
                    disabled=True
                )
            
            st.markdown("---")
            
            # АНАЛИЗ КАЧЕСТВА
            st.markdown("### 🎯 Анализ качества звонка")
            
            analysis = analyze_call_quality(transcription)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Вежливость", f"{analysis['politeness']}/5")
            with col2:
                st.metric("Понимание", f"{analysis['understanding']}/5")
            with col3:
                st.metric("Решение", f"{analysis['solution']}/5")
            with col4:
                st.metric("Закрытие", f"{analysis['closing']}/5")
            with col5:
                st.metric("Общая оценка", f"{analysis['total_score']}/20")
            
            st.markdown("---")
            
            # ТОНАЛЬНОСТЬ
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😞"}[analysis["sentiment"]]
                sentiment_text = {"positive": "Позитивная", "neutral": "Нейтральная", "negative": "Негативная"}[analysis["sentiment"]]
                st.metric("Тональность", f"{sentiment_emoji} {sentiment_text}")
            
            # СПИКЕРЫ
            st.markdown("### 👥 Определение спикеров")
            
            speakers = identify_speakers(transcription)
            
            for speaker in speakers[:5]:
                if speaker["speaker"] == "Менеджер":
                    st.markdown(f"**🎤 Менеджер:** {speaker['text']}")
                else:
                    st.markdown(f"**👤 Клиент:** {speaker['text']}")
            
            st.markdown("---")
            
            # КЛЮЧЕВЫЕ ФРАЗЫ
            st.markdown("### 🔑 Ключевые фразы")
            
            key_phrases = extract_key_phrases(transcription)
            
            cols = st.columns(len(key_phrases))
            for idx, phrase in enumerate(key_phrases):
                with cols[idx]:
                    st.info(f"📌 {phrase}")
            
            st.markdown("---")
            
            # РЕКОМЕНДАЦИИ
            st.markdown("### 💡 Рекомендации по улучшению")
            
            recommendations = []
            
            if analysis["politeness"] < 4:
                recommendations.append("🎤 Увеличить вежливость и благодарность клиенту")
            if analysis["understanding"] < 4:
                recommendations.append("👂 Лучше слушать и выяснять потребности клиента")
            if analysis["solution"] < 4:
                recommendations.append("💼 Четче представлять решение и его преимущества")
            if analysis["closing"] < 4:
                recommendations.append("✍️ Более активно закрывать сделку, предлагая КП")
            
            if analysis["sentiment"] == "negative":
                recommendations.append("⚠️ Клиент недоволен - срочно свяжитесь для уточнения")
            
            for rec in recommendations:
                st.warning(rec)
            
            st.markdown("---")
            
            # Сохранение звонка
            if st.button("💾 Сохранить анализ", use_container_width=True):
                new_call = {
                    "id": len(st.session_state["uploaded_calls"]) + 1,
                    "file": uploaded_file.name,
                    "manager": manager_select,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "duration": duration,
                    "quality": analysis["total_score"],
                    "sentiment": analysis["sentiment"],
                    "transcription": transcription,
                    "scores": {
                        "politeness": analysis["politeness"],
                        "understanding": analysis["understanding"],
                        "solution": analysis["solution"],
                        "closing": analysis["closing"]
                    }
                }
                
                st.session_state["uploaded_calls"].append(new_call)
                st.success("✅ Анализ звонка сохранён!")
    
    with tabs[1]:
        st.markdown("## 📊 История загруженных звонков")
        
        if st.session_state["uploaded_calls"]:
            calls_df = pd.DataFrame([
                {
                    "🎙️ Файл": c["file"],
                    "👤 Менеджер": c["manager"],
                    "📅 Дата": c["date"],
                    "⏱️ Длит.": c["duration"],
                    "⭐ Оценка": f"{c['quality']}/20",
                    "😊 Тональность": c["sentiment"]
                }
                for c in st.session_state["uploaded_calls"]
            ])
            
            st.dataframe(calls_df, use_container_width=True, hide_index=True)
            
            # Выбор для подробного просмотра
            selected_call_file = st.selectbox(
                "Выберите звонок для детального просмотра:",
                [c["file"] for c in st.session_state["uploaded_calls"]]
            )
            
            selected_call = [c for c in st.session_state["uploaded_calls"] if c["file"] == selected_call_file][0]
            
            st.markdown(f"### Детали: {selected_call['file']}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Оценка", f"{selected_call['quality']}/20")
                st.metric("Вежливость", f"{selected_call['scores']['politeness']}/5")
            
            with col2:
                st.metric("Тональность", selected_call["sentiment"])
                st.metric("Понимание", f"{selected_call['scores']['understanding']}/5")
            
            with col3:
                st.metric("Менеджер", selected_call["manager"])
                st.metric("Дата", selected_call["date"])
            
            st.markdown("#### Транскрибация:")
            st.text_area("", selected_call["transcription"], height=100, disabled=True, key=f"trans_{selected_call['id']}")
    
    with tabs[2]:
        st.markdown("## 📈 Статистика по звонкам")
        
        if st.session_state["uploaded_calls"]:
            # Средние оценки
            avg_quality = np.mean([c["quality"] for c in st.session_state["uploaded_calls"]])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Средняя оценка", f"{avg_quality:.1f}/20")
            
            positive_count = sum(1 for c in st.session_state["uploaded_calls"] if c["sentiment"] == "positive")
            with col2:
                st.metric("Позитивных звонков", f"{positive_count}/{len(st.session_state['uploaded_calls'])}")
            
            with col3:
                st.metric("Всего звонков", len(st.session_state["uploaded_calls"]))
            
            # График распределения оценок
            if px:
                quality_data = pd.DataFrame([
                    {"Оценка": c["quality"], "Менеджер": c["manager"]}
                    for c in st.session_state["uploaded_calls"]
                ])
                
                fig = px.bar(quality_data, x="Менеджер", y="Оценка", title="Распределение оценок по менеджерам")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

def show_pulse_module():
    """Модуль 'Пульс сделок'"""
    st.markdown("# ⛵ Пульс сделок")
    
    st.markdown("## Мониторинг здоровья сделок в реальном времени")
    
    for deal in DEALS_DATA:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"### {deal['title']}")
                st.markdown(f"**Менеджер:** {deal['manager']} | **Сумма:** {deal['amount']:,} ₽".replace(",", " "))
            
            with col2:
                st.markdown(f"**Стадия:** {deal['stage']}")
                st.markdown(f"**Вероятность:** {deal['probability']}%")
            
            with col3:
                # Цветной индикатор здоровья
                if deal['probability'] > 70:
                    st.success(f"Здоровье: {deal['days_in_stage']}+ дней")
                elif deal['probability'] > 40:
                    st.warning(f"Здоровье: {deal['days_in_stage']} дней")
                else:
                    st.error(f"Здоровье: {deal['days_in_stage']} дней")
            
            with col4:
                st.metric("💰 Потенциал", f"{int(deal['amount'] * deal['probability']/100):,} ₽".replace(",", " "))
            
            # Детали
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**✅ Позитивные факторы:**")
                for factor in deal["health_pos"]:
                    st.markdown(f"- ✓ {factor}")
            
            with col2:
                st.markdown("**⚠️ Негативные факторы:**")
                for factor in deal["health_neg"]:
                    st.markdown(f"- ✗ {factor}")

def show_assistant_module():
    """Модуль 'AI Ассистент'"""
    st.markdown("# 🤖 AI Ассистент")
    
    st.markdown("Помогу решить вашу задачу по управлению отделом продаж")
    
    # Chat history
    for message in st.session_state["chat_history"]:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
    
    # Input
    user_input = st.chat_input("Напишите вашу задачу...")
    
    if user_input:
        st.session_state["chat_history"].append({
            "role": "user",
            "content": user_input
        })
        
        # AI Response
        with st.chat_message("assistant"):
            with st.spinner("⏳ Обработка..."):
                time.sleep(1)
                
                response = generate_ai_response(user_input)
                st.markdown(response)
        
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": response
        })
        
        st.rerun()

def generate_ai_response(user_input: str) -> str:
    """Генерация ответа AI ассистента"""
    user_input_lower = user_input.lower()
    
    if "коммерческое" in user_input_lower or "кп" in user_input_lower or "предложение" in user_input_lower:
        return """Вот шаблон коммерческого предложения:

**КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ**

Компания: РУБИЧАТ
Дата: 31 октября 2025

**Услуга:** AI-платформа для управления отделом продаж

**Стоимость:**
- От 50,000₽/мес за 3 пользователей
- +7,500₽ за каждого дополнительного

**Включено:**
✓ Аудит воронки
✓ Оценка звонков  
✓ Результаты ОП
✓ AI Ассистент
✓ Интеграция с CRM

**Условия:** Интеграция за 1 день. Поддержка 24/7.

Рекомендую отправить это предложение после выявления потребностей клиента."""
    
    elif "письмо" in user_input_lower or "email" in user_input_lower:
        return """Вот шаблон письма:

Предмет: Эффективное управление отделом продаж

Добрый день!

Я хотел бы представить вам платформу РУБИЧАТ - уникальный сервис для контроля и управления отделом продаж.

**Основные преимущества:**
- Экономия 80% времени на ручном анализе CRM
- Снижение потери сделок на 40%
- Рост конверсии на 20%
- Прогнозирование плана за 2 недели до конца месяца

**Возможности:**
✓ Аудит воронки и выявление проблем
✓ Оценка качества звонков с AI
✓ Аналитика результатов отдела
✓ AI Ассистент для рекомендаций

Буду рад обсудить ваши потребности. Готов провести демонстрацию прямо сейчас.

С уважением,
Ваше имя"""
    
    elif "рекомендация" in user_input_lower or "совет" in user_input_lower:
        return """**Рекомендации по управлению отделом продаж:**

1. **Ежедневная проверка метрик** - контролируйте план/факт каждый день
2. **Аудит застрявших сделок** - выявляйте проблемы за 5 минут вместо часов
3. **Оценка звонков менеджеров** - улучшайте качество общения на 20%
4. **Пульс сделок** - отслеживайте здоровье каждой сделки
5. **Еженедельные 1-1 встречи** - давайте обратную связь и ставьте цели

**Ожидаемые результаты:**
- Рост выигранных сделок на 19%
- Снижение потерянных сделок на 30%
- Рост прибыли на 40% за год"""
    
    elif "звонк" in user_input_lower or "звон" in user_input_lower:
        return """**Рекомендации для улучшения качества звонков:**

1. **Начало разговора** - представьтесь, спросите о делах
2. **Выявление потребности** - слушайте активно, задавайте вопросы
3. **Презентация решения** - подвяжите преимущества к потребностям
4. **Работа с возражениями** - слушайте, понимайте, отвечайте уважительно
5. **Закрытие сделки** - предложите конкретное действие, назовите сроки

**КПД повышается на 20% при соблюдении этих правил!**"""
    
    else:
        return """Я ваш AI ассистент на платформе РУБИЧАТ. Могу вам помочь с:

✓ Генерацией писем и КП
✓ Анализом сделок и рекомендациями
✓ Советами по улучшению работы команды
✓ Расчетом метрик и аналитикой
✓ Ответами на вопросы по управлению продажами

Что вас интересует? Задайте конкретный вопрос или опишите задачу."""

if __name__ == "__main__":
    main()
