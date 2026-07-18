# Prudential Insurance Risk Decision Support Platform

An ultra-modern, interactive decision support system built for **Prudential Life Insurance Ghana**. This platform integrates classical actuarial frameworks (Generalized Linear Models) with advanced machine learning (XGBoost) and automated anomaly detection to optimize underwriting decisions, close pricing gaps, and detect premium leakage.

---

## 🚀 Key Features

*   **Executive Dashboard**: Real-time solvency monitoring, regional revenue tracking, and interactive portfolio performance analysis.
*   **Statistical Diagnostics**: Multicollinearity (VIF) checking, Pearson/Spearman correlation heatmaps, and formal GLM regressions.
*   **Predictive Underwriting**: 4-class XGBoost machine learning model trained on all numeric features with SMOTE class balancing.
*   **Interactive Underwriting Simulator**: Real-time pricing calculator employing a **hybrid approach**:
    *   **New Enrollees** (No claims history): Underwritten using a calibrated actuarial scorecard based on demographics.
    *   **Renewals** (Claims history available): Underwritten using the high-accuracy XGBoost ML model.
*   **Batch Scoring Portal**: Upload custom rosters (`.csv`/`.xlsx`) to score whole portfolios and estimate pricing gaps in bulk.
*   **Fraud & Anomaly Audit**: Isolation Forest outlier detection coupled with expert rules to flag high-risk, rushed, or suspicious claims.
*   **Automated Presentation Compiler**: Script to generate a premium, card-based board presentation deck using Morph transitions (`python-pptx`).

---

## 📊 Actuarial & ML Methodology

1.  **Claim Frequency (Poisson GLM with Log Link)**: Models the expected claim rate per policyholder based on demographic inputs, resolving OLS's issue of negative count predictions.
2.  **Claim Severity (Gamma GLM with Log Link)**: Models positive, right-skewed claim payouts, replacing linear severity models.
3.  **XGBoost Classifier**: Multi-classification model predicting four discrete risk tiers:
    *   `Low Risk` (0)
    *   `Medium Risk` (1)
    *   `High Risk` (2)
    *   `Critical Risk` (3)
4.  **Multicollinearity (VIF)**: Standardized inputs ensure all VIF factors remain close to 1.0 (well below the 5.0 collinearity threshold), keeping regression statistics reliable.

---

## 🛠️ Setup & Installation

### Prerequisites
*   Python 3.10 or higher
*   pip or conda environment manager

### 1. Clone & Navigate
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/insurance_app.git
cd insurance_app
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Place Raw Datasets
Place the raw data files in the root folder of the project:
*   `Insurance.csv` (Retail segment)
*   `Copy of Companies Ins.Data.xlsx` (Corporate segment)

*Note: The app will automatically fall back to local absolute paths if files are not detected in the workspace.*

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

### 5. Generate the Executive Board Presentation Slide Deck
To compile the slide presentation (`board_presentation_executive.pptx`):
```bash
python generate_deck.py
```

---

## 📂 Project Structure

```
insurance_app/
├── app.py                        # Main entry point (Streamlit landing dashboard)
├── utils.py                      # Data processing, GLM computations, and session configurations
├── generate_deck.py              # PowerPoint PPTX generator with Morph transition helper
├── requirements.txt              # Project packages list
├── .gitignore                    # Prevents cache, data, and presentation binaries from bloating Git
├── README.md                     # Repository documentation
├── landing/                      # Static landing assets (index.html, styles.css, app.js, logo.png)
└── pages/                        # Multi-page dashboard modules
    ├── 1_Executive_Overview.py   # Portfolio boxplots and KPI cards
    ├── 2_Statistical_Inference.py# Regression summaries and VIF/correlation heatmaps
    ├── 3_Predictive_Modeling.py  # XGBoost training, simulator, and batch portal
    └── 4_Fraud_Audit.py          # Isolation Forest and anomaly flags
```

---

## 👥 Contributors
Developed for Prudential Life Insurance Ghana.
