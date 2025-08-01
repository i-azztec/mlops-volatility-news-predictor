#!/usr/bin/env python3
"""
Script for adding alerts according to specification via Grafana API
Adds new alerts to existing ones without touching alert1
"""

import requests
import json
from datetime import datetime

# Grafana connection settings
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

def add_model_monitoring_alerts():
    """Adds model monitoring alerts according to specification"""
    
    print("🚨 Adding model monitoring alerts...")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # First get existing rules
    try:
        existing_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/Model%20Monitoring",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if existing_response.status_code == 200:
            existing_rules = existing_response.json()
            print(f"✅ Found existing rules: {len(existing_rules)}")
            
            # Get existing group
            if existing_rules:
                existing_group = existing_rules[0]  # Take first group
                existing_rules_list = existing_group.get("rules", [])
                print(f"📋 Existing alerts: {len(existing_rules_list)}")
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
            print("ℹ️ No existing rules found, creating new group")
            existing_rules_list = []
            existing_group = {
                "name": "evalutation_group1",
                "orgId": 1,
                "folder": "Model Monitoring",
                "interval": "1m", 
                "rules": []
            }
            
    except Exception as e:
        print(f"❌ Error getting existing rules: {e}")
        return
    
    # Define new alerts according to specification (using structure from your example)
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
                "description": "🚨 Model AUC has dropped below 0.52 (critical threshold from specification). Immediate attention required for model retraining.",
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
    
    # Combine existing and new alerts
    all_rules = existing_rules_list + new_alerts
    
    # Update group with new alerts
    updated_group = {
        "name": existing_group["name"],
        "orgId": existing_group["orgId"],
        "folder": existing_group["folder"],
        "interval": existing_group["interval"],
        "rules": all_rules
    }
    
    # Send updated group
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/Model%20Monitoring",
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"},
            json=[updated_group],
            timeout=10
        )
        
        if response.status_code in [202, 200]:
            print(f"✅ Successfully added {len(new_alerts)} new alerts to existing ones!")
            print(f"📊 Total alerts in group: {len(all_rules)}")
            
            for alert in new_alerts:
                print(f"  🚨 {alert['title']}")
        else:
            print(f"❌ Error adding alerts: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error adding alerts: {e}")
    
    print("\n🔍 Checking updated alerts...")
    
    # Check result
    try:
        check_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if check_response.status_code == 200:
            rules = check_response.json()
            print(f"📋 Total rule groups: {len(rules)}")
            
            for namespace, groups in rules.items():
                print(f"📁 Namespace: {namespace}")
                for group in groups:
                    group_name = group.get("name", "unnamed")
                    rules_count = len(group.get("rules", []))
                    print(f"  📂 Group: {group_name} ({rules_count} alerts)")
                    
                    for rule in group.get("rules", []):
                        rule_title = rule.get("title", "unnamed")
                        is_paused = rule.get("isPaused", False)
                        status = "⏸️ PAUSED" if is_paused else "▶️ ACTIVE"
                        print(f"    🚨 {rule_title} - {status}")
        else:
            print(f"❌ Error checking rules: {check_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking rules: {e}")

if __name__ == "__main__":
    add_model_monitoring_alerts()
