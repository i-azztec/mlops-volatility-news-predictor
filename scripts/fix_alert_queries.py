# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# Grafana configuration
GRAFANA_URL = "http://localhost:3000"
GRAFANA_AUTH = ("admin", "admin")

def print_header():
    print("Fixing alert SQL queries...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def fix_alert_queries():
    """Fix SQL queries in existing alerts"""
    
    # Get all alerts
    response = requests.get(
        f"{GRAFANA_URL}/api/v1/provisioning/alert-rules",
        auth=GRAFANA_AUTH
    )
    response.raise_for_status()
    alerts = response.json()
    
    # SQL query fixes - remove ORDER BY timestamp since we're using AVG
    query_fixes = {
        "Model AUC Drop Critical": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'auc' LIMIT 10",
        "Model F1-Score Drop": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'f1_score' LIMIT 10", 
        "Data Drift Detection": "SELECT AVG(metric_value) FROM volatility_metrics WHERE metric_name = 'drift_share' LIMIT 10"
    }
    
    fixed_count = 0
    
    for alert in alerts:
        title = alert.get("title", "")
        
        if title in query_fixes:
            print(f"Fixing alert: {title}")
            
            # Update the SQL query in data[0].model.rawSql
            for data_item in alert.get("data", []):
                if data_item.get("refId") == "A":
                    if "model" in data_item:
                        data_item["model"]["rawSql"] = query_fixes[title]
                        print(f"  Updated SQL: {query_fixes[title]}")
            
            # Update the alert via API
            alert_uid = alert.get("uid", "")
            if alert_uid:
                try:
                    update_response = requests.put(
                        f"{GRAFANA_URL}/api/v1/provisioning/alert-rules/{alert_uid}",
                        auth=GRAFANA_AUTH,
                        headers={"Content-Type": "application/json"},
                        json=alert
                    )
                    
                    if update_response.status_code == 200:
                        print(f"  SUCCESS: Updated {title}")
                        fixed_count += 1
                    else:
                        print(f"  ERROR updating {title}: {update_response.status_code}")
                        print(f"  Response: {update_response.text}")
                        
                except Exception as e:
                    print(f"  ERROR updating {title}: {e}")
    
    return fixed_count

def verify_alerts():
    """Verify fixed alerts"""
    print("\nVerifying fixed alerts...")
    
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/v1/provisioning/alert-rules",
            auth=GRAFANA_AUTH
        )
        response.raise_for_status()
        alerts = response.json()
        
        for alert in alerts:
            title = alert.get("title", "unnamed")
            if "Model" in title or "Data Drift" in title:
                print(f"\nAlert: {title}")
                
                # Check SQL query
                for data_item in alert.get("data", []):
                    if data_item.get("refId") == "A":
                        model = data_item.get("model", {})
                        raw_sql = model.get("rawSql", "")
                        print(f"  SQL: {raw_sql}")
                        
    except Exception as e:
        print(f"ERROR verifying alerts: {e}")

def main():
    print_header()
    
    fixed_count = fix_alert_queries()
    
    if fixed_count > 0:
        verify_alerts()
        print(f"\nSUCCESS: Fixed {fixed_count} alert queries!")
        print("Please check Grafana UI for updated alert status.")
    else:
        print("\nERROR: No alerts were fixed.")

if __name__ == "__main__":
    main()
