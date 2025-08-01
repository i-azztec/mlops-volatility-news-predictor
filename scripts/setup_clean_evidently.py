#!/usr/bin/env python3
"""
Script for setting up clean Evidently UI with simple data
"""

import pandas as pd
import numpy as np
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import DatasetSummaryMetric, ColumnSummaryMetric
from evidently.ui.workspace import Workspace
import os
from datetime import datetime

def setup_clean_evidently():
    print('=== SETTING UP CLEAN EVIDENTLY UI ===')
    
    try:
        # Check data
        if not os.path.exists('./data/processed/test_tall.parquet'):
            print('❌ No test_tall.parquet file')
            return
            
        if not os.path.exists('./data/processed/val_tall.parquet'):
            print('❌ No val_tall.parquet file')
            return
        
        # Load small portions of data
        print('📊 Load data...')
        test_data = pd.read_parquet('./data/processed/test_tall.parquet')
        val_data = pd.read_parquet('./data/processed/val_tall.parquet')
        
        print(f'Test data: {len(test_data)} rows')
        print(f'Val data: {len(val_data)} rows')
        
        # Create simple datasets for demonstration
        reference_data = val_data.sample(n=min(1000, len(val_data)), random_state=42).copy()
        current_data = test_data.sample(n=min(1000, len(test_data)), random_state=123).copy()
        
        # Add simple predictions
        np.random.seed(42)
        reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data), p=[0.5, 0.5])
        current_data['prediction'] = np.random.choice([0, 1], size=len(current_data), p=[0.6, 0.4])
        
        print('🔧 Setting up Column Mapping...')
        column_mapping = ColumnMapping()
        column_mapping.target = 'vol_up'
        column_mapping.prediction = 'prediction'
        
        # Select only available numerical columns
        numeric_cols = []
        for col in ['realized_vol', 'tr_vol', 'park_vol']:
            if col in reference_data.columns:
                numeric_cols.append(col)
        
        if numeric_cols:
            column_mapping.numerical_features = numeric_cols[:3]  # Maximum 3 columns
        
        print(f'Numeric features: {column_mapping.numerical_features}')
        
        # Create simple report
        print('📈 Creating report...')
        report = Report(metrics=[
            DatasetSummaryMetric(),
            ColumnSummaryMetric(column_name='vol_up'),
            ColumnSummaryMetric(column_name='prediction'),
        ])
        
        # Run report
        report.run(
            reference_data=reference_data, 
            current_data=current_data, 
            column_mapping=column_mapping
        )
        
        # Save HTML
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = f'./monitoring/evidently_reports/clean_report_{timestamp}.html'
        os.makedirs('./monitoring/evidently_reports', exist_ok=True)
        report.save_html(html_path)
        print(f'✅ HTML report saved: {html_path}')
        
        # Add to Evidently UI
        print('🎯 Adding to Evidently UI...')
        workspace_path = './monitoring/evidently_workspace'
        os.makedirs(workspace_path, exist_ok=True)
        
        ws = Workspace(workspace_path)
        
        # Create new project
        project = ws.create_project('MLOps Volatility Monitoring')
        print(f'✅ Project created: {project.name} (ID: {project.id})')
        
        # Add report
        ws.add_report(project.id, report)
        print('✅ Report added to UI!')
        
        # Check result
        projects = ws.list_projects()
        print(f'\n📋 Total projects in UI: {len(projects)}')
        for p in projects:
            print(f'  - {p.name} (ID: {p.id})')
        
        print('\n🌐 Open browser: http://localhost:8000')
        print('✅ Setup completed!')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_clean_evidently()
