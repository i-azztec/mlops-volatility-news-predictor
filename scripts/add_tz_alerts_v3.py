# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# Grafana configuration
GRAFANA_URL = "http://localhost:3000"
GRAFANA_AUTH = ("admin", "admin")

def print_header():
    print("Adding TZ model monitoring alerts v3...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def create_alert_rule(alert_name, description, query, threshold, operator, severity):
    """Create alert rule using provisioning API"""
    
    # Using exact structure from working alert1
    alert_data = {
        "uid": "",
        "title": alert_name,
        "condition": "C",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {
                    "from": 600,
                    "to": 0
                },
                "datasourceUid": "postgres_datasource",
                "model": {
                    "editorMode": "builder",
                    "format": "table",
                    "hide": False,
                    "intervalMs": 1000,
                    "maxDataPoints": 43200,
                    "rawSql": query,
                    "refId": "A",
                    "sql": {
                        "columns": [
                            {
                                "name": "AVG",
                                "parameters": [
                                    {
                                        "name": "metric_value",
                                        "type": "functionParameter"
                                    }
                                ],
                                "type": "function"
                            }
                        ],
                        "groupBy": [
                            {
                                "property": {
                                    "type": "string"
                                },
                                "type": "groupBy"
                            }
                        ],
                        "limit": 50
                    },
                    "table": "volatility_metrics"
                }
            },
            {
                "refId": "B",
                "queryType": "",
                "relativeTimeRange": {
                    "from": 600,
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
                                "params": [
                                    "B"
                                ]
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
                "queryType": "",
                "relativeTimeRange": {
                    "from": 600,
                    "to": 0
                },
                "datasourceUid": "__expr__",
                "model": {
                    "conditions": [
                        {
                            "evaluator": {
                                "params": [threshold],
                                "type": operator
                            },
                            "operator": {
                                "type": "and"
                            },
                            "query": {
                                "params": [
                                    "C"
                                ]
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
        "execErrState": "Error",
        "for": "5m",
        "annotations": {
            "description": description,
            "summary": f"{alert_name} - {severity}"
        },
        "labels": {
            "severity": severity,
            "team": "ml-ops"
        },
        "folderUID": "a70b97f7-1ef7-4ba5-bfc3-ff73d43c640d",  # Same folder as alert1
        "ruleGroup": "tz_monitoring_group"
    }
    
    return alert_data

def create_tz_alerts():
    """Create TZ requirement alerts"""
    
    alerts_to_create = [
        {
            "alert_name": "Model AUC Drop Critical",
            "description": "Critical AUC model drop below 0.52",
            "query": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'auc' ORDER BY timestamp DESC LIMIT 10",
            "threshold": 0.52,
            "operator": "lt",
            "severity": "critical"
        },
        {
            "alert_name": "Model F1-Score Drop",
            "description": "F1-Score model drop below 0.65",
            "query": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'f1_score' ORDER BY timestamp DESC LIMIT 10",
            "threshold": 0.65,
            "operator": "lt", 
            "severity": "warning"
        },
        {
            "alert_name": "Data Drift Detection",
            "description": "Data drift detected above 0.3",
            "query": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'drift_share' ORDER BY timestamp DESC LIMIT 10",
            "threshold": 0.3,
            "operator": "gt",
            "severity": "warning"
        }
    ]
    
    created_count = 0
    
    for alert_config in alerts_to_create:
        try:
            alert_data = create_alert_rule(**alert_config)
            
            response = requests.post(
                f"{GRAFANA_URL}/api/v1/provisioning/alert-rules",
                auth=GRAFANA_AUTH,
                headers={"Content-Type": "application/json"},
                json=alert_data
            )
            
            if response.status_code == 201:
                print(f"SUCCESS: Created alert '{alert_config['alert_name']}'")
                created_count += 1
            else:
                print(f"ERROR creating '{alert_config['alert_name']}': {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"ERROR creating '{alert_config['alert_name']}': {e}")
    
    return created_count

def verify_alerts():
    """Verify all alerts"""
    print("\nVerifying all alerts...")
    
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/v1/provisioning/alert-rules",
            auth=GRAFANA_AUTH
        )
        response.raise_for_status()
        alerts = response.json()
        
        print(f"Total alerts: {len(alerts)}")
        
        for alert in alerts:
            title = alert.get("title", "unnamed")
            group = alert.get("ruleGroup", "unknown")
            is_paused = alert.get("isPaused", False)
            status = "PAUSED" if is_paused else "ACTIVE"
            print(f"  Alert: {title} (group: {group}) - {status}")
                        
    except Exception as e:
        print(f"ERROR verifying alerts: {e}")

def main():
    print_header()
    
    print("Creating TZ alerts using provisioning API...")
    
    created_count = create_tz_alerts()
    
    if created_count > 0:
        verify_alerts()
        print(f"\nSUCCESS: Created {created_count} TZ alerts!")
        print("Available in Grafana: http://localhost:3000/alerting/list")
    else:
        print("\nERROR: Failed to create any alerts.")

if __name__ == "__main__":
    main()
