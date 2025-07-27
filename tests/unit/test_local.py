#!/usr/bin/env python3
"""
Локальный тест MLOps пайплайна без Docker
"""

from src.train import create_model_pipeline, prepare_features
import pandas as pd
from sklearn.metrics import accuracy_score

def test_model_training():
    print("🚀 Тестируем обучение модели...")
    
    # Загружаем небольшую выборку данных
    train_data = pd.read_parquet('data/processed/train_tall.parquet').head(1000)
    val_data = pd.read_parquet('data/processed/val_tall.parquet').head(500)
    
    print(f"Тренировочные данные: {train_data.shape}")
    print(f"Валидационные данные: {val_data.shape}")
    
    # Подготавливаем признаки
    X_train, y_train, numeric_features = prepare_features(train_data)
    X_val, y_val, _ = prepare_features(val_data)
    
    print(f"Подготовлены признаки: {X_train.shape}, целевая переменная: {y_train.shape}")
    
    # Создаем простую модель
    model = create_model_pipeline(
        max_features=100,
        ngram_range=(1, 1),
        xgb_params={
            'eval_metric': 'logloss', 
            'random_state': 42, 
            'max_depth': 3, 
            'n_estimators': 10
        }
    )
    
    print("✅ Модель создана, начинаем обучение...")
    
    # Обучаем
    model.fit(X_train, y_train)
    print("✅ Модель обучена!")
    
    # Простая оценка
    pred = model.predict(X_val)
    acc = accuracy_score(y_val, pred)
    print(f"📊 Accuracy на валидации: {acc:.3f}")
    
    return model

if __name__ == "__main__":
    model = test_model_training()
    print("🎉 Локальный тест успешно завершен!")
