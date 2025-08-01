#!/usr/bin/env python3
"""
Script for generating historical monitoring data for volatility model.
Emulates system operation over several weeks with gradual degradation.
"""

import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta
import os
import sys

# Add src to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# PostgreSQL connection
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monitoring',
    'user': 'user',
    'password': 'password'
}

def connect_to_db():
    """Connect to PostgreSQL"""
    return psycopg2.connect(**POSTGRES_CONFIG)

def insert_metric(cursor, timestamp, metric_name, metric_value):
    """Inserts one metric into database"""
    cursor.execute(
        "INSERT INTO volatility_metrics (timestamp, metric_name, metric_value) VALUES (%s, %s, %s)",
        (timestamp, metric_name, metric_value)
    )

def generate_degrading_metrics(base_accuracy=0.714, base_f1=0.750, base_auc=0.555, weeks=4):
    """
    Generates metrics with gradual model degradation
    
    Args:
        base_accuracy: Initial model accuracy
        base_f1: Initial F1-score
        base_auc: Initial AUC
        weeks: Number of weeks to generate data for
    
    Returns:
        List of tuples (timestamp, metrics_dict)
    """
    results = []
    
    # Start from current date and go back
    current_date = datetime.now()
    
    for week in range(weeks):
        # Each week model degrades by 1-3%
        degradation_factor = 1 - (week * 0.02 + np.random.normal(0, 0.01))
        degradation_factor = max(0.5, degradation_factor)  # Don't fall below 50%
        
        # Generate 3-4 measurements per week
        measurements_per_week = np.random.randint(3, 5)
        
        for measurement in range(measurements_per_week):
            # Measurement time (random within the week)
            days_back = week * 7 + measurement * (7 / measurements_per_week)
            timestamp = current_date - timedelta(days=days_back)
            
            # Add random noise to metrics
            noise = np.random.normal(0, 0.02)  # 2% noise
            
            metrics = {
                'accuracy': max(0.4, min(0.9, base_accuracy * degradation_factor + noise)),
                'f1': max(0.3, min(0.9, base_f1 * degradation_factor + noise * 0.8)),
                'auc': max(0.45, min(0.75, base_auc * degradation_factor + noise * 0.5)),
                
                # Data drift metrics (increase over time)
                'data_drift_detected': 1 if week > 2 and np.random.random() > 0.7 else 0,
                'drift_share': min(0.3, week * 0.05 + np.random.uniform(0, 0.05)),
                
                # Sample sizes (vary)
                'current_samples': np.random.randint(150, 300),
                'reference_samples': 6300,  # Constant
                
                # Prediction quantiles
                'prediction_mean_proba_quantile_0.05': np.random.uniform(0.1, 0.3),
                'prediction_mean_proba_quantile_0.95': np.random.uniform(0.7, 0.9),
            }
            
            results.append((timestamp, metrics))
    
    # Sort by time (from old to new)
    results.sort(key=lambda x: x[0])
    return results

def main():
    """Main function for generating and saving historical data"""
    print("🔄 Generating historical monitoring data...")
    
    # Generate data for 6 weeks
    historical_data = generate_degrading_metrics(weeks=6)
    
    print(f"📊 Generated {len(historical_data)} time points")
    
    # Connect to database
    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        
        # Clear old data (optional)
        print("🗑️ Clearing old data...")
        cursor.execute("DELETE FROM volatility_metrics WHERE timestamp < NOW() - INTERVAL '2 months'")
        
        # Insert new data
        print("💾 Inserting historical data...")
        total_inserted = 0
        
        for timestamp, metrics in historical_data:
            for metric_name, metric_value in metrics.items():
                insert_metric(cursor, timestamp, metric_name, metric_value)
                total_inserted += 1
        
        # Commit changes
        conn.commit()
        print(f"✅ Inserted {total_inserted} metrics into database")
        
        # Show statistics
        cursor.execute("""
            SELECT 
                metric_name, 
                COUNT(*) as count,
                MIN(metric_value) as min_val,
                MAX(metric_value) as max_val,
                AVG(metric_value) as avg_val
            FROM volatility_metrics 
            WHERE timestamp > NOW() - INTERVAL '2 months'
            GROUP BY metric_name 
            ORDER BY metric_name
        """)
        
        print("\n📈 Statistics of generated metrics:")
        print("Metric\t\t\t\tCount\tMin\tMax\tAverage")
        print("-" * 70)
        
        for row in cursor.fetchall():
            metric_name, count, min_val, max_val, avg_val = row
            print(f"{metric_name:30s}\t{count:3d}\t{min_val:.3f}\t{max_val:.3f}\t{avg_val:.3f}")
        
    except Exception as e:
        print(f"❌ Error working with database: {e}")
        return 1
    
    finally:
        if 'conn' in locals():
            conn.close()
    
    print("\n🎯 Now you can update the Grafana dashboard!")
    print("   Access: http://localhost:3000")
    print("   Login: admin / admin")
    
    return 0

if __name__ == "__main__":
    exit(main())
