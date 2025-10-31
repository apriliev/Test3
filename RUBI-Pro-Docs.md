# RUBI CHAT PRO - Полная интеграция с транскрибацией звонков

## ОПИСАНИЕ ПРОЕКТА

**RUBI Chat PRO** - это полный аналог платформы RUBI Chat с интегрированной функцией **транскрибации звонков**. Приложение предназначено для управления отделом продаж с использованием AI-анализа для:

- Контроля выполнения KPI
- Аудита воронки продаж
- **Оценки качества звонков с автоматической транскрибацией**
- Прогнозирования плана продаж
- Рекомендаций для менеджеров

---

## АРХИТЕКТУРА СИСТЕМЫ

### 1. Основные модули

```
RUBI CHAT PRO
├── Результаты ОП (Dashboard)
│   ├── KPI метрики (План/Факт/Потенциал)
│   ├── Таблица менеджеров с показателями
│   └── Графики динамики выручки
├── Аудит воронки
│   ├── Таблица сделок с фильтрами
│   ├── Анализ здоровья каждой сделки
│   └── Идентификация проблем
├── ☔ ОЦЕНКА ЗВОНКОВ (НОВОЕ)
│   ├── Загрузка аудиофайлов (MP3/WAV)
│   ├── Транскрибация речи в текст
│   ├── Определение спикеров (Agent/Client)
│   ├── Анализ качества звонка
│   ├── Оценка по критериям
│   ├── Определение тональности
│   ├── История звонков
│   └── Статистика и отчёты
├── Пульс сделок
│   ├── Мониторинг здоровья сделок
│   ├── Индикаторы потенциала
│   └── Рекомендации по действиям
└── AI Ассистент
    ├── Генерация писем/КП
    ├── Анализ сделок
    └── Рекомендации
```

### 2. Технический стек

**Backend:**
- Python 3.9+
- Streamlit (Web Framework)
- Pandas / NumPy (Data Processing)
- Requests (API Calls)

**Frontend:**
- Streamlit UI Components
- Plotly (Charts)
- Custom CSS

**Интеграции:**
- **Bitrix24 API** - для синхронизации CRM данных
- **Speech-to-Text API** - для транскрибации (OpenAI Whisper, Google Cloud, AssemblyAI, Deepgram)
- **Sentiment Analysis** - для определения тональности
- **Speaker Diarization** - для определения спикеров

---

## ФУНКЦИЯ ТРАНСКРИБАЦИИ ЗВОНКОВ

### Процесс работы:

```
1. Загрузка аудиофайла (MP3/WAV/OGG)
   ↓
2. Конвертация в нужный формат (если требуется)
   ↓
3. ТРАНСКРИБАЦИЯ (Speech-to-Text)
   ├── Отправка на сервис (Google/OpenAI/AssemblyAI)
   └── Получение полного текста разговора
   ↓
4. SPEAKER DIARIZATION (Определение спикеров)
   ├── Выделение реплик Менеджера
   └── Выделение реплик Клиента
   ↓
5. АНАЛИЗ КАЧЕСТВА
   ├── Оценка вежливости (0-5)
   ├── Понимание потребностей (0-5)
   ├── Представление решения (0-5)
   ├── Закрытие сделки (0-5)
   └── Итоговая оценка (0-20)
   ↓
6. SENTIMENT ANALYSIS (Анализ тональности)
   ├── Позитивная / Нейтральная / Негативная
   └── Уровень уверенности
   ↓
7. ИЗВЛЕЧЕНИЕ КЛЮЧЕВЫХ ФРАЗ
   ├── Ключевые моменты разговора
   └── Выявление проблем/возражений
   ↓
8. РЕКОМЕНДАЦИИ
   ├── Что улучшить
   └── План развития менеджера
```

### Рекомендуемые API сервисы:

#### **OpenAI Whisper API** (Рекомендуется)
- Высокая точность транскрибации
- Поддержка 99 языков
- Оценка: $0.006 за минуту аудио
- Самая точная транскрибация среди всех сервисов

```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")

with open("call.mp3", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="ru"
    )
    print(transcript.text)
```

#### **Google Cloud Speech-to-Text**
- Встроенная поддержка даризации спикеров
- Детальный анализ эмоций
- Более дорогой вариант ($0.024-0.036 за минуту)

```python
from google.cloud import speech_v1
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

client = speech_v1.SpeechClient()

with open("call.wav", "rb") as audio_file:
    content = audio_file.read()

audio = speech_v1.RecognitionAudio(content=content)

config = speech_v1.RecognitionConfig(
    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
    language_code="ru-RU",
    enable_speaker_diarization=True,
    diarization_speaker_count=2
)

response = client.recognize(config=config, audio=audio)

for result in response.results:
    print(result.alternatives[0].transcript)
```

#### **AssemblyAI**
- Быстрая транскрибация
- Встроенный анализ эмоций и тем
- $0.015 за минуту аудио

