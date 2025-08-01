#!/usr/bin/env python3
"""
Script for creating production monitoring simulation for ML model
"""

import pandas as pd
import numpy as np
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import *
from evidently.ui.workspace import Workspace
import os
from datetime import datetime

def create_production_monitoring_simulation():
    print('=== CREATING PRODUCTION MONITORING SIMULATION ===')
    
    # Load data
    test_data = pd.read_parquet('./data/processed/test_tall.parquet')
    val_data = pd.read_parquet('./data/processed/val_tall.parquet')
    
    # Reference data 
    reference_data = val_data.sample(n=2000, random_state=42).copy()
    np.random.seed(123)
    reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data), p=[0.5, 0.5])
    reference_data['prediction_proba'] = np.random.uniform(0.4, 0.7, size=len(reference_data))
    
    # Production data
    current_data = test_data.iloc[:1500].copy()
    np.random.seed(42)
    current_data['prediction'] = np.random.choice([0, 1], size=len(current_data), p=[0.7, 0.3])
    current_data['prediction_proba'] = np.random.uniform(0.1, 0.9, size=len(current_data))
    
    # Monitoring setup
    column_mapping = ColumnMapping()
    column_mapping.target = 'vol_up'
    column_mapping.prediction = 'prediction'
    column_mapping.text_features = ['Headline']
    column_mapping.numerical_features = ['realized_vol', 'tr_vol', 'park_vol', 'vol_ratio_5d']
    
    # Create report
    report = Report(metrics=[
        DataDriftPreset(stattest_threshold=0.1),
        TargetDriftPreset(),
        DatasetSummaryMetric(),
        ColumnSummaryMetric(column_name='prediction'),
        ColumnSummaryMetric(column_name='vol_up'),
        ColumnDriftMetric(column_name='realized_vol'),
        TextDescriptorsDistribution(column_name='Headline'),
    ])
    
    report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_path = f'./monitoring/evidently_reports/production_sim_{timestamp}.html'
    report.save_html(html_path)
    
    # Add to workspace
    try:
        ws = Workspace('./monitoring/evidently_workspace')
        projects = ws.list_projects()
        if projects:
            project_id = projects[0].id
        else:
            project = ws.create_project('Production Monitoring')
            project_id = project.id
        ws.add_report(project_id, report)
        print(f'✅ Report added to UI: {html_path}')
    except Exception as e:
        print(f'UI error: {e}')
    
    return html_path

if __name__ == "__main__":
    create_production_monitoring_simulation()
