## Barbershop Sales Dashboard (Streamlit)

Simple Streamlit app that loads sales from Google Sheets and generates daily/weekly/monthly summaries and AI insights.

### Prerequisites
- Python 3.9+
- Google Sheet with columns: `Date` (MM-DD-YYYY), `Barber Name`, `Price`, `Payment Method`
- Google service account JSON key file and share the sheet with its email

### Setup
```bash
cd /Users/instinct/Desktop/test
python3 -m pip install --upgrade -r requirements.txt
```

### Run
1. Copy the Sheet ID from the URL (`.../spreadsheets/d/THIS_PART/edit`).
2. Ensure the sheet is shared with the service account email in the JSON.
3. Launch the app:
```bash
export SHEET_ID="YOUR_SHEET_ID"
export GOOGLE_APPLICATION_CREDENTIALS="/Users/instinct/Desktop/test/lasgidi-471606-75e838c5829c.json"
streamlit run app.py
```

Set `OPENAI_API_KEY` to enable extra AI insights.

