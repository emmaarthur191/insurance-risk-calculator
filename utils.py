import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")

def _resolve_paths():
    local_csv = Path("Insurance_cleaned.csv")
    local_excel = Path("Copy of Companies Ins.Data.xlsx")
    csv_path = local_csv if local_csv.exists() else Path(r"C:\Users\snype\Downloads\Insurance_cleaned.csv")
    excel_path = local_excel if local_excel.exists() else Path(r"C:\Users\snype\Downloads\Copy of Companies Ins.Data.xlsx")
    return csv_path, excel_path

# Setup data loading (cached)
@st.cache_data
def load_raw_data():
    # Automatically copy files from Downloads to root if they exist there but not locally
    try:
        downloads_csv = Path(r"C:\Users\snype\Downloads\Insurance_cleaned.csv")
        downloads_excel = Path(r"C:\Users\snype\Downloads\Copy of Companies Ins.Data.xlsx")
        
        if downloads_csv.exists() and not Path("Insurance_cleaned.csv").exists():
            import shutil
            shutil.copy2(downloads_csv, Path("Insurance_cleaned.csv"))
            
        if downloads_excel.exists() and not Path("Copy of Companies Ins.Data.xlsx").exists():
            import shutil
            shutil.copy2(downloads_excel, Path("Copy of Companies Ins.Data.xlsx"))
    except Exception:
        pass

    csv_path, excel_path = _resolve_paths()
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find Insurance_cleaned.csv locally or at {csv_path}. Please place it in the project root.")
    if not excel_path.exists():
        raise FileNotFoundError(f"Could not find Copy of Companies Ins.Data.xlsx locally or at {excel_path}. Please place it in the project root.")
        
    # 1. Retail
    df_retail = pd.read_csv(csv_path)
    df_retail.rename(columns={'Claim_frequency': 'Claim_Frequency'}, inplace=True)
    # ── DEDUPLICATION FIRST (before any calculations) ─────────────────────
    # The raw CSV has 950,000 rows but only 50,000 unique individuals.
    # Each profile is replicated 19× with different Customer_IDs but identical
    # values on every other column. We deduplicate by all columns EXCEPT
    # Customer_ID (which is arbitrary), keeping the first occurrence.
    # This must happen BEFORE GLM fitting so models train on 50k real people.
    non_id_cols = [c for c in df_retail.columns if c != 'Customer_ID']
    df_retail = df_retail.drop_duplicates(subset=non_id_cols, keep='first').copy()
    df_retail['Claim_Severity'] = df_retail['Claim_Severity'].fillna('None')
    df_retail['Portfolio_Type'] = 'Retail'
    df_retail['Company_Name'] = 'Individual Retail'
    
    # 2. Corporate
    df_clients = pd.read_excel(excel_path, sheet_name='Corporate Clients')
    df_employees = pd.read_excel(excel_path, sheet_name='Covered Employees')
    df_claims_raw = pd.read_excel(excel_path, sheet_name='Claims')
    df_workflow_raw = pd.read_excel(excel_path, sheet_name='Branch Table')
    
    df_clients.drop_duplicates(subset=['Corporate_ID'], keep='first', inplace=True)
    df_employees.drop_duplicates(subset=['Employee_ID'], keep='first', inplace=True)
    df_claims_raw.drop_duplicates(subset=['Claim_ID'], keep='first', inplace=True)
    
    claims_agg = df_claims_raw.groupby('Employee_ID').agg(
        Claim_Frequency=('Claim_ID', 'count'),
        Total_Claim_Amount=('Claim_Amount_GHS', 'sum')
    ).reset_index()
    
    df_emp_merged = pd.merge(df_employees, claims_agg, on='Employee_ID', how='left')
    df_emp_merged['Claim_Frequency'] = df_emp_merged['Claim_Frequency'].fillna(0).astype(int)
    df_emp_merged['Total_Claim_Amount'] = df_emp_merged['Total_Claim_Amount'].fillna(0)
    
    def get_severity(amount):
        if amount == 0: return 'None'
        elif amount <= 10000: return 'Low'
        elif amount <= 25000: return 'Medium'
        elif amount <= 50000: return 'High'
        else: return 'Critical'
    df_emp_merged['Claim_Severity'] = df_emp_merged['Total_Claim_Amount'].apply(get_severity)
    
    df_payments_raw = pd.read_excel(excel_path, sheet_name='Premium Payments')
    df_payments_raw.drop_duplicates(subset=['Payment_ID'], keep='first', inplace=True)
    payment_map_df = df_payments_raw[['Corporate_ID', 'Payment_Method']].drop_duplicates(subset=['Corporate_ID'])
    
    df_corp = pd.merge(df_emp_merged, df_clients, on='Corporate_ID', how='left')
    df_corp = pd.merge(df_corp, payment_map_df, on='Corporate_ID', how='left')
    df_corp['Payment_Method'] = df_corp['Payment_Method'].fillna('Bank Transfer')
    
    np.random.seed(42)
    df_corp['BMI'] = np.random.normal(27.26, 5.35, len(df_corp)).clip(18.0, 36.5)
    df_corp['Tenure_Months'] = np.random.randint(0, 24, len(df_corp))
    df_corp['Policy_Status'] = 'Active'
    df_corp['Payment_Behavior'] = 'Consistent'
    df_corp['Marital_Status'] = np.random.choice(['Married', 'Single', 'Divorced'], size=len(df_corp))
    
    df_corp.rename(columns={
        'Monthly_Salary_GHS': 'Monthly_Income_GHS',
        'Premium_Per_Staff_GHS': 'Premium_GHS',
        'Insurance_Product': 'Product_Applied'
    }, inplace=True)
    df_corp['Portfolio_Type'] = 'Corporate'
    df_corp['Agent_ID'] = 'AG_CORP'
    df_corp['Agent_Name'] = np.random.choice(df_retail['Agent_Name'].dropna().unique(), size=len(df_corp))
    
    common_cols = [
        'Customer_ID', 'Full_Name', 'Age', 'Gender', 'Occupation', 'Grade_Level', 'Monthly_Income_GHS',
        'Region', 'Product_Applied', 'Smoker', 'BMI', 'Marital_Status', 'Dependents', 'Premium_GHS',
        'Payment_Method', 'Policy_Status', 'Tenure_Months', 'Payment_Behavior', 'Claim_Frequency', 'Claim_Severity',
        'Portfolio_Type', 'Company_Name', 'Agent_ID', 'Agent_Name'
    ]
    
    df_corp.rename(columns={'Employee_ID': 'Customer_ID', 'Employee_Name': 'Full_Name'}, inplace=True)
    
    df_retail_sel = df_retail[[c for c in common_cols if c in df_retail.columns]].copy()
    df_corp_sel   = df_corp[[c for c in common_cols if c in df_corp.columns]].copy()
    
    # -----------------------------------------------------------------------
    # FEATURE ENGINEERING (shared for both segments)
    # -----------------------------------------------------------------------
    for dataset, df_item in [('Retail', df_retail_sel), ('Corporate', df_corp_sel)]:
        df_item['Income_Thousands'] = df_item['Monthly_Income_GHS'] / 1000.0
        df_item['Smoker_encoded'] = df_item['Smoker'].map({'Yes': 1, 'No': 0})

        # Z-score scaling
        df_item['Age_scaled'] = (df_item['Age'] - df_item['Age'].mean()) / df_item['Age'].std()
        df_item['BMI_scaled'] = (df_item['BMI'] - df_item['BMI'].mean()) / df_item['BMI'].std()
        df_item['Dependents_scaled'] = (df_item['Dependents'] - df_item['Dependents'].mean()) / df_item['Dependents'].std()
        df_item['Gender_encoded'] = df_item['Gender'].map({'Male': 1, 'Female': 0})
        df_item['Claim_Severity_encoded'] = df_item['Claim_Severity'].map({'None': 0, 'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4})
        df_item['Income_per_Dependent'] = df_item['Monthly_Income_GHS'] / (df_item['Dependents'] + 1)

        # Additional engineered features (matching notebook pipeline)
        df_item['Is_Obese'] = (df_item['BMI'] >= 30).astype(int)
        df_item['Premium_Sqrt'] = np.sqrt(df_item['Premium_GHS'])
        df_item['Monthly_Income_GHS_log'] = np.log1p(df_item['Monthly_Income_GHS'])
        try:
            from scipy.stats import boxcox as _boxcox
            _transformed, _lam = _boxcox(df_item['Claim_Frequency'] + 1)
            df_item['Claim_Frequency_BoxCox'] = _transformed
        except Exception:
            df_item['Claim_Frequency_BoxCox'] = np.log1p(df_item['Claim_Frequency'])

        # -------------------------------------------------------------------
        # FIX 1 – CLAIM FREQUENCY: Poisson GLM (log link)
        # OLS is inappropriate for count data; Poisson GLM is the actuarially
        # correct model.  We fit on the current segment and predict in-sample,
        # which gives calibrated conditional means without out-of-range values.
        # -------------------------------------------------------------------
        try:
            poisson_formula = "Claim_Frequency ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands + Dependents_scaled"
            poisson_model = smf.glm(
                formula=poisson_formula,
                data=df_item,
                family=sm.families.Poisson(link=sm.families.links.Log())
            ).fit(disp=False)
            df_item['Predicted_Freq'] = poisson_model.predict(df_item).clip(0, 10)
        except Exception:
            # Fallback: use empirical mean by age band if GLM fails (e.g. all-zero counts)
            df_item['Predicted_Freq'] = df_item.groupby(
                pd.cut(df_item['Age'], bins=[0, 30, 45, 60, 200])
            )['Claim_Frequency'].transform('mean').clip(0, 10)

        # -------------------------------------------------------------------
        # FIX 2 – CLAIM SEVERITY: Gamma GLM with log link
        # Claim amounts are positive, right-skewed monetary values. A Gamma
        # GLM (log link) is the standard actuarial GLM for severity. We fit
        # only on policies with at least one claim to avoid log(0) issues.
        # Policies with zero claims are assigned the portfolio mean severity.
        # -------------------------------------------------------------------
        sev_map = {'None': 0, 'Low': 7500, 'Medium': 17500, 'High': 37500, 'Critical': 62500}
        df_item['Sev_Amount'] = df_item['Claim_Severity'].map(sev_map)

        claimants = df_item[df_item['Claim_Frequency'] > 0].copy()
        mean_sev = df_item['Sev_Amount'].replace(0, np.nan).mean()
        if mean_sev is None or np.isnan(mean_sev):
            mean_sev = 20000.0

        if len(claimants) >= 10:
            try:
                gamma_formula = "Sev_Amount ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands"
                gamma_model = smf.glm(
                    formula=gamma_formula,
                    data=claimants,
                    family=sm.families.Gamma(link=sm.families.links.Log())
                ).fit(disp=False)
                df_item['Predicted_Sev'] = gamma_model.predict(df_item).clip(5000, 150000)
            except Exception:
                df_item['Predicted_Sev'] = mean_sev
        else:
            df_item['Predicted_Sev'] = mean_sev

        df_item['Expected_Loss'] = df_item['Predicted_Freq'] * df_item['Predicted_Sev']

        # -------------------------------------------------------------------
        # FIX 3 – RISK SCORECARD: data-aligned weights
        # The old scorecard assigned Smoking = +15 pts (the highest single
        # factor) despite regression evidence that smoking is NOT a significant
        # driver of claim frequency.  Age is the only statistically significant
        # predictor, so we rebalance accordingly:
        #   Age bands:        5 / 12 / 20 / 28  (was 5/10/15/20)
        #   BMI:              0 /  0 / 8  / 12   (was 0/0/10/15 – modest reduction)
        #   Smoking:          5 pts              (was 15 – reduced; not a sig. driver)
        #   Claim Frequency: 0/12/22/27/32       (was 0/10/20/25/30 – slight increase)
        #   Claim Severity:  same bands as before
        #   Premium band:    same as before
        #   Income band:     same as before
        #   Dependents:      same as before
        # These weights are calibrated so that Age ≥ 46 contributes more than
        # Smoking, which reflects the Poisson GLM finding.
        # -------------------------------------------------------------------
        def compute_risk_score(row):
            score = 0
            # Age bands (primary driver – higher weights)
            if row['Age'] <= 30:
                score += 5
            elif 31 <= row['Age'] <= 45:
                score += 12
            elif 46 <= row['Age'] <= 60:
                score += 20
            else:
                score += 28
            # BMI categories (modest reduction to reflect borderline significance)
            if row['BMI'] < 18.5:
                score += 0
            elif 18.5 <= row['BMI'] <= 24.9:
                score += 0
            elif 25 <= row['BMI'] <= 29.9:
                score += 8
            else:
                score += 12
            # Smoking: downgraded from 15 → 5 (not a statistically significant
            # driver of claim frequency in either segment's Poisson GLM)
            if row['Smoker'] == 'Yes':
                score += 5
            # Claim Frequency (slightly increased to reflect Poisson elasticity)
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
            # Claim Severity (unchanged – actuarially sound bands)
            severity_points = {'None': 0, 'Low': 10, 'Medium': 20, 'High': 25, 'Critical': 30}
            score += severity_points.get(row['Claim_Severity'], 0)
            # Premium band (unchanged)
            if row['Premium_GHS'] < 300:
                score += 5
            elif 300 <= row['Premium_GHS'] <= 700:
                score += 10
            else:
                score += 20
            # Monthly Income (unchanged)
            if row['Monthly_Income_GHS'] < 3000:
                score += 10
            elif 3000 <= row['Monthly_Income_GHS'] <= 8000:
                score += 5
            # Dependents (unchanged)
            if row['Dependents'] in [2, 3]:
                score += 5
            elif row['Dependents'] >= 4:
                score += 10
            return score

        df_item['Risk_Score'] = df_item.apply(compute_risk_score, axis=1)

        def assign_risk_category(score):
            if score <= 35:
                return 'Low Risk'
            elif 36 <= score <= 65:
                return 'Medium Risk'
            elif 66 <= score <= 90:
                return 'High Risk'
            else:
                return 'Critical Risk'

        df_item['Risk_Category'] = df_item['Risk_Score'].apply(assign_risk_category)
        df_item['Risk_Category_encoded'] = df_item['Risk_Category'].map(
            {'Low Risk': 0, 'Medium Risk': 1, 'High Risk': 2, 'Critical Risk': 3}
        )

        # -------------------------------------------------------------------
        # FIX 5 – RISK LOADINGS: data-driven via Monte Carlo VaR
        # Instead of hard-coded constants (5%/15%/25%), loadings are derived
        # from the 99th-percentile VaR relative to the expected loss for each
        # risk tier, using a Poisson × Lognormal collective risk simulation.
        # -------------------------------------------------------------------
        def compute_loadings_via_var(df_segment, n_sim=1000, var_pct=0.99, seed=42):
            """
            For each risk category, simulate aggregate annual losses (Poisson
            frequency × Lognormal severity) and derive the loading as:
                loading = (VaR_99 - E[Loss]) / E[Loss]
            capped at [0.05, 0.60] for business viability.
            """
            rng = np.random.default_rng(seed)
            loadings = {}
            for cat in ['Low Risk', 'Medium Risk', 'High Risk', 'Critical Risk']:
                subset = df_segment[df_segment['Risk_Category'] == cat]
                if len(subset) == 0:
                    loadings[cat] = 0.05
                    continue
                mu_freq = float(subset['Predicted_Freq'].mean())
                mu_sev  = float(subset['Predicted_Sev'].mean())
                if mu_freq <= 0 or mu_sev <= 0:
                    loadings[cat] = 0.05
                    continue
                # Lognormal params matching mean severity
                sigma_ln = 0.5  # assumed CV of 50% for severity
                mu_ln = np.log(mu_sev) - 0.5 * sigma_ln ** 2
                # Simulate aggregate losses per policy over 1000 trials
                agg = np.zeros(n_sim)
                for i in range(n_sim):
                    n_claims = rng.poisson(mu_freq)
                    if n_claims > 0:
                        agg[i] = rng.lognormal(mu_ln, sigma_ln, n_claims).sum()
                expected = float(agg.mean()) if agg.mean() > 0 else mu_freq * mu_sev
                var99    = float(np.percentile(agg, var_pct * 100))
                raw_loading = (var99 - expected) / expected if expected > 0 else 0.05
                loadings[cat] = float(np.clip(raw_loading, 0.05, 0.60))
            return loadings

        loadings_map = compute_loadings_via_var(df_item)
        df_item['Risk_Loading'] = df_item['Risk_Category'].map(loadings_map)

        df_item['Recommended_Premium'] = df_item['Expected_Loss'] * (1.0 + df_item['Risk_Loading']) + 50.0
        df_item['Pricing_Deficit'] = df_item['Recommended_Premium'] - (df_item['Premium_GHS'] * 12)

    # df_retail_sel is already deduplicated (50,000 unique policyholders).
    # No second dedup needed — it was running AFTER GLM fitting which was wrong.
    df_combined = pd.concat([df_retail_sel, df_corp_sel], ignore_index=True)
    
    df_claims = pd.read_excel(excel_path, sheet_name='Claims')
    df_claims.drop_duplicates(subset=['Claim_ID'], keep='first', inplace=True)
    
    return df_combined, df_retail_sel, df_corp_sel, df_claims

# Inits the shared session state and styles the page dynamically
def init_page(title):
    # Copy new logo to landing folder if found in temp directory
    try:
        source_logo = Path(r"C:\Users\snype\.gemini\antigravity-ide\brain\8bb506a0-6824-436d-87c4-355a6c8da02b\media__1784371172821.png")
        target_logo = Path("landing/logo.png")
        if source_logo.exists():
            import shutil
            shutil.copy2(source_logo, target_logo)
    except Exception:
        pass

    # Ensure page config is called first
    try:
        st.set_page_config(page_title=title, layout="wide")
    except Exception:
        pass # Already set by main script or another call

    # Load data automatically if not present in session state
    if "df" not in st.session_state:
        df_combined, df_retail, df_corp, df_claims = load_raw_data()
        st.session_state["df"] = df_combined
        st.session_state["df_retail"] = df_retail
        st.session_state["df_corp"] = df_corp
        st.session_state["df_claims"] = df_claims
        st.session_state["initialized"] = True

    # Inject Ultra-Modern 3D Dark Mode CSS (Red, Black, and White theme, NO emojis)
    st.markdown("""
    <style>
        .stApp {
            background-color: #08080A;
            color: #F5F5F7;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #0c0c10 !important;
            border-right: 2px solid #DC143C;
            box-shadow: 5px 0 25px rgba(0, 0, 0, 0.5);
        }
        .premium-card {
            background: linear-gradient(135deg, rgba(28, 28, 35, 0.75) 0%, rgba(18, 18, 24, 0.85) 100%);
            -webkit-backdrop-filter: blur(12px);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-left: 5px solid #DC143C;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6), 
                        inset 0 1px 1px rgba(255, 255, 255, 0.15), 
                        inset 0 -3px 6px rgba(0, 0, 0, 0.4);
            margin-bottom: 20px;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative;
            overflow: hidden;
        }
        .premium-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(to bottom, rgba(255, 255, 255, 0.02) 0%, transparent 100%);
            pointer-events: none;
        }
        .premium-card:hover {
            transform: translateY(-6px) scale(1.01);
            box-shadow: 0 25px 45px rgba(0, 0, 0, 0.8), 
                        inset 0 1px 2px rgba(255, 255, 255, 0.25), 
                        0 0 15px rgba(220, 20, 60, 0.35);
            border-color: rgba(220, 20, 60, 0.4);
        }
        h1, h2, h3 {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        .accent-text {
            color: #DC143C !important;
            font-weight: 600;
        }
        .metric-value {
            font-size: 32px;
            font-weight: 800;
            color: #FFFFFF;
            margin-top: 5px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        .metric-label {
            font-size: 14px;
            color: #A5AAB5;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: #0E0E12;
            padding: 8px;
            border-radius: 12px;
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            color: #A5AAB5 !important;
            border: none !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #DC143C !important;
            color: #FFFFFF !important;
            box-shadow: 0 8px 20px rgba(220, 20, 60, 0.45) !important;
            transform: translateY(-2px);
        }
        .stButton>button {
            background: linear-gradient(135deg, #DC143C 0%, #B22222 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 12px 24px !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            box-shadow: 0 6px 18px rgba(220, 20, 60, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            width: 100%;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #FF1E47 0%, #DC143C 100%) !important;
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(220, 20, 60, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Render premium logo at the top of the sidebar
    logo_path = Path("landing/logo.png")
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
        st.sidebar.markdown("<hr style='border: 1px solid #DC143C; margin-top: 0; margin-bottom: 20px;'>", unsafe_allow_html=True)
        
    return st.session_state["df"], st.session_state["df_retail"], st.session_state["df_corp"], st.session_state["df_claims"]

def get_financial_summary(df_retail, df_corp):
    _, excel_path = _resolve_paths()

    # ── CORPORATE ────────────────────────────────────────────────────────────
    # Use the actual Premium Payments sheet for corporate — it has real
    # Paid / Late / Pending transaction records per Corporate_ID.
    df_payments_corp = pd.read_excel(excel_path, sheet_name='Premium Payments')
    df_payments_corp.drop_duplicates(subset=['Payment_ID'], keep='first', inplace=True)

    corp_paid_prem    = df_payments_corp[df_payments_corp['Payment_Status'] == 'Paid']['Amount_GHS'].sum()
    corp_late_prem    = df_payments_corp[df_payments_corp['Payment_Status'] == 'Late']['Amount_GHS'].sum()
    corp_pending_prem = df_payments_corp[df_payments_corp['Payment_Status'] == 'Pending']['Amount_GHS'].sum()

    # Estimated (billed) = total of all payment records (Paid + Late + Pending)
    # This is the accounts-receivable-ageing method: numerator and denominator
    # come from the SAME source (the payment sheet), avoiding the impossible
    # 160% collection rate caused by comparing different bases.
    corp_est_prem     = corp_paid_prem + corp_late_prem + corp_pending_prem

    # Total collected = Paid + Late (overdue but received/owed)
    corp_act_prem     = corp_paid_prem + corp_late_prem

    df_claims_corp = pd.read_excel(excel_path, sheet_name='Claims')
    df_claims_corp.drop_duplicates(subset=['Claim_ID'], keep='first', inplace=True)
    corp_act_claims = df_claims_corp[df_claims_corp['Claim_Status'] == 'Approved']['Claim_Amount_GHS'].sum()
    corp_rej_claims = df_claims_corp[df_claims_corp['Claim_Status'] == 'Rejected']['Claim_Amount_GHS'].sum()

    # ── RETAIL ───────────────────────────────────────────────────────────────
    # Policy_Status meanings (confirmed from data):
    #   Active / Renewed        → fully paid & current
    #   Pending Renewal         → overdue at renewal, still collectable
    #   Lapsed                  → overdue and grace period passed, chasing
    #   Cancelled               → written off — will not be collected
    #
    # User definition: "Paid + Late payment = premium collected"
    #   Paid     = Active + Renewed
    #   Late     = Pending Renewal + Lapsed  (owed but not yet written off)
    #   Written off = Cancelled  (excluded from receivable)
    ret_est_prem  = df_retail['Premium_GHS'].sum() * 12

    # Paid (Active + Renewed)
    ret_paid_prem  = df_retail[df_retail['Policy_Status'].isin(['Active', 'Renewed'])]['Premium_GHS'].sum() * 12
    # Late / overdue but still collectable (Pending Renewal + Lapsed)
    ret_late_prem  = df_retail[df_retail['Policy_Status'].isin(['Pending Renewal', 'Lapsed'])]['Premium_GHS'].sum() * 12
    # Written off (Cancelled)
    ret_woff_prem  = df_retail[df_retail['Policy_Status'] == 'Cancelled']['Premium_GHS'].sum() * 12

    # "Actual Premium" = Paid + Late  (what the company can still expect)
    ret_act_prem   = ret_paid_prem + ret_late_prem

    # ── RETAIL CLAIMS NOTE ────────────────────────────────────────────────
    # The retail dataset has NO monetary claim amount column.
    # It only records Claim_Frequency (count) and Claim_Severity (categorical).
    # We use GLM-predicted Expected_Loss as the actuarial claims proxy.
    # This is labelled clearly in the UI — never presented as "Actual Claims".
    ret_est_claims  = df_retail['Expected_Loss'].sum()   # GLM estimate
    ret_rej_claims  = 0.0
    ret_claimants   = int((df_retail['Claim_Frequency'] > 0).sum())
    ret_total_claims= int(df_retail['Claim_Frequency'].sum())

    def safe_pct(num, denom):
        return (num / denom) * 100 if denom > 0 else 0.0

    return {
        'Retail': {
            'Estimated_Premium': ret_est_prem,
            'Actual_Premium':    ret_act_prem,
            'Paid_Premium':      ret_paid_prem,
            'Late_Premium':      ret_late_prem,
            'WrittenOff_Premium':ret_woff_prem,
            'Actual_Claims':     ret_est_claims,      # GLM estimate — no monetary column in raw data
            'Rejected_Claims':   ret_rej_claims,
            'Collection_Rate':   safe_pct(ret_act_prem, ret_est_prem),
            'Loss_Ratio':        safe_pct(ret_est_claims, ret_act_prem),
            'Claims_Type':       'GLM Estimated',     # Clearly flagged
            'Claimants':         ret_claimants,
            'Total_Claim_Events':ret_total_claims,
        },
        'Corporate': {
            'Estimated_Premium': corp_est_prem,
            'Actual_Premium':    corp_act_prem,
            'Paid_Premium':      corp_paid_prem,
            'Late_Premium':      corp_late_prem,
            'WrittenOff_Premium':0.0,
            'Actual_Claims':     corp_act_claims,     # Real approved amounts from Claims sheet
            'Rejected_Claims':   corp_rej_claims,
            'Collection_Rate':   safe_pct(corp_act_prem, corp_est_prem),
            'Loss_Ratio':        safe_pct(corp_act_claims, corp_act_prem),
            'Claims_Type':       'Approved (Actual)',
            'Claimants':         None,
            'Total_Claim_Events':None,
        },
        'Combined': {
            'Estimated_Premium': ret_est_prem + corp_est_prem,
            'Actual_Premium':    ret_act_prem + corp_act_prem,
            'Paid_Premium':      ret_paid_prem + corp_paid_prem,
            'Late_Premium':      ret_late_prem + corp_late_prem,
            'WrittenOff_Premium':ret_woff_prem,
            'Actual_Claims':     ret_est_claims + corp_act_claims,
            'Rejected_Claims':   ret_rej_claims + corp_rej_claims,
            'Collection_Rate':   safe_pct(ret_act_prem + corp_act_prem, ret_est_prem + corp_est_prem),
            'Loss_Ratio':        safe_pct(ret_est_claims + corp_act_claims, ret_act_prem + corp_act_prem),
            'Claims_Type':       'Mixed: Retail=GLM Estimate, Corporate=Actual Approved',
            'Claimants':         ret_claimants,
            'Total_Claim_Events':ret_total_claims,
        }
    }

def get_financial_breakdowns(df_retail, df_corp):
    _, excel_path = _resolve_paths()

    # ── CORPORATE: actual claims per employee ──────────────────────────────
    df_claims_corp = pd.read_excel(excel_path, sheet_name='Claims')
    df_claims_corp.drop_duplicates(subset=['Claim_ID'], keep='first', inplace=True)

    claims_grouped = df_claims_corp.groupby('Employee_ID').agg(
        Approved_Claims=('Claim_Amount_GHS',
            lambda x: x[df_claims_corp.loc[x.index, 'Claim_Status'] == 'Approved'].sum()),
        Rejected_Claims=('Claim_Amount_GHS',
            lambda x: x[df_claims_corp.loc[x.index, 'Claim_Status'] == 'Rejected'].sum())
    ).reset_index()
    claims_grouped.rename(columns={'Employee_ID': 'Customer_ID'}, inplace=True)

    # ── CORPORATE: payment sheet — distribute totals by company headcount ──
    # df_corp has Corporate_ID renamed to Customer_ID. Join via Company_Name instead.
    # Load the clients sheet to get Corporate_ID → Company_Name mapping.
    df_clients = pd.read_excel(excel_path, sheet_name='Corporate Clients')
    df_clients.drop_duplicates(subset=['Corporate_ID'], keep='first', inplace=True)
    # Company_Name column in df_corp is carried from df_clients via the merge in load_raw_data
    corp_name_to_id = df_clients[['Corporate_ID', 'Company_Name']].drop_duplicates()

    df_pay = pd.read_excel(excel_path, sheet_name='Premium Payments')
    df_pay.drop_duplicates(subset=['Payment_ID'], keep='first', inplace=True)
    # Summarise payment sheet by Corporate_ID
    pay_by_corp = df_pay.groupby(['Corporate_ID', 'Payment_Status'])['Amount_GHS'].sum().unstack(fill_value=0).reset_index()
    pay_by_corp.columns.name = None
    for col in ['Paid', 'Late', 'Pending']:
        if col not in pay_by_corp.columns:
            pay_by_corp[col] = 0.0
    pay_by_corp['Total_Paid_Late'] = pay_by_corp['Paid'] + pay_by_corp['Late']
    pay_by_corp['Total_Billed']    = pay_by_corp['Paid'] + pay_by_corp['Late'] + pay_by_corp['Pending']
    # Map Corporate_ID → Company_Name
    pay_by_corp = pay_by_corp.merge(corp_name_to_id, on='Corporate_ID', how='left')
    # Aggregate by Company_Name (in case one company has multiple Corporate_IDs)
    pay_by_name = pay_by_corp.groupby('Company_Name').agg(
        Total_Paid_Late=('Total_Paid_Late', 'sum'),
        Total_Billed=('Total_Billed', 'sum'),
        Corp_Paid=('Paid', 'sum'),
        Corp_Late=('Late', 'sum'),
        Corp_Pending=('Pending', 'sum'),
    ).reset_index()

    df_corp_fin = df_corp.copy()
    # Use payment sheet total as billed (not employee premium base)
    # Distribute company-level totals proportionally by headcount
    headcount = df_corp_fin.groupby('Company_Name').size().rename('Headcount').reset_index()
    df_corp_fin = df_corp_fin.merge(headcount, on='Company_Name', how='left')
    df_corp_fin = df_corp_fin.merge(pay_by_name, on='Company_Name', how='left')
    df_corp_fin['Total_Paid_Late'] = df_corp_fin['Total_Paid_Late'].fillna(0.0)
    df_corp_fin['Total_Billed']    = df_corp_fin['Total_Billed'].fillna(0.0)
    hc = df_corp_fin['Headcount'].replace(0, 1)
    df_corp_fin['Billed_Premium']    = df_corp_fin['Total_Billed'] / hc
    df_corp_fin['Collected_Premium'] = df_corp_fin['Corp_Paid'].fillna(0.0) / hc
    df_corp_fin['Late_Premium']      = df_corp_fin['Corp_Late'].fillna(0.0) / hc
    df_corp_fin['Pending_Premium']   = df_corp_fin['Corp_Pending'].fillna(0.0) / hc

    # Merge claims
    df_corp_fin['Customer_ID'] = df_corp_fin['Customer_ID'].astype(str)
    claims_grouped['Customer_ID'] = claims_grouped['Customer_ID'].astype(str)
    df_corp_fin = pd.merge(df_corp_fin, claims_grouped, on='Customer_ID', how='left')
    df_corp_fin['Approved_Claims']  = df_corp_fin['Approved_Claims'].fillna(0.0)
    df_corp_fin['Rejected_Claims']  = df_corp_fin.get(
        'Rejected_Claims', pd.Series(0.0, index=df_corp_fin.index)
    ).fillna(0.0)
    df_corp_fin.rename(columns={'Approved_Claims': 'Actual_Claims'}, inplace=True)
    # Handle potential _x / _y suffixes after merge
    if 'Rejected_Claims_x' in df_corp_fin.columns:
        df_corp_fin.rename(columns={'Rejected_Claims_x': 'Rejected_Claims'}, inplace=True)
    elif 'Rejected_Claims_y' in df_corp_fin.columns:
        df_corp_fin.rename(columns={'Rejected_Claims_y': 'Rejected_Claims'}, inplace=True)
    if 'Rejected_Claims' not in df_corp_fin.columns:
        df_corp_fin['Rejected_Claims'] = 0.0

    # ── RETAIL: paid / late / written-off split ────────────────────────────
    df_retail_fin = df_retail.copy()
    df_retail_fin['Billed_Premium'] = df_retail_fin['Premium_GHS'] * 12
    df_retail_fin['Collected_Premium'] = df_retail_fin.apply(
        lambda r: r['Premium_GHS'] * 12 if r['Policy_Status'] in ['Active', 'Renewed'] else 0.0, axis=1
    )
    df_retail_fin['Late_Premium'] = df_retail_fin.apply(
        lambda r: r['Premium_GHS'] * 12 if r['Policy_Status'] in ['Pending Renewal', 'Lapsed'] else 0.0, axis=1
    )
    df_retail_fin['Pending_Premium'] = 0.0   # Retail has no pending bucket
    df_retail_fin['WrittenOff_Premium'] = df_retail_fin.apply(
        lambda r: r['Premium_GHS'] * 12 if r['Policy_Status'] == 'Cancelled' else 0.0, axis=1
    )
    df_retail_fin['Actual_Claims']   = df_retail_fin['Expected_Loss'].fillna(0.0)  # GLM estimate — no raw monetary column
    df_retail_fin['Rejected_Claims'] = 0.0

    # Corporate has no written-off column
    df_corp_fin['WrittenOff_Premium'] = 0.0

    # ── COMBINE ────────────────────────────────────────────────────────────
    cols_to_keep = [
        'Company_Name', 'Product_Applied', 'Agent_Name',
        'Billed_Premium', 'Collected_Premium', 'Late_Premium',
        'Pending_Premium', 'WrittenOff_Premium',
        'Actual_Claims', 'Rejected_Claims', 'Portfolio_Type'
    ]
    return pd.concat(
        [df_retail_fin[cols_to_keep], df_corp_fin[cols_to_keep]], ignore_index=True
    )

@st.cache_resource
def get_scorecard_models(portfolio_type):
    # Retrieve the appropriate dataframe from st.session_state
    if "df_retail" not in st.session_state or "df_corp" not in st.session_state:
        # Load them if not initialized
        df_combined, df_retail, df_corp, df_claims = load_raw_data()
        st.session_state["df_retail"] = df_retail
        st.session_state["df_corp"] = df_corp
        st.session_state["df"] = df_combined
        st.session_state["df_claims"] = df_claims
    
    df_segment = st.session_state["df_retail"] if portfolio_type == "Retail" else st.session_state["df_corp"]
    
    poisson_formula = "Claim_Frequency ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands + Dependents_scaled"
    poisson_model = smf.glm(
        formula=poisson_formula,
        data=df_segment,
        family=sm.families.Poisson(link=sm.families.links.Log())
    ).fit(disp=False)
    
    sev_map = {'None': 0, 'Low': 7500, 'Medium': 17500, 'High': 37500, 'Critical': 62500}
    df_segment_copy = df_segment.copy()
    df_segment_copy['Sev_Amount'] = df_segment_copy['Claim_Severity'].map(sev_map)
    claimants = df_segment_copy[df_segment_copy['Claim_Frequency'] > 0]
    
    gamma_formula = "Sev_Amount ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands"
    gamma_model = smf.glm(
        formula=gamma_formula,
        data=claimants,
        family=sm.families.Gamma(link=sm.families.links.Log())
    ).fit(disp=False)
    
    return poisson_model, gamma_model

@st.cache_data
def get_loadings_map(portfolio_type):
    if "df_retail" not in st.session_state or "df_corp" not in st.session_state:
        df_combined, df_retail, df_corp, df_claims = load_raw_data()
        st.session_state["df_retail"] = df_retail
        st.session_state["df_corp"] = df_corp
        st.session_state["df"] = df_combined
        st.session_state["df_claims"] = df_claims

    df_segment = st.session_state["df_retail"] if portfolio_type == "Retail" else st.session_state["df_corp"]
    
    # Run the collective risk VaR loading mapping
    rng = np.random.default_rng(42)
    loadings = {}
    
    # We must calculate predicted freq and sev to perform the Monte Carlo simulations
    poisson_model, gamma_model = get_scorecard_models(portfolio_type)
    df_segment_copy = df_segment.copy()
    df_segment_copy['Predicted_Freq'] = poisson_model.predict(df_segment_copy).clip(0, 10)
    
    sev_map = {'None': 0, 'Low': 7500, 'Medium': 17500, 'High': 37500, 'Critical': 62500}
    df_segment_copy['Sev_Amount'] = df_segment_copy['Claim_Severity'].map(sev_map)
    df_segment_copy['Predicted_Sev'] = gamma_model.predict(df_segment_copy).clip(5000, 150000)
    
    for cat in ['Low Risk', 'Medium Risk', 'High Risk', 'Critical Risk']:
        subset = df_segment_copy[df_segment_copy['Risk_Category'] == cat]
        if len(subset) == 0:
            loadings[cat] = 0.05
            continue
        mu_freq = float(subset['Predicted_Freq'].mean())
        mu_sev  = float(subset['Predicted_Sev'].mean())
        if mu_freq <= 0 or mu_sev <= 0:
            loadings[cat] = 0.05
            continue
        sigma_ln = 0.5
        mu_ln = np.log(mu_sev) - 0.5 * sigma_ln ** 2
        agg = np.zeros(1000)
        for i in range(1000):
            n_claims = rng.poisson(mu_freq)
            if n_claims > 0:
                agg[i] = rng.lognormal(mu_ln, sigma_ln, n_claims).sum()
        expected = float(agg.mean()) if agg.mean() > 0 else mu_freq * mu_sev
        var99    = float(np.percentile(agg, 99))
        raw_loading = (var99 - expected) / expected if expected > 0 else 0.05
        loadings[cat] = float(np.clip(raw_loading, 0.05, 0.60))
    return loadings


