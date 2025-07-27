#!/usr/bin/env python3
"""
Создание тестовых данных для мониторинга
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from src.utils import save_parquet_to_s3
from datetime import datetime, timedelta

def create_test_predictions():
    print("🎯 Создаем тестовые данные для мониторинга...")
    
    # Создаем тестовые предсказания за последние 7 дней
    test_predictions = pd.DataFrame({
        'date': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)],
        'prediction_mean_proba': [0.52, 0.48, 0.55, 0.49, 0.53, 0.51, 0.50],
        'prediction_mean_class': [1, 0, 1, 0, 1, 1, 0],
        'prediction_majority_vote': [1, 0, 1, 0, 1, 1, 0],
        'prediction_max_proba': [0.65, 0.58, 0.72, 0.55, 0.68, 0.63, 0.59],
        'prediction_max_class': [1, 1, 1, 1, 1, 1, 1],
        'num_headlines': [25, 25, 25, 25, 25, 25, 25],
        'model_version': ['test-1'] * 7,
        'true_vol_up': [1, 0, 1, 1, 0, 1, 0],
        'prediction_timestamp': [datetime.now().isoformat()] * 7
    })
    
    # Сохраняем каждый день отдельно в S3
    bucket_name = 'volatility-news-data'
    for _, row in test_predictions.iterrows():
        date_str = row['date']
        single_pred = pd.DataFrame([row])
        s3_key = f'predictions/{date_str}.parquet'
        try:
            save_parquet_to_s3(single_pred, bucket_name, s3_key)
            print(f'✅ Сохранено: {s3_key}')
        except Exception as e:
            print(f'❌ Ошибка для {s3_key}: {e}')
    
    print("🎉 Тестовые данные для мониторинга созданы!")

if __name__ == "__main__":
    create_test_predictions()
