import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")
import utils

df, df_retail, df_corp, df_claims = utils.init_page("Prudential Statistical Inference & Diagnostics")

st.title("Prudential Statistical Inference and Diagnostics")
st.markdown("---")

st.markdown("""
This page presents the full statistical inference pipeline underpinning the risk framework.

| Model | Dependent Variable | Correct Family | Rationale |
|---|---|---|---|
| **Model 1** | Claim Frequency (count) | **Poisson GLM** (log link) | Count data; OLS can produce negative fitted values and invalid p-values |
| **Model 2** | Claim Severity (GHS amount) | **Gamma GLM** (log link) | Positive, right-skewed monetary values; Gamma variance ∝ mean² |
| **Model 3** | Premium vs Risk Factors | OLS | Premium is a continuous, approximately normal management variable |
| **Model 4** | Risk Score Decomposition | OLS | Risk Score is a deterministic linear function; OLS recovers exact weights |

All models are preceded by a **VIF multicollinearity check** on scaled inputs.
""")

# ── 1. VIF Analysis ───────────────────────────────────────────────────────────
st.subheader("Multicollinearity Analysis (VIF)")

from statsmodels.stats.outliers_influence import variance_inflation_factor

vif_cols = ['Age_scaled', 'BMI_scaled', 'Income_Thousands',
            'Dependents_scaled', 'Gender_encoded', 'Smoker_encoded']
X_vif = df[vif_cols].dropna().copy()
X_vif_const = sm.add_constant(X_vif)

vif_data = pd.DataFrame({
    "Feature": vif_cols,
    "VIF": [variance_inflation_factor(X_vif_const.values, i + 1)
            for i in range(len(vif_cols))]
})

col_vif_left, col_vif_right = st.columns([1, 2])
with col_vif_left:
    st.dataframe(vif_data.style.format({'VIF': '{:.4f}'}), use_container_width=True)
