# -*- coding: utf-8 -*-
"""
БУРМАШ · Интеграция аналитики в основное приложение
Этот файл показывает, как подключить analytic_engine.py к burmash_analytics_v7.py
"""

# ====================================
# ПРИМЕР ИНТЕГРАЦИИ В STREAMLIT
# ====================================

import streamlit as st
import pandas as pd
from analytic_engine import AnalyticEngine


def render_analytics_tab():
    """
    Функция для рендеринга полной вкладки аналитики
    Вставьте этот код в основное приложение вместо или дополнительно к существующей аналитике
    """
    
    st.header("📊 Расширенная аналитика с AnalyticEngine")
    
    # Предполагаем, что df_all и users_map уже загружены
    # (они должны быть в st.session_state или параметрах функции)
    
    if 'df_all' not in st.session_state or 'users_map' not in st.session_state:
        st.error("Данные не загружены. Сначала загрузите сделки.")
        return
    
    df_all = st.session_state['df_all']
    users_map = st.session_state['users_map']
    
    # Инициализируем аналитический движок
    engine = AnalyticEngine(df_all, users_map)
    
    # ========== РАЗДЕЛ 1: АНАЛИЗ ТРЕНДА ==========
    st.subheader("📉 Анализ тренда конверсии")
    col1, col2, col3, col4 = st.columns(4)
    
    trend_data = engine.conversion_trend_analysis()
    
    with col1:
        st.metric(
            "📊 Тренд",
            trend_data["trend"],
            f"{trend_data['change_pct']:.1f}%"
        )
    with col2:
        st.metric(
            "Первый месяц",
            f"{trend_data['first_month_conv']:.2f}%"
        )
    with col3:
        st.metric(
            "Последний месяц",
            f"{trend_data['last_month_conv']:.2f}%"
        )
    with col4:
        st.metric(
            "Изменение (п.п.)",
            f"{trend_data['absolute_change']:.2f}%"
        )
    
    # ========== РАЗДЕЛ 2: АНАЛИЗ ПО ПЕРИОДАМ ==========
    st.subheader("📅 Конверсия по периодам")
    
    tab_year, tab_quarter, tab_month = st.tabs(["По годам", "По кварталам", "По месяцам"])
    
    with tab_year:
        yearly = engine.conversion_by_year()
        if yearly:
            df_yearly = pd.DataFrame([
                {
                    "Год": year,
                    "Сделок": data["total_deals"],
                    "Выигранных": data["won_deals"],
                    "Конверсия %": f"{data['conversion_pct']:.2f}%",
                    "Выручка": f"{data['revenue']/1e6:.1f}М",
                    "Средний чек": f"{data['avg_check']/1e3:.0f}К"
                }
                for year, data in yearly.items()
            ])
            st.dataframe(df_yearly, use_container_width=True)
        else:
            st.info("Данные по годам не найдены")
    
    with tab_quarter:
        quarterly = engine.conversion_by_quarter()
        if quarterly:
            df_quarterly = pd.DataFrame([
                {
                    "Период": period,
                    "Сделок": data["total_deals"],
                    "Выигранных": data["won_deals"],
                    "Конверсия %": f"{data['conversion_pct']:.2f}%",
                    "Выручка": f"{data['revenue']/1e6:.1f}М",
                    "Средний чек": f"{data['avg_check']/1e3:.0f}К"
                }
                for period, data in quarterly.items()
            ])
            st.dataframe(df_quarterly, use_container_width=True)
        else:
            st.info("Данные по кварталам не найдены")
    
    with tab_month:
        monthly = engine.conversion_by_month()
        if monthly:
            df_monthly = pd.DataFrame([
                {
                    "Месяц": month,
                    "Сделок": data["total_deals"],
                    "Выигранных": data["won_deals"],
                    "Конверсия %": f"{data['conversion_pct']:.2f}%",
                    "Выручка": f"{data['revenue']/1e6:.1f}М",
                    "Средний чек": f"{data['avg_check']/1e3:.0f}К"
                }
                for month, data in monthly.items()
            ])
            st.dataframe(df_monthly, use_container_width=True)
        else:
            st.info("Данные по месяцам не найдены")
    
    # ========== РАЗДЕЛ 3: РЕЙТИНГ МЕНЕДЖЕРОВ ==========
    st.subheader("👥 Рейтинг менеджеров по конверсии")
    
    ranking = engine.manager_ranking()
    
    if ranking:
        # Таблица рейтинга
        df_ranking = pd.DataFrame(ranking)
        
        # Кастомизация отображения
        st.dataframe(
            df_ranking[[
                "rank", "manager", "conversion", "status", "deals", "won", "revenue"
            ]].rename(columns={
                "rank": "🏆 Место",
                "manager": "👤 Менеджер",
                "conversion": "📈 Конверсия %",
                "status": "📊 Статус",
                "deals": "📋 Сделок",
                "won": "✅ Выигранных",
                "revenue": "💰 Выручка"
            }),
            use_container_width=True
        )
        
        # Визуализация
        import plotly.express as px
        fig = px.bar(
            df_ranking,
            x="manager",
            y="conversion",
            title="Конверсия по менеджерам",
            labels={"manager": "Менеджер", "conversion": "Конверсия %"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Данные по менеджерам не найдены")
    
    # ========== РАЗДЕЛ 4: ОБНАРУЖЕНИЕ КРИЗИСОВ ==========
    st.subheader("🚨 Обнаружение проблем")
    
    alerts = engine.crisis_detection()
    
    if alerts:
        for alert in alerts:
            level = alert["level"]
            issue = alert["issue"]
            
            if "КРИТИЧЕСКАЯ" in level:
                st.error(f"**{level}** {issue}")
            elif "КРИЗИС" in level or "ВНИМАНИЕ" in level:
                st.warning(f"**{level}** {issue}")
            else:
                st.info(f"**{level}** {issue}")
    else:
        st.success("🟢 Критических проблем не обнаружено")
    
    # ========== РАЗДЕЛ 5: РАСПРЕДЕЛЕНИЕ ПО РАЗМЕРУ ЧЕКА ==========
    st.subheader("💵 Анализ по размеру чека")
    
    opp_dist = engine.opportunity_distribution()
    
    if opp_dist:
        df_opp = pd.DataFrame([
            {
                "Сегмент": seg,
                "Сделок": data["deals"],
                "Выигранных": data["won"],
                "Конверсия %": f"{data['conversion']:.2f}%",
                "Средний чек": f"{data['avg_check']/1e3:.0f}К",
                "Выручка": f"{data['revenue']/1e6:.1f}М"
            }
            for seg, data in opp_dist.items()
        ])
        
        st.dataframe(df_opp, use_container_width=True)
        
        # График
        import plotly.express as px
        fig = px.bar(
            df_opp,
            x="Сегмент",
            y="Конверсия %",
            title="Конверсия по сегментам (размер чека)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Данные о распределении не найдены")
    
    # ========== РАЗДЕЛ 6: ЗАВИСШИЕ СДЕЛКИ ==========
    st.subheader("⏸️ Зависшие сделки (7+ дней без активности)")
    
    stalled = engine.stalled_deals(stuck_days=7)
    
    if stalled:
        df_stalled = pd.DataFrame(stalled)
        st.dataframe(df_stalled, use_container_width=True)
        st.metric("Количество зависших", len(stalled))
    else:
        st.success("✅ Нет зависших сделок")


# ====================================
# ИНТЕГРАЦИЯ В ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ====================================

"""
Чтобы добавить эту аналитику в основное приложение burmash_analytics_v7.py:

1. В начало файла добавьте импорт:
   from analytic_engine import AnalyticEngine

2. После загрузки данных сохраните их в session_state:
   st.session_state['df_all'] = df_all
   st.session_state['users_map'] = users_map

3. В вкладке "Аналитика" вызовите:
   render_analytics_tab()

Пример:
```python
import streamlit as st
from analytic_engine import AnalyticEngine

# ... другой код ...

# После загрузки данных
st.session_state['df_all'] = df_all
st.session_state['users_map'] = users_map

# Вкладки
tab_dashboard, tab_analytics, tab_managers, tab_history = st.tabs([...])

with tab_analytics:
    render_analytics_tab()
```
"""


# ====================================
# STANDALONE СКРИПТ ДЛЯ ТЕСТИРОВАНИЯ
# ====================================

if __name__ == "__main__":
    # Этот код выполняется, если запустить файл напрямую
    print("Этот файл предназначен для интеграции в основное приложение")
    print("\nПримеры использования:")
    print("  1. Импортируйте: from analytic_integration import AnalyticEngine")
    print("  2. Используйте: engine = AnalyticEngine(df_deals, users_map)")
    print("  3. Вызовите: render_analytics_tab()")
