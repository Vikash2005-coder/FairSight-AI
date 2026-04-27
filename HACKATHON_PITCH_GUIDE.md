# 🚀 FairSight AI — The Ultimate Hackathon Pitch Guide

Welcome to your master cheat sheet! This document explains exactly what we built, how it works behind the scenes, and what every complex technical term means. Use this to prepare for your presentation and Q&A with the judges.

---

## 🏗️ 1. What Exactly Did We Build?

**FairSight AI** is an end-to-end "AI Bias Auditing & Mitigation" platform. 
Modern companies use Machine Learning models to screen resumes, approve bank loans, and predict crime. However, these models inherently learn human biases (racism, sexism, classism) from historical data. 

Traditionally, a company would have to hire expensive Data Scientists to manually hunt for these biases. **You built a platform that automates this entire process.**
1. **Detects:** It uses strict mathematical algorithms to detect if a dataset is biased.
2. **Explains:** It uses Google's latest `Gemini 3.1 Flash Lite` AI to read the data, figure out *why* it's biased, and flag dangerous proxy variables.
3. **Mitigates:** It generates a professional PDF report and tells the engineers exactly how to fix their code.

---

## 🧠 2. Technical Glossary (What The Big Words Mean)

The judges will love it if you casually use these terms correctly during your pitch!

### The "Four-Fifths Rule" (or 80% Rule)
* **What it means:** A legal guideline used by the US government and regulators globally. 
* **The Math:** If men are approved for a loan 50% of the time, women must be approved at least 40% of the time (which is 80% of 50%). If the ratio falls below 0.80 (80%), the AI is legally considered discriminatory.
* **In FairSight:** This is what the **"Disparity Ratio"** number on your dashboard is calculating! 

### Protected Attribute
* **What it means:** The specific demographic column in a dataset that you are legally not allowed to discriminate against (e.g., `Race`, `Gender`, `Age`, `Religion`). 
* **In FairSight:** Your backend automatically scans the CSV to find these columns so it knows what groups to compare.

### Target Column
* **What it means:** The column in the CSV that shows the final decision made by the company's algorithm (e.g., `loan_approved`, `hired`, `arrested`).
* **In FairSight:** We compare the math of the *Target Column* against the *Protected Attribute*.

### Proxy Features (or Proxy Variables)
* **What it means:** This is your biggest selling point! A company might delete the "Race" column from their database to avoid being racist. BUT, they accidentally leave the "Zipcode" or "Neighborhood" column in. Because neighborhoods are often historically segregated, the AI uses "Zipcode" as a secret *Proxy* to figure out race anyway. 
* **In FairSight:** Gemini physically reads all the column names to hunt for Proxies (like `socioeconomic_status` or `prior_offenses`) and flags them to the user.

### Adversarial Debiasing & Re-weighting
* **What it means:** These are the technical fixes Gemini suggests in the Mitigation section.
    * **Re-weighting:** Tells the data scientists to mathematically boost the "weight" of marginalized groups in the training data so the AI treats them fairly.
    * **Adversarial Debiasing:** A crazy technique where you train a second "Auditor AI" to constantly fight the main AI until the main AI forgets how to be biased.

---

## ⚙️ 3. How the Code Architecture Works (Step-by-Step)

If the judges ask about the architecture, here is the exact flow of data:

### Step 1: The UI (Frontend)
Your user interface is built in lightweight, vanilla HTML/CSS/JS with no bloated React frameworks so it runs lightning fast. It uses asynchronous Javascript `fetch` requests to securely send the uploaded CSV file to your local Python server.

### Step 2: The Math Engine (Backend - `mitigator.py`)
FastAPI receives the CSV file. Before the AI is even involved, Python Pandas physical reads the thousands of rows. It isolates the privileged group (e.g., Male) and the unprivileged group (e.g., Female). It counts the exact approval rates for both and calculates the `Disparity Ratio`. It formats this pure math into a JSON dictionary.

### Step 3: The "Single-Shot" Master Agent (`orchestrator.py`)
This is where the magic happens. Originally, sending 5 different prompts to Gemini took way too long and burned through API quotas. 
We engineered a **Single-Shot Master Agent**. We take all the math from Step 2, package it into one massive, highly-engineered Prompt, and send it to your exclusive **Gemini 3.1 Flash Lite Preview** model. 
Gemini simultaneously:
1. Figures out the Root Cause.
2. Identifies Proxy Features.
3. Generates Short/Long Term Mitigation strategies.
4. Writes a 1000-word Deep Audit Markdown Report.

### Step 4: The Report Generator (`report_generator.py`)
When the user clicks the "Download PDF" button, the frontend sends the beautiful Gemini Intelligence back to the API. We use the `fpdf` library to programmatically generate a multi-page, formatted PDF. *We even had to engineer a custom Unicode Sanitizer to prevent the legacy PDF library from crashing when Gemini generated fancy em-dashes and typographic quotes!*

---

## 💡 4. Top Pro-Tips for Your Demo Presentation

1. **Focus on the Problem:** Start by saying, *"Algorithms govern human lives now, but companies have no idea their AI is prejudiced."*
2. **Show the Math First, then the Logic:** Point out the `99% Fair` score, and then immediately click the Gemini tab to show how the Math lied, and the AI correctly found the "Proxy Features". 
3. **Be proud of the PDF:** Showing that this isn't just a toy dashboard, but an actual enterprise tool that produces downloadable Compliance PDFs will blow them away.

Good luck! You have an incredible platform here. Let me know if any concept isn't 100% clear.
