#!/usr/bin/env python3
"""
Minimal script to populate Evidently UI with basic monitoring data
"""

import pandas as pd
import numpy as np
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metrics import DatasetSummaryMetric, ColumnSummaryMetric
from evidently.ui.workspace import Workspace
import os

def setup_evidently_minimal():
    """Setup Evidently UI with minimal working reports"""
    
    print("🚀 Setting up Evidently UI (minimal version)...")
    
    # Load data
    print("📊 Loading datasets...")
    val_data = pd.read_parquet('./data/processed/val_tall.parquet')
    test_data = pd.read_parquet('./data/processed/test_tall.parquet')
    
    # Create workspace
    workspace_path = './monitoring/evidently_workspace'
    os.makedirs(workspace_path, exist_ok=True)
    
    ws = Workspace(workspace_path)
    
    # Get or create project
    print("📁 Working with project...")
    projects = ws.list_projects()
    if projects:
        project_id = projects[0].id
        print(f"📋 Using existing project: {project_id}")
    else:
        project = ws.create_project("Volatility Monitoring")
        project_id = project.id
        print(f"✅ Created new project: {project_id}")
    
    # Prepare simple datasets
    print("🔧 Preparing datasets...")
    reference_data = val_data.sample(n=500, random_state=42).copy()
    current_data = test_data.sample(n=500, random_state=123).copy()
    
    # Add simple predictions
    np.random.seed(123)
    reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data))
    reference_data['prediction_proba'] = np.random.uniform(0.3, 0.7, size=len(reference_data))
    
    current_data['prediction'] = np.random.choice([0, 1], size=len(current_data))
    current_data['prediction_proba'] = np.random.uniform(0.2, 0.8, size=len(current_data))
    
    # Simple column mapping
    column_mapping = ColumnMapping()
    column_mapping.target = 'vol_up'
    column_mapping.prediction = 'prediction'
    
    # Create basic reports
    reports_data = [
        ("Production Baseline", reference_data, "Baseline production data"),
        ("Current Production", current_data, "Current production data"),
        ("Weekly Summary", test_data.sample(300, random_state=456), "Weekly monitoring summary")
    ]
    
    reports_created = 0
    
    for report_name, data, description in reports_data:
        print(f"📈 Creating {report_name}...")
        try:
            # Add predictions to weekly data if missing
            if 'prediction' not in data.columns:
                data = data.copy()
                data['prediction'] = np.random.choice([0, 1], size=len(data))
                data['prediction_proba'] = np.random.uniform(0.1, 0.9, size=len(data))
            
            # Very basic report with minimal metrics
            report = Report(metrics=[
                DatasetSummaryMetric(),
                ColumnSummaryMetric(column_name='vol_up'),
                ColumnSummaryMetric(column_name='prediction'),
                ColumnSummaryMetric(column_name='realized_vol'),
            ])
            
            # Run with same data as reference and current if needed
            if len(data) < 100:
                # Use bootstrap if data is too small
                data_sample = data.sample(n=min(100, len(data)), replace=True, random_state=42)
            else:
                data_sample = data.sample(n=100, random_state=42)
                
            report.run(reference_data=data_sample, 
                      current_data=data_sample, 
                      column_mapping=column_mapping)
            
            # Add to workspace
            ws.add_report(project_id, report)
            reports_created += 1
            
            # Save HTML
            safe_name = report_name.lower().replace(" ", "_")
            html_path = f"./monitoring/evidently_reports/ui_{safe_name}.html"
            report.save_html(html_path)
            
            print(f"✅ Created {report_name}")
            
        except Exception as e:
            print(f"❌ Failed to create {report_name}: {e}")
    
    # Create one comprehensive comparison report
    print("📊 Creating comparison report...")
    try:
        comparison_report = Report(metrics=[
            DatasetSummaryMetric(),
            ColumnSummaryMetric(column_name='vol_up'),
            ColumnSummaryMetric(column_name='prediction_proba'),
        ])
        
        comparison_report.run(reference_data=reference_data, 
                            current_data=current_data, 
                            column_mapping=column_mapping)
        
        ws.add_report(project_id, comparison_report)
        comparison_report.save_html("./monitoring/evidently_reports/ui_comparison.html")
        reports_created += 1
        print("✅ Created comparison report")
        
    except Exception as e:
        print(f"❌ Failed to create comparison report: {e}")
    
    print(f"\n🎉 Evidently UI Setup Complete!")
    print(f"📊 Created {reports_created} reports")
    print(f"📁 Project ID: {project_id}")
    print(f"🌐 Access UI at: http://localhost:8000")
    print(f"📄 HTML reports in: ./monitoring/evidently_reports/")
    
    # Verify projects and reports
    projects = ws.list_projects()
    print(f"\n📋 Available projects:")
    for proj in projects:
        print(f"  - {proj.name} (ID: {proj.id})")
        try:
            reports = ws.list_reports(proj.id)
            print(f"    📄 Reports: {len(reports)}")
        except:
            print(f"    📄 Reports: Unable to count")
        
    return reports_created > 0

if __name__ == "__main__":
    success = setup_evidently_minimal()
    if success:
        print("\n✨ Now refresh Evidently UI at http://localhost:8000")
        print("   You should see projects with reports in the UI!")
    else:
        print("\n❌ Setup failed, check error messages above")
