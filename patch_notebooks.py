import json
import os

notebooks = [
    "Insurance_data_merged (1).ipynb",
    "Insurance_data_Individual.ipynb",
    "Insurance_data_Corporate.ipynb"
]

for nb_name in notebooks:
    path = nb_name
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
        
    print(f"Patching {nb_name}...")
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = cell.get('source', [])
            new_source = []
            for line in source:
                # Replace multiclass target labels with binary ones
                line = line.replace('["Low", "Medium", "High", "Critical"]', '["Good Risk", "Adverse Outcome"]')
                line = line.replace('eval_metric="mlogloss"', 'eval_metric="logloss"')
                
                if "X_ml = df_encoded.select_dtypes(include=[np.number]).drop(columns=['Risk_Category_encoded', 'Risk_Score'])" in line:
                    new_source.append("    df_encoded['Adverse_Outcome'] = ((df_encoded['Claim_Frequency'] >= 2) | (df_encoded['Claim_Severity_encoded'] >= 3)).astype(int)\n")
                    line = "    X_ml = df_encoded.select_dtypes(include=[np.number]).drop(columns=['Risk_Category_encoded', 'Risk_Score', 'Gender_encoded', 'Adverse_Outcome'], errors='ignore')\n"
                elif "y_ml = df_encoded['Risk_Category_encoded']" in line:
                    line = "    y_ml = df_encoded['Adverse_Outcome']\n"
                    
                # Replace target split in individual/corporate notebooks
                if "X_ml = df_encoded[features_list].copy()" in line:
                    new_source.append("    df_encoded['Adverse_Outcome'] = ((df_encoded['Claim_Frequency'] >= 2) | (df_encoded['Claim_Severity_encoded'] >= 3)).astype(int)\n")
                    if nb_name == "Insurance_data_Individual.ipynb":
                        new_source.append("    features_list = [f for f in features_list if f not in ['Claim_Frequency', 'Claim_Severity_encoded', 'Premium_GHS', 'Gender_encoded']]\n")
                    else:
                        new_source.append("    features_list = [f for f in features_list if f not in ['Gender_encoded']]\n")
                    line = "    X_ml = df_encoded[features_list].copy()\n"
                
                if line:
                    new_source.append(line)
            cell['source'] = new_source
            
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"Successfully patched {nb_name}!")
