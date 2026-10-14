# Online Retail Analytics Dashboard

An interactive retail analytics dashboard built using Python, Pandas, Streamlit, and Plotly.

## Features

- Revenue and order KPIs
- Monthly sales trends
- Top-selling product analysis
- Country-wise revenue visualization
- Hourly and weekday purchasing patterns
- Customer segmentation using RFM analysis
- Interactive date and country filters
- Filtered sales data export

## Technologies Used

- Python
- Pandas and NumPy
- Plotly
- Streamlit

## Dataset

This project uses the Online Retail dataset from the UCI Machine Learning Repository.

Download: https://archive.ics.uci.edu/dataset/352/online+retail

Extract the dataset and place `Online Retail.xlsx` inside the `data/` folder.

## Installation

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the dashboard:

```bash
python -m streamlit run dashboard.py
```

## Project Purpose

To explore retail transactions, identify sales trends, understand customer purchasing behavior, and communicate actionable business insights through interactive visualizations.
