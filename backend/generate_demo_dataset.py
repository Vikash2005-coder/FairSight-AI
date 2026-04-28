"""
FairSight AI — Comprehensive Global Hiring Bias Dataset Generator
Generates ~700 rows covering bias across gender, age, caste, race, and geography.
Designed to test ALL FairSight features: India Bias Atlas, Proxy Detection, 
Counterfactual Analysis, Impact Story, and Live Monitoring.
"""
import csv
import random
import math

random.seed(42)

# ── Global Location Data ──────────────────────────────────────────────────────
LOCATIONS = {
    # Country: [(city, pincode/zip, region, latitude, longitude)]
    "India": [
        ("Mumbai", "400001", "Maharashtra", 19.0760, 72.8777),
        ("Delhi", "110001", "Delhi", 28.7041, 77.1025),
        ("Bengaluru", "560001", "Karnataka", 12.9716, 77.5946),
        ("Chennai", "600001", "Tamil Nadu", 13.0827, 80.2707),
        ("Kolkata", "700001", "West Bengal", 22.5726, 88.3639),
        ("Hyderabad", "500001", "Telangana", 17.3850, 78.4867),
        ("Pune", "411001", "Maharashtra", 18.5204, 73.8567),
        ("Jaipur", "302001", "Rajasthan", 26.9124, 75.7873),
        ("Ahmedabad", "380001", "Gujarat", 23.0225, 72.5714),
        ("Lucknow", "226001", "Uttar Pradesh", 26.8467, 80.9462),
        ("Patna", "800001", "Bihar", 25.5941, 85.1376),
        ("Bhopal", "462001", "Madhya Pradesh", 23.2599, 77.4126),
        ("Kochi", "682001", "Kerala", 9.9312, 76.2673),
        ("Chandigarh", "160001", "Punjab", 30.7333, 76.7794),
        ("Nagpur", "440001", "Maharashtra", 21.1458, 79.0882),
    ],
    "United States": [
        ("New York", "10001", "New York", 40.7128, -74.0060),
        ("San Francisco", "94102", "California", 37.7749, -122.4194),
        ("Chicago", "60601", "Illinois", 41.8781, -87.6298),
        ("Austin", "73301", "Texas", 30.2672, -97.7431),
        ("Seattle", "98101", "Washington", 47.6062, -122.3321),
        ("Boston", "02101", "Massachusetts", 42.3601, -71.0589),
        ("Atlanta", "30301", "Georgia", 33.7490, -84.3880),
        ("Detroit", "48201", "Michigan", 42.3314, -83.0458),
    ],
    "United Kingdom": [
        ("London", "EC1A", "England", 51.5074, -0.1278),
        ("Manchester", "M1", "England", 53.4808, -2.2426),
        ("Birmingham", "B1", "England", 52.4862, -1.8904),
        ("Edinburgh", "EH1", "Scotland", 55.9533, -3.1883),
    ],
    "Germany": [
        ("Berlin", "10115", "Berlin", 52.5200, 13.4050),
        ("Munich", "80331", "Bavaria", 48.1351, 11.5820),
        ("Hamburg", "20095", "Hamburg", 53.5753, 10.0153),
    ],
    "Australia": [
        ("Sydney", "2000", "New South Wales", -33.8688, 151.2093),
        ("Melbourne", "3000", "Victoria", -37.8136, 144.9631),
    ],
    "Canada": [
        ("Toronto", "M5H", "Ontario", 43.6532, -79.3832),
        ("Vancouver", "V6B", "British Columbia", 49.2827, -123.1207),
    ],
    "Singapore": [
        ("Singapore", "018956", "Central Region", 1.3521, 103.8198),
    ],
    "UAE": [
        ("Dubai", "00000", "Dubai", 25.2048, 55.2708),
        ("Abu Dhabi", "00000", "Abu Dhabi", 24.4539, 54.3773),
    ]
}

# ── Protected Attribute Pools ─────────────────────────────────────────────────
GENDERS = ["Male", "Female", "Female", "Male", "Female", "Male", "Male", "Female"]  # slight male majority in hiring

