#!/usr/bin/env python3
"""
Script for checking alert status in Grafana
"""

import requests
import json
from datetime import datetime

# Grafana connection settings
GRAFANA_URL = "http://localhost:3000"
USERNAME = "admin"
PASSWORD = "admin"

def check_grafana_alerts():
    """Checks alert status in Grafana"""
    
    print("🔍 Checking alerts in Grafana...")
    print(f"📅 Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check Grafana availability
    try:
        health_response = requests.get(f"{GRAFANA_URL}/api/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Grafana is available")
        else:
            print("❌ Grafana is unavailable")
            return
    except Exception as e:
        print(f"❌ Error connecting to Grafana: {e}")
        return
    
    # Get alert information
    try:
        # API for getting alert status
        alerts_response = requests.get(
            f"{GRAFANA_URL}/api/alertmanager/grafana/api/v2/alerts",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if alerts_response.status_code == 200:
            alerts = alerts_response.json()
            print(f"📊 Found alerts: {len(alerts)}")
            
            if alerts:
                for alert in alerts:
                    status = alert.get('status', {}).get('state', 'unknown')
                    name = alert.get('labels', {}).get('alertname', 'unnamed')
                    severity = alert.get('labels', {}).get('severity', 'unknown')
                    
                    status_icon = "🚨" if status == "firing" else "✅" if status == "resolved" else "⏳"
                    severity_icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
                    
                    print(f"{status_icon} {severity_icon} {name}: {status}")
            else:
                print("ℹ️  No active alerts found")
        else:
            print(f"❌ Error getting alerts: {alerts_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error getting alerts: {e}")
    
    # Check alert rules
    try:
        rules_response = requests.get(
            f"{GRAFANA_URL}/api/ruler/grafana/api/v1/rules",
            auth=(USERNAME, PASSWORD),
            timeout=10
        )
        
        if rules_response.status_code == 200:
            rules = rules_response.json()
            print(f"\n📋 Alert rules loaded: {len(rules) if rules else 0}")
            
            if rules:
                for namespace, groups in rules.items():
                    print(f"📁 Namespace: {namespace}")
                    for group in groups:
                        group_name = group.get('name', 'unnamed')
                        rules_count = len(group.get('rules', []))
                        print(f"  📂 Group: {group_name} ({rules_count} rules)")
                        
                        for rule in group.get('rules', []):
                            rule_name = rule.get('alert', 'unnamed')
                            print(f"    📌 {rule_name}")
        else:
            print(f"❌ Error getting rules: {rules_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error getting rules: {e}")

if __name__ == "__main__":
    check_grafana_alerts()
