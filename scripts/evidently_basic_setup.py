#!/usr/bin/env python3
"""
Базовый скрипт для настройки Evidently UI
Создает простой проект с минимальными отчетами
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
    """Создает базовый проект в Evidently UI"""
    
    print("=== СОЗДАНИЕ БАЗОВОГО ПРОЕКТА EVIDENTLY ===")
    
    try:
        # Загружаем данные
        print("📊 Загружаем данные...")
        test_data = pd.read_parquet('./data/processed/test_tall.parquet')
        val_data = pd.read_parquet('./data/processed/val_tall.parquet')
        
        # Подготавливаем данные
        print("🔧 Подготавливаем данные...")
        reference_data = val_data.sample(n=1000, random_state=42).copy()
        current_data = test_data.iloc[:1000].copy()
        
        # Добавляем предсказания
        np.random.seed(42)
        reference_data['prediction'] = np.random.choice([0, 1], size=len(reference_data))
        current_data['prediction'] = np.random.choice([0, 1], size=len(current_data))
        
        # Настройка колонок
        column_mapping = ColumnMapping()
        column_mapping.target = 'vol_up'
        column_mapping.prediction = 'prediction'
        column_mapping.numerical_features = ['realized_vol', 'tr_vol', 'park_vol']
        
        # Создаем отчет
        print("📈 Создаем отчет...")
        report = Report(metrics=[DataDriftPreset(stattest_threshold=0.1)])
        report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)
        
        # Сохраняем HTML отчет
        html_path = './monitoring/evidently_reports/basic_drift_report.html'
        os.makedirs('./monitoring/evidently_reports', exist_ok=True)
        report.save_html(html_path)
        print(f"✅ HTML отчет сохранен: {html_path}")
        
        # Добавляем в Evidently UI
        print("🌐 Добавляем в Evidently UI...")
        workspace_path = './monitoring/evidently_workspace'
        
        # Создаем workspace
        ws = Workspace(workspace_path)
        
        # Создаем проект
        project = ws.create_project('ML Volatility Monitoring')
        print(f"✅ Проект создан с ID: {project.id}")
        
        # Добавляем отчет в проект
        ws.add_report(project.id, report)
        print("✅ Отчет добавлен в проект")
        
        print("\n🎉 УСПЕШНО ЗАВЕРШЕНО!")
        print("🌐 Откройте Evidently UI: http://localhost:8000")
        print("📁 Проект: ML Volatility Monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = create_basic_evidently_project()
    if success:
        print("\n✅ Все готово!")
    else:
        print("\n❌ Что-то пошло не так.")
