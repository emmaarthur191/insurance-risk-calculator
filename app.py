import streamlit as st
import utils

# Initialize data and inject modern 3D styling
df, df_retail, df_corp, df_claims = utils.init_page("Prudential Insurance Risk Decision Support Platform")

st.title("Prudential Insurance Risk Decision Support Platform")
st.markdown("An ultra-modern decision support interface built for Prudential Insurance.")
st.markdown("---")

num_retail = len(df_retail)
num_corp = len(df_corp)
num_branches = df_retail['Region'].nunique()
corp_deficit = df_corp['Pricing_Deficit'].sum() / 1e6
combined_deficit = df['Pricing_Deficit'].sum() / 1e6

# Neumorphic KPI Summary Cards at the top for executives
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class="premium-card" style="margin: 0; padding: 1.2rem;">
        <div style="font-size: 0.8rem; color: #A5AAB5; font-weight: bold; text-transform: uppercase;">Retail Policies</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #DC143C; margin-top: 5px;">{num_retail:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="premium-card" style="margin: 0; padding: 1.2rem;">
        <div style="font-size: 0.8rem; color: #A5AAB5; font-weight: bold; text-transform: uppercase;">Corporate Employees</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: white; margin-top: 5px;">{num_corp:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="premium-card" style="margin: 0; padding: 1.2rem;">
        <div style="font-size: 0.8rem; color: #A5AAB5; font-weight: bold; text-transform: uppercase;">Active Branches</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #DC143C; margin-top: 5px;">{num_branches}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    st.markdown(f"""
    <div class="premium-card" style="margin: 0; padding: 1.2rem;">
        <div style="font-size: 0.8rem; color: #A5AAB5; font-weight: bold; text-transform: uppercase;">Corporate Deficit</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #B22222; margin-top: 5px;">{corp_deficit:.2f}M GHS</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown(f"""
    <div class="premium-card">
        <h3 style="color: #DC143C;">Segmented Risk Analytics Engine</h3>
        <p style="color: #A5AAB5; line-height: 1.6;">
            This system segments policy portfolios into two parallel streams to isolate risk weights accurately:
        </p>
        <ul style="color: #F5F5F7; margin-left: 20px;">
            <li><b>Individual Retail Portfolio:</b> {num_retail:,} unique records. Analyzes personal coverages, pricing gaps, and regional risk metrics.</li>
            <li><b>Corporate Client Portfolio:</b> {num_corp:,} records across multiple client organizations (MTN Ghana, GCB Bank, etc.).</li>
        </ul>
        <p style="color: #A5AAB5; margin-top: 15px;">
            Navigate to the individual pages in the left sidebar menu to inspect executive overviews, regression inferences, predictive models, claims audits, and interactive simulators.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="premium-card">
        <h3 style="color: #DC143C;">Key Solvency Callout</h3>
        <div class="metric-label">Emergency Reserves Deficit</div>
        <div class="metric-value" style="color: #B22222;">{combined_deficit:.2f}M GHS</div>
        <p style="color: #A5AAB5; font-size: 13px; margin-top: 10px;">
            Monte Carlo testing indicates a severe solvency shortfall. The combined segment's expected claims exceed premium revenue collections by a significant margin, requiring capital reserve strengthening.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="premium-card">
        <h3>Platform Sections</h3>
        <div style="font-size: 14px; color: #A5AAB5; line-height: 1.8;">
            1. <b>Executive Overview:</b> Portfolio Boxplots, Regional Revenues, Product Risks, and Answers to Key Business Questions.<br>
            2. <b>Statistical Inference:</b> Multicollinearity checks, correlation heatmaps, OLS regression summaries.<br>
            3. <b>Predictive Modeling:</b> XGBoost risk classification and Real-Time Underwriting Simulator.<br>
            4. <b>Fraud Audit:</b> Flagged rushed claims (approved in under 3 days) and anomalous accounts.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.success("All datasets successfully loaded and cached!")