```python
import requests

headers = {
    "authorization": "YOUR_API_KEY"
}

# Загрузка файла
with open("call.mp3", "rb") as f:
    response = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        data=f
    )
    audio_url = response.json()["upload_url"]

# Обработка
response = requests.post(
    "https://api.assemblyai.com/v2/transcript",
    headers=headers,
    json={"audio_url": audio_url}
)

transcript_id = response.json()["id"]

# Получение результата
while True:
    response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers=headers
    )
    if response.json()["status"] == "completed":
        print(response.json()["text"])
        break
```

---

## КРИТЕРИИ ОЦЕНКИ КАЧЕСТВА ЗВОНКА

### 1. Вежливость и профессионализм (0-5)
- ✓ Профессиональное приветствие
- ✓ Благодарность клиенту
- ✓ Вежливый тон общения
- ✓ Соблюдение стандартов компании
- ✗ Грубость, раздражение

### 2. Понимание потребностей (0-5)
- ✓ Активное слушание
- ✓ Задание уточняющих вопросов
- ✓ Выявление "болевых точек"
- ✓ Адекватная интерпретация ответов
- ✗ Монолог без диалога

### 3. Представление решения (0-5)
- ✓ Четкое описание услуги/продукта
- ✓ Связь преимуществ с потребностями
- ✓ Приведение примеров
- ✓ Ясность объяснения
- ✗ Размытая информация

### 4. Закрытие сделки (0-5)
- ✓ Предложение конкретного действия
- ✓ Установка сроков
- ✓ Получение согласия клиента
- ✓ Договоренность о КП/встрече
- ✗ Открытое завершение без результата

### Итоговая оценка: сумма всех критериев (0-20)

**Пороги оценок:**
- 18-20: Отличный звонок 🟢 (Зелёный)
- 14-17: Хороший звонок 🟡 (Жёлтый)
- 10-13: Средний звонок 🟠 (Оранжевый)
- 5-9: Плохой звонок 🔴 (Красный)
- 0-4: Очень плохой звонок ⚫ (Чёрный)

---

## ИНТЕГРАЦИЯ С BITRIX24

### Загрузка звонков из Bitrix24

```python
import requests

BITRIX_WEBHOOK = "https://YOUR_DOMAIN.bitrix24.ru/rest/1/USER_TOKEN/"

def get_calls_from_bitrix():
    """Получить список записей звонков из Bitrix24"""
    
    url = BITRIX_WEBHOOK + "crm.activity.list.json"
    
    params = {
        "filter[SUBJECT]": "Звонок",
        "filter[TYPE_ID]": "1",  # Phone call
        "select": ["ID", "SUBJECT", "CREATED", "DESCRIPTION", "CALL_ID"]
    }
    
    response = requests.get(url, params=params)
    return response.json().get("result", [])

def get_call_recording_url(call_id):
    """Получить URL записи звонка"""
    
    url = BITRIX_WEBHOOK + f"telephony.externalcall.finish.json"
    
    response = requests.get(url, params={"CALL_ID": call_id})
    return response.json().get("RECORD_URL")

# Использование
calls = get_calls_from_bitrix()
for call in calls:
    record_url = get_call_recording_url(call["ID"])
    # Загружаем звонок и обрабатываем
```

### Сохранение анализа обратно в Bitrix24

```python
def save_call_analysis_to_bitrix(call_id, analysis_data):
    """Сохранить результаты анализа в Bitrix24 как примечание"""
    
    note_text = f"""
    **АНАЛИЗ КАЧЕСТВА ЗВОНКА**
    
    Оценка: {analysis_data['total_score']}/20
    Вежливость: {analysis_data['politeness']}/5
    Понимание: {analysis_data['understanding']}/5
    Решение: {analysis_data['solution']}/5
    Закрытие: {analysis_data['closing']}/5
    
    Тональность: {analysis_data['sentiment']}
    
    Ключевые фразы:
    {', '.join(analysis_data['key_phrases'])}
    
    Рекомендации:
    {'. '.join(analysis_data['recommendations'])}
    """
    
    url = BITRIX_WEBHOOK + "crm.activity.add.json"
    
    data = {
        "fields": {
            "OWNER_ID": call_id,
            "OWNER_TYPE_ID": "2",  # Deal
            "TYPE_ID": "4",  # Note
            "DESCRIPTION": note_text,
            "SUBJECT": "АНАЛИЗ ЗВОНКА - AI"
        }
    }
    
    response = requests.post(url, json=data)
    return response.json()
```

---

## ЕЖЕДНЕВНЫЙ И ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ

### Ежедневный отчет (Email)

```
ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО ЗВОНКАМ - 31 октября 2025

📊 Статистика:
- Всего звонков: 47
- Средняя оценка: 14.2/20
- Позитивных: 28 (59.6%)
- Нейтральных: 15 (31.9%)
- Негативных: 4 (8.5%)

👥 По менеджерам:
Менеджер Иван:    16 звонков (средняя 16.3/20) ⭐⭐⭐⭐
Менеджер Артем:   15 звонков (средняя 14.1/20) ⭐⭐⭐
Менеджер Ирина:   12 звонков (средняя 12.5/20) ⭐⭐
Менеджер Мария:    4 звонков (средняя 10.2/20) ⭐

🎯 Рекомендации на завтра:
1. Проверить звонок Мария от 15:30 (оценка 7/20)
2. Провести коучинг с Ириной по закрытию сделок
3. Отметить отличную работу Ивана - 5 звонков на 16+ баллов
```