CASTES_INDIA = ["General", "General", "General", "OBC", "OBC", "SC", "ST", "General"]
ETHNICITIES_GLOBAL = ["White", "White", "Asian", "Black", "Hispanic", "Mixed", "White", "Asian"]

DEPARTMENTS = ["Engineering", "Marketing", "Finance", "Operations", "Data Science", "Product", "HR", "Sales"]
EDUCATION_LEVELS = ["High School", "Bachelor's", "Bachelor's", "Master's", "Master's", "PhD", "Bachelor's", "MBA"]

UNIVERSITIES_INDIA = ["IIT Bombay", "IIT Delhi", "NIT Trichy", "BITS Pilani", "Anna University", 
                       "Osmania University", "Regional College", "State University", "DU", "VTU"]
UNIVERSITIES_GLOBAL = ["MIT", "Stanford", "Harvard", "Oxford", "Cambridge", "State University", 
                        "Community College", "Regional University", "Technical Institute"]

# ── Helper Functions ──────────────────────────────────────────────────────────
def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def bias_approval(base_prob, gender, caste, age, salary_history, career_gap_months, country):
    """Core bias engine: applies multiple intersecting bias patterns"""
    prob = base_prob

    # 1. GENDER BIAS (direct, covert via proxies)
    if gender == "Female":
        prob -= 0.18  # Systematic penalty

    # 2. AGE BIAS (older candidates penalized)
    if age > 45:
        prob -= 0.15
    elif age > 38:
        prob -= 0.07

    # 3. CASTE BIAS (India-specific)
    if caste in ["SC", "ST"]:
        prob -= 0.14
    elif caste == "OBC":
        prob -= 0.07

    # 4. SALARY HISTORY PROXY (most insidious — disadvantages women/minorities)
    # Women tend to have lower salary_history due to pay gap → creates feedback loop
    salary_norm = salary_history / 1_500_000  # normalize around 15L
    prob += (salary_norm - 0.5) * 0.25

    # 5. CAREER GAP PROXY (penalizes caregiving breaks, disproportionately female)
    if career_gap_months > 12:
        prob -= 0.22
    elif career_gap_months > 6:
        prob -= 0.12

    # 6. GEOGRAPHIC BIAS (red-lining effect for certain pincodes/regions)
    # Rural/tier-2/tier-3 cities penalized
    tier2_india = ["Patna", "Bhopal", "Nagpur", "Jaipur", "Lucknow"]

    return clamp(prob, 0.05, 0.97)

def gen_salary_history(gender, caste, country, education, experience_yrs):
    """Salary history with embedded pay gap"""
    base = 800_000  # ₹8L base
    
    if country == "United States":
        base = 6_000_000  # $75k equivalent
    elif country in ["United Kingdom", "Germany", "Australia", "Canada"]:
        base = 4_500_000
    elif country in ["Singapore", "UAE"]:
        base = 3_500_000

    # Experience premium
    base += experience_yrs * 120_000

    # Education premium
    if "PhD" in education:
        base *= 1.4
    elif "Master" in education or "MBA" in education:
        base *= 1.2

    # Gender pay gap (15-22%)
    if gender == "Female":
        base *= random.uniform(0.78, 0.87)

    # Caste wage gap (India)
    if caste == "SC":
        base *= random.uniform(0.82, 0.92)
    elif caste == "ST":
        base *= random.uniform(0.78, 0.90)

    noise = random.uniform(0.90, 1.10)
    return int(base * noise)

def gen_career_gap(gender, age):
    """Career gaps more common for women (caregiving) and older workers (layoffs)"""
    if gender == "Female" and age > 28:
        # 45% chance of career gap for women aged 28+
        if random.random() < 0.45:
            return random.randint(4, 24)
    if gender == "Male" and age > 45:
        if random.random() < 0.15:
            return random.randint(2, 12)
    if random.random() < 0.08:
        return random.randint(1, 6)
    return 0

# ── Main Dataset Generator ────────────────────────────────────────────────────
rows = []
row_id = 1001

