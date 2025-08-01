#!/usr/bin/env python3
"""
Скрипт для проверки статуса алертов в Grafana
"""

import requests
import json
from datetime import datetime

# Настройки подключения к Grafana
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

def check_grafana_alerts():
    """Проверяет статус алертов в Grafana"""
    
    print("🔍 Проверка алертов в Grafana...")
    print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Проверяем доступность Grafana
    try:
        health_response = requests.get(f"{GRAFANA_URL}/api/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Grafana доступен")
        else:
            print("❌ Grafana недоступен")
            return
    except Exception as e:
        print(f"❌ Ошибка подключения к Grafana: {e}")
        return
    
    # Получаем информацию об алертах
    try:
        # API для получения статуса алертов
        alerts_response = requests.get(
            f"{GRAFANA_URL}/api/alertmanager/grafana/api/v2/alerts",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if alerts_response.status_code == 200:
            alerts = alerts_response.json()
            print(f"📊 Найдено алертов: {len(alerts)}")
            
            if alerts:
                for alert in alerts:
                    status = alert.get('status', {}).get('state', 'unknown')
                    name = alert.get('labels', {}).get('alertname', 'unnamed')
                    severity = alert.get('labels', {}).get('severity', 'unknown')
                    
                    status_icon = "🚨" if status == "firing" else "✅" if status == "resolved" else "⏳"
                    severity_icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
                    
                    print(f"{status_icon} {severity_icon} {name}: {status}")
            else:
                print("ℹ️  Активных алертов не найдено")
        else:
            print(f"❌ Ошибка получения алертов: {alerts_response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при получении алертов: {e}")
    
    # Проверяем правила алертов
    try:
        rules_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if rules_response.status_code == 200:
            rules = rules_response.json()
            print(f"\n📋 Правила алертов загружены: {len(rules) if rules else 0}")
            
            if rules:
                for namespace, groups in rules.items():
                    print(f"📁 Namespace: {namespace}")
                    for group in groups:
                        group_name = group.get('name', 'unnamed')
                        rules_count = len(group.get('rules', []))
                        print(f"  📂 Group: {group_name} ({rules_count} правил)")
                        
                        for rule in group.get('rules', []):
                            rule_name = rule.get('alert', 'unnamed')
                            print(f"    📌 {rule_name}")
        else:
            print(f"❌ Ошибка получения правил: {rules_response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при получении правил: {e}")

if __name__ == "__main__":
    check_grafana_alerts()
