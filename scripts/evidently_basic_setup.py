#!/usr/bin/env python3
"""
Basic script for setting up Evidently UI
Creates a simple project with minimal reports
"""
import pandas as pd
import numpy as np
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.ui.workspace import Workspace
from datetime import datetime
import os

def create_basic_evidently_project():
    """Creates basic project in Evidently UI"""
    
    print("=== CREATING BASIC EVIDENTLY PROJECT ===")
    
    try:
        # Load data
        print("📊 Loading data...")
        test_data = pd.read_parquet('./data/processed/test_tall.parquet')
        val_data = pd.read_parquet('./data/processed/val_tall.parquet')
        
        # Prepare data
        print("🔧 Preparing data...")
        reference_data = val_data.sample(n=1000, random_state=42).copy()
        current_data = test_data.iloc[:1000].copy()
        
        # Add predictions
        np.random.seed(42)
        reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data))
        current_data['prediction'] = np.random.choice([0, 1], size=len(current_data))
        
        # Column setup
        column_mapping = ColumnMapping()
        column_mapping.target = 'vol_up'
        column_mapping.prediction = 'prediction'
        column_mapping.numerical_features = ['realized_vol', 'tr_vol', 'park_vol']
        
        # Create report
        print("📈 Creating report...")
        report = Report(metrics=[DataDriftPreset(stattest_threshold=0.1)])
        report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
        
        # Save HTML report
        html_path = './monitoring/evidently_reports/basic_drift_report.html'
        os.makedirs('./monitoring/evidently_reports', exist_ok=True)
        report.save_html(html_path)
        print(f"✅ HTML report saved: {html_path}")
        
        # Add to Evidently UI
        print("🌐 Adding to Evidently UI...")
        workspace_path = './monitoring/evidently_workspace'
        
        # Create workspace
        ws = Workspace(workspace_path)
        
        # Create project
        project = ws.create_project('ML Volatility Monitoring')
        print(f"✅ Project created with ID: {project.id}")
        
        # Add report to project
        ws.add_report(project.id, report)
        print("✅ Report added to project")
        
        print("\n🎉 SUCCESSFULLY COMPLETED!")
        print("🌐 Open Evidently UI: http://localhost:8000")
        print("📁 Project: ML Volatility Monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = create_basic_evidently_project()
    if success:
        print("\n✅ All done!")
    else:
        print("\n❌ Something went wrong.")
