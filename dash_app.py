import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import requests
import plotly.express as px
import psycopg2

# Database connection to get date range from raw measurements (hourly data)
conn = psycopg2.connect(
    host="localhost",
    database="SE",
    user="SE",
    password="191919"
)
cur = conn.cursor()
# Use the raw_measurements table for date bounds
cur.execute("SELECT MIN(timestamp)::date, MAX(timestamp)::date FROM raw_measurements;")
MIN_DATE, MAX_DATE = cur.fetchone()
cur.close()
conn.close()

# API base URL
API_BASE = "http://localhost:5000/api"

# Initial load for pollutants and sensors
def fetch_initial_data():
    # Get list of pollutants from the aggregated endpoint
    resp_meas = requests.get(f"{API_BASE}/measurements")
    resp_meas.raise_for_status()
    meas_df = pd.DataFrame(resp_meas.json())
    pollutants = sorted(meas_df['pollutant'].unique())

    # Get sensor metadata
    resp_sensors = requests.get(f"{API_BASE}/sensors")
    resp_sensors.raise_for_status()
    sensors_df = pd.DataFrame(resp_sensors.json())
    sensors = sensors_df.to_dict('records')
    return pollutants, sensors

POLLUTANTS, SENSORS = fetch_initial_data()

# Create Dash app with a simple stylesheet for spacing
external_stylesheets = [{
    'href': 'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css',
    'rel': 'stylesheet'
}]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

app.layout = html.Div([
    html.Header(html.H1("Air Quality Dashboard"), style={
        'textAlign': 'center', 'padding': '20px 0', 'backgroundColor': '#f8f9fa'
    }),

    # Map panel
    html.Div([
        html.Div([
            html.Label("Select Pollutant"),
            dcc.Dropdown(
                id='map-pollutant',
                options=[{'label': p, 'value': p} for p in POLLUTANTS],
                value=POLLUTANTS[0],
                clearable=False
            ),
            html.Br(),
            html.Label("Select Date"),
            dcc.DatePickerSingle(
                id='map-date',
                date=MAX_DATE
            ),
        ], style={'width': '30%', 'padding': '10px'}),

        html.Div(
            dcc.Graph(id='map-graph', config={'displayModeBar': False}),
            style={'width': '70%', 'padding': '10px'}
        ),
    ], style={'display': 'flex', 'backgroundColor': '#ffffff', 'padding': '10px'}),

    # Time-series panel
    html.Div([
        html.Div([
            html.Label("Select Sensor"),
            dcc.Dropdown(
                id='ts-sensor',
                options=[{'label': s['station_name'], 'value': s['sensor_id']} for s in SENSORS],
                value=SENSORS[0]['sensor_id'],
                clearable=False
            ),
            html.Br(),
            html.Label("Select Date Range"),
            dcc.DatePickerRange(
                id='ts-range',
                min_date_allowed=MIN_DATE,
                max_date_allowed=MAX_DATE,
                start_date=MIN_DATE,
                end_date=MAX_DATE
            ),
        ], style={'width': '30%', 'padding': '10px'}),

        html.Div(
            dcc.Graph(id='ts-graph', config={'displayModeBar': False}),
            style={'width': '70%', 'padding': '10px'}
        ),
    ], style={'display': 'flex', 'backgroundColor': '#ffffff', 'padding': '10px'})
])

# Callback for updating the map
@app.callback(
    Output('map-graph', 'figure'),
    Input('map-pollutant', 'value'),
    Input('map-date', 'date')
)
def update_map(pollutant, map_date):
    params = {'pollutant': pollutant, 'start': map_date, 'end': map_date}
    df = pd.DataFrame(requests.get(f"{API_BASE}/measurements", params=params).json())
    if df.empty:
        return px.scatter_mapbox(
            pd.DataFrame(columns=['latitude', 'longitude', 'daily_avg']),
            lat='latitude', lon='longitude', zoom=6,
            mapbox_style='open-street-map',
            title=f'No data for {pollutant} on {map_date}'
        )
    df = df.merge(pd.DataFrame(SENSORS), on='sensor_id', how='left')
    fig = px.scatter_mapbox(
        df, lat='latitude', lon='longitude',
        color='daily_avg', size='daily_avg',
        hover_name='station_name', hover_data={'daily_avg':':.2f'},
        zoom=6, height=500,
        mapbox_style='open-street-map',
        title=f'{pollutant} on {map_date}'
    )
    return fig

# Callback for updating the time series using hourly data
@app.callback(
    Output('ts-graph', 'figure'),
    Input('ts-sensor', 'value'),
    Input('ts-range', 'start_date'),
    Input('ts-range', 'end_date')
)
def update_timeseries(sensor_id, start, end):
    # Fetch raw hourly measurements instead of daily aggregates
    params = {'sensor_id': sensor_id, 'start': start, 'end': end}
    resp = requests.get(f"{API_BASE}/raw_measurements", params=params)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    if df.empty:
        return px.line(title='No hourly data available for this range')

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Plot hourly values
    fig = px.line(
        df,
        x='timestamp',
        y='value',
        color='pollutant',
        markers=True,
        title=f"Hourly Measurements for Sensor {sensor_id}"
    )
    fig.update_layout(xaxis_title='Timestamp', yaxis_title='Value')
    return fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=False)
