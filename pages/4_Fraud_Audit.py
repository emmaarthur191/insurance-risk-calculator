import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import utils

# Initialize data and inject modern 3D styling
df, df_retail, df_corp, df_claims = utils.init_page("Prudential Anomaly & Fraud Risk Audit")

st.title("Prudential Anomaly and Fraud Risk Audit")
st.markdown("---")

st.markdown("""
To prevent premium leakage and coordinate fraud investigations, we deploy a hybrid fraud risk detection pipeline:
1. **Unsupervised Outlier Detection:** We use an **Isolation Forest** classifier (assuming ~1% contamination) across numerical features.
2. **Rule-Based Flags:** We apply programmatic business rules defined by underwriters:
    * **Claims Abuse Flag:** 3+ claims with High/Critical severity (+3 points).
    * **Early Churn Flag:** Claim filed in the first 3 months and policy now Cancelled (+2 points).
    * **Desk Anomaly Flag:** Software Engineer with low BMI (<18.5) and 1+ claims (+2 points).
    * **Isolation Outlier:** Flagged by the unsupervised Isolation Forest model (+1 point).
""")

# Compute Anomalies and Scorecard Indices
@st.cache_data
def run_anomaly_audit(dataframe):
    # Stratified sampling to 20,000 rows to ensure instant computation and prevent server freeze
    if len(dataframe) > 20000:
        dataframe = dataframe.sample(20000, random_state=42).copy()
    else:
        dataframe = dataframe.copy()
        
    # Standardize numeric columns for Isolation Forest
    anomaly_features = ['Age', 'BMI', 'Monthly_Income_GHS', 'Premium_GHS', 'Claim_Frequency', 'Tenure_Months', 'Dependents']
    scaler = StandardScaler()
    X_anomaly = scaler.fit_transform(dataframe[anomaly_features])
    
    # Fit Isolation Forest
    iso_forest = IsolationForest(contamination=0.01, random_state=42)
    dataframe['Is_Outlier'] = iso_forest.fit_predict(X_anomaly)
    
    # Calculate rule flags
    dataframe['Flag_Freq_Severity_Abuse'] = (
        (dataframe['Claim_Frequency'] >= 3) & 
        (dataframe['Claim_Severity'].isin(['High', 'Critical']))
    ).astype(int)
    
    dataframe['Flag_Early_Churn_Claims'] = (
        (dataframe['Tenure_Months'] <= 3) & 
        (dataframe['Claim_Frequency'] >= 1) & 
        (dataframe['Policy_Status'] == 'Cancelled')
    ).astype(int)
    
    dataframe['Flag_Underweight_Desk_Anomaly'] = (
        (dataframe['Occupation'] == 'Software Engineer') & 
        (dataframe['BMI'] < 18.5) & 
        (dataframe['Claim_Frequency'] >= 1)
    ).astype(int)
    
    # Combine into Claims Abuse Risk Index
    dataframe['Claims_Abuse_Index'] = (
        dataframe['Flag_Freq_Severity_Abuse'] * 3 + 
        dataframe['Flag_Early_Churn_Claims'] * 2 + 
        dataframe['Flag_Underweight_Desk_Anomaly'] * 2 + 
        (dataframe['Is_Outlier'] == -1).astype(int) * 1
    )
    
    return dataframe

# Cache the anomaly data
with st.spinner("Analyzing portfolio anomalies and fraud indexes..."):
    df_anomaly = run_anomaly_audit(df)

# Filter dataset to suspicious only
suspicious_df = df_anomaly[df_anomaly['Claims_Abuse_Index'] > 0].copy()

# Add KPIs for anomalies
total_outliers = (df_anomaly['Is_Outlier'] == -1).sum()
total_suspicious = len(suspicious_df)
avg_index = suspicious_df['Claims_Abuse_Index'].mean() if len(suspicious_df) > 0 else 0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Isolation Forest Outliers</div>
        <div class="metric-value">{total_outliers:,}</div>
    </div>
    """, unsafe_allow_html=True)
    
with col2:
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Fraud-Risk Flagged Accounts</div>
        <div class="metric-value">{total_suspicious:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Average Claims Abuse Index</div>
        <div class="metric-value">{avg_index:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Filter Sidebar for Anomaly table
st.subheader("Interactive Suspicious Accounts Audit Table")
st.markdown("Use the filters below to isolate suspicious accounts by region and occupation.")

col_f1, col_f2 = st.columns(2)

with col_f1:
    region_filter = st.multiselect("Filter by Region", options=sorted(df_anomaly['Region'].dropna().unique()))
with col_f2:
    occ_filter = st.multiselect("Filter by Occupation", options=sorted(df_anomaly['Occupation'].dropna().unique()))

# Apply filters
filtered_suspicious = suspicious_df.copy()
if region_filter:
    filtered_suspicious = filtered_suspicious[filtered_suspicious['Region'].isin(region_filter)]
if occ_filter:
    filtered_suspicious = filtered_suspicious[filtered_suspicious['Occupation'].isin(occ_filter)]

# Columns to show in Table
cols_show = [
    'Full_Name', 'Occupation', 'Region', 'Product_Applied', 'Monthly_Income_GHS', 
    'Claim_Frequency', 'Claim_Severity', 'Tenure_Months', 'Policy_Status', 'Claims_Abuse_Index'
]

# Display table
st.dataframe(
    filtered_suspicious[cols_show].sort_values(by='Claims_Abuse_Index', ascending=False).head(100),
    use_container_width=True
)

st.markdown("---")

# Visualizing where anomalies are concentrated
st.subheader("Fraud Risk Concentrations")

col_c1, col_c2 = st.columns(2)

with col_c1:
    st.markdown("#### Suspicious Accounts by Occupation")
    occ_counts = suspicious_df.groupby('Occupation').size().reset_index(name='Flagged Accounts').sort_values('Flagged Accounts')
    fig_occ = px.bar(
        occ_counts, 
        y='Occupation', 
        x='Flagged Accounts',
        orientation='h',
        color='Flagged Accounts',
        color_continuous_scale=["#FFFFFF", "#DC143C"],
        title="Number of Flagged Accounts by Occupation"
    )
    fig_occ.update_layout(
        plot_bgcolor="#14141A",
        paper_bgcolor="#08080A",
        font_color="#F5F5F7",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_occ, use_container_width=True)

with col_c2:
    st.markdown("#### Claims Abuse Index Distribution")
    fig_hist = px.histogram(
        suspicious_df,
        x='Claims_Abuse_Index',
        nbins=6,
        color='Claims_Abuse_Index',
        color_discrete_sequence=["#DC143C", "#8B0000", "#FFFFFF", "#A5AAB5"],
        title="Distribution of Claims Abuse Index score"
    )
    fig_hist.update_layout(
        plot_bgcolor="#14141A",
        paper_bgcolor="#08080A",
        font_color="#F5F5F7",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_hist, use_container_width=True)
