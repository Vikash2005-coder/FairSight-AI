"""
FairSight AI — Sample Dataset Generator
Generates realistic biased datasets for demo purposes.
Run this once: python generate_samples.py
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Dataset 1: Hiring Bias (Gender + Age) ────────────────────────────────────

def generate_hiring_dataset(n=500):
    """
    Indian tech company hiring dataset.
    Bias: Women and candidates >40 are significantly less likely to be hired.
    """
    data = []
    for _ in range(n):
        gender = np.random.choice(['Male', 'Female'], p=[0.55, 0.45])
        age = int(np.random.normal(30, 8))
        age = max(22, min(58, age))
        region = np.random.choice(['Mumbai', 'Bangalore', 'Delhi', 'Chennai', 'Hyderabad',
                                   'Rural Maharashtra', 'Rural UP', 'Rural Bihar'],
                                  p=[0.20, 0.20, 0.18, 0.12, 0.10, 0.08, 0.07, 0.05])
        education = np.random.choice(['BTech', 'MTech', 'MBA', 'BSc', 'MSc'],
                                     p=[0.40, 0.20, 0.15, 0.15, 0.10])
        experience = max(0, int(np.random.normal(5, 3)))
        skills_score = int(np.random.normal(70, 15))
        skills_score = max(30, min(100, skills_score))
        
        # Salary history — encodes gender bias (women paid less historically)
        base_salary = np.random.normal(800000, 200000)
        if gender == 'Female':
            base_salary *= 0.82  # 18% pay gap
        salary_history = max(300000, int(base_salary))

        # BIAS: hiring decision is biased against women and older candidates
        hire_prob = 0.5
        if gender == 'Male':
            hire_prob += 0.18     # Males get big advantage
        else:
            hire_prob -= 0.18     # Females get disadvantaged

        if age > 40:
            hire_prob -= 0.20     # Age bias
        elif age < 28:
            hire_prob += 0.05

        if 'Rural' in region:
            hire_prob -= 0.12     # Regional bias

        # Skills and experience should matter — but add noise
        hire_prob += (skills_score - 70) * 0.003
        hire_prob += experience * 0.015
        hire_prob += np.random.normal(0, 0.1)
        
        hired = int(np.random.random() < max(0.05, min(0.95, hire_prob)))

        data.append({
            'candidate_id': f'C{_+1000}',
            'gender': gender,
            'age': age,
            'region': region,
            'education': education,
            'years_experience': experience,
            'skills_score': skills_score,
            'salary_history': salary_history,
            'hired': hired
        })

    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "hiring_bias.csv")
    df.to_csv(path, index=False)
    print(f"Hiring dataset: {len(df)} rows -> {path}")
    print(f"   Hire rate — Male: {df[df.gender=='Male'].hired.mean():.2%} | Female: {df[df.gender=='Female'].hired.mean():.2%}")
    return df


# ── Dataset 2: Loan Approval Bias (Gender + Income + Religion) ───────────────

def generate_loan_dataset(n=600):
    """
    Indian bank loan approval dataset.
    Bias: Women, lower income groups, and certain religions face higher rejection.
    """
    data = []
    for _ in range(n):
        gender = np.random.choice(['Male', 'Female'], p=[0.58, 0.42])
        age = int(np.random.normal(35, 10))
        age = max(21, min(65, age))
        religion = np.random.choice(['Hindu', 'Muslim', 'Christian', 'Sikh', 'Other'],
                                    p=[0.70, 0.14, 0.08, 0.05, 0.03])
        income_bracket = np.random.choice(['<2L', '2-5L', '5-10L', '10-25L', '>25L'],
                                          p=[0.20, 0.30, 0.25, 0.15, 0.10])
        credit_score = int(np.random.normal(680, 80))
        credit_score = max(300, min(850, credit_score))
        loan_amount = int(np.random.uniform(100000, 5000000))
        employment = np.random.choice(['Salaried', 'Self-employed', 'Business', 'Unemployed'],
                                      p=[0.50, 0.25, 0.20, 0.05])
        zip_proxy = np.random.choice(['Urban-Premium', 'Urban-Middle', 'Urban-Low',
                                      'Semi-Urban', 'Rural'],
                                     p=[0.15, 0.25, 0.20, 0.25, 0.15])

        # Approval probability — with bias
        approve_prob = 0.55
        if gender == 'Female':
            approve_prob -= 0.15   # Gender bias
        if religion == 'Muslim':
            approve_prob -= 0.12   # Religious bias
        if income_bracket in ['<2L', '2-5L']:
            approve_prob -= 0.15   # Economic bias (proxy for caste)
        if zip_proxy in ['Urban-Low', 'Rural']:
            approve_prob -= 0.10   # Location bias

        # Legitimate factors
        approve_prob += (credit_score - 680) * 0.001
        if employment == 'Salaried':
            approve_prob += 0.10
        if employment == 'Unemployed':
            approve_prob -= 0.25
        approve_prob += np.random.normal(0, 0.08)

        loan_approved = int(np.random.random() < max(0.05, min(0.95, approve_prob)))

        data.append({
            'applicant_id': f'L{_+2000}',
            'gender': gender,
            'age': age,
            'religion': religion,
            'income_bracket': income_bracket,
            'credit_score': credit_score,
            'loan_amount_requested': loan_amount,
            'employment_type': employment,
            'residential_area': zip_proxy,
            'loan_approved': loan_approved
        })

    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "loan_bias.csv")
    df.to_csv(path, index=False)
    print(f"Loan dataset: {len(df)} rows -> {path}")
    print(f"   Approval — Male: {df[df.gender=='Male'].loan_approved.mean():.2%} | Female: {df[df.gender=='Female'].loan_approved.mean():.2%}")
    print(f"   Approval — Hindu: {df[df.religion=='Hindu'].loan_approved.mean():.2%} | Muslim: {df[df.religion=='Muslim'].loan_approved.mean():.2%}")
    return df


# ── Dataset 3: Healthcare Bias (Age + Gender) ─────────────────────────────────

def generate_healthcare_dataset(n=400):
    """
    Hospital treatment dataset.
    Bias: Elderly patients and women receive less aggressive treatment.
    """
    data = []
    for _ in range(n):
        gender = np.random.choice(['Male', 'Female'], p=[0.52, 0.48])
        age = int(np.random.normal(50, 18))
        age = max(18, min(90, age))
        income_level = np.random.choice(['Low', 'Middle', 'High'], p=[0.30, 0.45, 0.25])
        severity_score = int(np.random.normal(60, 20))
        severity_score = max(10, min(100, severity_score))
        insurance = np.random.choice(['None', 'Basic', 'Comprehensive'], p=[0.25, 0.45, 0.30])
        diagnosis = np.random.choice(['Cardiac', 'Diabetes', 'Cancer', 'Ortho', 'Neuro'],
                                     p=[0.25, 0.20, 0.20, 0.20, 0.15])

        # Treatment aggressiveness — biased
        treat_prob = 0.60
        if gender == 'Female':
            treat_prob -= 0.14   # Women undertreated globally
        if age > 65:
            treat_prob -= 0.18   # Elderly undertreated
        if income_level == 'Low':
            treat_prob -= 0.13
        if insurance == 'None':
            treat_prob -= 0.15

        # Legitimate
        treat_prob += (severity_score - 60) * 0.004
        if insurance == 'Comprehensive':
            treat_prob += 0.15
        treat_prob += np.random.normal(0, 0.08)

        received_treatment = int(np.random.random() < max(0.05, min(0.95, treat_prob)))
        # Outcome is affected by both severity and whether they got treatment
        good_outcome = int(np.random.random() < (0.4 + received_treatment * 0.3 +
                                                   severity_score * 0.003 + np.random.normal(0, 0.1)))

        data.append({
            'patient_id': f'P{_+3000}',
            'gender': gender,
            'age': age,
            'income_level': income_level,
            'diagnosis': diagnosis,
            'severity_score': severity_score,
            'insurance_type': insurance,
            'received_recommended_treatment': received_treatment,
            'positive_outcome': good_outcome
        })

    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "healthcare_bias.csv")
    df.to_csv(path, index=False)
    print(f"Healthcare dataset: {len(df)} rows -> {path}")
    print(f"   Treatment — Male: {df[df.gender=='Male'].received_recommended_treatment.mean():.2%} | Female: {df[df.gender=='Female'].received_recommended_treatment.mean():.2%}")
    return df


# ── Dataset 4: COMPAS-inspired Recidivism (Racial Proxy via Socioeconomic) ───

def generate_compas_dataset(n=300):
    """
    Recidivism prediction dataset inspired by the ProPublica COMPAS analysis.
    Adapted for Indian context: uses socioeconomic proxies.
    Bias: Lower socioeconomic groups have higher predicted recidivism despite similar actual rates.
    """
    data = []
    for _ in range(n):
        gender = np.random.choice(['Male', 'Female'], p=[0.75, 0.25])
        age = int(np.random.normal(28, 8))
        age = max(18, min(65, age))
        socioeconomic = np.random.choice(['Low', 'Middle', 'High'], p=[0.35, 0.40, 0.25])
        prior_offenses = max(0, int(np.random.exponential(1.2)))
        education_level = np.random.choice(['No Schooling', 'Primary', 'Secondary', 'Higher'],
                                           p=[0.15, 0.25, 0.35, 0.25])

        # Actual recidivism (ground truth) — mostly driven by prior offenses
        actual_recidiv_prob = 0.25 + prior_offenses * 0.10
        if age < 25:
            actual_recidiv_prob += 0.10
        actual_recidivism = int(np.random.random() < min(0.85, actual_recidiv_prob))

        # BIASED risk score — over-predicts for low socioeconomic groups
        risk_score = 3.0
        risk_score += prior_offenses * 0.8
        if socioeconomic == 'Low':
            risk_score += 2.5    # BIAS: penalizes poverty
        elif socioeconomic == 'Middle':
            risk_score += 0.8
        if age < 25:
            risk_score += 1.5
        if gender == 'Male':
            risk_score += 0.5
        risk_score += np.random.normal(0, 0.5)
        risk_score = max(1, min(10, round(risk_score, 1)))

        high_risk_prediction = int(risk_score >= 5)

        data.append({
            'person_id': f'R{_+4000}',
            'gender': gender,
            'age': age,
            'socioeconomic_status': socioeconomic,
            'prior_offenses': prior_offenses,
            'education_level': education_level,
            'risk_score': risk_score,
            'high_risk_predicted': high_risk_prediction,
            'actual_recidivism': actual_recidivism
        })

    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "compas_sample.csv")
    df.to_csv(path, index=False)
    print(f"COMPAS dataset: {len(df)} rows -> {path}")
    print(f"   High risk prediction — Low: {df[df.socioeconomic_status=='Low'].high_risk_predicted.mean():.2%} | High: {df[df.socioeconomic_status=='High'].high_risk_predicted.mean():.2%}")
    return df


# -- Dataset 5: Education Admissions Bias (Caste + Region + Gender) --------------

def generate_education_dataset(n=450):
    """
    University admissions dataset.
    Bias: Under-represented groups and rural applicants face higher rejection rates.
    """
    data = []
    for _ in range(n):
        gender = np.random.choice(['Male', 'Female', 'Other'], p=[0.48, 0.48, 0.04])
        category = np.random.choice(['General', 'OBC', 'SC/ST'], p=[0.40, 0.35, 0.25])
        region = np.random.choice(['Metro', 'Urban', 'Rural'], p=[0.30, 0.40, 0.30])
        entrance_exam_score = int(np.random.normal(75, 12))
        entrance_exam_score = max(0, min(100, entrance_exam_score))
        extracurricular_score = int(np.random.normal(60, 20))
        extracurricular_score = max(0, min(100, extracurricular_score))
        
        # Admission probability
        admit_prob = 0.40
        if category == 'General':
            admit_prob += 0.15
        if region == 'Metro':
            admit_prob += 0.10
        elif region == 'Rural':
            admit_prob -= 0.12
            
        # Merit factors
        admit_prob += (entrance_exam_score - 70) * 0.012
        admit_prob += (extracurricular_score - 60) * 0.005
        admit_prob += np.random.normal(0, 0.05)
        
        admitted = int(np.random.random() < max(0.05, min(0.95, admit_prob)))
        
        data.append({
            'student_id': f'S{_+5000}',
            'gender': gender,
            'caste_category': category,
            'parental_region': region,
            'entrance_score': entrance_exam_score,
            'extracurricular_score': extracurricular_score,
            'admission_status': admitted
        })
        
    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "education_bias.csv")
    df.to_csv(path, index=False)
    print(f"Education dataset: {len(df)} rows -> {path}")
    return df

# -- Dataset 6: Insurance Premium Bias (Age + Location + Occupation) ----------

def generate_insurance_dataset(n=550):
    """
    Health insurance premium dataset.
    Bias: High premiums for elderly and residents of specific regions.
    """
    data = []
    for _ in range(n):
        age = int(np.random.normal(45, 15))
        age = max(18, min(80, age))
        gender = np.random.choice(['Male', 'Female'], p=[0.5, 0.5])
        location = np.random.choice(['Tier-1', 'Tier-2', 'Tier-3', 'Rural'], p=[0.3, 0.3, 0.2, 0.2])
        health_score = int(np.random.normal(70, 15))
        health_score = max(20, min(100, health_score))
        occupation_risk = np.random.choice(['Low', 'Medium', 'High'], p=[0.6, 0.3, 0.1])
        
        # Base Dynamic Premium calculation (with bias)
        base_premium = 5000
        if age > 60:
            base_premium += 4000 # Age penalty
        if location == 'Rural':
            base_premium += 1500 # Location penalty (lack of infra proxy)
            
        # Standard risk calculation
        base_premium += (100 - health_score) * 100
        if occupation_risk == 'High':
            base_premium *= 1.4
            
        # Flagging "High Premium" (The Target)
        is_high_premium = int(base_premium > 12000)
        
        data.append({
            'policy_id': f'I{_+6000}',
            'age': age,
            'gender': gender,
            'location_tier': location,
            'health_score': health_score,
            'occupation_risk': occupation_risk,
            'annual_premium_estimate': int(base_premium),
            'high_premium_flag': is_high_premium
        })
        
    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "insurance_bias.csv")
    df.to_csv(path, index=False)
    print(f"Insurance dataset: {len(df)} rows -> {path}")
    return df

def generate_ecommerce_dataset(n=500):
    """
    Dynamic pricing bias for e-commerce.
    Bias: High prices for users from high-income regions but low price for premium loyalty.
    """
    data = []
    for _ in range(n):
        region = np.random.choice(['Delhi-NCR', 'Mumbai', 'Bangalore', 'Lucknow', 'Patna'], 
                                   p=[0.3, 0.25, 0.2, 0.15, 0.1])
        device = np.random.choice(['iPhone', 'High-end Android', 'Budget Android', 'PC'], 
                                  p=[0.2, 0.25, 0.45, 0.1])
        is_prime_member = np.random.choice([0, 1], p=[0.7, 0.3])
        past_purchases = np.random.randint(0, 50)
        
        # Price Surge logic
        surge_multiplier = 1.0
        if region in ['Delhi-NCR', 'Mumbai']:
            surge_multiplier += 0.25 # Geographic price discrimination
        if device == 'iPhone':
            surge_multiplier += 0.15 # Device-based discrimination
        if is_prime_member:
            surge_multiplier -= 0.1 # Loyalty reward
            
        price_surge_flag = int(surge_multiplier > 1.2)
        
        data.append({
            'user_id': f'U{_+7000}',
            'region': region,
            'device_type': device,
            'prime_membership': is_prime_member,
            'past_purchase_count': past_purchases,
            'surge_pricing_applied': price_surge_flag
        })
        
    df = pd.DataFrame(data)
    path = os.path.join(OUTPUT_DIR, "ecommerce_bias.csv")
    df.to_csv(path, index=False)
    print(f"E-commerce dataset: {len(df)} rows -> {path}")
    return df


# ── Text: Biased Job Description ─────────────────────────────────────────────

def generate_biased_job_description():
    text = """
