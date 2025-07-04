# manage_data.py

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# -----------------------------
# Step 1: Load Sensor Metadata
# -----------------------------
sensors_df = pd.read_csv("Database\data\Stazioni_qualit__dell_aria_20250507.csv", sep=",")

sensors_clean = sensors_df[[
    'IdSensore', 'NomeStazione', 'Provincia', 'lat', 'lng'
]].copy()

sensors_clean.rename(columns={
    'IdSensore': 'sensor_id',
    'NomeStazione': 'station_name',
    'Provincia': 'province',
    'lat': 'latitude',
    'lng': 'longitude'
}, inplace=True)

sensors_clean.dropna(subset=['latitude', 'longitude'], inplace=True)

# -----------------------------
# Step 2: Connect to Database
# -----------------------------
try:
    mydb = psycopg2.connect(
        host='localhost',
        database='SE',
        user='SE',
        password='191919'
    )
    print("📡 Connected to database.")
except Exception as e:
    print("❌ Connection failed:", e)
    exit()

cur = mydb.cursor()

# Insert sensor metadata
for _, row in sensors_clean.iterrows():
    cur.execute("""
        INSERT INTO sensors (sensor_id, station_name, province, latitude, longitude, geom)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        ON CONFLICT (sensor_id) DO NOTHING;
    """, (
        str(row['sensor_id']),
        row['station_name'],
        row['province'],
        row['latitude'],
        row['longitude'],
        row['longitude'],  # X
        row['latitude']    # Y
    ))

mydb.commit()

# -----------------------------
# Step 3: Load & Clean Measurements
# -----------------------------
measurements_df = pd.read_csv("Database\data\Dati_sensori_aria_dal_2018_20250507.csv", sep=",")

measurements_df.columns = measurements_df.columns.str.strip()
measurements_df['timestamp'] = pd.to_datetime(measurements_df['Data'], format='%d/%m/%Y %H:%M:%S')
measurements_df.dropna(subset=['idSensore', 'Valore'], inplace=True)

# Keep only data before 2024
measurements_df = measurements_df[measurements_df['timestamp'].dt.year < 2024]

measurements_df.rename(columns={
    'idSensore': 'sensor_id',
    'Valore': 'value'
}, inplace=True)

sensor_pollutants = sensors_df[['IdSensore', 'NomeTipoSensore']].copy()
sensor_pollutants.rename(columns={
    'IdSensore': 'sensor_id',
    'NomeTipoSensore': 'pollutant'
}, inplace=True)

measurements_merged = measurements_df.merge(sensor_pollutants, on='sensor_id', how='left')
measurements_merged.dropna(subset=['pollutant'], inplace=True)
# Filter out invalid values BEFORE storing in raw_measurements
measurements_merged = measurements_merged[
    (measurements_merged["value"] >= 0) & (measurements_merged["value"] != -9999)
]


# -----------------------------
# Step 4: Insert Raw Measurements
# -----------------------------
print("💾 Inserting raw measurements...")
cur.execute("DELETE FROM raw_measurements;")
raw_rows = [
    (
        str(row['sensor_id']),
        row['timestamp'],
        row['pollutant'],
        float(row['value'])
    )
    for _, row in measurements_merged.iterrows()
]

execute_values(
    cur,
    """
    INSERT INTO raw_measurements (sensor_id, timestamp, pollutant, value)
    VALUES %s
    """,
    raw_rows,
    page_size=10000
)

# -----------------------------
# Step 5: Aggregate Daily Data
# -----------------------------
print("📆 Aggregating daily data...")
measurements_merged['date'] = measurements_merged['timestamp'].dt.date

daily_stats = measurements_merged.groupby(
    ['sensor_id', 'pollutant', 'date']
)['value'].agg(
    daily_avg='mean',
    daily_min='min',
    daily_max='max'
).reset_index()

daily_stats.rename(columns={'date': 'timestamp'}, inplace=True)

cur.execute("DELETE FROM measurements;")
daily_rows = [
    (
        str(row['sensor_id']),
        row['timestamp'],
        row['pollutant'],
        round(row['daily_avg'], 3),
        round(row['daily_min'], 3),
        round(row['daily_max'], 3)
    )
    for _, row in daily_stats.iterrows()
]

execute_values(
    cur,
    """
    INSERT INTO measurements (sensor_id, timestamp, pollutant, daily_avg, daily_min, daily_max)
    VALUES %s
    """,
    daily_rows,
    page_size=10000
)

# -----------------------------
# Step 6: Fill sensor_pollutants table
# -----------------------------
print("🧭 Mapping sensors to pollutants...")
cur.execute("DELETE FROM sensor_pollutants;")
sensor_pollutant_pairs = measurements_merged[['sensor_id', 'pollutant']].drop_duplicates()

execute_values(
    cur,
    """
    INSERT INTO sensor_pollutants (sensor_id, pollutant)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """,
    list(sensor_pollutant_pairs.itertuples(index=False, name=None))
)

# -----------------------------
# Finalize
# -----------------------------
mydb.commit()
cur.close()
mydb.close()
print("✅ All data inserted successfully.")
