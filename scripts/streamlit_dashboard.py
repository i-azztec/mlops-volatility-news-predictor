"""
Streamlit Web UI for Volatility Prediction Results
This app displays and analyzes model predictions and monitoring data.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import os

# Configure page
st.set_page_config(
    page_title="MLOps Volatility Predictor Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def generate_demo_data():
    """Generate demo prediction data for visualization."""
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now(),
        freq='D'
    )
    
    # Generate realistic volatility predictions
    predictions = []
    for i, date in enumerate(dates):
        # Create some trend and noise
        trend = 0.52 + 0.05 * np.sin(i / 5) 
        noise = random.uniform(-0.1, 0.1)
        prob = max(0.1, min(0.9, trend + noise))
        
        predictions.append({
            'date': date,
            'prediction_mean_proba': prob,
            'prediction_majority_vote': 1 if prob > 0.5 else 0,
            'prediction_max_proba_class': 1 if random.random() > 0.4 else 0,
            'prediction_max_proba_value': prob + random.uniform(-0.05, 0.05),
            'model_version': '1',
            'auc_score': 0.54 + random.uniform(-0.02, 0.02),
            'f1_score': 0.52 + random.uniform(-0.03, 0.03),
            'data_drift_score': random.uniform(0.1, 0.4)
        })
    
    return pd.DataFrame(predictions)

def generate_news_examples():
    """Generate example news headlines with predictions."""
    examples = [
        {
            'headline': 'Fed announces surprise interest rate hike to combat inflation',
            'probability': 0.78,
            'prediction': 1,
            'confidence': 'High'
        },
        {
            'headline': 'Tech stocks surge on AI breakthrough announcement',
            'probability': 0.72,
            'prediction': 1,
            'confidence': 'High'
        },
        {
            'headline': 'Oil prices plummet amid global oversupply concerns',
            'probability': 0.68,
            'prediction': 1,
            'confidence': 'Medium'
        },
        {
            'headline': 'Market maintains steady course after economic data release',
            'probability': 0.45,
            'prediction': 0,
            'confidence': 'Medium'
        },
        {
            'headline': 'Corporate earnings meet expectations across sectors',
            'probability': 0.38,
            'prediction': 0,
            'confidence': 'Medium'
        }
    ]
    return pd.DataFrame(examples)

def main():
    """Main Streamlit application."""
    
    # Header
    st.title("📈 MLOps Volatility News Predictor")
    st.markdown("**Real-time DJIA volatility prediction based on news sentiment**")
    
    # Sidebar
    st.sidebar.header("🔧 Dashboard Controls")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Select Page",
        ["📊 Model Performance", "📰 Prediction Examples", "🔍 Monitoring", "ℹ️ About"]
    )
    
    if page == "📊 Model Performance":
        show_model_performance()
    elif page == "📰 Prediction Examples":
        show_prediction_examples()
    elif page == "🔍 Monitoring":
        show_monitoring()
    elif page == "ℹ️ About":
        show_about()

def show_model_performance():
    """Display model performance metrics and trends."""
    st.header("📊 Model Performance Dashboard")
    
    # Generate demo data
    df = generate_demo_data()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        latest_auc = df['auc_score'].iloc[-1]
        st.metric(
            "Latest AUC Score",
            f"{latest_auc:.3f}",
            delta=f"{latest_auc - 0.54:.3f}",
            delta_color="normal"
        )
    
    with col2:
        latest_f1 = df['f1_score'].iloc[-1]
        st.metric(
            "Latest F1 Score",
            f"{latest_f1:.3f}",
            delta=f"{latest_f1 - 0.52:.3f}",
            delta_color="normal"
        )
    
    with col3:
        accuracy = (df['prediction_majority_vote'] == df['prediction_max_proba_class']).mean()
        st.metric(
            "Prediction Accuracy",
            f"{accuracy:.1%}",
            delta="2.1%",
            delta_color="normal"
        )
    
    with col4:
        latest_drift = df['data_drift_score'].iloc[-1]
        drift_status = "🟢 Normal" if latest_drift < 0.3 else "🟡 Warning"
        st.metric(
            "Data Drift Status",
            drift_status,
            delta=f"{latest_drift:.3f}",
            delta_color="inverse" if latest_drift > 0.3 else "normal"
        )
    
    # Performance over time
    st.subheader("📈 Performance Trends")
    
    # AUC and F1 Score trends
    fig_metrics = go.Figure()
    fig_metrics.add_trace(go.Scatter(
        x=df['date'],
        y=df['auc_score'],
        mode='lines+markers',
        name='AUC Score',
        line=dict(color='blue')
    ))
    fig_metrics.add_trace(go.Scatter(
        x=df['date'],
        y=df['f1_score'],
        mode='lines+markers',
        name='F1 Score',
        line=dict(color='red')
    ))
    
    # Add threshold lines
    fig_metrics.add_hline(y=0.52, line_dash="dash", line_color="orange", 
                         annotation_text="Alert Threshold (AUC=0.52)")
    fig_metrics.add_hline(y=0.50, line_dash="dash", line_color="red",
                         annotation_text="Alert Threshold (F1=0.50)")
    
    fig_metrics.update_layout(
        title="Model Performance Over Time",
        xaxis_title="Date",
        yaxis_title="Score",
        yaxis=dict(range=[0.45, 0.60])
    )
    
    st.plotly_chart(fig_metrics, use_container_width=True)
    
    # Prediction distribution
    st.subheader("📊 Prediction Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Probability distribution
        fig_prob = px.histogram(
            df, 
            x='prediction_mean_proba',
            nbins=20,
            title="Distribution of Prediction Probabilities",
            labels={'prediction_mean_proba': 'Probability', 'count': 'Frequency'}
        )
        st.plotly_chart(fig_prob, use_container_width=True)
    
    with col2:
        # Class distribution
        class_counts = df['prediction_majority_vote'].value_counts()
        fig_class = px.pie(
            values=class_counts.values,
            names=['Decrease (0)', 'Increase (1)'],
            title="Prediction Class Distribution"
        )
        st.plotly_chart(fig_class, use_container_width=True)

def show_prediction_examples():
    """Display example predictions."""
    st.header("📰 Live Prediction Examples")
    
    # News input
    st.subheader("🔮 Try Your Own Prediction")
    user_headline = st.text_input(
        "Enter a news headline:",
        placeholder="Federal Reserve announces policy changes..."
    )
    
    if user_headline and st.button("🎯 Predict Volatility"):
        # Simple rule-based prediction for demo
        headline = user_headline.lower()
        
        # Keywords that suggest high volatility
        volatile_keywords = ['surge', 'crash', 'soar', 'plummet', 'rally', 'decline', 'boom', 'crisis']
        prob = 0.5
        
        for keyword in volatile_keywords:
            if keyword in headline:
                prob += 0.15
        
        prob = max(0.1, min(0.9, prob + random.uniform(-0.1, 0.1)))
        prediction = 1 if prob > 0.5 else 0
        confidence = "High" if prob > 0.7 or prob < 0.3 else "Medium" if prob > 0.6 or prob < 0.4 else "Low"
        
        # Display result
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Volatility Probability", f"{prob:.1%}")
        with col2:
            st.metric("Prediction", "Increase" if prediction else "Decrease")
        with col3:
            st.metric("Confidence", confidence)
    
    # Example predictions
    st.subheader("📋 Recent Prediction Examples")
    
    examples_df = generate_news_examples()
    
    for idx, row in examples_df.iterrows():
        with st.expander(f"📰 {row['headline'][:60]}..."):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Probability", f"{row['probability']:.1%}")
            with col2:
                direction = "📈 Increase" if row['prediction'] else "📉 Decrease"
                st.metric("Prediction", direction)
            with col3:
                confidence_emoji = "🟢" if row['confidence'] == "High" else "🟡" if row['confidence'] == "Medium" else "🔴"
                st.metric("Confidence", f"{confidence_emoji} {row['confidence']}")
            
            st.write(f"**Full headline:** {row['headline']}")

def show_monitoring():
    """Display monitoring dashboard."""
    st.header("🔍 Model Monitoring Dashboard")
    
    df = generate_demo_data()
    
    # Data drift monitoring
    st.subheader("📊 Data Drift Detection")
    
    fig_drift = px.line(
        df,
        x='date',
        y='data_drift_score',
        title="Data Drift Score Over Time"
    )
    fig_drift.add_hline(y=0.3, line_dash="dash", line_color="red",
                       annotation_text="Alert Threshold (0.3)")
    fig_drift.update_layout(yaxis=dict(range=[0, 0.5]))
    
    st.plotly_chart(fig_drift, use_container_width=True)
    
    # Alert status
    st.subheader("🚨 Current Alert Status")
    
    latest_auc = df['auc_score'].iloc[-1]
    latest_f1 = df['f1_score'].iloc[-1]
    latest_drift = df['data_drift_score'].iloc[-1]
    
    alerts = []
    if latest_auc < 0.52:
        alerts.append("🔴 AUC Score below threshold")
    if latest_f1 < 0.50:
        alerts.append("🔴 F1 Score below threshold")
    if latest_drift > 0.3:
        alerts.append("🟡 Data drift detected")
    
    if alerts:
        st.warning("Active Alerts:")
        for alert in alerts:
            st.write(f"- {alert}")
    else:
        st.success("🟢 All systems normal - no active alerts")
    
    # Model versions
    st.subheader("🏷️ Model Version History")
    
    version_data = pd.DataFrame({
        'Version': ['v1.0', 'v0.9', 'v0.8'],
        'Deploy Date': ['2025-07-31', '2025-07-24', '2025-07-17'],
        'AUC Score': [0.54, 0.53, 0.51],
        'Status': ['🟢 Active', '📦 Archived', '📦 Archived']
    })
    
    st.dataframe(version_data, use_container_width=True)

def show_about():
    """Display information about the project."""
    st.header("ℹ️ About MLOps Volatility Predictor")
    
    st.markdown("""
    ### 🎯 Project Overview
    
    This is a comprehensive MLOps pipeline for predicting stock market volatility based on news headlines.
    The project demonstrates modern MLOps practices including:
    
    - **🔄 Automated ML Pipeline**: Prefect-orchestrated workflows
    - **📊 Experiment Tracking**: MLflow for model versioning and metrics
    - **🗄️ Data Storage**: LocalStack S3 for data and artifacts
    - **📈 Monitoring**: Evidently for drift detection and performance tracking
    - **🎨 Visualization**: Grafana dashboards with alerting
    - **🌐 API Service**: FastAPI for real-time predictions
    
    ### 🏗️ Architecture
    
    ```
    News Data → Preprocessing → Model Training → Batch Scoring
         ↓              ↓              ↓             ↓
    S3 Storage ← → MLflow Registry ← → Monitoring ← → Alerts
    ```
    
    ### 📊 Model Details
    
    - **Algorithm**: XGBoost Classifier
    - **Features**: TF-IDF text vectors + historical volatility metrics
    - **Target**: Binary volatility direction (increase/decrease)
    - **Performance**: ~54% AUC, ~52% F1-score (realistic for financial prediction)
    
    ### 🔧 Technology Stack
    
    - **Orchestration**: Prefect 2.x
    - **ML Tracking**: MLflow
    - **Storage**: LocalStack (S3), PostgreSQL
    - **Monitoring**: Evidently, Grafana
    - **API**: FastAPI, Streamlit
    - **Infrastructure**: Docker Compose
    
    ### 📱 Available Interfaces
    
    | Service | URL | Description |
    |---------|-----|-------------|
    | **MLflow** | http://localhost:5000 | Model registry & experiments |
    | **Prefect** | http://localhost:4200 | Workflow orchestration |
    | **Grafana** | http://localhost:3000 | Monitoring dashboards |
    | **API Docs** | http://localhost:8000/docs | REST API documentation |
    | **Adminer** | http://localhost:8080 | Database management |
    
    ### 🚀 Getting Started
    
    1. **Start Infrastructure**: `docker compose up -d`
    2. **Run Pipelines**: `make flows`
    3. **View Results**: Open the web interfaces above
    4. **Monitor Performance**: Check Grafana dashboards
    
    ### 📈 Key Features
    
    - ✅ **Real-time Predictions**: API endpoint for single headlines
    - ✅ **Batch Processing**: Daily volatility forecasts
    - ✅ **Model Monitoring**: Automated drift detection
    - ✅ **Performance Tracking**: Historical metrics and trends
    - ✅ **Alerting System**: Notifications for model degradation
    - ✅ **Version Control**: Model registry with staging/production
    
    ---
    
    **📧 Questions?** This is a demo MLOps project showcasing production-ready practices.
    """)

if __name__ == "__main__":
    main()
