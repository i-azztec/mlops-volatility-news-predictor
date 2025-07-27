#!/usr/bin/env python3
"""
Тест scoring flow без зависимости от production модели
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.predict import predict_daily_batch
from src.train import create_model_pipeline, prepare_features
import pandas as pd

def test_scoring_locally():
    print("🚀 Тестируем scoring функциональность...")
    
    # Загружаем небольшую выборку для быстрого обучения модели
    train_data = pd.read_parquet('data/processed/train_tall.parquet').head(1000)
    test_data = pd.read_parquet('data/processed/test_tall.parquet').head(100)
    
    # Обучаем простую модель
    X_train, y_train, _ = prepare_features(train_data)
    model = create_model_pipeline(
        max_features=100,
        ngram_range=(1, 1),
        xgb_params={'eval_metric': 'logloss', 'random_state': 42, 'max_depth': 3, 'n_estimators': 10}
    )
    model.fit(X_train, y_train)
    print("✅ Модель обучена для тестирования")
    
    # Тестируем предсказание для одного дня
    test_day = test_data[test_data['Date'] == test_data['Date'].iloc[0]]
    headlines = test_day['Headline'].tolist()
    
    # Создаем исторические признаки из данных
    historical_features = {
        col: test_day[col].iloc[0] 
        for col in test_day.columns 
        if col not in ['Date', 'Headline', 'vol_up']
    }
    
    print(f"📰 Тестируем с {len(headlines)} заголовками")
    
    # Делаем batch предсказание
    result = predict_daily_batch(headlines, model, historical_features)
    
    print("📊 Результаты предсказания:")
    print(f"  - Дата: {result['date']}")
    print(f"  - Количество заголовков: {result['num_headlines']}")
    print(f"  - Средняя вероятность: {result['prediction_mean_proba']:.3f}")
    print(f"  - Класс (средний): {result['prediction_mean_class']}")
    print(f"  - Мажоритарное голосование: {result['prediction_majority_vote']}")
    print(f"  - Максимальная вероятность: {result['prediction_max_proba']:.3f}")
    
    # Сравнение с истинной меткой
    true_label = test_day['vol_up'].iloc[0]
    pred_label = result['prediction_mean_class']
    accuracy = "✅ Правильно" if pred_label == true_label else "❌ Неправильно"
    print(f"  - Истинная метка: {true_label}, Предсказание: {pred_label} ({accuracy})")
    
    return result

if __name__ == "__main__":
    result = test_scoring_locally()
    print("🎉 Тест scoring завершен успешно!")
