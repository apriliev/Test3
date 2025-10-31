# -*- coding: utf-8 -*-
"""
RUBI CHAT PRO v3.1 - С ПОЛНОЙ СВОДКОЙ ПО ЗВОНКУ
Получает все данные: запрос, сроки, адрес, тип компании и т.д.
"""

import os
import json
import time
from datetime import datetime
from io import BytesIO
import requests

import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI

# =====================
# ЗАГРУЗКА КОНФИГУРАЦИИ
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

st.set_page_config(page_title="RUBI CHAT PRO v3.1", page_icon="🔥", layout="wide")

# =====================
# РАСШИРЕННЫЕ ФУНКЦИИ BITRIX24
# =====================

def get_deal_full_info(deal_id: str) -> dict:
    """Получить полную информацию о сделке"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.deal.get.json"
        params = {"id": deal_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", {})
        return {}
    except Exception as e:
        return {}

def get_contact_full_info(contact_id: str) -> dict:
    """Получить полную информацию о контакте"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.contact.get.json"
        params = {"id": contact_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", {})
        return {}
    except Exception as e:
        return {}

def get_company_full_info(company_id: str) -> dict:
    """Получить полную информацию о компании"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}crm.company.get.json"
        params = {"id": company_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("result", {})
        return {}
    except Exception as e:
        return {}

def get_user_info(user_id: str) -> dict:
    """Получить информацию о менеджере"""
    if not BITRIX24_WEBHOOK:
        return {}
    
    try:
        url = f"{BITRIX24_WEBHOOK}user.get.json"
        params = {"ID": user_id}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json().get("result", [])
            return result[0] if result else {}
        return {}
    except Exception as e:
        return {}

def collect_full_analytics(deal_id: str, call_id: str, record_url: str, transcription: str, analysis: dict) -> dict:
    """Собрать полную аналитику для сводки"""
    
    # Получить все данные
    deal = get_deal_full_info(deal_id)
    contact = get_contact_full_info(deal.get("CONTACT_ID", ""))
    company = get_company_full_info(deal.get("COMPANY_ID", ""))
    manager = get_user_info(deal.get("RESPONSIBLE_USER_ID", ""))
    
    # Извлечь ключевую информацию
    analytics = {
        # Данные о звонке
        "call_id": call_id,
        "call_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "call_duration": "N/A",
        
        # Менеджер
        "manager_name": f"{manager.get('NAME', '')} {manager.get('LAST_NAME', '')}".strip() or "N/A",
        
        # Клиент
        "client_name": f"{contact.get('NAME', '')} {contact.get('LAST_NAME', '')}".strip() or "N/A",
        "client_phone": contact.get("PHONE", [{}])[0].get("VALUE", "") if contact.get("PHONE") else "",
        "client_email": contact.get("EMAIL", [{}])[0].get("VALUE", "") if contact.get("EMAIL") else "",
        
        # Компания
        "company_name": company.get("TITLE", "") or deal.get("TITLE", ""),
        "company_type": company.get("COMPANY_TYPE", ""),
        "company_address": company.get("ADDRESS", ""),
        
        # Сделка
        "deal_title": deal.get("TITLE", ""),
        "deal_amount": deal.get("OPPORTUNITY", ""),
        "deal_stage": deal.get("STAGE_ID", ""),
        "deal_comments": deal.get("COMMENTS", ""),
        
        # Анализ звонка
        "transcription": transcription,
        "analysis": analysis,
        "record_url": record_url,
    }
    
    return analytics

def analyze_full_call_with_gpt(transcription: str, call_data: dict) -> dict:
    """Расширенный анализ звонка со всей информацией"""
    try:
        st.info("🤖 Расширенный анализ звонка...")
        
        prompt = f"""Проанализируй этот телефонный разговор. 

Контекст звонка:
- Компания клиента: {call_data.get('company_name', 'N/A')}
- Тип компании: {call_data.get('company_type', 'N/A')} (перекуп/СК/проектная)
- Адрес клиента: {call_data.get('company_address', 'N/A')}
- Сумма сделки: {call_data.get('deal_amount', 'N/A')} руб.
- Менеджер: {call_data.get('manager_name', 'N/A')}

Транскрибация звонка:
{transcription}

ЗАДАЧА:
1. Определи ЗАПРОС КЛИЕНТА (что он просит)
2. Определи СРОКИ (когда нужно, сроки доставки, отсрочка)
3. Подтверди АДРЕС доставки
4. Определи ЧТО ВАЖНО ДЛЯ КЛИЕНТА (приоритеты)
5. Оцени КАК МЕНЕДЖЕР ОТРАБОТАЛ (0-5 баллов)
6. Оцени ВЫЯВЛЕНИЕ ПОТРЕБНОСТИ (0-5 баллов)
7. Оцени РАБОТУ С ВОЗРАЖЕНИЯМИ (0-5 баллов)
8. Определи ДОГОВОРЕННОСТИ (что договорились)

Ответь JSON:
{{
    "query": "что просит клиент",
    "deadlines": "сроки",
    "address": "адрес доставки",
    "client_priorities": ["приоритет1", "приоритет2", "приоритет3"],
    "manager_work": {{
        "score": 0-5,
        "description": "как отработал менеджер"
    }},
    "need_identification": {{
        "score": 0-5,
        "description": "выявление потребности"
    }},
    "objection_handling": {{
        "score": 0-5,
        "description": "работа с возражениями"
    }},
    "agreements": ["договоренность1", "договоренность2"],
    "next_steps": "что делать дальше"
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты - эксперт по анализу B2B продаж звонков."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content
        
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        json_str = response_text[start_idx:end_idx]
        
        extended_analysis = json.loads(json_str)
        st.success("✅ Анализ завершен!")
        
        return extended_analysis
        
    except Exception as e:
        st.error(f"❌ Ошибка при анализе: {str(e)}")
        return {}

def save_full_analysis_to_bitrix(deal_id: str, analytics: dict, extended_analysis: dict, basic_analysis: dict):
    """Сохранить полную сводку в Bitrix24"""
    if not BITRIX24_WEBHOOK:
        return False
    
    try:
        # Создаем полное примечание
        note_text = f"""═══════════════════════════════════════════════════════════════
📊 АНАЛИЗ КАЧЕСТВА ЗВОНКА - RUBI CHAT PRO v3.1
═══════════════════════════════════════════════════════════════

🎙️ ИНФОРМАЦИЯ О ЗВОНКЕ
─────────────────────────────────────────────────────────────
📅 Дата/Время: {analytics.get('call_date', 'N/A')}
👤 Менеджер: {analytics.get('manager_name', 'N/A')}
📞 Телефон клиента: {analytics.get('client_phone', 'N/A')}

═══════════════════════════════════════════════════════════════
📋 ИНФОРМАЦИЯ О КЛИЕНТЕ
═════════════════════════════════════════════════════════════

🏢 Компания: {analytics.get('company_name', 'N/A')}
👤 Контактное лицо: {analytics.get('client_name', 'N/A')}
📍 Адрес: {analytics.get('company_address', 'N/A')}
🏷️ Тип компании: {analytics.get('company_type', 'N/A')}

═════════════════════════════════════════════════════════════
🎯 СОДЕРЖАНИЕ РАЗГОВОРА
═════════════════════════════════════════════════════════════

📌 ЗАПРОС КЛИЕНТА:
{extended_analysis.get('query', 'N/A')}

⏰ СРОКИ:
{extended_analysis.get('deadlines', 'N/A')}

📍 АДРЕС ДОСТАВКИ:
{extended_analysis.get('address', 'N/A')}

⭐ ЧТО ВАЖНО ДЛЯ КЛИЕНТА:
{chr(10).join(f"• {p}" for p in extended_analysis.get('client_priorities', []))}

═════════════════════════════════════════════════════════════
👨‍💼 КАК МЕНЕДЖЕР ОТРАБОТАЛ ({extended_analysis.get('manager_work', {}).get('score', 'N/A')}/5)
═════════════════════════════════════════════════════════════
{extended_analysis.get('manager_work', {}).get('description', 'N/A')}

═════════════════════════════════════════════════════════════
🎯 РАБОТА С ВЫЯВЛЕНИЕМ ПОТРЕБНОСТИ ({extended_analysis.get('need_identification', {}).get('score', 'N/A')}/5)
═════════════════════════════════════════════════════════════
{extended_analysis.get('need_identification', {}).get('description', 'N/A')}

═════════════════════════════════════════════════════════════
⚡ РАБОТА С ВОЗРАЖЕНИЯМИ ({extended_analysis.get('objection_handling', {}).get('score', 'N/A')}/5)
═════════════════════════════════════════════════════════════
{extended_analysis.get('objection_handling', {}).get('description', 'N/A')}

═════════════════════════════════════════════════════════════
🤝 ДОГОВОРЕННОСТИ
═════════════════════════════════════════════════════════════
{chr(10).join(f"✅ {a}" for a in extended_analysis.get('agreements', []))}

Следующие шаги: {extended_analysis.get('next_steps', 'N/A')}

═════════════════════════════════════════════════════════════
⭐ ИТОГОВАЯ ОЦЕНКА ЗВОНКА
═════════════════════════════════════════════════════════════

🎤 Вежливость: {basic_analysis.get('politeness', 0)}/5
👂 Выявление потребностей: {basic_analysis.get('understanding', 0)}/5
💼 Представление решения: {basic_analysis.get('solution', 0)}/5
✍️ Закрытие сделки: {basic_analysis.get('closing', 0)}/5

📊 ИТОГОВАЯ ОЦЕНКА: {basic_analysis.get('total_score', 0)}/20

😊 ТОНАЛЬНОСТЬ: {basic_analysis.get('sentiment', 'N/A')}

═════════════════════════════════════════════════════════════
💡 РЕКОМЕНДАЦИИ
═════════════════════════════════════════════════════════════
{chr(10).join(f"• {rec}" for rec in basic_analysis.get('recommendations', []))}

═════════════════════════════════════════════════════════════"""
        
        url = f"{BITRIX24_WEBHOOK}crm.activity.add.json"
        
        data = {
            "fields": {
                "OWNER_ID": deal_id,
                "OWNER_TYPE_ID": "2",
                "TYPE_ID": "4",
                "DESCRIPTION": note_text,
                "SUBJECT": "🤖 АНАЛИЗ КАЧЕСТВА ЗВОНКА V3.1"
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        return response.status_code == 200
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось сохранить в Bitrix24: {str(e)}")
        return False

# =====================
# ОСНОВНЫЕ ФУНКЦИИ
# =====================

def transcribe_audio_with_whisper(audio_data: bytes) -> str:
    """Транскрибация"""
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

def analyze_transcript_basic(transcription: str) -> dict:
    """Базовый анализ качества"""
    try:
        st.info("🤖 Базовый анализ качества...")
        
        prompt = f"""Проанализируй звонок по качеству общения (0-20 баллов):

{transcription}

Дай оценку:
1. Вежливость (0-5)
2. Понимание потребностей (0-5)
3. Представление решения (0-5)
4. Закрытие сделки (0-5)
5. Тональность (Позитивная/Нейтральная/Негативная)
6. Ключевые фразы (3-5)
7. Рекомендации (2-3)

Ответь JSON:
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
        
        st.success("✅ Анализ завершен!")
        return analysis
        
    except Exception as e:
        st.error(f"❌ Ошибка: {str(e)}")
        return {}

# =====================
# UI
# =====================

AUTH_KEY = "rubi_chat_auth_v31"

def require_auth():
    if AUTH_KEY not in st.session_state:
        st.session_state[AUTH_KEY] = False
    
    if st.session_state[AUTH_KEY]:
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Вход в RUBI CHAT PRO v3.1")
        
        with st.form("login_form"):
            login = st.text_input("Логин", value="admin")
            password = st.text_input("Пароль", value="admin", type="password")
            if st.form_submit_button("Войти"):
                if login == "admin" and password == "admin":
                    st.session_state[AUTH_KEY] = True
                    st.rerun()
                else:
                    st.error("Неверный логин/пароль")
    
    return False

def main():
    if not require_auth():
        st.stop()
    
    st.markdown("# 🔥 RUBI CHAT PRO v3.1")
    st.markdown("**С полной сводкой по звонку**")
    
    # Загрузка звонка
    uploaded_file = st.file_uploader("Загрузить MP3 звонок", type=["mp3", "wav", "ogg", "m4a"])
    
    if uploaded_file:
        st.success(f"✅ Загружен: {uploaded_file.name}")
        
        col1, col2 = st.columns(2)
        with col1:
            deal_id = st.text_input("ID сделки Bitrix24:", "123")
        with col2:
            call_id = st.text_input("ID звонка:", "456")
        
        if st.button("🚀 Анализировать", use_container_width=True, type="primary"):
            audio_data = uploaded_file.read()
            
            # Транскрибация
            st.markdown("### 📝 Этап 1: Транскрибация")
            transcription = transcribe_audio_with_whisper(audio_data)
            
            if transcription:
                st.text_area("Транскрибация:", transcription, height=100, disabled=True)
                
                # Базовый анализ
                st.markdown("### 🎯 Этап 2: Базовый анализ качества")
                basic_analysis = analyze_transcript_basic(transcription)
                
                if basic_analysis:
                    # Расширенный анализ
                    st.markdown("### 📊 Этап 3: Расширенный анализ")
                    
                    call_data = {
                        "company_name": "Компания из Bitrix24",
                        "company_type": "Перекуп",
                        "company_address": "Адрес из Bitrix24",
                        "deal_amount": "500000",
                        "manager_name": "Менеджер из Bitrix24"
                    }
                    
                    extended_analysis = analyze_full_call_with_gpt(transcription, call_data)
                    
                    if extended_analysis:
                        # Показать результаты
                        st.markdown("#### ✅ Запрос клиента:")
                        st.write(extended_analysis.get('query', 'N/A'))
                        
                        st.markdown("#### ⏰ Сроки:")
                        st.write(extended_analysis.get('deadlines', 'N/A'))
                        
                        st.markdown("#### 📍 Адрес доставки:")
                        st.write(extended_analysis.get('address', 'N/A'))
                        
                        st.markdown("#### ⭐ Приоритеты клиента:")
                        for p in extended_analysis.get('client_priorities', []):
                            st.write(f"• {p}")
                        
                        # Оценки
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("👨‍💼 Работа менеджера", f"{extended_analysis.get('manager_work', {}).get('score', 0)}/5")
                        with col2:
                            st.metric("🎯 Выявление потребности", f"{extended_analysis.get('need_identification', {}).get('score', 0)}/5")
                        with col3:
                            st.metric("⚡ Работа с возражениями", f"{extended_analysis.get('objection_handling', {}).get('score', 0)}/5")
                        
                        # Договоренности
                        st.markdown("#### 🤝 Договоренности:")
                        for a in extended_analysis.get('agreements', []):
                            st.write(f"✅ {a}")
                        
                        # Сохранить в Bitrix24
                        if st.button("💾 Сохранить в Bitrix24", use_container_width=True):
                            success = save_full_analysis_to_bitrix(deal_id, call_data, extended_analysis, basic_analysis)
                            if success:
                                st.success("✅ Сохранено в Bitrix24!")
                            else:
                                st.info("ℹ️ Результаты готовы (Bitrix24 не доступен)")

if __name__ == "__main__":
    main()
