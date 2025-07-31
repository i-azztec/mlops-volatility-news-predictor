#!/usr/bin/env python3
"""
Скрипт для настройки чистого Evidently UI с простыми данными
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
    print('=== НАСТРОЙКА ЧИСТОГО EVIDENTLY UI ===')
    
    try:
        # Проверяем данные
        if not os.path.exists('./data/processed/test_tall.parquet'):
            print('❌ Нет файла test_tall.parquet')
            return
            
        if not os.path.exists('./data/processed/val_tall.parquet'):
            print('❌ Нет файла val_tall.parquet')
            return
        
        # Загружаем небольшие порции данных
        print('📊 Загружаем данные...')
        test_data = pd.read_parquet('./data/processed/test_tall.parquet')
        val_data = pd.read_parquet('./data/processed/val_tall.parquet')
        
        print(f'Test data: {len(test_data)} строк')
        print(f'Val data: {len(val_data)} строк')
        
        # Создаем простые dataset для демонстрации
        reference_data = val_data.sample(n=min(1000, len(val_data)), random_state=42).copy()
        current_data = test_data.sample(n=min(1000, len(test_data)), random_state=123).copy()
        
        # Добавляем простые предсказания
        np.random.seed(42)
        reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data), p=[0.5, 0.5])
        current_data['prediction'] = np.random.choice([0, 1], size=len(current_data), p=[0.6, 0.4])
        
        print('🔧 Настройка Column Mapping...')
        column_mapping = ColumnMapping()
        column_mapping.target = 'vol_up'
        column_mapping.prediction = 'prediction'
        
        # Выбираем только доступные численные колонки
        numeric_cols = []
        for col in ['realized_vol', 'tr_vol', 'park_vol']:
            if col in reference_data.columns:
                numeric_cols.append(col)
        
        if numeric_cols:
            column_mapping.numerical_features = numeric_cols[:3]  # Максимум 3 колонки
        
        print(f'Numeric features: {column_mapping.numerical_features}')
        
        # Создаем простой отчет
        print('📈 Создание отчета...')
        report = Report(metrics=[
            DatasetSummaryMetric(),
            ColumnSummaryMetric(column_name='vol_up'),
            ColumnSummaryMetric(column_name='prediction'),
        ])
        
        # Запускаем отчет
        report.run(
            reference_data=reference_data, 
            current_data=current_data, 
            column_mapping=column_mapping
        )
        
        # Сохраняем HTML
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = f'./monitoring/evidently_reports/clean_report_{timestamp}.html'
        os.makedirs('./monitoring/evidently_reports', exist_ok=True)
        report.save_html(html_path)
        print(f'✅ HTML отчет сохранен: {html_path}')
        
        # Добавляем в Evidently UI
        print('🎯 Добавление в Evidently UI...')
        workspace_path = './monitoring/evidently_workspace'
        os.makedirs(workspace_path, exist_ok=True)
        
        ws = Workspace(workspace_path)
        
        # Создаем новый проект
        project = ws.create_project('MLOps Volatility Monitoring')
        print(f'✅ Проект создан: {project.name} (ID: {project.id})')
        
        # Добавляем отчет
        ws.add_report(project.id, report)
        print('✅ Отчет добавлен в UI!')
        
        # Проверяем результат
        projects = ws.list_projects()
        print(f'\n📋 Итого проектов в UI: {len(projects)}')
        for p in projects:
            print(f'  - {p.name} (ID: {p.id})')
        
        print('\n🌐 Откройте браузер: http://localhost:8000')
        print('✅ Настройка завершена!')
        
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_clean_evidently()