### Еженедельный отчет (Analytics)

```
ЕЖЕНЕДЕЛЬНЫЙ АНАЛИТИЧЕСКИЙ ОТЧЕТ
Неделя: 25 октября - 31 октября 2025

📈 Динамика:
Понедельник:    12 звонков (avg 13.8)
Вторник:        14 звонков (avg 14.1)
Среда:          15 звонков (avg 14.5)
Четверг:        13 звонков (avg 14.2)
Пятница:        11 звонков (avg 15.1) ⬆️
Суббота-Воскресенье: выходные

💰 Корреляция с выручкой:
- Дни с average score >14: +35% выручки
- Дни с average score <13: -15% выручки

👁️ Трендинговые ошибки:
1. Недостаточное выявление потребностей (avg -0.8 балла)
2. Слабое закрытие (avg -0.6 балла)
3. Недостаток активного слушания (avg -0.7 балла)

📚 Рекомендуемое обучение:
- Модуль "Выявление потребностей" - для всех
- Модуль "Закрытие сделки" - для Ирины и Марии
- Коучинг 1-1 с Иваном по лучшим практикам
```

---

## УСТАНОВКА И РАЗВЕРТЫВАНИЕ

### Локальное тестирование

```bash
# 1. Клонируем/создаем проект
mkdir rubi-chat-pro
cd rubi-chat-pro

# 2. Создаем виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# 3. Устанавливаем зависимости
pip install -r requirements.txt

# 4. Создаем файл конфигурации
echo "BITRIX24_WEBHOOK=https://YOUR_DOMAIN.bitrix24.ru/rest/1/TOKEN/" > .env
echo "OPENAI_API_KEY=sk-..." >> .env
echo "GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json" >> .env

# 5. Запускаем приложение
streamlit run rubi_chat_pro_main.py
```

### Развертывание на сервере (Heroku/Railway/Render)

```bash
# 1. Создаем файл Procfile
echo "web: streamlit run rubi_chat_pro_main.py" > Procfile

# 2. Создаем requirements.txt с зависимостями

# 3. Инициализируем git
git init
git add .
git commit -m "Initial commit"

# 4. Деплоим на выбранную платформу
# Heroku:
git push heroku main

# Railway:
railway up

# Render:
# Создаем через UI платформы
```

---

## ФАЙЛОВАЯ СТРУКТУРА

```
rubi-chat-pro/
├── rubi_chat_pro_main.py          # Основной файл приложения
├── requirements.txt               # Зависимости
├── .env.example                   # Пример переменных окружения
├── .streamlit/
│   └── config.toml               # Конфиг Streamlit
├── modules/
│   ├── auth.py                   # Аутентификация
│   ├── bitrix_api.py             # Интеграция с Bitrix24
│   ├── transcription.py          # Работа с транскрибацией
│   ├── analysis.py               # Анализ звонков
│   └── utils.py                  # Утилиты
├── data/
│   ├── mock_managers.json        # Mock данные
│   ├── mock_deals.json           # Mock сделки
│   └── mock_calls.json           # Mock звонки
└── README.md                      # Документация
```

---

## ТРЕБОВАНИЯ К РАЗВЕРТЫВАНИЮ

### Переменные окружения (.env)

```
# Bitrix24
BITRIX24_WEBHOOK=https://your-domain.bitrix24.ru/rest/1/USER_TOKEN/

# OpenAI (Whisper)
OPENAI_API_KEY=sk-...

# Google Cloud (опционально)
GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json

# Sentio (опционально)
SENTIMENTAL_API_KEY=...

# Streamlit настройки
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_MAXUPLOADSIZE=200
```

### Требования к серверу

- Python 3.9+
- Минимум 2GB RAM
- Доступ в интернет (для API вызовов)
- SSL сертификат (рекомендуется для production)

---

## ДАЛЬНЕЙШЕЕ РАЗВИТИЕ

### v2.0 (Планируется)
- [ ] Real-time транскрибация во время звонка
- [ ] Интеграция с Telegram для уведомлений
- [ ] REST API для внешних интеграций
- [ ] Multilingual поддержка (EN, ES, DE, FR)
- [ ] Экспорт в PDF/Excel отчётов
- [ ] Dashboard в Bitrix24 как виджет

### v2.1
- [ ] Machine Learning модели для прогнозирования
- [ ] Автоматический коучинг во время звонка (в реальном времени)
- [ ] Интеграция с HubSpot
- [ ] Поддержка видео-звонков
- [ ] А/Б тестирование скриптов

---

## ЛИЦЕНЗИЯ И КОНТАКТЫ

**Автор:** RUBI CHAT Team
**Версия:** 1.0
**Дата:** Октябрь 2025

Для вопросов и поддержки: support@rubichat.ru
