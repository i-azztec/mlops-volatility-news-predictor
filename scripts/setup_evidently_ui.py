#!/usr/bin/env python3
"""
Script to populate Evidently UI with monitoring data and projects
Creates projects, datasets, and reports in Evidently UI
"""

import pandas as pd
import numpy as np
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset, ClassificationPreset
from evidently.metrics import *
from evidently.ui.workspace import Workspace
from evidently.ui.dashboards import CounterAgg, DashboardPanelCounter, PanelValue, ReportFilter
from evidently.renderers.html_widgets import WidgetSize
import os
from datetime import datetime, timedelta

def setup_evidently_ui():
    """Setup Evidently UI with projects and reports"""
    
    print("🚀 Setting up Evidently UI for MLOps Volatility Predictor...")
    
    # Load data
    print("📊 Loading datasets...")
    val_data = pd.read_parquet('./data/processed/val_tall.parquet')
    test_data = pd.read_parquet('./data/processed/test_tall.parquet')
    
    # Create workspace
    workspace_path = './monitoring/evidently_workspace'
    os.makedirs(workspace_path, exist_ok=True)
    
    ws = Workspace(workspace_path)
    
    # Create main project
    print("📁 Creating main project...")
    try:
        project = ws.create_project("MLOps Volatility Predictor", 
                                  description="Production monitoring for volatility prediction model")
        project_id = project.id
        print(f"✅ Created project: {project_id}")
    except Exception as e:
        print(f"ℹ️  Project might already exist: {e}")
        projects = ws.list_projects()
        if projects:
            project_id = projects[0].id
            print(f"📋 Using existing project: {project_id}")
        else:
            raise Exception("Could not create or find project")
    
    # Prepare reference dataset (validation data)
    print("🔧 Preparing reference dataset...")
    reference_data = val_data.sample(n=min(2000, len(val_data)), random_state=42).copy()
    
    # Add mock predictions to reference data (simulating production baseline)
    np.random.seed(123)
    reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data), p=[0.52, 0.48])
    reference_data['prediction_proba'] = np.random.uniform(0.45, 0.65, size=len(reference_data))
    
    # Column mapping
    column_mapping = ColumnMapping()
    column_mapping.target = 'vol_up'
    column_mapping.prediction = 'prediction'
    column_mapping.text_features = ['Headline']
    column_mapping.numerical_features = ['realized_vol', 'tr_vol', 'park_vol', 'vol_ratio_5d']
    
    # Create multiple time periods for monitoring simulation
    periods = [
        ("Week 1", test_data.iloc[:500].copy(), [0.55, 0.45], (0.4, 0.7)),
        ("Week 2", test_data.iloc[500:1000].copy(), [0.48, 0.52], (0.3, 0.8)),
        ("Week 3", test_data.iloc[1000:1500].copy(), [0.62, 0.38], (0.2, 0.9)),
        ("Current", test_data.iloc[1500:2000].copy(), [0.45, 0.55], (0.35, 0.75))
    ]
    
    reports_created = 0
    
    for period_name, current_data, pred_probs, proba_range in periods:
        print(f"📈 Creating report for {period_name}...")
        
        # Add predictions to current data
        np.random.seed(hash(period_name) % 1000)
        current_data['prediction'] = np.random.choice([0, 1], size=len(current_data), p=pred_probs)
        current_data['prediction_proba'] = np.random.uniform(proba_range[0], proba_range[1], size=len(current_data))
        
        # Create comprehensive report
        report = Report(metrics=[
            # Data Quality
            DatasetSummaryMetric(),
            DataDriftPreset(stattest_threshold=0.1),
            
            # Target and Predictions
            TargetDriftPreset(),
            ColumnSummaryMetric(column_name='prediction'),
            ColumnSummaryMetric(column_name='vol_up'),
            
            # Classification Performance  
            ClassificationQualityMetric(),
            ClassificationClassBalance(),
            ClassificationConfusionMatrix(),
            
            # Feature Analysis
            ColumnDriftMetric(column_name='realized_vol'),
            ColumnDriftMetric(column_name='vol_ratio_5d'),
            
            # Text Analysis
            TextDescriptorsDistribution(column_name='Headline'),
            
            # Custom metrics
            ColumnQuantileMetric(column_name='prediction_proba', quantile=0.95),
            ColumnQuantileMetric(column_name='prediction_proba', quantile=0.05),
        ])
        
        # Run report
        try:
            report.run(reference_data=reference_data, 
                      current_data=current_data, 
                      column_mapping=column_mapping)
            
            # Add to workspace
            ws.add_report(project_id, report, 
                         tags=[period_name.lower().replace(" ", "_"), "production"])
            
            # Save HTML report
            html_filename = f"monitoring_report_{period_name.lower().replace(' ', '_')}.html"
            html_path = f"./monitoring/evidently_reports/{html_filename}"
            report.save_html(html_path)
            
            reports_created += 1
            print(f"✅ Created report for {period_name}")
            
        except Exception as e:
            print(f"❌ Failed to create report for {period_name}: {e}")
    
    # Create test suite for additional validation
    print("🧪 Creating test suite...")
    try:
        from evidently.test_suite import TestSuite
        from evidently.tests import (TestNumberOfColumnsWithMissingValues, TestNumberOfRowsWithMissingValues,
                                   TestNumberOfConstantColumns, TestNumberOfDuplicatedRows, 
                                   TestColumnsType, TestTargetFeaturesCorrelations, 
                                   TestPredictionFeaturesCorrelations)
        
        test_suite = TestSuite(tests=[
            TestNumberOfColumnsWithMissingValues(),
            TestNumberOfRowsWithMissingValues(), 
            TestNumberOfConstantColumns(),
            TestNumberOfDuplicatedRows(),
            TestColumnsType(),
            TestTargetFeaturesCorrelations(),
            TestPredictionFeaturesCorrelations()
        ])
        
        test_suite.run(reference_data=reference_data, 
                      current_data=current_data, 
                      column_mapping=column_mapping)
        
        ws.add_test_suite(project_id, test_suite)
        print("✅ Added test suite")
        
    except Exception as e:
        print(f"⚠️  Test suite creation failed (non-critical): {e}")
    
    # Summary
    print(f"\n🎉 Evidently UI Setup Complete!")
    print(f"📊 Created {reports_created} reports")
    print(f"📁 Project ID: {project_id}")
    print(f"🌐 Access UI at: http://localhost:8000")
    print(f"📄 HTML reports in: ./monitoring/evidently_reports/")
    
    # List all projects for verification
    projects = ws.list_projects()
    print(f"\n📋 Available projects:")
    for proj in projects:
        print(f"  - {proj.name} (ID: {proj.id})")

if __name__ == "__main__":
    setup_evidently_ui()
