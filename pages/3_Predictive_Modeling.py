# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier
import utils

# Initialize data and inject modern 3D styling
df, df_retail, df_corp, df_claims = utils.init_page("Prudential Machine Learning Classification")

# SEO Headers
st.markdown("""
<meta name="description" content="Prudential Life Underwriting Predictive Modeling & Scorecard Portal. Perform real-time manual risk calculation or batch score applicants using collective risk-calibrated models.">
<title>Prudential Underwriting Predictive Modeling & Scorecard</title>
""", unsafe_allow_html=True)

st.title("Prudential Underwriting Predictive Modeling & Scorecard")
st.markdown("---")

st.markdown("""
This consolidated portal brings together the machine learning predictive models and the points-based underwriting risk scorecard.
You can analyze model performance, score individual applicants in real-time, or process bulk rosters.
""")

# Portfolio Segment Selection
portfolio_type = st.radio("Select Portfolio Segment", options=["Retail", "Corporate"])

# Cache training and model outputs
@st.cache_resource
def train_and_evaluate_models(port_type):
    if port_type == "Retail":
        dataframe = st.session_state["df_retail"]
    else:
        dataframe = st.session_state["df_corp"]

    # Sample dataframe to 20,000 rows for instant dashboard rendering (Retail only)
    if len(dataframe) > 20000:
        dataframe = dataframe.groupby('Risk_Category', group_keys=False).apply(lambda x: x.sample(min(len(x), 5000), random_state=42))

    # ── Match notebook: ALL numeric features, drop target + score + gender ──
    drop_cols = [
        'Risk_Category_encoded', 'Risk_Score', 'Gender_encoded',
        'Predicted_Freq', 'Predicted_Sev', 'Expected_Loss', 'Sev_Amount',
        'Risk_Loading', 'Recommended_Premium', 'Pricing_Deficit'
    ]
    available_drops = [c for c in drop_cols if c in dataframe.columns]
    X_ml = dataframe.select_dtypes(include=[np.number]).drop(columns=available_drops)
    y_ml = dataframe['Risk_Category_encoded']

    # Align indices (drop NaN rows)
    valid_idx = X_ml.dropna().index.intersection(y_ml.dropna().index)
    X_ml = X_ml.loc[valid_idx]
    y_ml = y_ml.loc[valid_idx]

    X_train, X_temp, y_train, y_temp = train_test_split(
        X_ml, y_ml, test_size=0.3, random_state=42, stratify=y_ml
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_train_bal, y_train_bal = smote.fit_resample(X_train_scaled, y_train)
    except ImportError:
        X_train_bal, y_train_bal = X_train_scaled, y_train
        
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric="mlogloss"
    )
    xgb.fit(X_train_bal, y_train_bal)
    acc_xgb = xgb.score(X_val_scaled, y_val)
    
    importances = pd.DataFrame({
        'Feature': X_ml.columns,
        'Importance': xgb.feature_importances_
    }).sort_values('Importance', ascending=False).head(15)
    
    risk_labels = ["Low", "Medium", "High", "Critical"]
    y_pred_xgb = xgb.predict(X_val_scaled)
    cm = confusion_matrix(y_val, y_pred_xgb)
    report = classification_report(y_val, y_pred_xgb, target_names=risk_labels)

    # Store boxcox lambda for individual predictions
    try:
        from scipy.stats import boxcox as _bc
        _, bc_lam = _bc(dataframe['Claim_Frequency'].dropna() + 1)
    except Exception:
        bc_lam = 0.0
    
    return {
        "accuracy": acc_xgb,
        "xgb_cm": cm,
        "xgb_report": report,
        "xgb_importance": importances,
        "xgb_model": xgb,
        "scaler": scaler,
        "features": list(X_ml.columns),
        "boxcox_lambda": bc_lam
    }

# Run the training pipeline
target_df = df_retail if portfolio_type == "Retail" else df_corp
with st.spinner(f"Training Classifiers on Balanced {portfolio_type} Dataset..."):
    results = train_and_evaluate_models(portfolio_type)

