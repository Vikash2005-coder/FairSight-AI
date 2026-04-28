import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import sys

# Add the project root to import generate_samples
sys.path.append(os.path.dirname(__file__))
from generate_samples import generate_hiring_dataset

def create_biased_model():
    os.makedirs('sample_data', exist_ok=True)
    
    print("Generating hiring dataset to match backend structure...")
    df = generate_hiring_dataset(1000)
    
    target_col = 'hired'
    X = df.drop(columns=[target_col, 'candidate_id'], errors='ignore')
    X_numeric = X.select_dtypes(include=[np.number])
    y = df[target_col]
    
    # Train the model exactly on the numeric columns the backend will use
    # In this dataset, 'age' and 'salary_history' contain the bias
    print(f"Training model on features: {list(X_numeric.columns)}")
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    model.fit(X_numeric, y)
    
    model_path = 'sample_data/synthetic_biased_model.pkl'
    joblib.dump(model, model_path)
    
    print(f"Model saved successfully to: {model_path}")

if __name__ == "__main__":
    create_biased_model()
