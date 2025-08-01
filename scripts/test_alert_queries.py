#!/usr/bin/env python3
"""
Testing SQL queries for alerts
"""

import psycopg2
from datetime import datetime

# PostgreSQL connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monitoring',
    'user': 'user',
    'password': 'password'
}

def test_alert_queries():
    """Tests SQL queries used in alerts"""
    
    print("🔍 Testing SQL queries for alerts...")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Tests for each alert type
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
                
                # Check alert condition
                if alert['operator'] == "<":
                    should_alert = value < alert['threshold']
                else:  # operator == ">"
                    should_alert = value > alert['threshold']
                
                status_icon = "🚨 ALERT!" if should_alert else "✅ OK"
                
                print(f"📊 Value: {value:.3f}")
                print(f"🎯 Threshold: {alert['operator']} {alert['threshold']}")
                print(f"📅 Time: {timestamp_readable}")
                print(f"🔔 Status: {status_icon}")
                
                if should_alert:
                    print(f"💥 ALERT SHOULD TRIGGER!")
            else:
                print("❌ No data")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    test_alert_queries()
