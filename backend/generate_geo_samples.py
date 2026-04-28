import pandas as pd
import random

states = [
    "Maharashtra", "Bihar", "Uttar Pradesh", "West Bengal", "Telangana", 
    "Tamil Nadu", "Karnataka", "Gujarat", "Rajasthan", "Madhya Pradesh",
    "Delhi NCR", "Kerala", "Punjab", "Haryana", "Assam"
]

data = []
for i in range(250):
    state = random.choice(states)
    gender = random.choice(["Male", "Female"])
    income = random.randint(20000, 150000)
    credit_score = random.randint(300, 850)
    
    # ── Logic for synthetic bias ──
    # Bias: In Bihar, UP, and Rajasthan, Female approval is significantly lower
    if state in ["Bihar", "Uttar Pradesh", "Rajasthan"]:
        if gender == "Female":
            approval = 1 if (credit_score > 750 and income > 80000) else 0
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
        "Application_ID": f"FS-{1000+i}",
        "State": state,
        "Gender": gender,
        "Income_INR": income,
        "Credit_Score": credit_score,
        "Loan_Status": "Approved" if approval == 1 else "Rejected"
    })

df = pd.DataFrame(data)
df.to_csv("sample_data/india_banking_bias.csv", index=False)
print("Generated india_banking_bias.csv with 250 rows and 15 states.")