Senior Software Engineer — XYZ Technologies Pvt. Ltd.

We are looking for a young, energetic, and highly motivated individual to join our team
as a Senior Software Engineer. The ideal candidate should be a native English speaker
with a strong academic background from a top-tier institution.

Responsibilities:
- He will be responsible for designing and developing scalable software solutions
- Managing a team of junior developers and ensuring high performance
- Collaborating with the business team to deliver projects on time

Requirements:
- 5-8 years of experience (career gaps will be viewed negatively)
- Must be available for frequent travel and extended work hours
- Graduated from IIT/NIT or equivalent premier institution preferred
- Candidates from Tier 1 cities preferred due to our work culture
- Age: 25-35 years (mandatory)
- Native-level English proficiency required

We offer a dynamic, fast-paced environment for go-getters and self-starters.
Only shortlisted candidates will be contacted.

Note: We are an equal opportunity employer.
"""
    path = os.path.join(OUTPUT_DIR, "biased_job_description.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text.strip())
    print(f"Biased job description -> {path}")


# ── Run All ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating FairSight AI sample datasets...\n")
    generate_hiring_dataset(500)
    generate_loan_dataset(600)
    generate_healthcare_dataset(400)
    generate_compas_dataset(300)
    generate_education_dataset(450)
    generate_insurance_dataset(550)
    generate_ecommerce_dataset(500)
    generate_biased_job_description()
    print(f"\nAll sample datasets generated in: {OUTPUT_DIR}")
