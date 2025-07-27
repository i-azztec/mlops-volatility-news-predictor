#!/usr/bin/env python3
"""
Простой тест для проверки работоспособности модулей.
"""

import pandas as pd
from src.preprocess import transform_to_tall_format, calculate_volatility_metrics, add_technical_features

def test_preprocessing():
    """Тестирование предобработки данных."""
    print("🚀 Загружаем данные...")
    df = pd.read_csv('data/raw/Combined_News_DJIA.csv')
    print(f"   Исходный размер: {df.shape}")
    print(f"   Колонки: {df.columns.tolist()[:5]}...")
    
    print("\n📊 Преобразование в длинный формат...")
    df_tall = transform_to_tall_format(df)
    print(f"   Размер после преобразования: {df_tall.shape}")
    
    print("\n📈 Расчет метрик волатильности...")
    try:
        df_with_vol = calculate_volatility_metrics(df_tall)
        print(f"   Размер с волатильностью: {df_with_vol.shape}")
        print(f"   Новые колонки: {[col for col in df_with_vol.columns if 'volatility' in col.lower()]}")
    except Exception as e:
        print(f"   ❌ Ошибка в расчете волатильности: {e}")
    
    print("\n✅ Базовое тестирование завершено!")

if __name__ == "__main__":
    test_preprocessing()
