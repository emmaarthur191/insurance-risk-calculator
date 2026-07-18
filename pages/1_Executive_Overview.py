import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import utils

# Initialize data and inject modern 3D styling
df, df_retail, df_corp, df_claims = utils.init_page("Prudential Executive Underwriting Overview")

st.markdown("---")
segment = st.selectbox("Select Portfolio Segment", options=["Combined Portfolio", "Retail Segment", "Corporate Segment"])

if segment == "Retail Segment":
    active_df = df_retail
elif segment == "Corporate Segment":
    active_df = df_corp
else:
    active_df = df

# Actuarial Metric Calculations
# Total premiums = Paid + Late (overdue but still owed) — NOT written-off (Cancelled)
summary_for_metrics = utils.get_financial_summary(df_retail, df_corp)
seg_key_top = "Combined" if segment == "Combined Portfolio" else ("Retail" if segment == "Retail Segment" else "Corporate")
_s = summary_for_metrics[seg_key_top]

total_premiums       = _s['Actual_Premium']      # Paid + Late
paid_premiums        = _s['Paid_Premium']
late_premiums        = _s['Late_Premium']
if seg_key_top == "Corporate":
    total_expected_loss = _s['Actual_Claims']
    total_deficit = _s['Actual_Claims'] - _s['Actual_Premium']
    avg_deficit = total_deficit / len(df_corp) if len(df_corp) > 0 else 0
elif seg_key_top == "Combined":
    total_expected_loss = summary_for_metrics['Retail']['Actual_Claims'] + summary_for_metrics['Corporate']['Actual_Claims']
    total_deficit = df_retail['Pricing_Deficit'].sum() + (summary_for_metrics['Corporate']['Actual_Claims'] - summary_for_metrics['Corporate']['Actual_Premium'])
    avg_deficit = total_deficit / (len(df_retail) + len(df_corp))
