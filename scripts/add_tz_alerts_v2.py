# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# Grafana configuration
GRAFANA_URL = "http://localhost:3000"
GRAFANA_AUTH = ("admin", "admin")

def print_header():
    print("Adding TZ model monitoring alerts...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def create_alert_rule_data(alert_name, description, query, threshold, operator, severity):
    """Create alert rule data structure based on working alert1 example"""
    
    # Base database query - simplified
    base_query_model = {
        "editorMode": "builder",
        "format": "table", 
        "hide": False,
        "intervalMs": 1000,
        "maxDataPoints": 43200,
        "rawSql": query,
        "refId": "A",
        "table": "volatility_metrics"
    }
    
    # Reduce operation model
    reduce_model = {
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
    
    # Threshold operation model
    threshold_model = {
        "datasource": {
            "type": "__expr__",
            "uid": "__expr__"
        },
        "expression": "B",
        "hide": False,
        "intervalMs": 1000,
        "maxDataPoints": 43200,
        "refId": "C",
        "type": "threshold",
        "conditions": [
            {
                "evaluator": {
                    "params": [threshold],
                    "type": operator
                },
                "operator": {
                    "type": "and"
                }
            }
        ]
    }
    
    return {
        "expr": "",
        "for": "5m",
        "annotations": {
            "description": description,
            "summary": f"{alert_name} - {severity}"
        },
        "grafana_alert": {
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
                    "model": base_query_model
                },
                {
                    "refId": "B", 
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": reduce_model
                },
                {
                    "refId": "C",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 600,
                        "to": 0
                    },
                    "datasourceUid": "__expr__",
                    "model": threshold_model
                }
            ],
            "intervalSeconds": 60,
            "no_data_state": "NoData",
            "exec_err_state": "Error",
            "labels": {
                "severity": severity,
                "team": "ml-ops"
            }
        }
    }

def create_new_group_with_alerts():
    """Create new group with TZ alerts"""
    
    # Create new alerts according to TZ requirements
    new_alerts = [
        create_alert_rule_data(
            alert_name="Model AUC Drop Critical",
            description="Critical AUC model drop below 0.52",
            query="SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'auc' ORDER BY timestamp DESC LIMIT 10",
            threshold=0.52,
            operator="lt",
            severity="critical"
        ),
        create_alert_rule_data(
            alert_name="Model F1-Score Drop",
            description="F1-Score model drop below 0.65",
            query="SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'f1_score' ORDER BY timestamp DESC LIMIT 10",
            threshold=0.65,
            operator="lt", 
            severity="warning"
        ),
        create_alert_rule_data(
            alert_name="Data Drift Detection",
            description="Data drift detected above 0.3",
            query="SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'drift_share' ORDER BY timestamp DESC LIMIT 10",
            threshold=0.3,
            operator="gt",
            severity="warning"
        )
    ]
    
    # Create new group
    new_group = {
        "name": "tz_model_monitoring", 
        "interval": "1m",
        "rules": new_alerts
    }
    
    # Prepare data for sending
    update_data = [new_group]
    
    try:
        # Use different namespace to avoid conflict with existing alert1
        response = requests.post(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules/TZ%20Model%20Monitoring", 
            auth=GRAFANA_AUTH,
            headers={"Content-Type": "application/json"},
            json=update_data
        )
        
        if response.status_code == 202:
            print("SUCCESS: New TZ alert group created!")
            return True
        else:
            print(f"ERROR creating alert group: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR creating alert group: {e}")
        return False

def verify_alerts():
    """Verify added alerts"""
    print("\nVerifying all alerts...")
    
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=GRAFANA_AUTH
        )
        response.raise_for_status()
        rules = response.json()
        
        total_groups = sum(len(groups) for groups in rules.values())
        print(f"Total rule groups: {total_groups}")
        
        for namespace, groups in rules.items():
            print(f"Namespace: {namespace}")
            for group in groups:
                group_name = group.get("name", "unnamed")
                rules_count = len(group.get("rules", []))
                print(f"  Group: {group_name} ({rules_count} alerts)")
                
                for rule in group.get("rules", []):
                    if "grafana_alert" in rule:
                        alert_title = rule["grafana_alert"].get("title", "unnamed")
                        is_paused = rule["grafana_alert"].get("is_paused", False)
                        status = "PAUSED" if is_paused else "ACTIVE"
                        print(f"    Alert: {alert_title} - {status}")
                        
    except Exception as e:
        print(f"ERROR verifying alerts: {e}")

def main():
    print_header()
    
    print("Creating separate alert group for TZ requirements (preserving existing alert1)")
    
    # Create new alert group
    success = create_new_group_with_alerts()
    
    if success:
        # Verify result
        verify_alerts()
        print("\nSUCCESS: Model monitoring alerts configured according to TZ!")
        print("Available in Grafana: http://localhost:3000/alerting/list")
        print("Original alert1 preserved in 'Model Monitoring' group")
        print("New TZ alerts created in 'TZ Model Monitoring' group")
    else:
        print("\nERROR: Failed to create alerts. Check configuration.")

if __name__ == "__main__":
    main()
