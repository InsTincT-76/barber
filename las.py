import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
# Step 1: Define the scope
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Step 2: Load your service account credentials
# Make sure the JSON file path matches your 
# 
#file
creds = ServiceAccountCredentials.from_json_keyfile_name('lasgidi-471606-75e838c5829c.json', scope)

# Step 3: Authorize the client
client = gspread.authorize(creds)

# Step 4: Open your Google Sheet by ID if provided, otherwise by name
sheet_id = os.getenv("SHEET_ID")
if sheet_id:
    sheet = client.open_by_key(sheet_id).sheet1
else:
    sheet = client.open("Barbershop Sales").sheet1  # replace with your sheet name

# Step 5: Get all records into a list of dictionaries
data = sheet.get_all_records()

# Step 6: Convert to a pandas DataFrame
df = pd.DataFrame(data)

# Step 7: Convert Date column to datetime format
df['Date'] = pd.to_datetime(df['Date'], errors='coerce', infer_datetime_format=True)

# Optional: print first 5 rows to verify
print(df.head())