else:
    total_expected_loss = df_retail['Expected_Loss'].sum()
    total_deficit = df_retail['Pricing_Deficit'].sum()
    avg_deficit = df_retail['Pricing_Deficit'].mean()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Total Premiums (Paid + Late)</div>
        <div class="metric-value" style="color: #DC143C;">{total_premiums:,.0f} GHS</div>
        <div style="font-size:11px; color:#A5AAB5; margin-top:4px;">
            Paid: {paid_premiums:,.0f} &nbsp;|&nbsp; Late/Overdue: {late_premiums:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
with col2:
    _claims_card_label = (
        "GLM Est. Claims (no raw GHS data)" if seg_key_top == "Retail"
        else ("Actual Approved Claims" if seg_key_top == "Corporate"
              else "Claims (Retail=GLM | Corp=Actual)")
    )
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">{_claims_card_label}</div>
        <div class="metric-value">{total_expected_loss:,.0f} GHS</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Underpricing Deficit</div>
        <div class="metric-value" style="color: #B22222;">{total_deficit:,.0f} GHS</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    loss_ratio = (total_expected_loss / total_premiums * 100) if total_premiums > 0 else 0
    st.markdown(f"""
    <div class="premium-card">
        <div class="metric-label">Loss Ratio (Claims / Premiums)</div>
        <div class="metric-value" style="color: #B22222;">{loss_ratio:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Executive Financial Premium & Claims Overview Section ---
st.subheader(f"Executive Financial Premium & Claims Overview ({segment})")

summary = utils.get_financial_summary(df_retail, df_corp)
segment_key = "Combined" if segment == "Combined Portfolio" else ("Retail" if segment == "Retail Segment" else "Corporate")
active_summary = summary[segment_key]

has_rejected = (segment_key != "Retail")
rej_str = f"{active_summary['Rejected_Claims']:,.2f}" if has_rejected else "Not Tracked"

claims_type_label = active_summary.get('Claims_Type', '')
pending_prem = active_summary.get('Pending_Premium', 0.0)
pending_row_html = ""
if pending_prem > 0:
    pending_row_html = f"""
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;">&nbsp;&nbsp;&nbsp;↳ <b>Pending Premium</b> — invoiced but not yet due</td>
            <td style="padding: 12px 15px; text-align: right; color: #FF8C00; font-size: 14px; font-weight: bold;">{pending_prem:,.2f}</td>
        </tr>"""

table_html = f"""
<table style="width:100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; background-color: #14141A; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
    <thead>
        <tr style="background-color: #0E0E12; border-bottom: 2px solid #DC143C;">
            <th style="padding: 15px; text-align: left; color: #FFFFFF; font-weight: bold; font-size: 14px;">Financial Indicator</th>
            <th style="padding: 15px; text-align: right; color: #FFFFFF; font-weight: bold; font-size: 14px;">Value (GHS)</th>
        </tr>
    </thead>
    <tbody>
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;"><b>Estimated (Billed) Premium</b> — total invoiced</td>
            <td style="padding: 12px 15px; text-align: right; color: #FFFFFF; font-size: 14px; font-weight: bold;">{active_summary['Estimated_Premium']:,.2f}</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background-color: rgba(255,255,255,0.01);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;">&nbsp;&nbsp;&nbsp;↳ <b>Paid Premium</b> — fully collected</td>
            <td style="padding: 12px 15px; text-align: right; color: #32CD32; font-size: 14px; font-weight: bold;">{active_summary['Paid_Premium']:,.2f}</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;">&nbsp;&nbsp;&nbsp;↳ <b>Late / Overdue Premium</b> — owed, being chased</td>
            <td style="padding: 12px 15px; text-align: right; color: #FFD700; font-size: 14px; font-weight: bold;">{active_summary['Late_Premium']:,.2f}</td>
        </tr>{pending_row_html}
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background-color: rgba(255,255,255,0.01);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;">&nbsp;&nbsp;&nbsp;↳ <b>Written-Off Premium</b> — Cancelled (not collectable)</td>
            <td style="padding: 12px 15px; text-align: right; color: #FF6B6B; font-size: 14px; font-weight: bold;">{active_summary['WrittenOff_Premium']:,.2f}</td>
        </tr>
        <tr style="background-color: rgba(220,20,60,0.07); border-bottom: 1px solid rgba(220,20,60,0.3);">
            <td style="padding: 13px 15px; color: #FFFFFF; font-size: 14px; font-weight: bold;">Actual Premium (Paid + Late)</td>
            <td style="padding: 13px 15px; text-align: right; color: #FFFFFF; font-size: 15px; font-weight: 800;">{active_summary['Actual_Premium']:,.2f}</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;"><b>Claims — {claims_type_label}</b>
                {"<br><span style='font-size:11px;color:#FF8C00;'>⚠ Retail has no monetary claim amount in the raw data. This is a Poisson×Gamma GLM actuarial estimate only.</span>" if segment_key in ("Retail","Combined") else ""}
            </td>
            <td style="padding: 12px 15px; text-align: right; color: #DC143C; font-size: 14px; font-weight: bold;">{active_summary['Actual_Claims']:,.2f}</td>
        </tr>
        <tr style="border-bottom: 2px solid #0E0E12; background-color: rgba(255,255,255,0.01);">
            <td style="padding: 12px 15px; color: #A5AAB5; font-size: 14px;"><b>Rejected Claims</b> (Audited &amp; Disapproved)</td>
            <td style="padding: 12px 15px; text-align: right; color: #A5AAB5; font-size: 14px; font-weight: bold;">{rej_str}</td>
        </tr>
        <tr style="background-color: rgba(220,20,60,0.05); border-bottom: 1px solid rgba(220,20,60,0.2);">
            <td style="padding: 14px 15px; color: #FFFFFF; font-size: 14px; font-weight: bold;">Gross Collection Rate (Actual / Billed)</td>
            <td style="padding: 14px 15px; text-align: right; color: #32CD32; font-size: 15px; font-weight: 800;">{active_summary['Collection_Rate']:.2f}%</td>
        </tr>
        <tr style="background-color: rgba(178,34,34,0.05);">
            <td style="padding: 14px 15px; color: #FFFFFF; font-size: 14px; font-weight: bold;">Loss Ratio (Claims / Actual Premium)</td>
            <td style="padding: 14px 15px; text-align: right; color: #FF4500; font-size: 15px; font-weight: 800;">{active_summary['Loss_Ratio']:.2f}%</td>
        </tr>
    </tbody>
</table>
"""
st.markdown(table_html.replace("\n", ""), unsafe_allow_html=True)

# ── Data quality note on retail claims ──────────────────────────────────────
if segment_key == "Retail":
    st.info(
        "**Retail Claims Data Limitation:** The retail dataset contains `Claim_Frequency` (count) "
        "and `Claim_Severity` (category: None / Low / Medium / High / Critical) but **no GHS claim "
        "amount column**. The figure above is a Poisson × Gamma GLM actuarial estimate using "
        "severity midpoints (Low=GHS 7,500, Medium=GHS 17,500, High=GHS 37,500, Critical=GHS 62,500). "
        f"Observed data: **{active_summary.get('Claimants',0):,} policyholders** filed at least one "
        f"claim | **{active_summary.get('Total_Claim_Events',0):,} total claim events** recorded."
    )
elif segment_key == "Combined":
    st.info(
        "**Mixed claims data:** Corporate claims (GHS 47.2M) are real approved amounts from the "
        "Claims transaction sheet. Retail claims (GHS 717.8M) are Poisson × Gamma GLM estimates — "
        "the retail dataset records only claim count and severity category, not GHS amounts. "
        f"Observed retail: **{active_summary.get('Claimants',0):,} policyholders** with claims "
        f"| **{active_summary.get('Total_Claim_Events',0):,} total claim events.**"
    )
elif segment_key == "Corporate":
    st.info(
        "**Corporate claims are actual approved amounts** sourced from the Claims transaction sheet. "
        "Approved: GHS 47,248,039 | Rejected: GHS 7,603,156."
    )

# --- Financial Breakdowns Section ---
st.subheader("Underwriting & Collection Breakdowns")
st.markdown("""
Drill down into premium billing, collection performance, and actual claims payouts grouped by **Company (Corporate Accounts)**, **Insurance Product Type**, or **Sales Agent**.
""")

breakdown_type = st.radio("Group Breakdown By:", options=["Company Name", "Insurance Product Type", "Sales Agent"], horizontal=True)

# Get financial breakdown df
df_breakdown = utils.get_financial_breakdowns(df_retail, df_corp)

# Filter by segment if needed
if segment == "Retail Segment":
    df_breakdown_filtered = df_breakdown[df_breakdown['Portfolio_Type'] == 'Retail'].copy()
elif segment == "Corporate Segment":
    df_breakdown_filtered = df_breakdown[df_breakdown['Portfolio_Type'] == 'Corporate'].copy()
else:
    df_breakdown_filtered = df_breakdown.copy()

# Group by the selected option
group_col = {
    "Company Name": "Company_Name",
    "Insurance Product Type": "Product_Applied",
    "Sales Agent": "Agent_Name"
}[breakdown_type]

# Group and aggregate — WrittenOff_Premium holds Cancelled for retail, Pending_Premium for corporate
df_grouped = df_breakdown_filtered.groupby(group_col).agg(
    Estimated_Premium=('Billed_Premium',    'sum'),
    Paid_Premium=     ('Collected_Premium', 'sum'),
    Late_Premium=     ('Late_Premium',      'sum'),
    Pending_Premium=  ('Pending_Premium',   'sum'),
    WrittenOff_Premium=('WrittenOff_Premium', 'sum'),
    Actual_Claims=    ('Actual_Claims',     'sum'),
    Rejected_Claims=  ('Rejected_Claims',   'sum')
).reset_index()

df_grouped['Total_Receivable'] = df_grouped['Paid_Premium'] + df_grouped['Late_Premium']
df_grouped['Collection_Rate'] = (df_grouped['Total_Receivable'] / df_grouped['Estimated_Premium'].replace(0, 1)) * 100
df_grouped['Loss_Ratio'] = (df_grouped['Actual_Claims'] / df_grouped['Total_Receivable'].replace(0, 1)) * 100

# Format for display
df_grouped_display = df_grouped.copy()
df_grouped_display['Billed (GHS)']        = df_grouped_display['Estimated_Premium'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Paid (GHS)']          = df_grouped_display['Paid_Premium'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Late/Overdue (GHS)']  = df_grouped_display['Late_Premium'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Pending (GHS)']       = df_grouped_display['Pending_Premium'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Written Off (GHS)']   = df_grouped_display['WrittenOff_Premium'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Total Receivable (GHS)'] = df_grouped_display['Total_Receivable'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Rejected (GHS)']   = df_grouped_display['Rejected_Claims'].apply(lambda x: f"{x:,.0f}")
df_grouped_display['Collection %']    = df_grouped_display['Collection_Rate'].apply(lambda x: f"{x:.1f}%")
df_grouped_display['Loss Ratio %']    = df_grouped_display['Loss_Ratio'].apply(lambda x: f"{x:.1f}%")

# Label the claims column to make the source clear
if segment == "Retail Segment":
    claims_col_name = "GLM Est. Claims (GHS)"
    claims_note_txt = "Retail: no raw GHS claim amounts in dataset — GLM estimate shown"
elif segment == "Corporate Segment":
    claims_col_name = "Approved Claims (GHS)"
    claims_note_txt = "Corporate: actual approved claim amounts from Claims sheet"
else:
    claims_col_name = "Claims — Retail=GLM / Corp=Actual (GHS)"
    claims_note_txt = "Retail figure = GLM estimate (no raw GHS data). Corporate figure = actual approved amounts."

df_grouped_display[claims_col_name] = df_grouped_display['Actual_Claims'].apply(lambda x: f"{x:,.0f}")

cols_display = [group_col,
                'Billed (GHS)', 'Paid (GHS)', 'Late/Overdue (GHS)',
                'Written Off (GHS)', 'Total Receivable (GHS)',
                claims_col_name, 'Rejected (GHS)',
                'Collection %', 'Loss Ratio %']
df_grouped_display = df_grouped_display[cols_display].rename(columns={group_col: breakdown_type})

st.caption(f"**Claims column note:** {claims_note_txt}")

# Show Premium Interactive Table
st.dataframe(df_grouped_display, use_container_width=True)

# Billed vs Receivable vs Actual Claims — top 10 by claims
df_plot = df_grouped.sort_values(by='Actual_Claims', ascending=False).head(10)
fig_breakdown = px.bar(
    df_plot,
    x=group_col,
    y=['Estimated_Premium', 'Total_Receivable', 'Actual_Claims'],
    barmode='group',
    labels={group_col: breakdown_type, "value": "Amount (GHS)", "variable": "Financial Indicator"},
    title=f"Top 10: Billed vs Receivable (Paid+Late) vs Claims — by {breakdown_type}",
    color_discrete_map={
        "Estimated_Premium": "#A5AAB5",
        "Total_Receivable":  "#FFFFFF",
        "Actual_Claims":     "#DC143C"
    }
)
fig_breakdown.update_layout(
    plot_bgcolor="#14141A",
    paper_bgcolor="#08080A",
    font_color="#F5F5F7",
    height=400
)
st.plotly_chart(fig_breakdown, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("View Actuarial Proof of Underwriting Deficits"):
    st.markdown("### Actuarial Proof: Why the Company is Losing Money")
    st.markdown("""
    A common misconception is that poor collections are the primary driver of underwriting losses.
    Below is the mathematical proof that **systemic flat-rate underpricing** is the root cause,
    and that 100% collections alone cannot restore solvency.
    """)

    if segment_key == "Combined":
        comb_s = summary['Combined']
        ret_s  = summary['Retail']
        corp_s = summary['Corporate']
        st.markdown(f"""
        1. **The Collections Failure Illusion:**
           * Even collecting 100% of all billed premiums, the combined receivable is **GHS {comb_s['Actual_Premium']/1e6:.1f}M** against expected claims of **GHS {comb_s['Actual_Claims']/1e6:.1f}M** — 
             a **{comb_s['Loss_Ratio']:.0f}% loss ratio**. Collections fixes save nothing meaningful.
        2. **The Underwriting Mismatch Reality:**
           * Retail billed premiums: **GHS {ret_s['Estimated_Premium']/1e6:.1f}M** (annualised). Expected claims: **GHS {ret_s['Actual_Claims']/1e6:.1f}M** — 
             {ret_s['Actual_Claims']/max(ret_s['Estimated_Premium'],1):.1f}× the billed amount.
        3. **The MTN Ghana Corporate Case:**
           * MTN Ghana approved claims: **GHS 13.37M** against total corporate receivable of **GHS {corp_s['Actual_Premium']/1e6:.1f}M**.
        4. **Statistical Proof (Poisson GLM):**
           * Premiums are completely uncorrelated with risk factors (OLS R² = 0.000). 
             Age (the primary risk driver) has near-zero weight in current pricing.
        """)
    elif segment_key == "Retail":
        ret_s = summary['Retail']
        ret_deficit = ret_s['Actual_Claims'] - ret_s['Actual_Premium']
        n_retail = len(df_retail)
        avg_deficit = ret_deficit / max(n_retail, 1)
        st.markdown(f"""
        1. **The Collections Failure Illusion:**
           * Retail total receivable (Paid + Late) = **GHS {ret_s['Actual_Premium']/1e6:.1f}M**. Expected claims = **GHS {ret_s['Actual_Claims']/1e6:.1f}M**. 
             Even 100% collections covers only **{ret_s['Actual_Premium']/max(ret_s['Actual_Claims'],1)*100:.0f}%** of expected claims.
        2. **The Underwriting Mismatch:**
           * Every one of the {n_retail:,} retail policyholders has expected loss > paid premium. 
             Avg annual deficit per policyholder = **GHS {avg_deficit:,.0f}**. 
             Total retail deficit = **GHS {ret_deficit/1e6:.1f}M**.
        """)
    else:
        corp_s = summary['Corporate']
        st.markdown(f"""
        1. **The Collections Failure Illusion:**
           * Corporate total receivable (Paid + Late from payment sheet) = **GHS {corp_s['Actual_Premium']/1e6:.1f}M**. 
             Approved claims = **GHS {corp_s['Actual_Claims']/1e6:.1f}M** — a **{corp_s['Loss_Ratio']:.0f}% loss ratio**. 
             Even 100% collections covers only {corp_s['Actual_Premium']/max(corp_s['Actual_Claims'],1)*100:.0f}% of claims.
        2. **The MTN Ghana Case:**
           * MTN Ghana: approved claims **GHS 13.37M** against flat annual premiums collected. 
             This single account accounts for 28% of all corporate approved claims.
        3. **Operational Backdoor:**
           * **24 corporate claims** approved in ≤ 3 days — mandatory 7-day hold required.
        """)

    st.error("""
    **Executive Verdict:**
    Prudential's underwriting losses are structurally baked into its base product pricing.
    Premium collection optimization cannot save the company.
    A minimum 2.94× rate increase (retail) and full renegotiation of corporate group contracts
    are required for solvency.
    """)

st.markdown("<br>", unsafe_allow_html=True)

# 1. Boxplot Visualization of Flat Pricing Gap
st.subheader("The Pricing-to-Risk Disconnect Visualized")
st.markdown("""
A healthy, risk-adjusted portfolio should show higher premiums for higher risk categories. 
Currently, the premium distributions are nearly identical (flat) across all risk bands, 
exposing the company to massive, unpriced claim frequencies in the High and Critical Risk tiers.
""")

fig_pricing = px.box(
    active_df, 
    x='Risk_Category', 
    y='Premium_GHS',
    color='Risk_Category',
    category_orders={"Risk_Category": ["Low Risk", "Medium Risk", "High Risk", "Critical Risk"]},
    color_discrete_map={
        "Low Risk": "#FFFFFF",
        "Medium Risk": "#A5AAB5",
        "High Risk": "#DC143C",
        "Critical Risk": "#8B0000"
    },
    title=f"Premium Distribution by Risk Category ({segment})"
)
fig_pricing.update_layout(
    plot_bgcolor="#14141A",
    paper_bgcolor="#08080A",
    font_color="#F5F5F7",
    height=450
)
st.plotly_chart(fig_pricing, use_container_width=True)

# 2. Section 5: The 12 Key Business Questions and Visualizations (Dynamic Segment Symmetrical Q&A)
st.markdown("---")
st.header(f"Executive Answers to the 12 Key Business Questions ({segment})")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Q1 - Q4: Risk Profiles & Losses", 
    "Q5 - Q8: Deficits & Branch Performance", 
    "Q9 - Q12: Operations & Cash Management",
    "Payment & Collection Analytics",
    "Actuarial Solvency & Monte Carlo"
])

if segment == "Combined Portfolio":
    with tab1:
        st.markdown("### Q1: Who are our highest-risk exposures and products?")
        st.markdown("""
        * **Retail highest-risk:** Emily Burke (Critical Risk, Score 93), Colleen Butler (Critical Risk, Score 93), Kerry Mcintyre PhD (Critical Risk, Score 102).
        * **Corporate highest-risk:** David Singh (Ashesi, Risk Score 125), April Frazier (Ashesi, 120).
        * **Highest-risk products:** All 6 retail products run at 293–297% loss ratio. Corporate group plans run at 647%+ loss ratio.
        * **Business Implication:** Apply risk-based pricing caps at all renewals. Corporate group contracts must move to experience-rated pricing.
        """)

        st.markdown("### Q2: What variables drive the size/cost of claims?")
        st.markdown("""
        * **Corrected Finding (Gamma GLM):** Age is the only significant driver of claim severity (coef = +0.104, p < 0.001). BMI is completely non-significant (p = 0.999). Each SD increase in age raises expected claim amount by ~11%.
        * **Business Implication:** Focus underwriting on age-band rating. Deductibles and co-insurance are the correct tools to control severity — demographics cannot predict claim size with precision.
        """)

        st.markdown("### Q3: Which clients and products have the highest claim payouts?")

        # Dynamic: compute retail product-level expected claims from the breakdown data
        ret_breakdown = df_breakdown[df_breakdown['Portfolio_Type'] == 'Retail'].copy()
        ret_by_product = ret_breakdown.groupby('Product_Applied')['Actual_Claims'].sum().sort_values(ascending=False)
        # Corporate top clients from claims sheet
        df_q3_items = []
        # Add top 3 corporate
        df_q3_items.append({"Source": "MTN Ghana (Corporate)", "Claims (Million GHS)": 13.37, "Segment": "Corporate"})
        df_q3_items.append({"Source": "GCB Bank (Corporate)", "Claims (Million GHS)": 8.94, "Segment": "Corporate"})
        df_q3_items.append({"Source": "Enterprise Ins. (Corporate)", "Claims (Million GHS)": 7.26, "Segment": "Corporate"})
        # Add top 3 retail products (dynamic)
        for prod, claims_val in ret_by_product.head(3).items():
            df_q3_items.append({"Source": f"{prod} (Retail GLM)", "Claims (Million GHS)": round(claims_val / 1e6, 2), "Segment": "Retail"})
        df_q3_comb = pd.DataFrame(df_q3_items)
        fig_q3_comb = px.bar(df_q3_comb, y='Source', x='Claims (Million GHS)', color='Segment', orientation='h',
            title="Highest Expected Claim Sources Across Both Segments (GHS)",
            color_discrete_map={"Retail": "#FFFFFF", "Corporate": "#DC143C"})
        fig_q3_comb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=380)
        st.plotly_chart(fig_q3_comb, use_container_width=True)
        if len(ret_by_product) > 0:
            top_prod = ret_by_product.index[0]
            top_prod_claims = ret_by_product.iloc[0] / 1e6
            st.markdown(f"""
        * **Retail:** {top_prod} expected claims **GHS {top_prod_claims:.2f}M** (highest retail product).
        * **Corporate:** MTN Ghana approved claims **GHS 13.37M** — largest single corporate exposure.
            """)

        st.markdown("### Q4: Are our product premiums sufficient to cover claims?")
        # Dynamic values from summary
        ret_summ = summary['Retail']
        corp_summ = summary['Corporate']
        ret_recv_m = ret_summ['Actual_Premium'] / 1e6
        ret_claims_m = ret_summ['Actual_Claims'] / 1e6
        corp_recv_m = corp_summ['Actual_Premium'] / 1e6
        corp_claims_m = corp_summ['Actual_Claims'] / 1e6
        st.markdown(f"""
        * **No.** All retail products and all corporate group plans run at significant loss ratios.
        * Retail receivable (Paid+Late): **GHS {ret_recv_m:.1f}M** vs expected claims **GHS {ret_claims_m:.1f}M** ({ret_summ['Loss_Ratio']:.0f}% loss ratio).
        * Corporate receivable (Paid+Late): **GHS {corp_recv_m:.1f}M** vs approved claims **GHS {corp_claims_m:.1f}M** ({corp_summ['Loss_Ratio']:.0f}% loss ratio).
        """)
        df_q4_comb = pd.DataFrame([
            {"Segment": "Retail", "Type": "Receivable (Paid+Late)", "Amount (Million GHS)": round(ret_recv_m, 1)},
            {"Segment": "Retail", "Type": "Expected Claims (GLM)", "Amount (Million GHS)": round(ret_claims_m, 1)},
            {"Segment": "Corporate", "Type": "Receivable (Paid+Late)", "Amount (Million GHS)": round(corp_recv_m, 1)},
            {"Segment": "Corporate", "Type": "Approved Claims", "Amount (Million GHS)": round(corp_claims_m, 1)},
        ])
        fig_q4_comb = px.bar(df_q4_comb, x="Segment", y="Amount (Million GHS)", color="Type", barmode="group",
            title="Receivable (Paid+Late) vs Claims: Retail vs Corporate",
            color_discrete_map={"Receivable (Paid+Late)": "#FFFFFF", "Expected Claims (GLM)": "#DC143C",
                                "Approved Claims": "#DC143C"})
        fig_q4_comb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q4_comb, use_container_width=True)

    with tab2:
        st.markdown("### Q5: Who are the clients/individuals where expected loss exceeds premium?")
        st.markdown("""
        * **100% of both portfolios** — all 50,000 retail policyholders and all 1,974 corporate employees.
        * Retail avg annual deficit per policyholder: **GHS 11,388**.
        * Top retail: Emily Burke (deficit **GHS 38,202**), Colleen Butler (**GHS 38,082**).
        """)

        st.markdown("### Q6: Can Risk Scores predict claim frequency?")
        st.markdown("""
        * **Yes** — Pearson correlation = 0.799, Spearman = 0.795 (from notebook OLS Model 4, R² = 0.915).
        * Note: some of this correlation is mechanical since Risk_Score is partly derived from Claim_Frequency. The Poisson GLM provides the causal, independent estimate — Age coef = +0.324 (z=249, p<0.001).
        """)

        st.markdown("### Q7: Which regional branches are performing best/worst?")
        df_q7_comb = pd.DataFrame([
            {"Branch": "Cape Coast", "Deficit (Million GHS)": 58.3, "Type": "Retail Deficit"},
            {"Branch": "Accra",      "Deficit (Million GHS)": 58.3, "Type": "Retail Deficit"},
            {"Branch": "Kumasi",     "Deficit (Million GHS)": 59.1, "Type": "Retail Deficit"},
            {"Branch": "Takoradi",   "Deficit (Million GHS)": 59.4, "Type": "Retail Deficit"},
            {"Branch": "Ho",         "Deficit (Million GHS)": 59.4, "Type": "Retail Deficit"},
            {"Branch": "Tamale",     "Deficit (Million GHS)": 59.4, "Type": "Retail Deficit"},
            {"Branch": "Koforidua",  "Deficit (Million GHS)": 59.8, "Type": "Retail Deficit"},
            {"Branch": "Sunyani",    "Deficit (Million GHS)": 60.2, "Type": "Retail Deficit"},
        ])
        fig_q7_comb = px.bar(df_q7_comb, x='Branch', y='Deficit (Million GHS)', color='Type',
            title="Retail Underpricing Deficit by Region (Claims − Receivable, GHS Million)",
            color_discrete_map={"Retail Deficit": "#DC143C"})
        fig_q7_comb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q7_comb, use_container_width=True)
        st.markdown("* **Worst retail region:** Sunyani (deficit **GHS 60.2M**), Koforidua (GHS 59.8M). All regions are severely loss-making.")

        st.markdown("### Q8: Do we have rushed claims?")
        st.markdown("""
        * **24 corporate claims** approved in ≤ 3 days — implement mandatory 7-day validation hold.
        * Retail has no transaction-level approval tracking — must be built into the system.
        """)

    with tab3:
        st.markdown("### Q9: Do smokers claim more frequently than non-smokers?")
        st.markdown("""
        * **No.** Non-smokers: **0.664 claims/year** (retail). Smokers: **0.653 claims/year** (retail).
        * Poisson GLM confirms: Smoker coefficient = **−0.018** (p < 0.001) — smokers claim marginally LESS.
        * The old +15 scorecard penalty was not supported by data. Reduced to +5 pts.
        """)

        st.markdown("### Q10: How volatile is our monthly cash float?")
        st.markdown("""
        * **Retail:** ~GHS 20.3M/month receivable (Paid+Late = GHS 243.9M ÷ 12). Stable but insufficient.
        * **Corporate:** GHS 37,800 – GHS 367,810/month (highly volatile per payment sheet).
        * Hold high-liquidity reserves to handle corporate claim spikes.
        """)

        st.markdown("### Q11: Where are the claim processing bottlenecks?")
        df_q11_comb = pd.DataFrame([
            {"Agent": "Benjamin Nyarko", "Deficit (Million GHS)": 36.9, "Type": "Retail Deficit"},
            {"Agent": "Collins Addae",   "Deficit (Million GHS)": 36.9, "Type": "Retail Deficit"},
            {"Agent": "Isaac Tetteh",    "Deficit (Million GHS)": 36.3, "Type": "Retail Deficit"},
            {"Agent": "Stephen Kwarteng","Deficit (Million GHS)": 35.8, "Type": "Retail Deficit"},
            {"Agent": "Naa Adoley",      "Deficit (Million GHS)": 35.7, "Type": "Retail Deficit"},
        ])
        fig_q11_comb = px.bar(df_q11_comb, x='Deficit (Million GHS)', y='Agent', color='Type', orientation='h',
            title="Top Agents by Underpricing Deficit Booked (Retail)",
            color_discrete_map={"Retail Deficit": "#DC143C"})
        fig_q11_comb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q11_comb, use_container_width=True)

        st.markdown("### Q12: How well does the predictive model forecast claim frequency?")
        st.markdown("""
        * **Poisson GLM (corrected):** Age is the only significant predictor (coef = +0.324, z = 249, p < 0.001).
        * Income (p = 0.304) and Dependents (p = 0.475) are not significant.
        * Age-band rating multipliers: ≤30: 1.0×, 31–45: 1.38×, 46–60: 1.90×, >60: 2.62× (derived from e^β).
        """)

    with tab4:
        st.markdown("### Portfolio Payment Mode & Collection Analytics")
        df_pm_ret_comb = df_retail.groupby('Payment_Method')['Pricing_Deficit'].mean().reset_index().rename(
            columns={'Pricing_Deficit': 'Avg Deficit (GHS)', 'Payment_Method': 'Method'})
        df_pm_ret_comb['Segment'] = 'Retail'
        df_pm_corp_comb = df_corp.groupby('Payment_Method')['Pricing_Deficit'].mean().reset_index().rename(
            columns={'Pricing_Deficit': 'Avg Deficit (GHS)', 'Payment_Method': 'Method'})
        df_pm_corp_comb['Segment'] = 'Corporate'
        df_pm_comb_dyn = pd.concat([df_pm_ret_comb, df_pm_corp_comb], ignore_index=True)
        fig_pm_comb = px.bar(df_pm_comb_dyn, x="Method", y="Avg Deficit (GHS)", color="Segment", barmode="group",
            title="Average Pricing Deficit by Payment Method (GHS)",
            color_discrete_map={"Retail": "#FFFFFF", "Corporate": "#DC143C"})
        fig_pm_comb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=380)
        st.plotly_chart(fig_pm_comb, use_container_width=True)
        st.markdown("* **OLS R² = 0.000** — payment method explains zero variation in the deficit. Loss is structural underpricing, not payment behaviour.")

    with tab5:
        st.markdown("### Actuarial Policy Pricing Audit & Solvency Capital Analysis")
        solv_col1, solv_col2, solv_col3 = st.columns(3)
        with solv_col1:
            st.metric("Total Receivable (Paid+Late)", "GHS 251.2M")
        with solv_col2:
            st.metric("Total Expected Claims", "GHS 765.0M")
        with solv_col3:
            st.metric("Combined Loss Ratio", "304.6%", delta="Structurally insolvent", delta_color="inverse")
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("Monte Carlo Expected Claims", "GHS 823.5M")
        with mc2:
            st.metric("99% VaR (1-in-100 yr)", "GHS 834.4M")
        with mc3:
            st.metric("Solvency Capital Required", "GHS 544.7M", delta="Reserve needed", delta_color="inverse")

        st.markdown("""
        <div class="premium-card" style="border-left: 5px solid #DC143C; margin-bottom: 20px;">
            <h4 style="color: #FFFFFF; margin-top: 0; font-weight: 700;">Solvency Waterfall (Corrected GLM — 50k Deduplicated Retail)</h4>
            <ul style="color: #A5AAB5; font-size: 14px; line-height: 1.6; margin-bottom: 0;">
                <li><b>Retail billed premiums:</b> GHS 285.1M | Paid: GHS 162.9M | Late/Overdue: GHS 81.0M | Written-off: GHS 41.3M</li>
                <li><b>Retail receivable (Paid+Late):</b> GHS 243.9M</li>
                <li><b>Retail expected claims (Poisson × Gamma GLM):</b> GHS 717.8M — 2.94× receivable</li>
                <li><b>Corporate receivable (Paid+Late):</b> GHS 7.3M (from payment sheet: Paid GHS 5.6M + Late GHS 1.7M)</li>
                <li><b>Corporate approved claims:</b> GHS 47.2M — 6.47× receivable</li>
                <li><b>Combined receivable:</b> GHS 251.2M vs <b>combined claims GHS 765.0M → 304.6% loss ratio</b></li>
                <li><b>Monte Carlo (1,000 trials, Poisson×Lognormal):</b> Expected claims GHS 823.5M | 99% VaR GHS 834.4M | Solvency capital required GHS 544.7M</li>
                <li><b>Minimum rate increase needed:</b> 2.94× retail | 6.47× corporate | Investable surplus: GHS 0</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Top 5 Underpriced Retail Individuals (GLM-Based)")
        df_pricing_audit = pd.DataFrame([
            {"Full Name": "Emily Burke",          "Risk Score": 93,  "Current Annual Premium (GHS)": 844,    "Recommended (GHS)": 39046, "Deficit (GHS)": 38202},
            {"Full Name": "Colleen Butler",        "Risk Score": 93,  "Current Annual Premium (GHS)": 912,    "Recommended (GHS)": 38994, "Deficit (GHS)": 38082},
            {"Full Name": "Sherri Rodriguez",      "Risk Score": 95,  "Current Annual Premium (GHS)": 1249,   "Recommended (GHS)": 38655, "Deficit (GHS)": 37406},
            {"Full Name": "Kerry Mcintyre PhD",    "Risk Score": 102, "Current Annual Premium (GHS)": 803,    "Recommended (GHS)": 38013, "Deficit (GHS)": 37210},
            {"Full Name": "Melanie Mclaughlin",    "Risk Score": 102, "Current Annual Premium (GHS)": 1820,   "Recommended (GHS)": 38901, "Deficit (GHS)": 37082},
        ])
        st.dataframe(df_pricing_audit.style.format({c: "{:,.0f}" for c in df_pricing_audit.columns if "(GHS)" in c}), use_container_width=True)
        st.caption("Source: Poisson GLM × Gamma GLM expected loss + risk loading. Based on 50,000 deduplicated policyholders.")

        st.markdown("#### VIF Diagnostics")
        df_vif = pd.DataFrame([
            {"Variable": "Age",                 "VIF": 11.72, "Status": "High (correlated with Risk_Score — expected)"},
            {"Variable": "BMI",                 "VIF": 19.12, "Status": "High (same reason)"},
            {"Variable": "Monthly Income",      "VIF": 3.83,  "Status": "OK"},
            {"Variable": "Dependents",          "VIF": 3.45,  "Status": "OK"},
            {"Variable": "Claim Frequency",     "VIF": 6.36,  "Status": "Moderate"},
            {"Variable": "Premium (GHS)",       "VIF": 5.02,  "Status": "Borderline"},
            {"Variable": "Risk Score",          "VIF": 42.89, "Status": "Very high (composite — exclude from GLM inputs)"},
        ])
        st.dataframe(df_vif, use_container_width=True)

elif segment == "Retail Segment":
    with tab1:
        st.markdown("### Q1: Who are our highest-risk retail individuals and products?")
        st.markdown("""
        * **Highest-risk individuals (corrected scorecard):** Emily Burke (Score 93, Critical Risk, deficit GHS 38,202), Colleen Butler (Score 93, deficit GHS 38,082), Kerry Mcintyre PhD (Score 102).
        * **All 6 products** run at 293–297% loss ratio. Highest: Mekakrawa (297.4%).
        """)

        st.markdown("### Q2: What variables drive claim size?")
        st.markdown("""
        * **Corrected (Gamma GLM):** Age is the only significant severity driver (coef = +0.104, p < 0.001). BMI is completely non-significant (p = 0.999).
        * Focus underwriting on age-band rating and deductibles — not BMI or smoking surcharges.
        """)

        st.markdown("### Q3: Which retail products have the highest expected claim payouts?")
        df_q3_ret = pd.DataFrame({
            'Product': ['Ultimate Premier Farewell', 'Pru Wealth Plan', 'Prudent Life Plan',
                        'Travel Insurance Plan', 'Mekakrawa', 'Dignity Farewell Plan'],
            'Expected Claims (Million GHS)': [118.4, 118.5, 119.6, 120.0, 120.5, 120.7]
        })
        fig_q3_ret = px.bar(df_q3_ret, y='Product', x='Expected Claims (Million GHS)', orientation='h',
            title="Expected Annual Claims by Retail Product — GLM-Based (GHS Million)",
            color='Expected Claims (Million GHS)', color_continuous_scale=["#FFFFFF", "#DC143C"])
        fig_q3_ret.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q3_ret, use_container_width=True)
        st.markdown("* **Dignity Farewell Plan:** Expected claims GHS 120.75M vs receivable GHS 41.1M (293.6% loss ratio).")

        st.markdown("### Q4: Are retail product premiums sufficient?")
        st.markdown("* No. All products run at 293–297% loss ratio. Every GHS 1 collected generates GHS 2.94 in expected claims.")
        df_q4_ret = pd.DataFrame([
            {"Product": "Dignity Farewell",  "Type": "Receivable (Paid+Late)", "Amount (M GHS)": 41.1},
            {"Product": "Dignity Farewell",  "Type": "Expected Claims (GLM)",  "Amount (M GHS)": 120.7},
            {"Product": "Mekakrawa",         "Type": "Receivable (Paid+Late)", "Amount (M GHS)": 40.5},
            {"Product": "Mekakrawa",         "Type": "Expected Claims (GLM)",  "Amount (M GHS)": 120.5},
            {"Product": "Prudent Life",      "Type": "Receivable (Paid+Late)", "Amount (M GHS)": 40.5},
            {"Product": "Prudent Life",      "Type": "Expected Claims (GLM)",  "Amount (M GHS)": 119.6},
        ])
        fig_q4_ret = px.bar(df_q4_ret, x="Product", y="Amount (M GHS)", color="Type", barmode="group",
            title="Retail: Receivable (Paid+Late) vs Expected Claims per Product",
            color_discrete_map={"Receivable (Paid+Late)": "#FFFFFF", "Expected Claims (GLM)": "#DC143C"})
        fig_q4_ret.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q4_ret, use_container_width=True)

    with tab2:
        st.markdown("### Q5: Who are retail customers where expected loss exceeds premium?")
        st.markdown("""
        * **100% of 50,000 policyholders** (corrected deduplication — raw CSV had 950k rows inflated 19×).
        * Average deficit: **GHS 11,388/yr** per policyholder. Total retail deficit: **GHS 569.4M**.
        * Top 3: Emily Burke (GHS 38,202), Colleen Butler (GHS 38,082), Sherri Rodriguez (GHS 37,406).
        """)

        st.markdown("### Q6: Can Risk Scores predict retail claim frequency?")
        st.markdown("""
        * **Yes** — correlation = 0.799 (Pearson). But note: Risk_Score contains Claim_Frequency in its formula, so this is partly mechanical.
        * Independent causal estimate: Poisson GLM, Age coef = **+0.324** (z = 249). Each SD age increase → 38% more claims.
        """)

        st.markdown("### Q7: Which retail regions are performing worst?")
        df_q7_ret = pd.DataFrame({
            'Region': ['Cape Coast', 'Accra', 'Kumasi', 'Takoradi', 'Ho', 'Tamale', 'Koforidua', 'Sunyani'],
            'Deficit (Million GHS)': [58.3, 58.3, 59.1, 59.4, 59.4, 59.4, 59.8, 60.2]
        })
        fig_q7_ret = px.bar(df_q7_ret, x='Region', y='Deficit (Million GHS)',
            color='Deficit (Million GHS)', color_continuous_scale=["#FFFFFF", "#DC143C"],
            title="Retail Claims − Receivable Deficit by Region (GHS Million)")
        fig_q7_ret.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q7_ret, use_container_width=True)
        st.markdown("* **Worst:** Sunyani (GHS 60.2M deficit), Koforidua (GHS 59.8M). All regions are severely loss-making.")

        st.markdown("### Q8: Do we have rushed claims in Retail?")
        st.markdown("* Retail records only contain annualised claim summaries — no transaction-level approval timestamps. Must be built into system.")

    with tab3:
        st.markdown("### Q9: Do smokers claim more frequently than non-smokers?")
        st.markdown("""
        * **No.** Non-smokers: **0.664 claims/yr**. Smokers: **0.653 claims/yr**.
        * Poisson GLM confirms: Smoker coef = **−0.018** (p < 0.001). The old +15 pt smoking surcharge had no data support.
        """)

        st.markdown("### Q10: Monthly retail cash float?")
        st.markdown("""
        * Retail total receivable (Paid+Late): **GHS 243.9M/yr** → ~GHS 20.3M/month.
        * Billed but written-off (Cancelled): **GHS 41.3M/yr** — never recovered.
        * Expected claims: **GHS 717.8M/yr** → ~GHS 59.8M/month. Cash shortfall every month.
        """)

        st.markdown("### Q11: Retail processing bottlenecks (agent deficits)?")
        df_q11_ret = pd.DataFrame({
            'Sales Agent': ['Evelyn Agyeman', 'Mabel Osei', 'Naa Adoley', 'Stephen Kwarteng', 'Isaac Tetteh',
                            'Collins Addae', 'Benjamin Nyarko'],
            'Deficit Booked (M GHS)': [35.1, 35.2, 35.7, 35.8, 36.3, 36.9, 36.9]
        }).sort_values('Deficit Booked (M GHS)', ascending=True)
        fig_q11_ret = px.bar(df_q11_ret, x='Deficit Booked (M GHS)', y='Sales Agent', orientation='h',
            title="Retail Underpricing Deficit Booked by Agent (GHS Million)",
            color='Deficit Booked (M GHS)', color_continuous_scale=["#FFFFFF", "#DC143C"])
        fig_q11_ret.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q11_ret, use_container_width=True)
        st.markdown("* Top agents by deficit: Benjamin Nyarko (GHS 36.9M), Collins Addae (GHS 36.9M). Tie commissions to loss ratio.")

        st.markdown("### Q12: How well does the model forecast claim frequency?")
        st.markdown("""
        * **Poisson GLM:** Age coef = +0.324 (z=249, p<0.001). BMI = +0.006 (p<0.001 but small). Smoker, Income, Dependents not significant.
        * Age-band multipliers: ≤30: 1.0×, 31–45: 1.38×, 46–60: 1.90×, >60: 2.62×.
        """)

    with tab4:
        st.markdown("### Retail Payment Collection Analytics")
        col_pay1, col_pay2 = st.columns(2)
        df_ret_pm = df_retail.groupby('Payment_Method')['Pricing_Deficit'].mean().reset_index().rename(
            columns={'Pricing_Deficit': 'Avg Deficit (GHS)', 'Payment_Method': 'Payment Mode'})
        df_ret_pb = df_retail.groupby('Payment_Behavior')['Pricing_Deficit'].mean().reset_index().rename(
            columns={'Pricing_Deficit': 'Avg Deficit (GHS)', 'Payment_Behavior': 'Payment Regularity'})
        with col_pay1:
            fig_ret_pm = px.bar(df_ret_pm, x='Payment Mode', y='Avg Deficit (GHS)',
                title="Retail Deficits by Payment Mode", color_discrete_sequence=["#FFFFFF"])
            fig_ret_pm.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=320)
            st.plotly_chart(fig_ret_pm, use_container_width=True)
        with col_pay2:
            fig_ret_pb = px.bar(df_ret_pb, x='Payment Regularity', y='Avg Deficit (GHS)',
                title="Retail Deficits by Payment Regularity", color_discrete_sequence=["#DC143C"])
            fig_ret_pb.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=320)
            st.plotly_chart(fig_ret_pb, use_container_width=True)
        st.markdown("* **OLS R² = 0.000** — payment behaviour explains zero variation in deficit. Loss is structural flat-rate underpricing.")

    with tab5:
        st.markdown("### Actuarial Solvency (Retail)")
        st.markdown("Retail-only solvency position based on corrected 50k dedup and GLM models:")
        rc1, rc2, rc3 = st.columns(3)
        with rc1: st.metric("Retail Receivable (Paid+Late)", "GHS 243.9M")
        with rc2: st.metric("Expected Claims (GLM)", "GHS 717.8M")
        with rc3: st.metric("Retail Loss Ratio", "294.3%", delta="Structurally insolvent", delta_color="inverse")
        st.markdown("Switch to **Combined Portfolio** for the full Monte Carlo solvency simulation.")

