#!/usr/bin/env python3
"""
Скрипт для генерации исторических данных мониторинга модели волатильности.
Эмулирует работу системы в течение нескольких недель с постепенной деградацией.
"""

import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta
import os
import sys

# Добавляем src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# PostgreSQL connection
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monitoring',
    'user': 'user',
    'password': 'password'
}

def connect_to_db():
    """Подключение к PostgreSQL"""
    return psycopg2.connect(**POSTGRES_CONFIG)

def insert_metric(cursor, timestamp, metric_name, metric_value):
    """Вставляет одну метрику в базу данных"""
    cursor.execute(
        "INSERT INTO volatility_metrics (timestamp, metric_name, metric_value) VALUES (%s, %s, %s)",
        (timestamp, metric_name, metric_value)
    )

def generate_degrading_metrics(base_accuracy=0.714, base_f1=0.750, base_auc=0.555, weeks=4):
    """
    Генерирует метрики с постепенной деградацией модели
    
    Args:
        base_accuracy: Начальная точность модели
        base_f1: Начальный F1-score
        base_auc: Начальный AUC
        weeks: Количество недель для генерации данных
    
    Returns:
        List of tuples (timestamp, metrics_dict)
    """
    results = []
    
    # Начинаем с текущей даты и идем назад
    current_date = datetime.now()
    
    for week in range(weeks):
        # Каждую неделю модель деградирует на 1-3%
        degradation_factor = 1 - (week * 0.02 + np.random.normal(0, 0.01))
        degradation_factor = max(0.5, degradation_factor)  # Не падаем ниже 50%
        
        # Генерируем 3-4 измерения в неделю
        measurements_per_week = np.random.randint(3, 5)
        
        for measurement in range(measurements_per_week):
            # Время измерения (случайное в течение недели)
            days_back = week * 7 + measurement * (7 / measurements_per_week)
            timestamp = current_date - timedelta(days=days_back)
            
            # Добавляем случайный шум к метрикам
            noise = np.random.normal(0, 0.02)  # 2% шум
            
            metrics = {
                'accuracy': max(0.4, min(0.9, base_accuracy * degradation_factor + noise)),
                'f1': max(0.3, min(0.9, base_f1 * degradation_factor + noise * 0.8)),
                'auc': max(0.45, min(0.75, base_auc * degradation_factor + noise * 0.5)),
                
                # Data drift метрики (увеличиваются со временем)
                'data_drift_detected': 1 if week > 2 and np.random.random() > 0.7 else 0,
                'drift_share': min(0.3, week * 0.05 + np.random.uniform(0, 0.05)),
                
                # Размеры выборок (варьируются)
                'current_samples': np.random.randint(150, 300),
                'reference_samples': 6300,  # Константа
                
                # Квантили предсказаний
                'prediction_mean_proba_quantile_0.05': np.random.uniform(0.1, 0.3),
                'prediction_mean_proba_quantile_0.95': np.random.uniform(0.7, 0.9),
            }
            
            results.append((timestamp, metrics))
    
    # Сортируем по времени (от старых к новым)
    results.sort(key=lambda x: x[0])
    return results

def main():
    """Основная функция для генерации и сохранения исторических данных"""
    print("🔄 Генерация исторических данных мониторинга...")
    
    # Генерируем данные за 6 недель
    historical_data = generate_degrading_metrics(weeks=6)
    
    print(f"📊 Сгенерировано {len(historical_data)} временных точек")
    
    # Подключаемся к базе данных
    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        
        # Очищаем старые данные (опционально)
        print("🗑️ Очистка старых данных...")
        cursor.execute("DELETE FROM volatility_metrics WHERE timestamp < NOW() - INTERVAL '2 months'")
        
        # Вставляем новые данные
        print("💾 Вставка исторических данных...")
        total_inserted = 0
        
        for timestamp, metrics in historical_data:
            for metric_name, metric_value in metrics.items():
                insert_metric(cursor, timestamp, metric_name, metric_value)
                total_inserted += 1
        
        # Подтверждаем изменения
        conn.commit()
        print(f"✅ Вставлено {total_inserted} метрик в базу данных")
        
        # Показываем статистику
        cursor.execute("""
            SELECT 
                metric_name, 
                COUNT(*) as count,
                MIN(metric_value) as min_val,
                MAX(metric_value) as max_val,
                AVG(metric_value) as avg_val
            FROM volatility_metrics 
            WHERE timestamp > NOW() - INTERVAL '2 months'
            GROUP BY metric_name 
            ORDER BY metric_name
        """)
        
        print("\n📈 Статистика сгенерированных метрик:")
        print("Метрика\t\t\t\tКоличество\tМин\tМакс\tСреднее")
        print("-" * 70)
        
        for row in cursor.fetchall():
            metric_name, count, min_val, max_val, avg_val = row
            print(f"{metric_name:30s}\t{count:3d}\t{min_val:.3f}\t{max_val:.3f}\t{avg_val:.3f}")
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        return 1
    
    finally:
        if 'conn' in locals():
            conn.close()
    
    print("\n🎯 Теперь можно обновить Grafana дашборд!")
    print("   Доступ: http://localhost:3000")
    print("   Логин: admin / admin")
    
    return 0

if __name__ == "__main__":
    exit(main())
