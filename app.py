from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import logging

app = Flask(__name__)
CORS(app)  # allow cross-origin requests
logging.basicConfig(level=logging.DEBUG)


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="SE",
        user="SE",
        password="191919"
    )


@app.route("/api/sensors", methods=["GET"])
def list_sensors():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                sensor_id,
                station_name,
                province,
                latitude,
                longitude,
                ST_AsGeoJSON(geom)::json AS geometry
            FROM sensors;
        """)
        cols = [c[0] for c in cur.description]
        sensors = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(sensors)
    except Exception as e:
        logging.exception("Failed to fetch sensors")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sensors/<sensor_id>", methods=["GET"])
def get_sensor(sensor_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                sensor_id,
                station_name,
                province,
                latitude,
                longitude,
                ST_AsGeoJSON(geom)::json AS geometry
            FROM sensors
            WHERE sensor_id = %s;
        """, (sensor_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "sensor not found"}), 404
        keys = ["sensor_id", "station_name", "province", "latitude", "longitude", "geometry"]
        return jsonify(dict(zip(keys, row)))
    except Exception as e:
        logging.exception(f"Failed to fetch sensor {sensor_id}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/date_range", methods=["GET"])
def get_date_range():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # If you want hourly range, use raw_measurements; for daily, switch to measurements
        cur.execute("""
            SELECT
                MIN(timestamp)::date AS first_date,
                MAX(timestamp)::date AS last_date
            FROM raw_measurements;
        """)
        first_date, last_date = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({
            "first_date": first_date.isoformat(),
            "last_date": last_date.isoformat()
        })
    except Exception as e:
        logging.exception("Failed to fetch date range")
        return jsonify({"error": str(e)}), 500


@app.route("/api/raw_measurements", methods=["GET"])
def list_raw_measurements():
    sensor_id = request.args.get("sensor_id")
    pollutant = request.args.get("pollutant")
    start     = request.args.get("start")
    end       = request.args.get("end")

    filters, params = [], []
    if sensor_id:
        filters.append("sensor_id = %s");     params.append(sensor_id)
    if pollutant:
        filters.append("pollutant = %s");     params.append(pollutant)
    if start:
        filters.append("timestamp >= %s");    params.append(start)
    if end:
        filters.append("timestamp < %s::date + INTERVAL '1 day'"); params.append(end)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    sql = f"""
        SELECT measurement_id,
               sensor_id,
               timestamp,
               pollutant,
               value
        FROM raw_measurements
        {where}
        ORDER BY timestamp;
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logging.exception("Failed to fetch raw measurements")
        return jsonify({"error": str(e)}), 500


@app.route("/api/measurements", methods=["GET"])
def list_measurements():
    """
    Returns daily aggregates from the precomputed `measurements` table.
    Optional query params: sensor_id, pollutant, start (YYYY-MM-DD), end (YYYY-MM-DD)
    """
    sensor_id = request.args.get("sensor_id")
    pollutant = request.args.get("pollutant")
    start     = request.args.get("start")
    end       = request.args.get("end")

    filters, params = [], []
    if sensor_id:
        filters.append("sensor_id = %s");    params.append(sensor_id)
    if pollutant:
        filters.append("pollutant = %s");    params.append(pollutant)
    if start:
        filters.append("timestamp >= %s");   params.append(start)
    if end:
        filters.append("timestamp < %s::date + INTERVAL '1 day'"); params.append(end)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    sql = f"""
        SELECT
            sensor_id,
            timestamp AS date,
            pollutant,
            daily_avg,
            daily_min,
            daily_max
        FROM measurements
        {where}
        ORDER BY date;
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logging.exception("Failed to fetch daily measurements")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sensors/<sensor_id>/measurements", methods=["GET"])
def measurements_by_sensor(sensor_id):
    """
    Returns daily aggregates for one sensor from the `measurements` table.
    Optional query params: start, end (YYYY-MM-DD)
    """
    start = request.args.get("start")
    end   = request.args.get("end")

    filters = ["sensor_id = %s"]
    params  = [sensor_id]
    if start:
        filters.append("timestamp >= %s");   params.append(start)
    if end:
        filters.append("timestamp < %s::date + INTERVAL '1 day'"); params.append(end)
    where = " AND ".join(filters)

    sql = f"""
        SELECT
            timestamp::date AS date,
            pollutant,
            daily_avg,
            daily_min,
            daily_max
        FROM measurements
        WHERE {where}
        ORDER BY date;
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        if not rows:
            return jsonify({"error": "no measurements found"}), 404
        return jsonify(rows)
    except Exception as e:
        logging.exception(f"Failed to fetch measurements for sensor {sensor_id}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # debug=True will show you stack traces in the console
    app.run(host="0.0.0.0", port=5000, debug=True)