elif segment == "Corporate Segment":
    with tab1:
        st.markdown("### Q1: Who are our highest-risk corporate employees and companies?")
        st.markdown("""
        * David Singh (Ashesi, Score 125), April Frazier (Ashesi, 120), Lindsey Robinson (Ashesi, 120).
        * **MTN Ghana** approved claims: GHS 13.37M — largest single exposure.
        * Corporate portfolio_type Poisson GLM effect: coef = **+0.736** (z=36.7, p<0.001) — corporate employees have **2.09×** the claim rate of comparable retail policyholders.
        """)

        st.markdown("### Q2: What drives corporate claim size?")
        st.markdown("""
        * **Gamma GLM:** Age is the only significant severity driver. BMI not significant (p = 0.999).
        * Corporate employees file more claims (2.09× rate) AND each claim is larger for older employees.
        """)

        st.markdown("### Q3: Which companies have highest payouts?")
        df_q3_corp = pd.DataFrame({
            'Company': ['Ashesi Univ.', 'AngloGold Ashanti', 'DHL Ghana', 'Kasapreko', 'Enterprise Ins.', 'GCB Bank', 'MTN Ghana'],
            'Approved Claims (M GHS)': [1.97, 4.74, 4.77, 6.19, 7.26, 8.94, 13.37]
        })
        fig_q3_corp = px.bar(df_q3_corp, y='Company', x='Approved Claims (M GHS)', orientation='h',
            title="Corporate Approved Claims by Company (GHS Million)",
            color='Approved Claims (M GHS)', color_continuous_scale=["#FFFFFF", "#DC143C"])
        fig_q3_corp.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q3_corp, use_container_width=True)

        st.markdown("### Q4: Are corporate premiums sufficient?")
        st.markdown("""
        * Corporate receivable (Paid+Late): **GHS 7.3M** vs approved claims **GHS 47.2M** — **647% loss ratio**.
        * All 3 group plans run at 600%+ loss ratio. Base premiums must increase by minimum 6.47×.
        """)
        df_q4_corp = pd.DataFrame([
            {"Product": "Group Life",    "Type": "Receivable", "Amount (M GHS)": 2.4},
            {"Product": "Group Life",    "Type": "Claims",     "Amount (M GHS)": 13.84},
            {"Product": "Group Funeral", "Type": "Receivable", "Amount (M GHS)": 2.4},
            {"Product": "Group Funeral", "Type": "Claims",     "Amount (M GHS)": 14.51},
            {"Product": "Group Welfare", "Type": "Receivable", "Amount (M GHS)": 2.5},
            {"Product": "Group Welfare", "Type": "Claims",     "Amount (M GHS)": 18.90},
        ])
        fig_q4_corp = px.bar(df_q4_corp, x="Product", y="Amount (M GHS)", color="Type", barmode="group",
            title="Corporate: Receivable vs Approved Claims per Product",
            color_discrete_map={"Receivable": "#FFFFFF", "Claims": "#DC143C"})
        fig_q4_corp.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q4_corp, use_container_width=True)

    with tab2:
        st.markdown("### Q5: Who are the employees where claims exceed premiums?")
        st.markdown("""
        * All 1,974 corporate employees. 
        * Corporate receivable (Paid+Late): GHS 7.3M vs approved claims GHS 47.2M. 647% loss ratio.
        """)

        st.markdown("### Q6: Do Risk Scores predict corporate claim frequency?")
        st.markdown("""
        * Yes — Poisson GLM shows age is the dominant driver (coef = +0.324).
        * Corporate employees have 2.09× the claim rate of retail after controlling for age (GLM portfolio_type coef = +0.736).
        """)

        st.markdown("### Q7: Corporate regional performance?")
        df_q7_corp = pd.DataFrame({
            'Branch': ['Obuasi', 'Ho', 'Tamale', 'Kumasi', 'Takoradi', 'Accra'],
            'Net Loss (M GHS)': [1.84, 3.45, 4.27, 9.86, 9.94, 12.28]
        })
        fig_q7_corp = px.bar(df_q7_corp, x='Branch', y='Net Loss (M GHS)',
            color='Net Loss (M GHS)', color_continuous_scale=["#FFFFFF", "#DC143C"],
            title="Corporate Net Claims Loss by Regional Branch (GHS Million)")
        fig_q7_corp.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q7_corp, use_container_width=True)

        st.markdown("### Q8: Rushed claims?")
        st.markdown("* **24 corporate claims** approved in ≤ 3 days. Implement mandatory 7-day validation hold.")

    with tab3:
        st.markdown("### Q9: Do smokers claim more?")
        st.markdown("* No — Poisson GLM Smoker coef = −0.018 (p < 0.001). Old +15 pt penalty reduced to +5 pts.")

        st.markdown("### Q10: Corporate cash float volatility?")
        st.markdown("""
        * Payment sheet: Paid = GHS 5.6M, Late = GHS 1.7M, Pending = GHS 1.3M.
        * Monthly range: GHS 37,800 – GHS 367,810. Highly volatile — hold liquidity reserves.
        """)

        st.markdown("### Q11: Corporate processing bottlenecks?")
        df_q11_corp = pd.DataFrame({
            'Sales Agent': ['Daniel Asare', 'Kwame Mensah', 'John Mensah', 'Abena Ofori', 'Ama Boateng', 'Michael Owusu'],
            'Avg Processing (Days)': [13.2, 14.1, 14.2, 14.7, 15.1, 15.3]
        })
        fig_q11_corp = px.bar(df_q11_corp, x='Avg Processing (Days)', y='Sales Agent', orientation='h',
            title="Average Claims Processing Time by Agent (Days)",
            color='Avg Processing (Days)', color_continuous_scale=["#FFFFFF", "#DC143C"])
        fig_q11_corp.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_q11_corp, use_container_width=True)

        st.markdown("### Q12: Model forecast quality?")
        st.markdown("* Poisson GLM: Age coef = +0.324 (p<0.001). Corporate portfolio adds 2.09× multiplier. Income not significant (p=0.609).")

    with tab4:
        st.markdown("### Corporate Payment Analytics")
        df_corp_pm = df_corp.groupby('Payment_Method')['Pricing_Deficit'].mean().reset_index().rename(
            columns={'Pricing_Deficit': 'Avg Deficit (GHS)', 'Payment_Method': 'Payment Mode'})
        fig_corp_pm = px.bar(df_corp_pm, x='Payment Mode', y='Avg Deficit (GHS)',
            title="Corporate Deficits by Payment Mode", color_discrete_sequence=["#DC143C"])
        fig_corp_pm.update_layout(plot_bgcolor="#14141A", paper_bgcolor="#08080A", font_color="#F5F5F7", height=350)
        st.plotly_chart(fig_corp_pm, use_container_width=True)
        st.markdown("* OLS R² = 0.000. Payment mode has no effect on deficits — it's structural flat-rate pricing.")

    with tab5:
        st.markdown("### Corporate Solvency")
        cc1, cc2, cc3 = st.columns(3)
        with cc1: st.metric("Corporate Receivable (Paid+Late)", "GHS 7.3M")
        with cc2: st.metric("Corporate Approved Claims", "GHS 47.2M")
        with cc3: st.metric("Corporate Loss Ratio", "647.4%", delta="Structurally insolvent", delta_color="inverse")
        st.markdown("Switch to **Combined Portfolio** for the full Monte Carlo solvency simulation.")


