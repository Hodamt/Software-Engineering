import psycopg2

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

# Enable PostGIS extension
cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

# Drop existing tables
cur.execute("DROP TABLE IF EXISTS measurements;")
cur.execute("DROP TABLE IF EXISTS sensors;")

# Create sensors table
cur.execute('''
    CREATE TABLE sensors (
        sensor_id VARCHAR(50) PRIMARY KEY,
        station_name VARCHAR(100) NOT NULL,
        province VARCHAR(50),
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        geom GEOMETRY(Point, 4326)
    );
''')

# Drop raw_measurements table if it exists
cur.execute("DROP TABLE IF EXISTS raw_measurements;")

# Create raw measurements table (hourly or raw records)
cur.execute('''
    CREATE TABLE raw_measurements (
        measurement_id SERIAL PRIMARY KEY,
        sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
        timestamp TIMESTAMP NOT NULL,
        pollutant VARCHAR(50) NOT NULL,
        value DOUBLE PRECISION
    );
''')

# Create updated measurements table
cur.execute('''
    CREATE TABLE measurements (
        measurement_id SERIAL PRIMARY KEY,
        sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
        timestamp DATE NOT NULL,
        pollutant VARCHAR(50) NOT NULL,
        daily_avg DOUBLE PRECISION,
        daily_min DOUBLE PRECISION,
        daily_max DOUBLE PRECISION
    );
''')

# Drop and create sensor-pollutant map table
cur.execute("DROP TABLE IF EXISTS sensor_pollutants;")
cur.execute('''
    CREATE TABLE sensor_pollutants (
        sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
        pollutant VARCHAR(50),
        PRIMARY KEY (sensor_id, pollutant)
    );
''')

mydb.commit()
cur.close()
mydb.close()
print("✅ Tables created successfully.")