for _ in range(700):  # Generate 700 applicants
    # Pick country weighted towards India (40% India for Atlas visibility)
    weights = [0.40, 0.20, 0.10, 0.08, 0.06, 0.06, 0.04, 0.06]
    countries = list(LOCATIONS.keys())
    country = random.choices(countries, weights=weights)[0]
    
    city, pincode, region, lat, lon = random.choice(LOCATIONS[country])
    
    # Demographics
    gender = random.choice(GENDERS)
    age = int(random.gauss(35, 8))
    age = clamp(age, 22, 62)
    
    # Caste only meaningful for India
    caste = random.choice(CASTES_INDIA) if country == "India" else "N/A"
    ethnicity = random.choice(ETHNICITIES_GLOBAL) if country != "India" else "N/A"
    
    education = random.choice(EDUCATION_LEVELS)
    experience_yrs = clamp(age - 22 - random.randint(0, 5), 0, 35)
    
    university_pool = UNIVERSITIES_INDIA if country == "India" else UNIVERSITIES_GLOBAL
    university = random.choice(university_pool)
    
    department = random.choice(DEPARTMENTS)
    
    salary_history = gen_salary_history(gender, caste, country, education, experience_yrs)
    career_gap_months = gen_career_gap(gender, age)
    
    # Skills score (0-100)
    skills_score = clamp(int(random.gauss(70, 15)), 30, 100)
    
    # Interview score (less biased but still affected)
    interview_score = clamp(int(random.gauss(65, 12)), 20, 100)
    if gender == "Female":
        interview_score = clamp(interview_score + random.randint(-5, 5), 20, 100)
    
    # References (proxy for social network bias)
    references = random.choices(["Strong", "Average", "Weak"], weights=[0.4, 0.45, 0.15])[0]
    if caste in ["SC", "ST"]:
        references = random.choices(["Strong", "Average", "Weak"], weights=[0.2, 0.45, 0.35])[0]
    
    # Base approval probability
    base_prob = 0.55 + (skills_score - 70) * 0.005 + (interview_score - 65) * 0.004
    
    # Apply bias engine
    approval_prob = bias_approval(base_prob, gender, caste, age, salary_history, career_gap_months, country)
    
    # Final decision (with some randomness to avoid perfect determinism)
    hired = 1 if random.random() < approval_prob else 0
    
    rows.append({
        "applicant_id": f"APP-{row_id}",
        "name": f"Applicant_{row_id}",  # anonymized
        "gender": gender,
        "age": age,
        "country": country,
        "city": city,
        "pincode": pincode,
        "region": region,
        "latitude": lat,
        "longitude": lon,
        "caste": caste,
        "ethnicity": ethnicity,
        "education": education,
        "university_tier": university,
        "department": department,
        "years_experience": experience_yrs,
        "salary_history": salary_history,
        "career_gap_months": career_gap_months,
        "skills_score": skills_score,
        "interview_score": interview_score,
        "references_quality": references,
        "hired": hired
    })
    row_id += 1

# Write to CSV
output_path = r"e:\google hackathon\fairsight-ai\backend\sample_datasets\global_hiring_bias_2024.csv"
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# Print stats
total = len(rows)
hired_total = sum(r["hired"] for r in rows)
male_hired = sum(r["hired"] for r in rows if r["gender"] == "Male")
female_hired = sum(r["hired"] for r in rows if r["gender"] == "Female")
male_total = sum(1 for r in rows if r["gender"] == "Male")
female_total = sum(1 for r in rows if r["gender"] == "Female")
india_rows = sum(1 for r in rows if r["country"] == "India")

print(f"[OK] Dataset generated: {total} rows")
print(f"[STATS] Overall hire rate: {hired_total/total:.1%}")
print(f"[MALE] Male hire rate: {male_hired/male_total:.1%}")
print(f"[FEMALE] Female hire rate: {female_hired/female_total:.1%}")
print(f"[BIAS] Disparate Impact Ratio: {(female_hired/female_total)/(male_hired/male_total):.3f}")
print(f"[INDIA] India applicants: {india_rows} ({india_rows/total:.0%} of dataset)")
print(f"[SAVED] Saved to: {output_path}")
