import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import sys
import random

def generate_india_dataset(n=2000):
    """
    Generates a dataset with applicants from multiple Indian states.
    Bias: Rejects almost all applicants from Bihar, UP, and Rajasthan if Female.
    """
    states = [
        "Maharashtra", "Bihar", "Uttar Pradesh", "West Bengal", "Telangana", 
        "Tamil Nadu", "Karnataka", "Gujarat", "Rajasthan", "Madhya Pradesh",
        "Delhi", "Kerala", "Punjab", "Haryana", "Assam"
    ]
    
    data = []
    for i in range(n):
        state = random.choice(states)
        gender = random.choice(["Male", "Female"])
        income = random.randint(20000, 150000)
        credit_score = random.randint(300, 850)
        age = random.randint(21, 65)
        
        # ── Logic for synthetic bias ──
        # Bias: In Bihar, UP, and Rajasthan, Female approval is significantly lower
        if state in ["Bihar", "Uttar Pradesh", "Rajasthan"]:
            if gender == "Female":
                approval = 1 if (credit_score > 780 and income > 100000) else 0
            else:
                approval = 1 if (credit_score > 600 or income > 40000) else 0
        
        # Fairness: In Kerala and Karnataka, the model is meritocratic
        elif state in ["Kerala", "Karnataka", "Maharashtra"]:
            approval = 1 if (credit_score > 650) else 0
            
        # Moderate Bias elsewhere
        else:
            if gender == "Female":
                approval = 1 if (credit_score > 700) else 0
            else:
                approval = 1 if (credit_score > 620) else 0
                
        data.append({
            "applicant_id": f"IND-{1000+i}",
            "state": state,
            "gender": gender,
            "age": age,
            "income": income,
            "credit_score": credit_score,
            "loan_approved": approval
        })

    df = pd.DataFrame(data)
    os.makedirs('sample_data', exist_ok=True)
    df.to_csv("sample_data/india_geo_data.csv", index=False)
    print(f"Generated india_geo_data.csv with {n} rows.")
    return df

def create_india_geo_model():
    df = generate_india_dataset(2000)
    
    target_col = 'loan_approved'
    X = df.drop(columns=[target_col, 'applicant_id'], errors='ignore')
    X_numeric = X.select_dtypes(include=[np.number])
    y = df[target_col]
    
    print(f"Training model on features: {list(X_numeric.columns)}")
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    model.fit(X_numeric, y)
    
    model_path = 'sample_data/india_geo_model.pkl'
    joblib.dump(model, model_path)
    print(f"Model saved successfully to: {model_path}")

if __name__ == "__main__":
    create_india_geo_model()
