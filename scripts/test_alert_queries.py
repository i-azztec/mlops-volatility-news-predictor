#!/usr/bin/env python3
"""
Тестирование SQL запросов для алертов
"""

import psycopg2
from datetime import datetime

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monitoring',
    'user': 'user',
    'password': 'password'
}

def test_alert_queries():
    """Тестирует SQL запросы, используемые в алертах"""
    
    print("🔍 Тестирование SQL запросов для алертов...")
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Тесты для каждого типа алерта
        alert_queries = [
            {
                "name": "🚨 AUC Critical Alert (< 0.52)",
                "query": "SELECT EXTRACT(EPOCH FROM timestamp) * 1000 as time, metric_value as value FROM volatility_metrics WHERE metric_name = 'auc' ORDER BY timestamp DESC LIMIT 1",
                "threshold": 0.52,
                "operator": "<"
            },
            {
                "name": "⚠️ F1-Score Warning Alert (< 0.65)",
                "query": "SELECT EXTRACT(EPOCH FROM timestamp) * 1000 as time, metric_value as value FROM volatility_metrics WHERE metric_name = 'f1' ORDER BY timestamp DESC LIMIT 1",
                "threshold": 0.65,
                "operator": "<"
            },
            {
                "name": "⚠️ Accuracy Warning Alert (< 0.65)",
                "query": "SELECT EXTRACT(EPOCH FROM timestamp) * 1000 as time, metric_value as value FROM volatility_metrics WHERE metric_name = 'accuracy' ORDER BY timestamp DESC LIMIT 1",
                "threshold": 0.65,
                "operator": "<"
            },
            {
                "name": "⚠️ Data Drift Warning Alert (> 0.3)",
                "query": "SELECT EXTRACT(EPOCH FROM timestamp) * 1000 as time, metric_value as value FROM volatility_metrics WHERE metric_name = 'drift_share' ORDER BY timestamp DESC LIMIT 1",
                "threshold": 0.3,
                "operator": ">"
            }
        ]
        
        for alert in alert_queries:
            print(f"\n{alert['name']}")
            print("-" * 50)
            
            cursor.execute(alert['query'])
            result = cursor.fetchone()
            
            if result:
                timestamp, value = result
                timestamp_readable = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                # Проверяем условие алерта
                if alert['operator'] == "<":
                    should_alert = value < alert['threshold']
                else:  # operator == ">"
                    should_alert = value > alert['threshold']
                
                status_icon = "🚨 ALERT!" if should_alert else "✅ OK"
                
                print(f"📊 Значение: {value:.3f}")
                print(f"🎯 Порог: {alert['operator']} {alert['threshold']}")
                print(f"📅 Время: {timestamp_readable}")
                print(f"🔔 Статус: {status_icon}")
                
                if should_alert:
                    print(f"💥 АЛЕРТ ДОЛЖЕН СРАБОТАТЬ!")
            else:
                print("❌ Нет данных")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")

if __name__ == "__main__":
    test_alert_queries()