# Setup tabs
tab_perf, tab_indiv, tab_batch = st.tabs([
    "Model Performance & Analytics",
    "Individual Underwriting Calculator",
    "Batch Scoring Portal"
])

# --- Local Scorecard Helper Functions ---
def compute_scorecard_score(row):
    score = 0
    # Age bands (primary driver)
    if row['Age'] <= 30:
        score += 5
    elif 31 <= row['Age'] <= 45:
        score += 12
    elif 46 <= row['Age'] <= 60:
        score += 20
    else:
        score += 28
        
    # BMI categories
    if row['BMI'] < 18.5:
        score += 0
    elif 18.5 <= row['BMI'] <= 24.9:
        score += 0
    elif 25 <= row['BMI'] <= 29.9:
        score += 8
    else:
        score += 12
        
    # Smoking
    if row['Smoker'] == 'Yes':
        score += 5
        
    # Claim Frequency
    if row['Claim_Frequency'] == 0:
        score += 0
    elif row['Claim_Frequency'] == 1:
        score += 12
    elif row['Claim_Frequency'] == 2:
        score += 22
    elif row['Claim_Frequency'] == 3:
        score += 27
    elif row['Claim_Frequency'] >= 4:
        score += 32
        
    # Claim Severity
    severity_points = {'None': 0, 'Low': 10, 'Medium': 20, 'High': 25, 'Critical': 30}
    score += severity_points.get(row['Claim_Severity'], 0)
    
    # Premium band
    if row['Premium_GHS'] < 300:
        score += 5
    elif 300 <= row['Premium_GHS'] <= 700:
        score += 10
    else:
        score += 20
        
    # Monthly Income
    if row['Monthly_Income_GHS'] < 3000:
        score += 10
    elif 3000 <= row['Monthly_Income_GHS'] <= 8000:
        score += 5
        
    # Dependents
    if row['Dependents'] in [2, 3]:
        score += 5
    elif row['Dependents'] >= 4:
        score += 10
        
    return score

def assign_scorecard_category(score):
    if score <= 35:
        return 'Low Risk'
    elif 36 <= score <= 65:
        return 'Medium Risk'
    elif 66 <= score <= 90:
        return 'High Risk'
    else:
        return 'Critical Risk'