# --- Executive Strategic Diagnosis & Corporate Action Plan ---
st.markdown("---")
st.header("Executive Strategic Diagnosis & Corporate Action Plan")

ret_p = summary['Retail']['Actual_Premium'] / 1e6
ret_c = summary['Retail']['Actual_Claims'] / 1e6
ret_lr = summary['Retail']['Loss_Ratio']
ret_def = df_retail['Pricing_Deficit'].sum() / 1e6
ret_avg_def = df_retail['Pricing_Deficit'].mean()
ret_len = len(df_retail)

corp_p = summary['Corporate']['Actual_Premium'] / 1e6
corp_c = summary['Corporate']['Actual_Claims'] / 1e6
corp_lr = summary['Corporate']['Loss_Ratio']

comb_p = summary['Combined']['Actual_Premium'] / 1e6
comb_c = summary['Combined']['Actual_Claims'] / 1e6
comb_lr = summary['Combined']['Loss_Ratio']

st.markdown(f"""
<div class="premium-card" style="border-left: 5px solid #DC143C; margin-bottom: 20px;">
    <h3 style="color: #FFFFFF; margin-top: 0; font-weight: 700;">Actuarial Diagnosis (Corrected Numbers)</h3>
    <ul style="color: #A5AAB5; font-size: 14px; line-height: 1.6;">
        <li><b>Root Cause — Flat-Rate Underpricing:</b> OLS Model 3 confirms R² = 0.000 — premiums are completely uncorrelated with risk factors. Every policyholder pays ~GHS 470.86/month regardless of actual risk profile.</li>
        <li><b>Retail Portfolio ({ret_len:,} deduplicated policyholders):</b> Receivable = GHS {ret_p:.1f}M (Paid+Late). Expected claims = GHS {ret_c:.1f}M. Expected Loss ratio = {ret_lr:.1f}%. Avg deficit = GHS {ret_avg_def:,.0f}/policyholder/yr. Total deficit = GHS {ret_def:.1f}M.</li>
        <li><b>Corporate Portfolio:</b> Receivable = GHS {corp_p:.1f}M (payment sheet). Approved claims = GHS {corp_c:.1f}M. Incurred Loss ratio = {corp_lr:.1f}%. MTN Ghana alone: GHS 13.37M in claims.</li>
        <li><b>Combined:</b> Total receivable = GHS {comb_p:.1f}M vs total claims = GHS {comb_c:.1f}M — {comb_lr:.1f}% loss ratio. Minimum rate increase: {ret_c/max(ret_p,1):.2f}× retail, {corp_c/max(corp_p,1):.2f}× corporate.</li>
        <li><b>Scorecard Correction:</b> Smoking coefficient = −0.024 (not a risk factor). Age is the sole driver (coef = +0.300, z=55.0). Age-band multipliers: 1.0× / 1.35× / 1.82× / 2.46×.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

ret_agent_def = df_retail.groupby('Agent_Name')['Pricing_Deficit'].sum().sort_values(ascending=False)
top_agent_1 = ret_agent_def.index[0]
top_agent_1_val = ret_agent_def.iloc[0] / 1e6
top_agent_2 = ret_agent_def.index[1]
top_agent_2_val = ret_agent_def.iloc[1] / 1e6

st.markdown(f"""
<div class="premium-card" style="border-left: 5px solid #32CD32; background: linear-gradient(135deg, rgba(20, 35, 20, 0.45) 0%, rgba(10, 20, 10, 0.55) 100%);">
    <h3 style="color: #FFFFFF; margin-top: 0; font-weight: 700;">Corporate Action Plan</h3>
    <ol style="color: #A5AAB5; font-size: 14px; line-height: 1.6; margin-left: 20px; padding-left: 0;">
        <li><b>Mandatory Rate Increase ({ret_c/max(ret_p,1):.2f}× retail, {corp_c/max(corp_p,1):.2f}× corporate minimum):</b>
            Deploy age-band multipliers derived from Poisson GLM: ≤30 → 1.0×, 31–45 → 1.35×, 46–60 → 1.82×, &gt;60 → 2.46×. Apply across all products immediately.
        </li>
        <li><b>Renegotiate All Corporate Contracts:</b>
            MTN Ghana (approved claims GHS 13.37M), GCB Bank (GHS 8.94M), Enterprise Insurance (GHS 7.26M) must move to experience-rated pricing with 10–20% co-insurance clauses.
        </li>
        <li><b>Deploy ML Adverse Outcome Triage:</b>
            XGBoost binary classifier (demographic features only, no leakage) routes high-adverse-probability applicants to manual underwriting.
        </li>
        <li><b>Fraud Investigation Sweep:</b>
            Implement mandatory 7-day validation hold immediately for all claims, especially rushed corporate claims (≤3 days).
        </li>
        <li><b>Align Agent Incentives:</b>
            {top_agent_1} (GHS {top_agent_1_val:.1f}M deficit) and {top_agent_2} (GHS {top_agent_2_val:.1f}M deficit) booked the highest underwriting deficits. Restructure commissions to reward loss ratio quality, not premium volume.
        </li>
    </ol>
</div>
""", unsafe_allow_html=True)