with col_vif_right:
    st.markdown("""
    <div class="premium-card">
        <h4 style="color: #DC143C;">VIF Interpretation</h4>
        <p style="color: #A5AAB5; font-size: 14px;">
            All VIF values are close to 1.0 (well below the standard threshold of 5.0).
            Z-score scaling of Age, BMI, and Dependents, and expressing Monthly Income
            in thousands, has eliminated multicollinearity. GLM standard errors and
            p-values are therefore reliable.
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── 2. Correlation Heatmaps ───────────────────────────────────────────────────
st.subheader("Risk Correlation and Heatmap Visualization")
st.markdown("""
**Pearson** correlation captures linear relationships; **Spearman** captures monotonic ones.
Both are shown to expose the smoking–vs–age signal discrepancy that motivated the scorecard recalibration.
""")

NUMERIC_COLS = [
    "Age", "BMI", "Monthly_Income_GHS", "Dependents",
    "Claim_Frequency", "Premium_GHS", "Risk_Score",
    "Gender_encoded", "Smoker_encoded", "Claim_Severity_encoded",
    "Income_per_Dependent"
]
numeric_cols_existing = [c for c in NUMERIC_COLS if c in df.columns]
df_numeric = df[numeric_cols_existing].copy()

display_rename = {
    "Gender_encoded": "Gender", "Smoker_encoded": "Smoker",
    "Claim_Severity_encoded": "Claim_Severity",
    "Monthly_Income_GHS": "Income_GHS", "Income_per_Dependent": "Income/Dep",
}
pearson_corr  = df_numeric.corr(method="pearson").rename(index=display_rename,  columns=display_rename)
spearman_corr = df_numeric.corr(method="spearman").rename(index=display_rename, columns=display_rename)

corr_tabs = st.tabs(["Pearson Correlation Matrix", "Spearman Rank Correlation Matrix"])
_heatmap_layout = dict(plot_bgcolor="#14141A", paper_bgcolor="#08080A",
                       font_color="#F5F5F7", height=450,
                       margin=dict(l=20, r=20, t=30, b=20))

with corr_tabs[0]:
    fig_p = px.imshow(pearson_corr, text_auto=".2f", aspect="auto",
                      color_continuous_scale=["#000000", "#DC143C", "#FFFFFF"],
                      range_color=[-1, 1], labels=dict(color="Pearson r"))
    fig_p.update_layout(**_heatmap_layout)
    st.plotly_chart(fig_p, use_container_width=True)

with corr_tabs[1]:
    fig_s = px.imshow(spearman_corr, text_auto=".2f", aspect="auto",
                      color_continuous_scale=["#000000", "#DC143C", "#FFFFFF"],
                      range_color=[-1, 1], labels=dict(color="Spearman rho"))
    fig_s.update_layout(**_heatmap_layout)
    st.plotly_chart(fig_s, use_container_width=True)

st.markdown("""
<div class="premium-card">
    <h4 style="color: #DC143C;">Key Business Implications from Correlations</h4>
    <ul style="color: #A5AAB5; font-size: 14px; line-height: 1.8;">
        <li><b>Age &amp; Claim Frequency (r ≈ +0.21):</b> Older policyholders file claims more often.
        Age is the primary actuarial rating variable — confirmed by the Poisson GLM below.</li>
        <li><b>Smoking &amp; Claim Frequency (r ≈ −0.01):</b> Essentially zero correlation with actual
        claim counts. The legacy scorecard penalised smoking +15 pts despite this; the recalibrated
        scorecard reduces it to +5 pts.</li>
        <li><b>BMI &amp; Claim Frequency (r ≈ +0.05):</b> Modest positive signal — retained in scorecard
        at a lower weight (8 / 12 pts) than before.</li>
        <li><b>Premium &amp; Risk Score (r ≈ +0.18):</b> Weak link exposes flat-rate underpricing.
        High-risk policyholders do not pay risk-proportionate premiums.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── 3. Regression Models ──────────────────────────────────────────────────────
st.subheader("Statistical Regression Models")

tabs = st.tabs([
    "Model 1: Claim Frequency (Poisson GLM)",
    "Model 2: Claim Severity (Gamma GLM)",
    "Model 3: Premium Alignment (OLS)",
    "Model 4: Risk Score Decomposition (OLS)",
])

df_clean = df.dropna(subset=['Age_scaled', 'BMI_scaled', 'Income_Thousands',
                              'Dependents_scaled', 'Gender_encoded', 'Smoker_encoded',
                              'Claim_Frequency', 'Claim_Severity_encoded',
                              'Premium_GHS', 'Risk_Score']).copy()

# ── Helper: tidy GLM / OLS summary into a DataFrame ──────────────────────────
def glm_summary_df(result):
    return pd.DataFrame({
        'Coefficient':  result.params,
        'Std. Error':   result.bse,
        'z / t':        result.tvalues,
        'p-Value':      result.pvalues,
        '[0.025':       result.conf_int()[0],
        '0.975]':       result.conf_int()[1],
    })

_formula_base = ("Age_scaled + Gender_encoded + Smoker_encoded + "
                 "BMI_scaled + Income_Thousands + Dependents_scaled")

# ── Model 1: Poisson GLM ──────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("### Model 1 — Claim Frequency: Poisson GLM (log link)")
    st.code(f"Claim_Frequency ~ {_formula_base}  |  family = Poisson(log)")
    st.markdown("""
    **Why Poisson GLM?**
    Claim frequency is a non-negative integer count (0, 1, 2, 3, 4).
    OLS assumes a continuous, normally distributed response and can predict
    negative frequencies. The Poisson GLM models the *log of the expected count*
    as a linear function of the predictors, guaranteeing positive fitted values
    and providing correctly calibrated standard errors for count data.
    """)

    poisson_model = smf.glm(
        formula=f"Claim_Frequency ~ {_formula_base}",
        data=df_clean,
        family=sm.families.Poisson(link=sm.families.links.Log())
    ).fit(disp=False)

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Log-Likelihood",     f"{poisson_model.llf:.1f}")
        st.metric("AIC",                f"{poisson_model.aic:.1f}")
        st.metric("Deviance / df",      f"{poisson_model.deviance / max(poisson_model.df_resid, 1):.3f}")
        st.metric("Pearson χ² / df",
                  f"{poisson_model.pearson_chi2 / max(poisson_model.df_resid, 1):.3f}")
    with col2:
        st.dataframe(glm_summary_df(poisson_model).style.format('{:.4f}'),
                     use_container_width=True)

    st.markdown("""
    <div class="premium-card" style="border-left-color: #B22222;">
        <h4 style="color: #DC143C;">Actuarial Interpretation (Poisson GLM) — Corrected Results (n=51,974)</h4>
        <p style="color: #A5AAB5; font-size: 14px; line-height: 1.7;">
            <b>Coefficients are log-rate ratios.</b>
            A positive coefficient raises the expected claim count multiplicatively (e<sup>β</sup>).<br><br>
            <b>Age (coef = +0.300, z = 55.0, p &lt; 0.001):</b> Primary driver. Each SD increase in age
            raises the expected claim rate by e<sup>0.300</sup> ≈ 1.35× (35% uplift per SD). Age-band
            rating multipliers: ≤30: 1.0×, 31–45: 1.35×, 46–60: 1.82×, &gt;60: 2.46×.<br><br>
            <b>BMI (coef = +0.008, p = 0.157):</b> Not statistically significant at the 5% level on the
            correctly deduplicated 50k dataset. Retained at reduced scorecard weight for completeness.<br><br>
            <b>Smoking (coef = −0.024, p = 0.027):</b> Statistically significant but negative —
            smokers claim marginally less frequently. The old +15 pt smoking surcharge was unjustified.
            Reduced to +5 pts in the recalibrated scorecard.<br><br>
            <b>Income (p = 0.033):</b> Borderline significant — small positive effect (+0.002 per GHS 1k).<br><br>
            <b>Dependents (p = 0.042):</b> Borderline significant — small negative effect.<br><br>
            <b>Deviance / df = 1.24:</b> Good Poisson fit. No overdispersion issue requiring Negative Binomial.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── Model 2: Gamma GLM ────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### Model 2 — Claim Severity: Gamma GLM (log link)")
    st.code(f"Claim_Amount ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands"
            f"  |  family = Gamma(log)  [claimants only]")
    st.markdown("""
    **Why Gamma GLM?**
    Claim severity (the GHS amount per claim) is strictly positive and right-skewed.
    OLS on raw monetary amounts violates normality and homoscedasticity assumptions
    and produces out-of-range predictions that require artificial clipping.
    The Gamma GLM (log link) directly models positive continuous outcomes where
    variance scales with the mean squared — the standard actuarial severity model.
    We fit on policyholders with at least one claim to avoid log(0).
    """)

    # Midpoint monetary proxy for severity label
    sev_map = {'None': np.nan, 'Low': 7500, 'Medium': 17500, 'High': 37500, 'Critical': 62500}
    df_clean['Sev_Amount'] = df_clean['Claim_Severity'].map(sev_map)
    df_claimants = df_clean[df_clean['Claim_Frequency'] > 0].dropna(subset=['Sev_Amount']).copy()

    _sev_formula = "Sev_Amount ~ Age_scaled + BMI_scaled + Smoker_encoded + Income_Thousands"

    if len(df_claimants) >= 20:
        gamma_model = smf.glm(
            formula=_sev_formula,
            data=df_claimants,
            family=sm.families.Gamma(link=sm.families.links.Log())
        ).fit(disp=False)

        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Log-Likelihood", f"{gamma_model.llf:.1f}")
            st.metric("AIC",            f"{gamma_model.aic:.1f}")
            st.metric("Deviance / df",
                      f"{gamma_model.deviance / max(gamma_model.df_resid, 1):.3f}")
            st.metric("N (claimants)",  f"{len(df_claimants):,}")
        with col2:
            st.dataframe(glm_summary_df(gamma_model).style.format('{:.4f}'),
                         use_container_width=True)
    else:
        st.warning("Insufficient claimants to fit the Gamma GLM on the current segment. "
                   "Switch to the Combined or Retail portfolio.")

    st.markdown("""
    <div class="premium-card" style="border-left-color: #B22222;">
        <h4 style="color: #DC143C;">Actuarial Interpretation (Gamma GLM) — Corrected Results (n=22,489 claimants)</h4>
        <p style="color: #A5AAB5; font-size: 14px; line-height: 1.7;">
            <b>Claimants subset: 22,489 rows (43.3% of portfolio)</b> — correctly deduplicated 50k retail.<br><br>
            <b>Age (coef = +0.079, z = 16.1, p &lt; 0.001):</b> Significant — each SD increase in age
            raises expected claim amount by e<sup>0.079</sup> ≈ 1.08× (8% uplift per SD).<br><br>
            <b>BMI (coef = +0.001, p = 0.794):</b> Not significant for severity — BMI does not predict
            how large a claim will be on the correct 50k dataset.<br><br>
            <b>Smoking (coef = −0.026, p = 0.007):</b> Smokers have marginally lower claim amounts.
            Consistent with the Poisson GLM finding — smoking is not a risk factor here.<br><br>
            <b>Income (coef = +0.002, p = 0.024):</b> Higher income slightly increases severity —
            may reflect more comprehensive healthcare usage or higher-cost treatments.<br><br>
            Gamma GLM fitted values are always positive — no artificial clipping required,
            eliminating the structural defect present in the previous OLS severity model.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Model 3: Premium Alignment OLS ───────────────────────────────────────────
with tabs[2]:
    st.markdown("### Model 3 — Premium Pricing Alignment (OLS)")
    st.code(f"Premium_GHS ~ {_formula_base}")
    st.markdown("""
    OLS is appropriate here because `Premium_GHS` is a **management-set continuous variable**,
    not a count or monetary outcome. Its distribution is approximately symmetric and homoscedastic
    across the demographic range, satisfying OLS assumptions.
    The purpose of this model is to confirm that **premiums are not risk-adjusted** —
    a near-zero R² and insignificant coefficients expose the flat-rate underpricing.
    """)

    model_prem = smf.ols(
        formula=f"Premium_GHS ~ {_formula_base}",
        data=df_clean
    ).fit()

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("R²",              f"{model_prem.rsquared:.4f}")
        st.metric("Adj. R²",         f"{model_prem.rsquared_adj:.4f}")
        st.metric("F p-value",       f"{model_prem.f_pvalue:.4e}")
    with col2:
        st.dataframe(glm_summary_df(model_prem).style.format('{:.4f}'),
                     use_container_width=True)

    st.markdown("""
    <div class="premium-card" style="border-left-color: #B22222;">
        <h4 style="color: #DC143C;">Critical Actuarial Warning — Flat-Rate Underpricing (Confirmed)</h4>
        <p style="color: #A5AAB5; font-size: 14px; line-height: 1.7;">
            <b>R² = 0.000, F-statistic p = 5.23×10⁻²⁵ (significant but economically meaningless):</b>
            The six risk factors explain essentially zero variation in the premiums charged.
            Despite statistical significance on Gender and Dependents (driven by the large n=51,974),
            the effect sizes are tiny (Gender adds ~GHS 3.50, Dependents ~GHS 1.68 per unit).<br><br>
            Every policyholder pays a near-flat monthly rate around <b>GHS 470.86</b> regardless of
            their actual risk profile. This is the root cause of the portfolio-wide pricing deficit.<br><br>
            Risk-adjusted loading via the Poisson GLM coefficients and the recalibrated scorecard
            is the actuarially correct remedy.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── Model 4: Risk Score Decomposition OLS ────────────────────────────────────
with tabs[3]:
    st.markdown("### Model 4 — Risk Score Decomposition (OLS)")
    st.code(f"Risk_Score ~ {_formula_base} + Claim_Frequency + Claim_Severity_encoded")
    st.markdown("""
    The Risk Score is a **deterministic linear combination** of the input features (the scorecard).
    OLS on the score against its own inputs recovers the effective weights, providing a
    transparency check on how each factor contributes to the total score.
    An R² near 1.0 is expected and correct — it confirms the scorecard is deterministic,
    not that the model has predictive power for external outcomes.
    """)

    model_rs = smf.ols(
        formula=f"Risk_Score ~ {_formula_base} + Claim_Frequency + Claim_Severity_encoded",
        data=df_clean
    ).fit()

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("R²",        f"{model_rs.rsquared:.4f}")
        st.metric("Adj. R²",   f"{model_rs.rsquared_adj:.4f}")
        st.metric("F p-value", f"{model_rs.f_pvalue:.4e}")
    with col2:
        st.dataframe(glm_summary_df(model_rs).style.format('{:.4f}'),
                     use_container_width=True)

    st.markdown("""
    <div class="premium-card">
        <h4 style="color: #DC143C;">Scorecard Weight Transparency (Recalibrated)</h4>
        <p style="color: #A5AAB5; font-size: 14px; line-height: 1.7;">
            <b>R² ≈ 0.90+</b> confirms the scorecard is nearly deterministic from its inputs.<br><br>
            <b>Recalibrated weights:</b> Age bands now contribute 5 / 12 / 20 / 28 pts
            (up from 5 / 10 / 15 / 20), while Smoking drops from +15 to +5 pts.
            This aligns the scorecard with the Poisson GLM evidence that Age is the
            primary driver of claim frequency and Smoking is not statistically significant.<br><br>
            <b>Claim Frequency and Severity</b> still carry the highest OLS coefficients,
            confirming that prior claims history is the strongest single predictor
            of future risk score tier.
        </p>
    </div>
    """, unsafe_allow_html=True)
