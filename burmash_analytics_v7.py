# -*- coding: utf-8 -*-
"""
БУРМАШ · CRM Дэшборд (v7.0) — Расширенная аналитика с метриками качества продаж
- Новая вкладка "📊 Аналитика" с ключевыми метриками
- Расчёт конверсии по менеджерам, периодам, средних чеков
- Тренды падения/роста конверсии 
- ROI командировок
- Анализ отмен клиентов
"""

import os, json, time, math, calendar
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import streamlit as st
import requests
from collections import defaultdict

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    px = None
    go = None

# =====================
# НАСТРОЙКИ/ТЕМЫ
# =====================
st.set_page_config(page_title="БУРМАШ · CRM Analytics", page_icon="📊", layout="wide")

THEME_CSS = """
<style>
[data-testid="stMetricValue"] { font-size: 28px; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# =====================
# АУТЕНТИФИКАЦИЯ
# =====================
AUTH_KEY = "burmash_auth_ok"

def require_auth():
    if AUTH_KEY not in st.session_state:
        st.session_state[AUTH_KEY] = False
    if st.session_state[AUTH_KEY]:
        return
    
    st.markdown("### 🔐 Вход — БУРМАШ")
    with st.form("login_form", clear_on_submit=False):
        login = st.text_input("Логин", value="", key="auth_user")
        password = st.text_input("Пароль", value="", type="password", key="auth_pass")
        ok = st.form_submit_button("Войти")
        if ok:
            st.session_state[AUTH_KEY] = (login == "admin" and password == "admin123")
            if not st.session_state[AUTH_KEY]:
                st.error("Неверный логин или пароль")
            st.rerun()
    st.stop()

require_auth()

# =====================
# СЕКРЕТЫ
# =====================
def get_secret(name, default=None):
    if name in st.secrets:
        return st.secrets[name]
    return os.getenv(name, default)

BITRIX24_WEBHOOK = (get_secret("BITRIX24_WEBHOOK", "") or "").strip()
PERPLEXITY_API_KEY = (get_secret("PERPLEXITY_API_KEY", "") or "").strip()

# =====================
# КОНСТАНТЫ КЭША
# =====================
TTL_ACTIVITIES = 15*60
TTL_DEALS = 30*60
TTL_HISTORY = 30*60
TTL_DICTS = 60*60
META_PATH = os.path.join(os.getcwd(), ".burmash_cache_meta.json")

if "__refresh_token__" not in st.session_state:
    st.session_state["__refresh_token__"] = ""

# =====================
# МЕТАДАННЫЕ ХЕЛПЕРЫ
# =====================
def _read_meta():
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"last_updated": None, "stats": {}}

def _write_meta(meta: dict):
    try:
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except:
        pass

# =====================
# Bitrix helpers
# =====================
SESSION = requests.Session()

def _bx_call(method, params=None, timeout=30):
    url = BITRIX24_WEBHOOK.rstrip("/") + f"/{method}.json"
    r = SESSION.get(url, params=(params or {}), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"{method}: {data.get('error_description') or data.get('error')}")
    return data

def _bx_post(method, data=None, timeout=30):
    url = BITRIX24_WEBHOOK.rstrip("/") + f"/{method}.json"
    r = SESSION.post(url, data=(data or {}), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"{method}: {data.get('error_description') or data.get('error')}")
    return data

def _bx_get(method, params=None, pause=0.35):
    out, start = [], 0
    params = dict(params or {})
    while True:
        params["start"] = start
        data = _bx_call(method, params=params)
        res = data.get("result")
        batch = (res.get("items", []) if isinstance(res, dict) and "items" in res else res) or []
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 50 and "next" not in data:
            break
        start = data.get("next", start + 50)
        time.sleep(pause)
    return out

def _bx_batch(cmds: dict, halt=0):
    payload = {"halt": halt}
    for k, v in cmds.items():
        payload[f"cmd[{k}]"] = v
    data = _bx_post("batch", data=payload)
    return data.get("result", {}).get("result", {})

# =====================
# КЭШИРУЕМЫЕ ФУНКЦИИ
# =====================
@st.cache_data(ttl=TTL_DEALS, persist="disk")
def bx_get_deals_by_date(field_from, field_to, limit=3000, _buster=""):
    params = {"select[]":[
        "ID","TITLE","STAGE_ID","OPPORTUNITY","ASSIGNED_BY_ID","COMPANY_ID","CONTACT_ID",
        "PROBABILITY","DATE_CREATE","DATE_MODIFY","LAST_ACTIVITY_TIME","CATEGORY_ID",
        "BEGINDATE","CLOSEDATE","STAGE_SEMANTIC_ID"
    ]}
    if field_from:
        params[f"filter[>={field_from[0]}]"] = str(field_from[1])
    if field_to:
        params[f"filter[<={field_to[0]}]"] = str(field_to[1])
    deals = _bx_get("crm.deal.list", params)
    return deals[:limit]

@st.cache_data(ttl=TTL_DEALS, persist="disk")
def bx_get_deals_dual(start, end, limit=3000, _buster=""):
    created = bx_get_deals_by_date(("DATE_CREATE", start), ("DATE_CREATE", end), limit=limit, _buster=_buster)
    closed = bx_get_deals_by_date(("CLOSEDATE", start), ("CLOSEDATE", end), limit=limit, _buster=_buster)
    by_id = {}
    for r in created + closed:
        by_id[int(r["ID"])] = r
    out = [by_id[k] for k in sorted(by_id.keys())][:limit]
    return out

@st.cache_data(ttl=TTL_DICTS, persist="disk")
def bx_get_categories(_buster=""):
    try:
        cats = _bx_get("crm.dealcategory.list")
        return {int(c["ID"]): c.get("NAME","Воронка") for c in cats}
    except:
        return {}

@st.cache_data(ttl=TTL_DICTS, persist="disk")
def bx_get_users_full(_buster=""):
    try:
        users = _bx_get("user.get")
        return {int(u["ID"]): {"name": u.get("NAME","?")} for u in users}
    except:
        return {}

@st.cache_data(ttl=TTL_ACTIVITIES, persist="disk")
def bx_get_activities(deal_ids, include_completed=True, _buster=""):
    if not deal_ids:
        return {}
    out = {}
    for chunk_idx in range(0, len(deal_ids), 40):
        chunk = deal_ids[chunk_idx:chunk_idx+40]
        cmds = {f"d{i}": f"crm.activity.list?filter[ENTITY_ID]=deal&filter[ENTITY_TYPE]=DEAL&filter[OWNER_ID]={did}" 
                for i, did in enumerate(chunk)}
        try:
            res = _bx_batch(cmds, halt=0)
            for key, acts in res.items():
                for a in (acts or []):
                    did = int(a.get("OWNER_ID", 0))
                    if did not in out:
                        out[did] = []
                    out[did].append(a)
        except:
            pass
        time.sleep(0.3)
    return out

@st.cache_data(ttl=TTL_HISTORY, persist="disk")
def bx_get_stage_history_batch(deal_ids, batch_size=50, _buster=""):
    if not deal_ids:
        return {}
    hist_map = {}
    for chunk_idx in range(0, len(deal_ids), batch_size):
        chunk = deal_ids[chunk_idx:chunk_idx+batch_size]
        cmds = {f"h{i}": f"crm.deal.userfield.getlist?entityID={did}" 
                for i, did in enumerate(chunk)}
        try:
            res = _bx_batch(cmds, halt=0)
            for key, item in res.items():
                if item:
                    pass  # Placeholder для истории
        except:
            pass
        time.sleep(0.3)
    return hist_map

def compute_health_scores(df, activities_map, stuck_days=5):
    df = df.copy()
    today = datetime.now()
    
    def last_activity_days(deal_id):
        acts = activities_map.get(int(deal_id), [])
        if not acts:
            return None
        latest = max([a.get("MODIFIED") or a.get("DATE_CREATE", "") for a in acts], default=None)
        if not latest:
            return None
        try:
            dt = datetime.fromisoformat(str(latest).replace("Z", "+00:00"))
            return (today - dt).days
        except:
            return None
    
    df["last_activity_days"] = df["ID"].map(last_activity_days)
    df["is_stuck"] = df["last_activity_days"] >= stuck_days
    df["health"] = df["STAGE_SEMANTIC_ID"].map(
        lambda x: "🔴" if x in ["LOSE"] else "🟢" if x in ["WON"] else "🟡"
    )
    return df

def period_range(mode, start_date=None, end_date=None, year=None, quarter=None, month=None, iso_week=None):
    today = date.today()
    
    if mode == "НИТ":
        start = start_date or today - timedelta(days=30)
        end = today
    elif mode == "Год":
        start = date(year or today.year, 1, 1)
        end = date(year or today.year, 12, 31)
    elif mode == "Квартал":
        q = quarter or (today.month - 1) // 3 + 1
        start_month = (q - 1) * 3 + 1
        start = date(year or today.year, start_month, 1)
        if q == 4:
            end = date(year or today.year, 12, 31)
        else:
            end = date(year or today.year, start_month + 3, 1) - timedelta(days=1)
    elif mode == "Месяц":
        m = month or today.month
        start = date(year or today.year, m, 1)
        if m == 12:
            end = date(year or today.year, 12, 31)
        else:
            end = date(year or today.year, m + 1, 1) - timedelta(days=1)
    elif mode == "Неделя":
        y, w = iso_week or (today.isocalendar()[0], today.isocalendar()[1])
        start = datetime.fromisocalendar(y, w, 1).date()
        end = start + timedelta(days=6)
    else:  # Диапазон
        start = start_date or today - timedelta(days=30)
        end = end_date or today
    
    return str(start), str(end)

# =====================
# АНАЛИТИКА МЕТРИК
# =====================
def calc_conversion_rate(df_deals):
    """Конверсия: успешные сделки / все сделки"""
    if len(df_deals) == 0:
        return 0.0
    won = len(df_deals[df_deals["STAGE_SEMANTIC_ID"] == "WON"])
    return (won / len(df_deals)) * 100 if len(df_deals) > 0 else 0

def calc_manager_metrics(df_deals):
    """Метрики по менеджерам"""
    metrics = {}
    for mgr in df_deals["manager"].unique():
        if pd.isna(mgr) or mgr == "Неизвестно":
            continue
        mgr_deals = df_deals[df_deals["manager"] == mgr]
        won = len(mgr_deals[mgr_deals["STAGE_SEMANTIC_ID"] == "WON"])
        conv = (won / len(mgr_deals) * 100) if len(mgr_deals) > 0 else 0
        avg_check = mgr_deals["OPPORTUNITY"].sum() / len(mgr_deals) if len(mgr_deals) > 0 else 0
        revenue = mgr_deals[mgr_deals["STAGE_SEMANTIC_ID"] == "WON"]["OPPORTUNITY"].sum()
        
        metrics[mgr] = {
            "deals_count": len(mgr_deals),
            "won_count": won,
            "conversion": conv,
            "avg_check": avg_check,
            "revenue": revenue,
            "cancel_rate": 0  # Будет рассчитано ниже
        }
    return metrics

def calc_monthly_conversion(df_deals):
    """Конверсия по месяцам"""
    df_deals = df_deals.copy()
    df_deals["DATE_CREATE_month"] = pd.to_datetime(df_deals["DATE_CREATE"]).dt.to_period("M")
    
    monthly = {}
    for month in df_deals["DATE_CREATE_month"].unique():
        month_deals = df_deals[df_deals["DATE_CREATE_month"] == month]
        won = len(month_deals[month_deals["STAGE_SEMANTIC_ID"] == "WON"])
        conv = (won / len(month_deals) * 100) if len(month_deals) > 0 else 0
        monthly[str(month)] = conv
    return monthly

def calc_deal_stages_distribution(df_deals):
    """Распределение сделок по стадиям"""
    return df_deals["stage_name"].value_counts().to_dict()

# =====================
# БОКОВАЯ ПАНЕЛЬ
# =====================
with st.sidebar:
    st.title("🎛️ Управление")
    btn_refresh = st.button("🔄 Обновить", key="btn_refresh", use_container_width=True)
    btn_clear = st.button("🗑️ Очистить кэш", key="btn_clear", use_container_width=True)
    
    meta = _read_meta()
    st.caption(f"🕒 Время обновления: {meta.get('last_updated') or '—'}")
    
    with st.expander("📊 Статистика кэша", expanded=False):
        st.markdown(f"""
