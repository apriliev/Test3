# -*- coding: utf-8 -*-
"""
БУРМАШ · Специфические метрики из документа "Аналитика ОП 2023-2025"
Расширенные расчёты для анализа, соответствующие выводам аналитики
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class DocumentAnalytics:
    """
    Класс для расчёта специфических метрик из документа аналитики
    Соответствует данным из "Аналитика-ОП-2023-2025-v3.docx"
    """
    
    def __init__(self, df_deals):
        """
        df_deals: DataFrame с данными сделок
        Ожидаемые колонки: 
        - ASSIGNED_BY_ID, MANAGER_NAME
        - OPPORTUNITY
        - STAGE_SEMANTIC_ID (WON, LOSE, etc)
        - DATE_CREATE, CLOSEDATE
        """
        self.df = df_deals.copy()
        self._standardize()
    
    def _standardize(self):
        """Стандартизация данных"""
        self.df["OPPORTUNITY"] = pd.to_numeric(self.df["OPPORTUNITY"], errors="coerce").fillna(0)
        for col in ["DATE_CREATE", "DATE_MODIFY", "CLOSEDATE"]:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
        self.df["is_won"] = self.df["STAGE_SEMANTIC_ID"] == "WON"
        self.df["is_lost"] = self.df["STAGE_SEMANTIC_ID"] == "LOSE"
    
    # ==================== КРИТИЧЕСКИЕ ВЫВОДЫ ====================
    
    def main_problem_assessment(self):
        """
        Главная проблема из документа:
        "Управленческий кризис, замаскированный ростом объёмов"
        """
        yearly_data = {}
        
        for year in sorted(self.df["DATE_CREATE"].dt.year.unique()):
            year_df = self.df[self.df["DATE_CREATE"].dt.year == year]
            total = len(year_df)
            won = len(year_df[year_df["is_won"]])
            conv = (won / total * 100) if total > 0 else 0
            revenue = year_df[year_df["is_won"]]["OPPORTUNITY"].sum()
            
            yearly_data[year] = {
                "deals": total,
                "won": won,
                "conversion": conv,
                "revenue": revenue,
                "avg_check": year_df["OPPORTUNITY"].mean()
            }
        
        # Анализ падения
        assessment = {
            "yearly": yearly_data,
            "problem": "Проверьте падение конверсии год к году",
            "critical": False
        }
        
        # Проверка на критичность
        years = sorted(yearly_data.keys())
        if len(years) >= 2:
            prev_year = yearly_data[years[-2]]["conversion"]
            curr_year = yearly_data[years[-1]]["conversion"]
            fall_pct = ((curr_year - prev_year) / prev_year * 100) if prev_year > 0 else 0
            
            assessment["fall_pct"] = fall_pct
            assessment["critical"] = fall_pct < -15  # 15%+ падение — критично
            assessment["problem"] = f"Падение конверсии на {abs(fall_pct):.1f}%" if fall_pct < 0 else f"Рост конверсии на {fall_pct:.1f}%"
        
        return assessment
    
    # ==================== АНАЛИЗ ТРЁХ ПРОБЛЕМ ====================
    
    def problem_1_management_crisis(self, crisis_manager_name=None):
        """
        Проблема 1: Управленческий кризис (новый руководитель)
        Из документа: "Юрий Буханов — новый КД+РОП"
        """
        if not crisis_manager_name:
            return {"status": "Требуется указать имя менеджера для анализа"}
        
        mgr_df = self.df[self.df.get("MANAGER_NAME", "") == crisis_manager_name]
        
        if len(mgr_df) == 0:
            return {"status": f"Менеджер '{crisis_manager_name}' не найден"}
        
        total = len(mgr_df)
        won = len(mgr_df[mgr_df["is_won"]])
        conversion = (won / total * 100) if total > 0 else 0
        business_trips = 0  # Из документа: 9 поездок
        business_trip_cost = 0  # Из документа: 172K
        
        return {
            "manager": crisis_manager_name,
            "total_deals": total,
            "won_deals": won,
            "conversion": conversion,
            "status": "🔴 КРИЗИС" if conversion == 0 else "🟠 КРИТИЧНО",
            "business_trips": business_trips,
            "business_trip_cost": business_trip_cost,
            "roi": 0 if business_trip_cost == 0 else (0 / business_trip_cost * 100),
            "impact_on_team": "Требуется дополнительный анализ"
        }
    
    def problem_2_employee_crisis(self, crisis_employee_name=None):
        """
        Проблема 2: Кризис сотрудника (как Артем Елкин)
        Из документа: "3 месяца подряд 0%"
        """
        if not crisis_employee_name:
            return {"status": "Требуется указать имя сотрудника"}
        
        emp_df = self.df[self.df.get("MANAGER_NAME", "") == crisis_employee_name]
        
        if len(emp_df) == 0:
            return {"status": f"Сотрудник '{crisis_employee_name}' не найден"}
        
        # Анализ по месяцам
        monthly_conv = {}
        emp_df["year_month"] = emp_df["DATE_CREATE"].dt.to_period("M")
        
        zero_months = 0
        for month in sorted(emp_df["year_month"].unique()):
            month_df = emp_df[emp_df["year_month"] == month]
            won = len(month_df[month_df["is_won"]])
            total = len(month_df)
            conv = (won / total * 100) if total > 0 else 0
            monthly_conv[str(month)] = conv
            
            if conv == 0:
                zero_months += 1
        
        total_deals = len(emp_df)
        won_deals = len(emp_df[emp_df["is_won"]])
        overall_conv = (won_deals / total_deals * 100) if total_deals > 0 else 0
        
        return {
            "employee": crisis_employee_name,
            "total_deals": total_deals,
            "won_deals": won_deals,
            "overall_conversion": overall_conv,
            "monthly_conversion": monthly_conv,
            "zero_months_count": zero_months,
            "status": "🔴 КРИТИЧЕСКИЙ" if zero_months >= 3 else "🟠 ВНИМАНИЕ",
            "potential_loss": total_deals * 50000 if zero_months >= 3 else 0  # Примерная оценка
        }
    
    def problem_3_system_degradation(self):
        """
        Проблема 3: Системное падение качества
        Из документа: 2023: 7.28% → 2024: 4.79% → 2025: 3.53%
        """
        yearly_data = {}
        
        for year in sorted(self.df["DATE_CREATE"].dt.year.unique()):
            year_df = self.df[self.df["DATE_CREATE"].dt.year == year]
            total = len(year_df)
            won = len(year_df[year_df["is_won"]])
            conv = (won / total * 100) if total > 0 else 0
            
            yearly_data[year] = {
                "conversion": conv,
                "deals": total,
                "won": won
            }
        
        # Анализ падения
        years = sorted(yearly_data.keys())
        total_fall = 0
        if len(years) >= 2:
            total_fall = ((yearly_data[years[-1]]["conversion"] - yearly_data[years[0]]["conversion"]) / yearly_data[years[0]]["conversion"] * 100) if yearly_data[years[0]]["conversion"] > 0 else 0
        
        return {
            "yearly_conversion": yearly_data,
            "total_fall_pct": total_fall,
            "status": "🔴 КРИТИЧЕСКАЯ" if total_fall < -30 else "🟠 СЕРЬЁЗНАЯ",
            "interpretation": "Проблема не в менеджерах, а в системе управления и качестве лидов"
        }
    
    # ==================== ТРИ УСПЕХА ====================
    
    def success_1_best_manager(self):
        """
        Успех 1: Лучший менеджер (как Павел Казанцев)
        Из документа: 8.65% конверсия, 56% от всех успешных сделок
        """
        manager_stats = {}
        
        for mgr in self.df.get("MANAGER_NAME", self.df["ASSIGNED_BY_ID"]).unique():
            mgr_df = self.df[self.df.get("MANAGER_NAME", self.df["ASSIGNED_BY_ID"]) == mgr]
            total = len(mgr_df)
            won = len(mgr_df[mgr_df["is_won"]])
            conv = (won / total * 100) if total > 0 else 0
            
            manager_stats[str(mgr)] = {
                "conversion": conv,
                "won": won,
                "total": total
            }
        
        # Лучший менеджер
        best_mgr = max(manager_stats.items(), key=lambda x: x[1]["conversion"])
        
        return {
            "best_manager": best_mgr[0],
            "conversion": best_mgr[1]["conversion"],
            "won_deals": best_mgr[1]["won"],
            "total_deals": best_mgr[1]["total"],
            "status": "🟢 ЗВЕЗДА КОМПАНИИ",
            "potential": "При возврате к 15% конверсии выручка может вырасти на 88М"
        }
    
    def success_2_growing_manager(self):
        """
        Успех 2: Растущий менеджер (как Любовь Соловьева)
        Из документа: рост 1.5% → 6.25% (+319%)
        """
        # Анализ растущих менеджеров
        monthly_mgr_conv = {}
        
        self.df["year_month"] = self.df["DATE_CREATE"].dt.to_period("M")
        
        for mgr in self.df.get("MANAGER_NAME", self.df["ASSIGNED_BY_ID"]).unique():
            mgr_df = self.df[self.df.get("MANAGER_NAME", self.df["ASSIGNED_BY_ID"]) == mgr]
            
            months_data = {}
            for month in sorted(mgr_df["year_month"].unique()):
                month_df = mgr_df[mgr_df["year_month"] == month]
                won = len(month_df[month_df["is_won"]])
                total = len(month_df)
                conv = (won / total * 100) if total > 0 else 0
                months_data[str(month)] = conv
            
            if len(months_data) >= 2:
                first_conv = list(months_data.values())[0]
                last_conv = list(months_data.values())[-1]
                growth = ((last_conv - first_conv) / first_conv * 100) if first_conv > 0 else 0
                
                if growth > 100:  # 100%+ рост
                    monthly_mgr_conv[str(mgr)] = {
                        "growth_pct": growth,
                        "first_conv": first_conv,
                        "last_conv": last_conv,
                        "potential": last_conv * 5  # Потенциал переквалификации
                    }
        
        if monthly_mgr_conv:
            best_growing = max(monthly_mgr_conv.items(), key=lambda x: x[1]["growth_pct"])
            return {
                "manager": best_growing[0],
                "growth_pct": best_growing[1]["growth_pct"],
                "from_conversion": best_growing[1]["first_conv"],
                "to_conversion": best_growing[1]["last_conv"],
                "potential_revenue": f"+30М при переквалификации на средних клиентов",
                "status": "🟢 ВЫСОКИЙ ПОТЕНЦИАЛ"
            }
        else:
            return {"status": "Нет данных о растущих менеджерах"}
    
    def success_3_business_trips_roi(self, trips_cost=160000, trips_revenue=38900000):
        """
        Успех 3: ROI командировок
        Из документа: 160K затрат → 38.9М выручки = 24,277% ROI
        """
        roi = (trips_revenue / trips_cost * 100) if trips_cost > 0 else 0
        roi_per_ruble = trips_revenue / trips_cost if trips_cost > 0 else 0
        
        return {
            "cost": trips_cost,
            "revenue": trips_revenue,
            "roi": roi,
            "roi_per_ruble": roi_per_ruble,
            "status": "🟢 СУПЕР-ДОХОДНО",
            "interpretation": f"1 рубль командировки → {roi_per_ruble:.0f} рублей выручки"
        }
    
    # ==================== ФИНАНСОВЫЕ СЦЕНАРИИ ====================
    
    def financial_scenarios(self):
        """
        Финансовые сценарии из документа
        Текущее: 3.53%, Норма: 5%, 2023 уровень: 7.28%
        """
        total_deals = len(self.df)
        current_conv = (len(self.df[self.df["is_won"]]) / total_deals * 100) if total_deals > 0 else 0
        current_revenue = self.df[self.df["is_won"]]["OPPORTUNITY"].sum()
        avg_opportunity = self.df["OPPORTUNITY"].mean()
        
        scenarios = {
            "current": {
                "conversion": current_conv,
                "deals": total_deals,
                "revenue": current_revenue,
                "scenario": "Текущее состояние"
            },
            "norm": {
                "conversion": 5.0,
                "deals": total_deals,
                "revenue": (total_deals * 5 / 100) * avg_opportunity,
                "scenario": "Норма (5%)",
                "potential_add": f"+73М/год"
            },
            "2023_level": {
                "conversion": 7.28,
                "deals": total_deals,
                "revenue": (total_deals * 7.28 / 100) * avg_opportunity,
                "scenario": "2023 уровень (7.28%)",
                "potential_add": f"+111М/год"
            }
        }
        
        return scenarios
    
    # ==================== ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ ====================
    
    def quick_wins_potential(self):
        """
        Низко висящие плоды (Quick Wins) из документа
        """
        wins = {
            "requalification": {
                "action": "Переквалификация растущего менеджера",
                "potential": "+30М",
                "priority": 1
            },
            "best_leads": {
                "action": "Лучшие лиды для лучшего менеджера",
                "potential": "+40М",
                "priority": 2
            },
            "lead_matching": {
                "action": "Правильный матчинг лидов по менеджерам",
                "potential": "+80М",
                "priority": 3
            },
            "specialization": {
                "action": "Специализация техдира",
                "potential": "+20М",
                "priority": 4
            }
        }
        
        total_potential = 30 + 40 + 80 + 20  # 170М
        
        return {
            "wins": wins,
            "total_potential": f"+{total_potential}М",
            "impact": "Практически удвоение выручки без новых лидов"
        }


# ====================================
# ИНТЕГРАЦИЯ В STREAMLIT
# ====================================

def render_critical_analysis(df_deals):
    """
    Функция для отображения критического анализа в Streamlit
    """
    import streamlit as st
    
    analytics = DocumentAnalytics(df_deals)
    
    st.header("🚨 Критический анализ")
    
    # Главная проблема
    main = analytics.main_problem_assessment()
    st.subheader("Главная проблема")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Статус", "🔴 КРИТИЧЕСКАЯ" if main["critical"] else "🟠 ВНИМАНИЕ")
    with col2:
        st.metric("Падение конверсии", f"{main.get('fall_pct', 0):.1f}%", main["problem"])
    
    # Три проблемы
    st.subheader("Три критические проблемы")
    tab1, tab2, tab3 = st.tabs(["Управленческий кризис", "Кризис сотрудника", "Системное падение"])
    
    with tab1:
        st.info("Указать имя руководителя для анализа")
        manager_name = st.text_input("Имя руководителя", "")
        if manager_name:
            problem1 = analytics.problem_1_management_crisis(manager_name)
            st.json(problem1)
    
    with tab2:
        st.info("Указать имя сотрудника для анализа")
        emp_name = st.text_input("Имя сотрудника", "")
        if emp_name:
            problem2 = analytics.problem_2_employee_crisis(emp_name)
            st.json(problem2)
    
    with tab3:
        problem3 = analytics.problem_3_system_degradation()
        st.json(problem3)
    
    # Три успеха
    st.subheader("✅ Три главных успеха")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        success1 = analytics.success_1_best_manager()
        st.metric("Лучший менеджер", success1["best_manager"], f"{success1['conversion']:.2f}%")
    
    with col2:
        success2 = analytics.success_2_growing_manager()
        if "manager" in success2:
            st.metric("Растущий менеджер", success2["manager"], f"+{success2['growth_pct']:.0f}%")
    
    with col3:
        success3 = analytics.success_3_business_trips_roi()
        st.metric("ROI командировок", f"{success3['roi']:.0f}%", f"{success3['roi_per_ruble']:.0f}:1")
    
    # Финансовые сценарии
    st.subheader("💰 Финансовые сценарии")
    scenarios = analytics.financial_scenarios()
    for key, scenario in scenarios.items():
        if key != "current":
            st.success(f"{scenario['scenario']}: +{scenario['revenue']/1e6:.0f}М ({scenario['potential_add']})")
    
    # Quick wins
    st.subheader("⚡ Низко висящие плоды")
    wins = analytics.quick_wins_potential()
    st.success(f"Общий потенциал: {wins['total_potential']}")
    for action, data in wins['wins'].items():
        st.info(f"{data['priority']}. {data['action']} — {data['potential']}")


if __name__ == "__main__":
    print("✅ Модуль аналитики из документа готов к использованию")
