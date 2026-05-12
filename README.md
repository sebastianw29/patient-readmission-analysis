# Patient Readmission Risk Analysis

Exploratory data analysis on the UCI Diabetes 130-US Hospitals dataset (101,766 records)
to identify 30-day readmission risk factors.

## Dataset
Download `diabetic_data.csv` from:
https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008

Place it in the project folder before running.

## Setup
pip install -r requirements.txt

## Run
python analysis.py
python build_excel.py

## Key Findings
- Prior inpatient visits is the strongest predictor of readmission
- Circulatory disease patients have the highest volume and elevated risk
- HbA1c > 8 correlates with higher readmission rates
- Longer length of stay associates with increased readmission risk