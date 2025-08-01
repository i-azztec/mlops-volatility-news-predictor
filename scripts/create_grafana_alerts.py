#!/usr/bin/env python3
"""
Скрипт для создания алертов в Grafana через API
"""

import requests
import json
from datetime import datetime

# Настройки подключения к Grafana
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

def create_alert_rules():
    """Создает правила алертов через Grafana API"""
    
    print("🚨 Создание алертов в Grafana...")
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Создаем папку для алертов
    folder_data = {
        "title": "Model Monitoring",
        "type": "dash-folder"
    }
    
    try:
        folder_response = requests.post(
            f"{GRAFANA_URL}/api/folders",
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"},
            json=folder_data,
            timeout=10
        )
        
        if folder_response.status_code in [200, 409]:  # 409 if folder exists
            print("✅ Папка 'Model Monitoring' создана/существует")
            if folder_response.status_code == 200:
                folder_uid = folder_response.json()["uid"]
            else:
                # Если папка существует, получаем её UID
                folders_response = requests.get(f"{GRAFANA_URL}/api/folders", auth=(USERNAME, PASSWORD))
                folders = folders_response.json()
                folder_uid = next((f["uid"] for f in folders if f["title"] == "Model Monitoring"), "general")
        else:
            print(f"❌ Ошибка создания папки: {folder_response.status_code}")
            folder_uid = "general"
            
    except Exception as e:
        print(f"❌ Ошибка при создании папки: {e}")
        folder_uid = "general"
    
    # Определяем правила алертов
    alert_rules = [
        {
            "uid": "model_auc_alert",
            "title": "Model AUC Drop Alert", 
            "condition": "C",
            "data": [
                {
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {"from": 300, "to": 0},
                    "datasource": {"type": "postgres", "uid": "postgres_datasource"},
                    "model": {
                        "format": "time_series",
                        "rawSql": "SELECT EXTRACT(EPOCH FROM timestamp) * 1000 as time, metric_value as value FROM volatility_metrics WHERE metric_name = 'auc' ORDER BY timestamp DESC LIMIT 1"
                    }
                },
                {
                    "refId": "B", 
                    "queryType": "",
                    "relativeTimeRange": {"from": 0, "to": 0},
                    "datasource": {"type": "__expr__", "uid": "__expr__"},
                    "model": {
                        "expression": "A",
                        "reducer": "last",
                        "type": "reduce"
                    }
                },
                {
                    "refId": "C",
                    "queryType": "",
                    "relativeTimeRange": {"from": 0, "to": 0}, 
                    "datasource": {"type": "__expr__", "uid": "__expr__"},
                    "model": {
                        "expression": "B < 0.52",
                        "type": "math"
                    }
                }
            ],
            "noDataState": "NoData",
            "execErrState": "Alerting", 
            "for": "2m",
            "annotations": {
                "description": "Model AUC has dropped below 0.52. Critical performance degradation detected.",
                "summary": "Critical: Model AUC Alert"
            },
            "labels": {
                "severity": "critical",
                "team": "ml-ops"
            },
            "folderUID": folder_uid
        }
    ]
    
    # Создаем каждое правило алерта
    for rule in alert_rules:
        try:
            # Формируем данные для создания правила
            rule_data = {
                "rules": [rule]
            }
            
            response = requests.post(
                f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/{folder_uid}",
                auth=(USERNAME, PASSWORD),
                headers={"Content-Type": "application/json"},
                json=rule_data,
                timeout=10
            )
            
            if response.status_code in [202, 200]:
                print(f"✅ Алерт '{rule['title']}' создан успешно")
            else:
                print(f"❌ Ошибка создания алерта '{rule['title']}': {response.status_code}")
                print(f"   Ответ: {response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка при создании алерта '{rule['title']}': {e}")
    
    print("\n🔍 Проверяем созданные алерты...")
    
    # Проверяем созданные алерты
    try:
        rules_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if rules_response.status_code == 200:
            rules = rules_response.json()
            print(f"📋 Общее количество правил: {len(rules)}")
            
            for namespace, groups in rules.items():
                print(f"📁 Namespace: {namespace}")
                for group in groups:
                    group_name = group.get("name", "unnamed")
                    rules_count = len(group.get("rules", []))
                    print(f"  📂 Group: {group_name} ({rules_count} правил)")
        else:
            print(f"❌ Ошибка получения правил: {rules_response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке правил: {e}")

if __name__ == "__main__":
    create_alert_rules()
