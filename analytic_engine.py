# -*- coding: utf-8 -*-
"""
БУРМАШ · Расширенная аналитика (v7.1)
Модуль для расчёта специальных метрик из документа "Аналитика ОП 2023-2025"
- Конверсия по периодам (год/квартал/месяц)
- Анализ падения/роста конверсии
- ROI командировок
- Анализ менеджеров (лучший, худший, кризисные)
- Динамика изменения средних чеков
- Фотокасса корреляций
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np


class AnalyticEngine:
    """Основной модуль расширенной аналитики"""
    
    def __init__(self, df_deals, users_map=None):
        """
        df_deals: DataFrame с сделками от Bitrix24
        users_map: dict {user_id: user_name}
        """
        self.df = df_deals.copy()
        self.users_map = users_map or {}
        self._prepare_data()
    
    def _prepare_data(self):
        """Подготовка данных для анализа"""
        # Преобразование дат
        for col in ["DATE_CREATE", "DATE_MODIFY", "CLOSEDATE"]:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
        
        # Стандартизация OPPORTUNITY
        self.df["OPPORTUNITY"] = pd.to_numeric(self.df["OPPORTUNITY"], errors="coerce").fillna(0)
        
        # Статусы
        self.df["is_won"] = self.df["STAGE_SEMANTIC_ID"] == "WON"
        self.df["is_lost"] = self.df["STAGE_SEMANTIC_ID"] == "LOSE"
        
        # Менеджеры
        self.df["manager"] = self.df.get("ASSIGNED_BY_ID", "").astype(str)
        if self.users_map:
            self.df["manager_name"] = self.df["manager"].map(self.users_map).fillna("Неизвестно")
        else:
            self.df["manager_name"] = self.df["manager"]
    
    def conversion_by_year(self):
        """Конверсия по годам"""
        self.df["year"] = self.df["DATE_CREATE"].dt.year
        result = {}
        for year in sorted(self.df["year"].unique()):
            year_data = self.df[self.df["year"] == year]
            total = len(year_data)
            won = len(year_data[year_data["is_won"]])
            result[year] = {
                "total_deals": total,
                "won_deals": won,
                "conversion_pct": (won / total * 100) if total > 0 else 0,
                "revenue": year_data[year_data["is_won"]]["OPPORTUNITY"].sum(),
                "avg_check": year_data["OPPORTUNITY"].mean()
            }
        return result
    
    def conversion_by_quarter(self, year=None):
        """Конверсия по кварталам"""
        self.df["year"] = self.df["DATE_CREATE"].dt.year
        self.df["quarter"] = self.df["DATE_CREATE"].dt.quarter
        
        result = {}
        filter_year = year or self.df["year"].max()
        
        for q in range(1, 5):
            q_data = self.df[(self.df["year"] == filter_year) & (self.df["quarter"] == q)]
            if len(q_data) == 0:
                continue
            
            total = len(q_data)
            won = len(q_data[q_data["is_won"]])
            result[f"Q{q} {filter_year}"] = {
                "total_deals": total,
                "won_deals": won,
                "conversion_pct": (won / total * 100) if total > 0 else 0,
                "revenue": q_data[q_data["is_won"]]["OPPORTUNITY"].sum(),
                "avg_check": q_data["OPPORTUNITY"].mean()
            }
        return result
    
    def conversion_by_month(self, year=None, month=None):
        """Конверсия по месяцам"""
        self.df["year"] = self.df["DATE_CREATE"].dt.year
        self.df["month"] = self.df["DATE_CREATE"].dt.month
        self.df["month_name"] = self.df["DATE_CREATE"].dt.strftime("%B %Y")
        
        result = {}
        if year and month:
            # Один конкретный месяц
            m_data = self.df[(self.df["year"] == year) & (self.df["month"] == month)]
            if len(m_data) > 0:
                total = len(m_data)
                won = len(m_data[m_data["is_won"]])
                result[f"{month:02d}.{year}"] = {
                    "total_deals": total,
                    "won_deals": won,
                    "conversion_pct": (won / total * 100) if total > 0 else 0,
                    "revenue": m_data[m_data["is_won"]]["OPPORTUNITY"].sum(),
                    "avg_check": m_data["OPPORTUNITY"].mean()
                }
        else:
            # Все месяцы в датасете
            for month_name in sorted(self.df["month_name"].unique()):
                m_data = self.df[self.df["month_name"] == month_name]
                total = len(m_data)
                won = len(m_data[m_data["is_won"]])
                result[month_name] = {
                    "total_deals": total,
                    "won_deals": won,
                    "conversion_pct": (won / total * 100) if total > 0 else 0,
                    "revenue": m_data[m_data["is_won"]]["OPPORTUNITY"].sum(),
                    "avg_check": m_data["OPPORTUNITY"].mean()
                }
        return result
    
    def manager_metrics(self):
        """Метрики по менеджерам с анализом статуса"""
        result = {}
        
        for mgr in self.df["manager_name"].unique():
            if pd.isna(mgr) or mgr == "Неизвестно":
                continue
            
            mgr_data = self.df[self.df["manager_name"] == mgr]
            total = len(mgr_data)
            won = len(mgr_data[mgr_data["is_won"]])
            lost = len(mgr_data[mgr_data["is_lost"]])
            
            conversion = (won / total * 100) if total > 0 else 0
            avg_check = mgr_data["OPPORTUNITY"].mean()
            revenue = mgr_data[mgr_data["is_won"]]["OPPORTUNITY"].sum()
            cancel_rate = (lost / total * 100) if total > 0 else 0
            
            # Статус менеджера
            if conversion > 8:
                status = "🟢 Отличный"
            elif conversion > 5:
                status = "🟢 Хороший"
            elif conversion > 3:
                status = "🟡 Нормальный"
            elif conversion > 1:
                status = "🟠 Критический"
            else:
                status = "🔴 Кризис"
            
            result[mgr] = {
                "deals_count": total,
                "won_count": won,
                "lost_count": lost,
                "conversion_pct": conversion,
                "avg_check": avg_check,
                "revenue": revenue,
                "cancel_rate": cancel_rate,
                "status": status
            }
        
        return result
    
    def conversion_trend_analysis(self):
        """Анализ тренда конверсии (растёт/падает)"""
        monthly_conv = self.conversion_by_month()
        
        if len(monthly_conv) < 2:
            return {"trend": "Недостаточно данных", "change_pct": 0}
        
        sorted_months = sorted(monthly_conv.keys())
        first_conv = monthly_conv[sorted_months[0]]["conversion_pct"]
        last_conv = monthly_conv[sorted_months[-1]]["conversion_pct"]
        
        change = last_conv - first_conv
        change_pct = (change / first_conv * 100) if first_conv > 0 else 0
        
        if change_pct > 10:
            trend = "📈 Резкий рост"
        elif change_pct > 0:
            trend = "📊 Слабый рост"
        elif change_pct > -10:
            trend = "📉 Слабое падение"
        else:
            trend = "📉 Резкое падение"
        
        return {
            "trend": trend,
            "change_pct": change_pct,
            "first_month_conv": first_conv,
            "last_month_conv": last_conv,
            "absolute_change": change
        }
    
    def manager_ranking(self):
        """Ранжирование менеджеров по конверсии"""
        metrics = self.manager_metrics()
        
        # Сортировка по конверсии (descending)
        ranking = sorted(metrics.items(), key=lambda x: x[1]["conversion_pct"], reverse=True)
        
        result = []
        for rank, (mgr, data) in enumerate(ranking, 1):
            result.append({
                "rank": rank,
                "manager": mgr,
                "conversion": data["conversion_pct"],
                "status": data["status"],
                "deals": data["deals_count"],
                "won": data["won_count"],
                "revenue": data["revenue"]
            })
        
        return result
    
    def crisis_detection(self):
        """Обнаружение кризисных ситуаций"""
        alerts = []
        
        # Общая конверсия
        total_conv = (len(self.df[self.df["is_won"]]) / len(self.df) * 100) if len(self.df) > 0 else 0
        if total_conv < 3:
            alerts.append({
                "level": "🔴 КРИТИЧЕСКАЯ",
                "issue": "Конверсия компании < 3%",
                "conversion": total_conv
            })
        
        # По менеджерам
        metrics = self.manager_metrics()
        for mgr, data in metrics.items():
            if data["conversion_pct"] == 0 and data["deals_count"] > 5:
                alerts.append({
                    "level": "🔴 КРИЗИС",
                    "issue": f"{mgr}: {data['deals_count']} сделок, 0% конверсия",
                    "manager": mgr
                })
            elif data["cancel_rate"] > 60:
                alerts.append({
                    "level": "🟠 ВНИМАНИЕ",
                    "issue": f"{mgr}: высокая отмена {data['cancel_rate']:.0f}%",
                    "manager": mgr
                })
        
        # Тренд падения
        trend = self.conversion_trend_analysis()
        if trend["change_pct"] < -30:
            alerts.append({
                "level": "🟠 ТРЕВОГА",
                "issue": f"Конверсия упала на {abs(trend['change_pct']):.1f}% за период",
                "change": trend["change_pct"]
            })
        
        return alerts
    
    def roi_calculation(self, business_trips_cost, business_trips_revenue):
        """ROI командировок"""
        if business_trips_cost == 0:
            return 0
        return (business_trips_revenue / business_trips_cost) * 100
    
    def segment_analysis(self, segment_field="CATEGORY_ID"):
        """Анализ по сегментам (категориям, воронкам)"""
        if segment_field not in self.df.columns:
            return {}
        
        result = {}
        for segment in self.df[segment_field].unique():
            if pd.isna(segment):
                continue
            
            seg_data = self.df[self.df[segment_field] == segment]
            total = len(seg_data)
            won = len(seg_data[seg_data["is_won"]])
            
            result[f"Segment_{segment}"] = {
                "total_deals": total,
                "won_deals": won,
                "conversion_pct": (won / total * 100) if total > 0 else 0,
                "revenue": seg_data[seg_data["is_won"]]["OPPORTUNITY"].sum(),
                "avg_check": seg_data["OPPORTUNITY"].mean()
            }
        
        return result
    
    def opportunity_distribution(self):
        """Распределение сделок по размеру чека"""
        # Квартили
        q1 = self.df["OPPORTUNITY"].quantile(0.25)
        q2 = self.df["OPPORTUNITY"].quantile(0.50)
        q3 = self.df["OPPORTUNITY"].quantile(0.75)
        
        micro = self.df[self.df["OPPORTUNITY"] <= q1]
        small = self.df[(self.df["OPPORTUNITY"] > q1) & (self.df["OPPORTUNITY"] <= q2)]
        medium = self.df[(self.df["OPPORTUNITY"] > q2) & (self.df["OPPORTUNITY"] <= q3)]
        large = self.df[self.df["OPPORTUNITY"] > q3]
        
        segments = {
            "Микро": micro,
            "Малые": small,
            "Средние": medium,
            "Крупные": large
        }
        
        result = {}
        for seg_name, seg_data in segments.items():
            if len(seg_data) == 0:
                continue
            won = len(seg_data[seg_data["is_won"]])
            result[seg_name] = {
                "deals": len(seg_data),
                "won": won,
                "conversion": (won / len(seg_data) * 100) if len(seg_data) > 0 else 0,
                "avg_check": seg_data["OPPORTUNITY"].mean(),
                "revenue": seg_data[seg_data["is_won"]]["OPPORTUNITY"].sum()
            }
        
        return result
    
    def stalled_deals(self, stuck_days=7):
        """Зависшие сделки (без активности X дней)"""
        today = datetime.now()
        
        if "LAST_ACTIVITY_TIME" not in self.df.columns:
            return []
        
        self.df["last_activity"] = pd.to_datetime(
            self.df["LAST_ACTIVITY_TIME"], 
            errors="coerce"
        )
        self.df["days_stalled"] = (today - self.df["last_activity"]).dt.days
        
        stalled = self.df[
            (self.df["days_stalled"] >= stuck_days) & 
            (~self.df["is_won"]) & 
            (~self.df["is_lost"])
        ]
        
        return stalled[[
            "ID", "TITLE", "manager_name", "OPPORTUNITY", 
            "days_stalled", "DATE_CREATE"
        ]].to_dict("records")


# =====================
# Примеры использования в Streamlit
# =====================
def create_analytics_dashboard(df_deals, users_map):
    """Функция создания аналитической таблицы для Streamlit"""
    engine = AnalyticEngine(df_deals, users_map)
    
    analytics_data = {
        "conversion_by_year": engine.conversion_by_year(),
        "conversion_by_month": engine.conversion_by_month(),
        "manager_metrics": engine.manager_metrics(),
        "manager_ranking": engine.manager_ranking(),
        "trend_analysis": engine.conversion_trend_analysis(),
        "crisis_alerts": engine.crisis_detection(),
        "opportunity_dist": engine.opportunity_distribution(),
        "stalled_deals": engine.stalled_deals(stuck_days=7)
    }
    
    return analytics_data


if __name__ == "__main__":
    # Пример использования
    print("✅ Модуль аналитики готов к использованию")