# --- TAB 1: MODEL PERFORMANCE & ANALYTICS ---
with tab_perf:
    st.subheader("XGBoost Validation Accuracy")
    st.metric(
        label="XGBoost Validation Accuracy",
        value=f"{results['accuracy']*100:.2f}%",
        delta="Best Model Performer",
        delta_color="normal"
    )
    
    col_diag_left, col_diag_right = st.columns(2)
    
    with col_diag_left:
        st.markdown("#### Confusion Matrix")
        risk_labels = ["Low", "Medium", "High", "Critical"]
        fig_cm = px.imshow(
            results["xgb_cm"],
            labels=dict(x="Predicted Risk", y="Actual Risk", color="Count"),
            x=risk_labels,
            y=risk_labels,
            text_auto=True,
            color_continuous_scale=["#000000", "#DC143C", "#FFFFFF"]
        )
        fig_cm.update_layout(
            plot_bgcolor="#14141A",
            paper_bgcolor="#08080A",
            font_color="#F5F5F7",
            height=380
        )
        st.plotly_chart(fig_cm, use_container_width=True)
        
    with col_diag_right:
        st.markdown("#### Classification Report")
        st.text(results["xgb_report"])
        st.markdown("""
        <div class="premium-card">
            <h4 style="color: #DC143C;">Actuarial Insight</h4>
            <p style="color: #A5AAB5; font-size: 14px;">
                XGBoost classifies into 4 risk tiers (Low / Medium / High / Critical) using all numeric features
                with SMOTE-balanced training, matching the notebook pipeline exactly.
                Gender is excluded to ensure fair, non-discriminatory underwriting.
                The model uses <code>select_dtypes(include=[np.number])</code> for feature selection,
                dropping only the target (<i>Risk_Category_encoded</i>), the scorecard (<i>Risk_Score</i>),
                and derived actuarial outputs to prevent data leakage.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    # XGBoost Feature Importance
    st.subheader("Feature Importance Leaderboard")
    fig_imp = px.bar(
        results["xgb_importance"].sort_values("Importance", ascending=True),
        y="Feature",
        x="Importance",
        orientation="h",
        color="Importance",
        color_continuous_scale=["#FFFFFF", "#DC143C"],
        title="Top 15 Most Influential Features (XGBoost Classifier)"
    )
    fig_imp.update_layout(
        plot_bgcolor="#14141A",
        paper_bgcolor="#08080A",
        font_color="#F5F5F7",
        height=450,
        showlegend=False
    )
    st.plotly_chart(fig_imp, use_container_width=True)


# --- TAB 2: INDIVIDUAL UNDERWRITING CALCULATOR ---
with tab_indiv:
    st.subheader("Individual Risk Assessment Calculator")
    
    col_sim_in, col_sim_out = st.columns([3, 2])
    
    with col_sim_in:
        st.markdown("#### Policyholder Input Parameters")
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            sim_age = st.number_input("Age (Years)", min_value=18, max_value=85, value=35, key="calc_age")
            sim_bmi = st.number_input("BMI (kg/m²)", min_value=10.0, max_value=60.0, value=24.5, step=0.1, key="calc_bmi")
            sim_smoker = st.selectbox("Smoker Status", ["No", "Yes"], index=0, key="calc_smoker")
            sim_dependents = st.number_input("Dependents", min_value=0, max_value=15, value=1, step=1, key="calc_dependents")
            
        with col_s2:
            sim_income = st.number_input("Monthly Income (GHS)", min_value=500.0, max_value=150000.0, value=5000.0, step=100.0, key="calc_income")
            proposed_premium = st.number_input("Proposed Monthly Premium (GHS)", min_value=10.0, max_value=10000.0, value=400.0, step=10.0, key="calc_premium")
            claim_frequency = st.number_input("Claim Frequency (Past 12m)", min_value=0, max_value=20, value=0, step=1, key="calc_freq")
            claim_severity = st.selectbox("Claim Severity (Highest Claim)", ["None", "Low", "Medium", "High", "Critical"], index=0, key="calc_sev")
            sim_tenure = st.number_input("Tenure (Months)", min_value=0, max_value=120, value=12, step=1, key="calc_tenure")
            
    # Calculate actuarial scorecard
    age_scaled = (sim_age - target_df['Age'].mean()) / target_df['Age'].std()
    bmi_scaled = (sim_bmi - target_df['BMI'].mean()) / target_df['BMI'].std()
    dependents_scaled = (sim_dependents - target_df['Dependents'].mean()) / target_df['Dependents'].std()
    income_thousands = sim_income / 1000.0
    smoker_encoded = 1 if sim_smoker == "Yes" else 0
    
    # Load GLM models & loadings map
    poisson_model, gamma_model = utils.get_scorecard_models(portfolio_type)
    loadings_map = utils.get_loadings_map(portfolio_type)
    
    # Build full feature row matching notebook's select_dtypes numeric columns
    sev_encoded = {'None': 0, 'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}.get(claim_severity, 0)
    try:
        from scipy.special import boxcox1p
        cf_boxcox = boxcox1p(claim_frequency, results.get('boxcox_lambda', 0.0))
    except Exception:
        cf_boxcox = np.log1p(claim_frequency)

    sim_row = {
        'Age': sim_age,
        'BMI': sim_bmi,
        'Smoker_encoded': smoker_encoded,
        'Claim_Frequency': claim_frequency,
        'Claim_Severity_encoded': sev_encoded,
        'Premium_GHS': proposed_premium,
        'Monthly_Income_GHS': sim_income,
        'Dependents': sim_dependents,
        'Income_Thousands': income_thousands,
        'Income_per_Dependent': sim_income / (sim_dependents + 1),
        'Age_scaled': age_scaled,
        'BMI_scaled': bmi_scaled,
        'Dependents_scaled': dependents_scaled,
        'Is_Obese': int(sim_bmi >= 30),
        'Premium_Sqrt': np.sqrt(proposed_premium),
        'Monthly_Income_GHS_log': np.log1p(sim_income),
        'Claim_Frequency_BoxCox': cf_boxcox,
        'Tenure_Months': sim_tenure,
    }

    # Build DataFrame with only the features the model was trained on
    sim_df = pd.DataFrame([sim_row])
    for feat in results["features"]:
        if feat not in sim_df.columns:
            sim_df[feat] = 0.0
    X_sim = sim_df[results["features"]]
    X_sim_scaled = results["scaler"].transform(X_sim)
    pred_class_idx = int(results["xgb_model"].predict(X_sim_scaled)[0])
    pred_probs = results["xgb_model"].predict_proba(X_sim_scaled)[0]
    
    ml_risk_tiers = {0: "Low Risk", 1: "Medium Risk", 2: "High Risk", 3: "Critical Risk"}
    pred_tier = ml_risk_tiers.get(pred_class_idx, "Unknown")
    tier_colors = {"Low Risk": "#FFFFFF", "Medium Risk": "#A5AAB5", "High Risk": "#DC143C", "Critical Risk": "#8B0000"}
    pred_color = tier_colors.get(pred_tier, "#FFFFFF")
    
    # Actuarial Calculations
    predicted_freq = poisson_model.predict(X_sim).clip(0, 10).values[0]
    predicted_sev = gamma_model.predict(X_sim).clip(5000, 150000).values[0]
    expected_loss = predicted_freq * predicted_sev
    
    row_dict = {
        'Age': sim_age,
        'BMI': sim_bmi,
        'Smoker': sim_smoker,
        'Claim_Frequency': claim_frequency,
        'Claim_Severity': claim_severity,
        'Premium_GHS': proposed_premium,
        'Monthly_Income_GHS': sim_income,
        'Dependents': sim_dependents
    }
    
    score = compute_scorecard_score(row_dict)
    risk_category = assign_scorecard_category(score)
    loading = loadings_map.get(risk_category, 0.05)
    
    recommended_annual = expected_loss * (1.0 + loading) + 50.0
    proposed_annual = proposed_premium * 12
    deficit = recommended_annual - proposed_annual
    
    risk_colors = {
        "Low Risk": "#FFFFFF",
        "Medium Risk": "#A5AAB5",
        "High Risk": "#DC143C",
        "Critical Risk": "#8B0000"
    }
    risk_color = risk_colors.get(risk_category, "#FFFFFF")
    
    # Determine client type: New Enrollee vs Renewal
    is_new_enrollee = (claim_frequency == 0 and claim_severity == "None")
    
    with col_sim_out:
        st.markdown("#### Actuarial & Machine Learning Outputs")
        
        # Client Type Badge
        if is_new_enrollee:
            badge_color = "#3498db"
            badge_label = "NEW ENROLLEE"
            final_tier = risk_category
            final_color = risk_color
            badge_note = "Scorecard-based underwriting (no claims history)"
        else:
            badge_color = "#e67e22"
            badge_label = "RENEWAL / EXPERIENCE-RATED"
            final_tier = pred_tier
            final_color = pred_color
            badge_note = "XGBoost ML prediction (claims history available)"
        
        st.markdown(f"""
        <div class="premium-card" style="border-left: 5px solid {badge_color}; padding: 10px 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="background: {badge_color}; color: #FFF; padding: 3px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">{badge_label}</span>
                <span style="color: #A5AAB5; font-size: 0.85rem;">{badge_note}</span>
            </div>
            <div class="metric-label" style="margin-top: 8px;">Final Underwriting Decision</div>
            <div class="metric-value" style="color: {final_color}; font-size: 2rem;">{final_tier}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Risk Scorecard Card
        st.markdown(f"""
        <div class="premium-card" style="border-left: 5px solid {risk_color};">
            <div class="metric-label">Actuarial Risk Tier (Scorecard)</div>
            <div class="metric-value" style="color: {risk_color};">{risk_category}</div>
            <div style="font-size: 0.9rem; color: #A5AAB5; margin-top: 5px;">
                Scorecard Points: <b>{score}</b> | Risk Loading: <b>{loading*100:.1f}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ML Prediction Output Card
        if is_new_enrollee:
            st.markdown(f"""
            <div class="premium-card" style="border-left: 5px solid #555; opacity: 0.6;">
                <div class="metric-label">XGBoost ML Risk Classification</div>
                <div class="metric-value" style="color: #555; font-size: 1.4rem;">N/A — New Enrollee</div>
                <div style="font-size: 0.85rem; color: #777; margin-top: 5px;">
                    ML model requires claims history. Scorecard tier is used instead.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="premium-card" style="border-left: 5px solid {pred_color};">
                <div class="metric-label">XGBoost ML Risk Classification</div>
                <div class="metric-value" style="color: {pred_color}; font-size: 1.8rem;">{pred_tier}</div>
                <div style="font-size: 0.9rem; color: #A5AAB5; margin-top: 5px;">
                    Confidence Probability: <b>{pred_probs[pred_class_idx]*100:.1f}%</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Deficit / Surplus Card
        deficit_status = "Deficit" if deficit > 0 else "Surplus"
        deficit_color = "#DC143C" if deficit > 0 else "#2ecc71"
        st.markdown(f"""
        <div class="premium-card" style="border-left: 5px solid {deficit_color};">
            <div class="metric-label">Pricing Gap ({deficit_status})</div>
            <div class="metric-value" style="color: {deficit_color};">GHS {abs(deficit):,.2f}</div>
            <div style="font-size: 0.85rem; color: #A5AAB5; margin-top: 5px;">
                Actuarial Premium: <b>GHS {recommended_annual:,.2f}/yr</b><br>
                Proposed Annualized: <b>GHS {proposed_annual:,.2f}/yr</b>
            </div>
        </div>
        """, unsafe_allow_html=True)


# --- TAB 3: BATCH SCORING PORTAL ---
with tab_batch:
    st.subheader("Batch Upload & Scoring Portal")
    st.markdown("""
    Execute bulk underwriting evaluations by uploading a policy roster CSV or Excel sheet.
    """)
    
    uploaded_file = st.file_uploader("Upload CSV or Excel roster", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
                
            st.success("File uploaded successfully!")
            st.write("Preview of original roster (First 5 rows):")
            st.dataframe(df_upload.head())
            
            # Map Column Selectboxes
            st.markdown("#### Map Custom Columns to Actuarial Parameters")
            cols = list(df_upload.columns)
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                map_age = st.selectbox("Age Column", cols, index=cols.index("Age") if "Age" in cols else 0)
                map_bmi = st.selectbox("BMI Column", cols, index=cols.index("BMI") if "BMI" in cols else 0)
                map_smoker = st.selectbox("Smoker Column", cols, index=cols.index("Smoker") if "Smoker" in cols else 0)
                map_dependents = st.selectbox("Dependents Column", cols, index=cols.index("Dependents") if "Dependents" in cols else 0)
                
            with col_m2:
                map_income = st.selectbox("Monthly Income Column", cols, index=cols.index("Monthly_Income_GHS") if "Monthly_Income_GHS" in cols else 0)
                map_premium = st.selectbox("Premium Column", cols, index=cols.index("Premium_GHS") if "Premium_GHS" in cols else 0)
                map_freq = st.selectbox("Claim Frequency Column", cols, index=cols.index("Claim_Frequency") if "Claim_Frequency" in cols else 0)
                map_sev = st.selectbox("Claim Severity Column", cols, index=cols.index("Claim_Severity") if "Claim_Severity" in cols else 0)
                
            if st.button("Score Roster (Run Batch Prediction)"):
                df_mapped = pd.DataFrame()
                df_mapped['Age'] = df_upload[map_age].astype(int)
                df_mapped['BMI'] = df_upload[map_bmi].astype(float)
                df_mapped['Smoker'] = df_upload[map_smoker].astype(str)
                df_mapped['Monthly_Income_GHS'] = df_upload[map_income].astype(float)
                df_mapped['Premium_GHS'] = df_upload[map_premium].astype(float)
                df_mapped['Claim_Frequency'] = df_upload[map_freq].astype(int)
                df_mapped['Claim_Severity'] = df_upload[map_sev].astype(str)
                df_mapped['Dependents'] = df_upload[map_dependents].astype(int)
                
                # Z-scale
                df_mapped['Age_scaled'] = (df_mapped['Age'] - target_df['Age'].mean()) / target_df['Age'].std()
                df_mapped['BMI_scaled'] = (df_mapped['BMI'] - target_df['BMI'].mean()) / target_df['BMI'].std()
                df_mapped['Dependents_scaled'] = (df_mapped['Dependents'] - target_df['Dependents'].mean()) / target_df['Dependents'].std()
                df_mapped['Income_Thousands'] = df_mapped['Monthly_Income_GHS'] / 1000.0
                df_mapped['Smoker_encoded'] = df_mapped['Smoker'].map({'Yes': 1, 'No': 0}).fillna(0).astype(int)
                df_mapped['Income_per_Dependent'] = df_mapped['Monthly_Income_GHS'] / (df_mapped['Dependents'] + 1)
                
                # Predict models
                poisson_model, gamma_model = utils.get_scorecard_models(portfolio_type)
                loadings_map = utils.get_loadings_map(portfolio_type)
                
                # Expected loss
                df_mapped['Predicted_Freq'] = poisson_model.predict(df_mapped).clip(0, 10)
                
                sev_map = {'None': 0, 'Low': 7500, 'Medium': 17500, 'High': 37500, 'Critical': 62500}
                df_mapped['Sev_Amount'] = df_mapped['Claim_Severity'].map(sev_map).fillna(0)
                df_mapped['Predicted_Sev'] = gamma_model.predict(df_mapped).clip(5000, 150000)
                df_mapped['Expected_Loss'] = df_mapped['Predicted_Freq'] * df_mapped['Predicted_Sev']
                
                # Scorecard category and points
                df_mapped['Risk_Score'] = df_mapped.apply(compute_scorecard_score, axis=1)
                df_mapped['Risk_Category'] = df_mapped['Risk_Score'].apply(assign_scorecard_category)
                df_mapped['Risk_Loading'] = df_mapped['Risk_Category'].map(loadings_map)
                
                df_mapped['Recommended_Premium_Annual'] = df_mapped['Expected_Loss'] * (1.0 + df_mapped['Risk_Loading']) + 50.0
                df_mapped['Proposed_Premium_Annual'] = df_mapped['Premium_GHS'] * 12
                df_mapped['Annual_Pricing_Deficit'] = df_mapped['Recommended_Premium_Annual'] - df_mapped['Proposed_Premium_Annual']
                
                # Batch engineered features for ML
                df_mapped['Claim_Severity_encoded'] = df_mapped['Claim_Severity'].map(
                    {'None': 0, 'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}).fillna(0).astype(int)
                df_mapped['Is_Obese'] = (df_mapped['BMI'] >= 30).astype(int)
                df_mapped['Premium_Sqrt'] = np.sqrt(df_mapped['Premium_GHS'])
                df_mapped['Monthly_Income_GHS_log'] = np.log1p(df_mapped['Monthly_Income_GHS'])
                try:
                    from scipy.special import boxcox1p as _bc1p
                    df_mapped['Claim_Frequency_BoxCox'] = _bc1p(df_mapped['Claim_Frequency'], results.get('boxcox_lambda', 0.0))
                except Exception:
                    df_mapped['Claim_Frequency_BoxCox'] = np.log1p(df_mapped['Claim_Frequency'])
                if 'Tenure_Months' not in df_mapped.columns:
                    df_mapped['Tenure_Months'] = 0

                # Ensure all model features exist, fill missing with 0
                for feat in results["features"]:
                    if feat not in df_mapped.columns:
                        df_mapped[feat] = 0.0

                # ML Classifier (4-class)
                X_mapped = df_mapped[results["features"]]
                X_mapped_scaled = results["scaler"].transform(X_mapped)
                
                ml_preds = results["xgb_model"].predict(X_mapped_scaled)
                ml_proba = results["xgb_model"].predict_proba(X_mapped_scaled)
                df_mapped['ML_Predicted_Class'] = ml_preds
                df_mapped['ML_Confidence'] = ml_proba.max(axis=1)
                ml_tier_map = {0: 'Low Risk', 1: 'Medium Risk', 2: 'High Risk', 3: 'Critical Risk'}
                df_mapped['ML_Risk_Category'] = df_mapped['ML_Predicted_Class'].map(ml_tier_map)
                
                # Hybrid: New enrollees use Scorecard, renewals use ML
                df_mapped['Client_Type'] = np.where(
                    (df_mapped['Claim_Frequency'] == 0) & (df_mapped['Claim_Severity'] == 'None'),
                    'New Enrollee', 'Renewal'
                )
                df_mapped['Final_Risk_Tier'] = np.where(
                    df_mapped['Client_Type'] == 'New Enrollee',
                    df_mapped['Risk_Category'],
                    df_mapped['ML_Risk_Category']
                )
                
                # Totals
                billed_total = df_mapped['Proposed_Premium_Annual'].sum()
                recommended_total = df_mapped['Recommended_Premium_Annual'].sum()
                deficit_total = recommended_total - billed_total
                
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    st.metric("Total Proposed Premium (Annualized)", f"GHS {billed_total:,.2f}")
                with col_b2:
                    st.metric("Total Actuarial Recommended Premium", f"GHS {recommended_total:,.2f}")
                with col_b3:
                    st.metric("Portfolio Pricing Deficit / Surplus", f"GHS {deficit_total:,.2f}",
                              delta="Deficit" if deficit_total > 0 else "Surplus", delta_color="inverse")
                
                # Charts
                st.markdown("#### Batch Analytics Charts")
                col_ch1, col_ch2 = st.columns(2)
                
                with col_ch1:
                    cat_counts = df_mapped['Risk_Category'].value_counts().reset_index()
                    cat_counts.columns = ['Risk Tier', 'Count']
                    fig_pie = px.pie(
                        cat_counts,
                        names='Risk Tier',
                        values='Count',
                        title="Scorecard Risk Category Distribution",
                        color='Risk Tier',
                        color_discrete_map={
                            "Low Risk": "#FFFFFF",
                            "Medium Risk": "#A5AAB5",
                            "High Risk": "#DC143C",
                            "Critical Risk": "#8B0000"
                        }
                    )
                    fig_pie.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7")
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                with col_ch2:
                    fig_hist = px.histogram(
                        df_mapped,
                        x='Annual_Pricing_Deficit',
                        nbins=30,
                        title="Distribution of Pricing Deficits (GHS)",
                        color_discrete_sequence=["#DC143C"]
                    )
                    fig_hist.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7")
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                # Export scored dataset
                df_export = df_upload.copy()
                df_export['Risk_Score'] = df_mapped['Risk_Score']
                df_export['Risk_Category'] = df_mapped['Risk_Category']
                df_export['Risk_Loading'] = df_mapped['Risk_Loading']
                df_export['Recommended_Premium_Annual'] = df_mapped['Recommended_Premium_Annual']
                df_export['Annual_Pricing_Deficit'] = df_mapped['Annual_Pricing_Deficit']
                df_export['ML_Confidence'] = df_mapped['ML_Confidence']
                df_export['ML_Risk_Category'] = df_mapped['ML_Risk_Category']
                df_export['Client_Type'] = df_mapped['Client_Type']
                df_export['Final_Risk_Tier'] = df_mapped['Final_Risk_Tier']
                
                st.markdown("#### Scored Dataset Preview")
                st.dataframe(df_export.head(100))
                
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Combined Scored CSV File",
                    data=csv,
                    file_name="scored_underwriting_roster.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"An error occurred while scoring the batch file: {e}")