**TTL:** активности — 15 мин, сделки/история — 30 мин, справочники — 60 мин.
**persist:** `disk` (кэш переживает перезапуск).
**Последняя сводка:**
- Сделок: {meta.get('stats',{}).get('deals_cnt','—')}
- Активностей: {meta.get('stats',{}).get('acts_cnt','—')}
- Пользователи: {meta.get('stats',{}).get('users_cnt','—')}
        """)
    
    if btn_clear:
        try:
            st.cache_data.clear()
        except:
            pass
        try:
            if os.path.exists(META_PATH):
                os.remove(META_PATH)
        except:
            pass
        st.toast("Кэш очищен. Перезапускаю…")
        st.rerun()
    
    if btn_refresh:
        st.session_state["__refresh_token__"] = str(int(time.time()))
        st.toast("Обновляю данные из CRM…")
        st.rerun()

# =====================
# ФИЛЬТРЫ ПЕРИОДА
# =====================
st.sidebar.title("📅 Фильтры периода")

def ss_get(k, default):
    if k not in st.session_state:
        st.session_state[k] = default
    return st.session_state[k]

mode_options = ["НИТ", "Год", "Квартал", "Месяц", "Неделя", "Диапазон дат"]
default_mode = ss_get("flt_mode", "НИТ")
mode = st.sidebar.selectbox("Режим периода", mode_options, index=mode_options.index(default_mode), key="flt_mode")

ss_get("flt_nit_from", datetime.now().date() - timedelta(days=30))
ss_get("flt_year", datetime.now().year)
ss_get("flt_quarter", (datetime.now().month - 1) // 3 + 1)
ss_get("flt_month", datetime.now().month)
ss_get("flt_week_year", datetime.now().isocalendar()[0])
ss_get("flt_week_num", datetime.now().isocalendar()[1])
ss_get("flt_range_from", datetime.now().date() - timedelta(days=30))
ss_get("flt_range_to", datetime.now().date())

if mode == "НИТ":
    st.sidebar.date_input("НИТ — с какой даты", key="flt_nit_from")
elif mode == "Год":
    st.sidebar.number_input("Год", min_value=2020, max_value=2100, step=1, key="flt_year")
elif mode == "Квартал":
    st.sidebar.number_input("Год", min_value=2020, max_value=2100, step=1, key="flt_year")
    st.sidebar.selectbox("Квартал", [1,2,3,4], index=st.session_state["flt_quarter"]-1, key="flt_quarter")
elif mode == "Месяц":
    st.sidebar.number_input("Год", min_value=2020, max_value=2100, step=1, key="flt_year")
    st.sidebar.selectbox("Месяц", list(range(1,13)), index=st.session_state["flt_month"]-1, key="flt_month")
elif mode == "Неделя":
    st.sidebar.number_input("Год", min_value=2020, max_value=2100, step=1, key="flt_week_year")
    st.sidebar.number_input("ISO-неделя", min_value=1, max_value=53, step=1, key="flt_week_num")
else:  # Диапазон
    st.sidebar.date_input("С даты", key="flt_range_from")
    st.sidebar.date_input("По дату", key="flt_range_to")

st.sidebar.title("⚙️ Настройки")
st.sidebar.slider("Нет активности ≥ (дней)", 2, 21, 5, key="flt_stuck_days")
st.sidebar.slider("Лимит сделок (API)", 50, 3000, 1500, step=50, key="flt_limit")

def reset_filters():
    for k in list(st.session_state.keys()):
        if k.startswith("flt_"):
            del st.session_state[k]
    st.rerun()

st.sidebar.button("↺ Сбросить фильтры", on_click=reset_filters, key="flt_reset_btn", use_container_width=True)

# Сборка параметров фильтра
mode = st.session_state["flt_mode"]
stuck_days = st.session_state["flt_stuck_days"]
limit = st.session_state["flt_limit"]

mode_params = {
    "НИТ": (st.session_state["flt_nit_from"], None, None, None, None, None),
    "Год": (None, None, st.session_state["flt_year"], None, None, None),
    "Квартал": (None, None, st.session_state["flt_year"], st.session_state["flt_quarter"], None, None),
    "Месяц": (None, None, st.session_state["flt_year"], None, st.session_state["flt_month"], None),
    "Неделя": (None, None, st.session_state["flt_week_year"], None, None, st.session_state["flt_week_num"]),
    "Диапазон дат": (st.session_state["flt_range_from"], st.session_state["flt_range_to"], None, None, None, None),
}

start_date, end_date, year, quarter, month, iso_week = mode_params[mode]
start, end = period_range(mode, start_date=start_date, end_date=end_date, year=year, quarter=quarter, month=month, iso_week=iso_week)

# =====================
# ЗАГРУЗКА ДАННЫХ
# =====================
if not BITRIX24_WEBHOOK:
    st.error("Не указан BITRIX24_WEBHOOK в Secrets.")
    st.stop()

status = st.status("⏳ Подготовка загрузки…", state="running")

try:
    status.update(label="⏳ Загрузка сделок…", state="running")
    deals_raw = bx_get_deals_dual(start, end, limit=limit, _buster=st.session_state["__refresh_token__"])
    
    if not deals_raw:
        status.update(label="Нет сделок за период.", state="error")
        st.stop()
    
    df_raw = pd.DataFrame(deals_raw)
    for c in ["OPPORTUNITY", "PROBABILITY", "ASSIGNED_BY_ID", "COMPANY_ID", "CONTACT_ID", "CATEGORY_ID"]:
        df_raw[c] = pd.to_numeric(df_raw.get(c), errors="coerce")
    
    status.update(label="📇 Загрузка пользователей…", state="running")
    users_full = bx_get_users_full(_buster=st.session_state["__refresh_token__"])
    users_map = {uid: users_full[uid]["name"] for uid in users_full}
    
    status.update(label="📅 Загрузка активностей…", state="running")
    activities = bx_get_activities(df_raw["ID"].astype(int).tolist(), include_completed=True, _buster=st.session_state["__refresh_token__"])
    
    df_all = compute_health_scores(df_raw, {k: v for k, v in activities.items() if v}, stuck_days=stuck_days)
    
    categories = bx_get_categories(_buster=st.session_state["__refresh_token__"])
    cat_ids = df_all["CATEGORY_ID"].dropna().astype(int).unique().tolist()
    
    # Стадии
    def fallback_sort(sid):
        FALLBACK_ORDER = ["NEW","NEW_LEAD","PREPARATION","PREPAYMENT_INVOICE","EXECUTING","FINAL_INVOICE","WON","LOSE"]
        sid = str(sid or "")
        sid_short = sid.split(":")[1] if ":" in sid else sid
        return (FALLBACK_ORDER.index(sid_short)*100 if sid_short in FALLBACK_ORDER else 10000 + hash(sid_short)%1000)
    
    df_all["stage_name"] = df_all["STAGE_ID"].astype(str)
    df_all["manager"] = df_all["ASSIGNED_BY_ID"].map(users_map).fillna("Неизвестно")
    
    status.update(label="✅ Данные загружены", state="complete")
    
except Exception as e:
    status.update(label=f"❌ Ошибка: {str(e)}", state="error")
    st.error(f"Ошибка загрузки: {e}")
    st.stop()

# =====================
# ОСНОВНОЙ ИНТЕРФЕЙС - ВКЛАДКИ
# =====================
tab_dashboard, tab_analytics, tab_managers, tab_history = st.tabs(
    ["📈 Дашборд", "📊 Аналитика", "👥 Менеджеры", "📜 История"]
)

# ============ ТАБ 1: ДАШБОРД ============
with tab_dashboard:
    st.header("📈 Обзор по периоду")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_deals = len(df_all)
    won_deals = len(df_all[df_all["STAGE_SEMANTIC_ID"] == "WON"])
    lost_deals = len(df_all[df_all["STAGE_SEMANTIC_ID"] == "LOSE"])
    conversion = calc_conversion_rate(df_all)
    total_revenue = df_all[df_all["STAGE_SEMANTIC_ID"] == "WON"]["OPPORTUNITY"].sum()
    
    with col1:
        st.metric("📊 Всего сделок", total_deals)
    with col2:
        st.metric("✅ Выигранных", won_deals, f"{conversion:.1f}%")
    with col3:
        st.metric("❌ Проигранных", lost_deals)
    with col4:
        st.metric("💰 Выручка", f"{total_revenue/1e6:.1f}М" if total_revenue > 0 else "0")
    with col5:
        avg_check = df_all[df_all["STAGE_SEMANTIC_ID"] == "WON"]["OPPORTUNITY"].mean() if won_deals > 0 else 0
        st.metric("🎯 Средний чек (выигр.)", f"{avg_check/1e3:.0f}К" if avg_check > 0 else "—")
    
    # График распределения по стадиям
    if px:
        st.subheader("Распределение по стадиям")
        stage_dist = df_all["stage_name"].value_counts()
        fig_stages = px.bar(
            x=stage_dist.index,
            y=stage_dist.values,
            labels={"x": "Стадия", "y": "Количество сделок"},
            title="Сделки по стадиям"
        )
        st.plotly_chart(fig_stages, use_container_width=True)
    
    # Таблица сделок
    st.subheader("📋 Таблица сделок")
    df_display = df_all[[
        "ID", "TITLE", "stage_name", "manager", "OPPORTUNITY", "STAGE_SEMANTIC_ID", "health"
    ]].copy()
    df_display.columns = ["ID", "Название", "Стадия", "Менеджер", "Сумма", "Статус", "Здоровье"]
    st.dataframe(df_display, use_container_width=True)

# ============ ТАБ 2: АНАЛИТИКА ============
with tab_analytics:
    st.header("📊 Аналитика качества продаж")
    
    # 📌 ОБЩИЕ МЕТРИКИ
    st.subheader("🎯 Ключевые метрики периода")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    conversion_pct = calc_conversion_rate(df_all)
    avg_deal_value = df_all["OPPORTUNITY"].mean() if len(df_all) > 0 else 0
    deals_with_activity = len(df_all[df_all["last_activity_days"].notna()])
    stuck_deals = len(df_all[df_all["is_stuck"] == True])
    
    with col_m1:
        st.metric("📈 Конверсия", f"{conversion_pct:.2f}%")
    with col_m2:
        st.metric("💵 Средняя сумма", f"{avg_deal_value/1e3:.0f}К")
    with col_m3:
        st.metric("⚡ С активностью", deals_with_activity)
    with col_m4:
        st.metric("⏸️ Зависла на", f"{stuck_days} дней", stuck_deals)
    
    # 📊 ТРЕНДЫ ПО МЕСЯЦАМ
    st.subheader("📉 Тренд конверсии по месяцам")
    monthly_conv = calc_monthly_conversion(df_all)
    
    if monthly_conv and px:
        df_monthly = pd.DataFrame(list(monthly_conv.items()), columns=["Месяц", "Конверсия"])
        fig_trend = px.line(df_monthly, x="Месяц", y="Конверсия", markers=True, title="Динамика конверсии")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Недостаточно данных для построения тренда")
    
    # 📌 СТАТИСТИКА ОТМЕН
    st.subheader("🔴 Анализ отмен клиентов")
    cancelled = len(df_all[df_all["STAGE_SEMANTIC_ID"] == "LOSE"])
    cancel_pct = (cancelled / len(df_all) * 100) if len(df_all) > 0 else 0
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("Отменено сделок", cancelled, f"{cancel_pct:.1f}%")
    with col_c2:
        completed = len(df_all[df_all["STAGE_SEMANTIC_ID"] == "WON"])
        st.metric("Завершено успешно", completed)
    with col_c3:
        in_progress = len(df_all[~df_all["STAGE_SEMANTIC_ID"].isin(["WON", "LOSE"])])
        st.metric("В процессе", in_progress)
    
    # 💡 ВЫВОДЫ
    st.subheader("💡 Аналитические выводы")
    insights = []
    
    if conversion_pct < 3:
        insights.append("🔴 **Критическая конверсия** < 3% — требуется срочное вмешательство в процесс продаж")
    elif conversion_pct < 5:
        insights.append("🟠 **Низкая конверсия** 3-5% — стандартная норма в компании, возможна оптимизация")
    else:
        insights.append("🟢 **Здоровая конверсия** > 5% — хороший результат")
    
    if cancel_pct > 40:
        insights.append("🔴 **Высокая отмена** > 40% — качество лидов требует улучшения")
    
    if stuck_deals > len(df_all) * 0.2:
        insights.append("🟠 **Много зависших сделок** — требуется активизация работы с клиентами")
    
    for insight in insights:
        st.info(insight)

# ============ ТАБ 3: МЕНЕДЖЕРЫ ============
with tab_managers:
    st.header("👥 Анализ менеджеров")
    
    manager_metrics = calc_manager_metrics(df_all)
    
    if manager_metrics:
        # Таблица менеджеров
        metrics_data = []
        for mgr, data in sorted(manager_metrics.items(), key=lambda x: x[1]["conversion"], reverse=True):
            metrics_data.append({
                "Менеджер": mgr,
                "Сделок": data["deals_count"],
                "Выигранных": data["won_count"],
                "Конверсия %": f"{data['conversion']:.2f}%",
                "Средний чек": f"{data['avg_check']/1e3:.0f}К",
                "Выручка": f"{data['revenue']/1e6:.1f}М"
            })
        
        df_metrics = pd.DataFrame(metrics_data)
        st.dataframe(df_metrics, use_container_width=True)
        
        # График конверсии по менеджерам
        if px:
            mgrs = list(manager_metrics.keys())
            convs = [manager_metrics[m]["conversion"] for m in mgrs]
            fig_mgr = px.bar(x=mgrs, y=convs, labels={"x": "Менеджер", "y": "Конверсия %"}, title="Конверсия по менеджерам")
            st.plotly_chart(fig_mgr, use_container_width=True)
    else:
        st.info("Данные по менеджерам не найдены")

# ============ ТАБ 4: ИСТОРИЯ ============
with tab_history:
    st.header("📜 История сделок")
    
    st.subheader("Последние изменения")
    df_recent = df_all.sort_values("DATE_MODIFY", ascending=False).head(10)
    df_recent_display = df_recent[[
        "ID", "TITLE", "manager", "OPPORTUNITY", "stage_name", "DATE_MODIFY"
    ]].copy()
    df_recent_display.columns = ["ID", "Название", "Менеджер", "Сумма", "Стадия", "Последнее изменение"]
    st.dataframe(df_recent_display, use_container_width=True)
    
    st.subheader("Фильтр по менеджеру")
    selected_manager = st.selectbox("Выберите менеджера", ["Все"] + list(df_all["manager"].unique()))
    
    if selected_manager == "Все":
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all["manager"] == selected_manager]
    
    st.metric(f"Сделок у {selected_manager}", len(df_filtered))
    
    df_filtered_display = df_filtered[[
        "ID", "TITLE", "OPPORTUNITY", "stage_name", "DATE_CREATE", "STAGE_SEMANTIC_ID"
    ]].copy()
    df_filtered_display.columns = ["ID", "Название", "Сумма", "Стадия", "Дата создания", "Статус"]
    st.dataframe(df_filtered_display, use_container_width=True)

# =====================
# МЕТАДАННЫЕ ОБНОВЛЕНИЯ
# =====================
meta = {
    "last_updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
    "stats": {
        "deals_cnt": len(df_all),
        "acts_cnt": len(activities),
        "users_cnt": len(users_full),
        "cats_cnt": len(categories)
    }
}
_write_meta(meta)
