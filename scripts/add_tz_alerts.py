#!/usr/bin/env python3
"""
Скрипт для добавления алертов согласно ТЗ через Grafana API
Добавляет новые алерты к существующим, не трогая alert1
"""

import requests
import json
from datetime import datetime

# Настройки подключения к Grafana
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

def add_model_monitoring_alerts():
    """Добавляет алерты мониторинга модели согласно ТЗ"""
    
    print("🚨 Добавление алертов мониторинга модели...")
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Сначала получаем существующие правила
    try:
        existing_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/Model%20Monitoring",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if existing_response.status_code == 200:
            existing_rules = existing_response.json()
            print(f"✅ Найдены существующие правила: {len(existing_rules)}")
            
            # Получаем существующую группу
            if existing_rules:
                existing_group = existing_rules[0]  # Берем первую группу
                existing_rules_list = existing_group.get("rules", [])
                print(f"📋 Существующие алерты: {len(existing_rules_list)}")
            else:
                existing_rules_list = []
                existing_group = {
                    "name": "evalutation_group1",
                    "orgId": 1,
                    "folder": "Model Monitoring", 
                    "interval": "1m",
                    "rules": []
                }
        else:
            print("ℹ️ Существующих правил не найдено, создаем новую группу")
            existing_rules_list = []
            existing_group = {
                "name": "evalutation_group1",
                "orgId": 1,
                "folder": "Model Monitoring",
                "interval": "1m", 
                "rules": []
            }
            
    except Exception as e:
        print(f"❌ Ошибка получения существующих правил: {e}")
        return
    
    # Определяем новые алерты согласно ТЗ (используя структуру из вашего примера)
    new_alerts = [
        {
            "uid": "model-auc-drop-critical-tz",
            "title": "Model AUC Drop - Critical (ТЗ)",
            "condition": "C",
            "data": [
                {
                    "refId": "A",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "postgres_datasource",
                    "model": {
                        "editorMode": "code",
                        "format": "table",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "rawSql": "SELECT metric_value FROM volatility_metrics WHERE metric_name = 'auc' ORDER BY timestamp DESC LIMIT 1",
                        "refId": "A"
                    }
                },
                {
                    "refId": "B",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "conditions": [
                            {
                                "evaluator": {
                                    "params": [],
                                    "type": "gt"
                                },
                                "operator": {
                                    "type": "and"
                                },
                                "query": {
                                    "params": ["B"]
                                },
                                "reducer": {
                                    "params": [],
                                    "type": "last"
                                },
                                "type": "query"
                            }
                        ],
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "A",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "reducer": "last",
                        "refId": "B",
                        "type": "reduce"
                    }
                },
                {
                    "refId": "C",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "conditions": [
                            {
                                "evaluator": {
                                    "params": [0.52],
                                    "type": "lt"
                                },
                                "operator": {
                                    "type": "and"
                                },
                                "query": {
                                    "params": ["C"]
                                },
                                "reducer": {
                                    "params": [],
                                    "type": "last"
                                },
                                "type": "query"
                            }
                        ],
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "B",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "refId": "C",
                        "type": "threshold"
                    }
                }
            ],
            "noDataState": "NoData",
            "execErrState": "Alerting",
            "for": "2m",
            "annotations": {
                "description": "🚨 Model AUC has dropped below 0.52 (critical threshold from ТЗ). Immediate attention required for model retraining.",
                "summary": "Critical: Model AUC performance degradation detected"
            },
            "labels": {
                "severity": "critical",
                "team": "ml-ops"
            },
            "isPaused": False
        },
        {
            "uid": "model-f1-drop-warning-tz",
            "title": "Model F1-Score Drop - Warning (ТЗ)",
            "condition": "C",
            "data": [
                {
                    "refId": "A",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "postgres_datasource",
                    "model": {
                        "editorMode": "code",
                        "format": "table",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "rawSql": "SELECT metric_value FROM volatility_metrics WHERE metric_name = 'f1' ORDER BY timestamp DESC LIMIT 1",
                        "refId": "A"
                    }
                },
                {
                    "refId": "B",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "A",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "reducer": "last",
                        "refId": "B",
                        "type": "reduce"
                    }
                },
                {
                    "refId": "C",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "conditions": [
                            {
                                "evaluator": {
                                    "params": [0.65],
                                    "type": "lt"
                                },
                                "operator": {
                                    "type": "and"
                                },
                                "query": {
                                    "params": ["C"]
                                },
                                "reducer": {
                                    "params": [],
                                    "type": "last"
                                },
                                "type": "query"
                            }
                        ],
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "B",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "refId": "C",
                        "type": "threshold"
                    }
                }
            ],
            "noDataState": "NoData",
            "execErrState": "Alerting",
            "for": "5m",
            "annotations": {
                "description": "⚠️ Model F1-score has dropped below 0.65. Consider model retraining.",
                "summary": "Warning: Model F1-score degradation detected"
            },
            "labels": {
                "severity": "warning",
                "team": "ml-ops"
            },
            "isPaused": False
        },
        {
            "uid": "data-drift-warning-tz",
            "title": "Data Drift Detection - Warning (ТЗ)",
            "condition": "C",
            "data": [
                {
                    "refId": "A",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "datasourceUid": "postgres_datasource",
                    "model": {
                        "editorMode": "code",
                        "format": "table",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "rawSql": "SELECT metric_value FROM volatility_metrics WHERE metric_name = 'drift_share' ORDER BY timestamp DESC LIMIT 1",
                        "refId": "A"
                    }
                },
                {
                    "refId": "B",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "A",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "reducer": "last",
                        "refId": "B",
                        "type": "reduce"
                    }
                },
                {
                    "refId": "C",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": {
                        "conditions": [
                            {
                                "evaluator": {
                                    "params": [0.3],
                                    "type": "gt"
                                },
                                "operator": {
                                    "type": "and"
                                },
                                "query": {
                                    "params": ["C"]
                                },
                                "reducer": {
                                    "params": [],
                                    "type": "last"
                                },
                                "type": "query"
                            }
                        ],
                        "datasource": {
                            "type": "__expr__",
                            "uid": "__expr__"
                        },
                        "expression": "B",
                        "hide": False,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "refId": "C",
                        "type": "threshold"
                    }
                }
            ],
            "noDataState": "NoData",
            "execErrState": "Alerting",
            "for": "10m",
            "annotations": {
                "description": "⚠️ Data drift detected with high feature drift share exceeding threshold of 0.3. Feature distribution may have changed significantly.",
                "summary": "Warning: Significant data drift detected"
            },
            "labels": {
                "severity": "warning",
                "team": "ml-ops"
            },
            "isPaused": False
        }
    ]
    
    # Объединяем существующие и новые алерты
    all_rules = existing_rules_list + new_alerts
    
    # Обновляем группу с новыми алертами
    updated_group = {
        "name": existing_group["name"],
        "orgId": existing_group["orgId"],
        "folder": existing_group["folder"],
        "interval": existing_group["interval"],
        "rules": all_rules
    }
    
    # Отправляем обновленную группу
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/Model%20Monitoring",
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"},
            json=[updated_group],
            timeout=10
        )
        
        if response.status_code in [202, 200]:
            print(f"✅ Успешно добавлено {len(new_alerts)} новых алертов к существующим!")
            print(f"📊 Общее количество алертов в группе: {len(all_rules)}")
            
            for alert in new_alerts:
                print(f"  🚨 {alert['title']}")
        else:
            print(f"❌ Ошибка добавления алертов: {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при добавлении алертов: {e}")
    
    print("\n🔍 Проверяем обновленные алерты...")
    
    # Проверяем результат
    try:
        check_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if check_response.status_code == 200:
            rules = check_response.json()
            print(f"📋 Общее количество групп правил: {len(rules)}")
            
            for namespace, groups in rules.items():
                print(f"📁 Namespace: {namespace}")
                for group in groups:
                    group_name = group.get("name", "unnamed")
                    rules_count = len(group.get("rules", []))
                    print(f"  📂 Group: {group_name} ({rules_count} алертов)")
                    
                    for rule in group.get("rules", []):
                        rule_title = rule.get("title", "unnamed")
                        is_paused = rule.get("isPaused", False)
                        status = "⏸️ ПРИОСТАНОВЛЕН" if is_paused else "▶️ АКТИВЕН"
                        print(f"    🚨 {rule_title} - {status}")
        else:
            print(f"❌ Ошибка проверки правил: {check_response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке правил: {e}")

if __name__ == "__main__":
    add_model_monitoring_alerts()
