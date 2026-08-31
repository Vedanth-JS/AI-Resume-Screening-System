import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load variables
load_dotenv()

# Setup Supabase connection parameters
USER = "postgres"
PASSWORD = "Vedanth@1236"  # <-- REPLACE with your actual database password
HOST = "db.mqjunxiyurwtvoibqyfc.supabase.co"
PORT = "5432"
DBNAME = "postgres"

import urllib.parse

# Construct connection string with URL-encoded password
PASSWORD_ENCODED = urllib.parse.quote_plus(PASSWORD)
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD_ENCODED}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

print(f"Testing connection to: postgresql://{USER}:****@{HOST}:{PORT}/{DBNAME}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        from sqlalchemy import text
        connection.execute(text("SELECT 1"))
        print("\n[SUCCESS] Connection successful! Database is active and reachable.")
except Exception as e:
    print(f"\n[ERROR] Failed to connect: {e}")
    print("\nTroubleshooting tips:")
    print("1. Did you replace 'YOUR_DATABASE_PASSWORD' with your actual database password?")
    print("2. Check if your network blocks outbound traffic on port 5432 (enterprise/school Wi-Fi).")
    print("3. Verify the credentials in Supabase settings.")
