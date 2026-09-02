Retail Demand Forecasting

A user-friendly web-based demand forecasting application designed for retail and kirana stores. The system analyzes historical sales data and predicts future product demand.

Features
CSV and Excel sales data upload
Automatic detection and validation of sales data
Store-wise and product-wise demand forecasting
7-day, 14-day, and 30-day forecasts
Baseline, limited-history, and full forecasting
Daily demand predictions
Total and average expected demand
Forecast accuracy and confidence indicators
Demand insights and visualizations
Manual daily sales recording
Forecasting using recorded sales data
Quick demand estimation without historical data
Simple interface for non-technical users
Technologies Used
Python
FastAPI
Uvicorn
Pandas
HTML
CSS
JavaScript
JSON file-based storage
Project Structure
demand-forecasting-app/
│
├── backend/
│   ├── app.py
│   └── model.py
│
├── frontend/
│   ├── index.html
│   ├── options.html
│   ├── upload.html
│   ├── data-check.html
│   ├── forecast-setup.html
│   ├── forecast.html
│   ├── record.html
│   ├── recorded-forecast.html
│   ├── quick-estimate.html
│   ├── script.js
│   └── style.css
│
├── requirements.txt
└── README.md
How to Run
1. Install the required packages

Open Command Prompt in the project folder and run:

pip install -r requirements.txt
2. Start the application

From the project folder, run:

python -m uvicorn backend.app:app --reload
3. Open the application

Open the local address shown in the terminal, usually:

http://127.0.0.1:8000
Data Input

The application supports:

CSV files
Excel .xlsx files
Manual daily sales recording
Quick demand estimation when historical data is unavailable

For uploaded datasets, the application identifies and validates the date, store, product/item, and sales/quantity information.

Forecast Periods

The application provides demand forecasts for:

7 days
14 days
30 days
Database

No traditional database is used. Recorded sales are stored using a JSON file.

Project Purpose

The project aims to help small retail and kirana stores make better inventory decisions by providing accessible demand forecasting even when historical sales data is limited.