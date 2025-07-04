# SE4GEO Air Quality Dashboard

This project is an interactive air quality monitoring system designed for the Lombardy region. It processes data from Dati Lombardia and includes:

- A **PostgreSQL/PostGIS** spatial database  
- A **Flask REST API** for data access  
- A **Dash web app** for interactive visualization

## 📁 Project Structure

```
├── create_table.py        # Creates the PostgreSQL schema and tables
├── manage_data.py         # Loads and cleans data into PostgreSQL
├── app.py                 # Flask REST API
├── dash_app.py            # Dash dashboard frontend
├── /docs                  # Documentation
├── /data                  # Raw input CSV files
```

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/air-quality-dashboard.git
cd air-quality-dashboard
```

### 2. Set Up Python Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure PostgreSQL with PostGIS

- Create the database:

```sql
CREATE DATABASE se4geo;
\c se4geo
CREATE EXTENSION postgis;
```

- Update database credentials in:
  - `create_table.py`
  - `manage_data.py`
  - `app.py`
  - `dash_app.py`

### 4. Create Tables

Run the table creation script:

```bash
python create_table.py
```

### 5. Load the Data

Place your CSV files from Dati Lombardia into the `/data` folder, then run:

```bash
python manage_data.py
```

This script:
- Loads sensors and their metadata
- Links sensors to pollutants
- Loads hourly measurements
- Computes daily aggregates

## 🌐 Run the API Server

```bash
python app.py
```

- Base URL: `http://localhost:5000/api`
- Example: `http://localhost:5000/api/sensors`

## 📊 Launch the Dashboard

```bash
python dash_app.py
```

Then open your browser at:  
📍 `http://localhost:8050`

## 🧪 Features

- 📍 **Map Panel**  
  Shows pollutant levels by sensor on a map (color/size-coded)

- 📈 **Time-Series Panel**  
  Visualizes trends for a selected sensor (raw or daily-aggregated)

- 🔎 **Filters**  
  Dropdowns for pollutant, station, date range, and resolution

## 🗂 Data Sources

- [Air Quality Measurements](https://www.dati.lombardia.it/Ambiente/Dati-sensori-aria-dal-2018/g2hp-ar79)
- [Sensor Metadata](https://www.dati.lombardia.it/Ambiente/Stazioni-qualita-dell-aria/ib47-atvt)

## ⚙️ Technologies Used

- Python 3.11  
- Flask 3.x  
- Dash 2.x / Plotly  
- PostgreSQL 17 + PostGIS 3.4  
- Pandas / Requests / Psycopg2

## ✅ Requirements

- Python 3.8+  
- PostgreSQL with PostGIS extension  
- Internet browser (Chrome, Firefox, etc.)

## 👨‍💻 Authors

Developed as part of the **SE4GEO** course at *Politecnico di Milano*.


