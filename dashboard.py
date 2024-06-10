"""
Columns: ['grid_type', 'diffusion_hps', 'diffusion_evs', 'diffusion_pv_storage',
       'curtailment', 'tariff_wholesale', 'tariff_grid_usage', 'q',
       'component', 'value']
       
Selectables:
grid_type: ['standard']
diffusion_hps: ['standard']
diffusion_evs: ['30', '50']
diffusion_pv_storage: ['standard']
curtailment: ['none', 'smart']
tariff_wholesale: ['rtt']
tariff_grid_usage: ['fix']

"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

import pandas as pd
import sqlite3
import atexit

# Connect to the SQL database
conn = sqlite3.connect('data/240603_database sample.db', check_same_thread=False)

# Register a function to close the connection when the app shuts down
def close_db():
    conn.close()

atexit.register(close_db)

# Fetch data from the database
L_LIMIT = 0
U_LIMIT = 1_000
query = f"SELECT * FROM merge LIMIT {L_LIMIT}, {U_LIMIT}"
df = pd.read_sql_query(query, conn)

# Create the Dash app
app = dash.Dash(__name__)

# Define the layout of the dashboard
app.layout = html.Div(
    children=[
        html.H1("VISE-D: Data Visualization Dashboard"),
        html.H3("EV Penetration:"),
        dcc.Dropdown(options=[{'label': i, 'value': i} for i in ['30', '50']],
                     value='30', 
                     id='ev-dropdown'),
        html.H3("Curtailment Strategy:"),
        dcc.Dropdown(options=[{'label': i, 'value': i} for i in ['none', 'smart']],
                     value='none',
                     id='curtailment-dropdown'),
        dcc.Graph(id="data-graph"),
        dcc.Graph(id='violin-graph')
    ]
)

@app.callback(
    Output('data-graph', 'figure'),
    [Input('ev-dropdown', 'value'),
     Input('curtailment-dropdown', 'value')]
)
def update_graph(ev_penetration, curtailment):
    query = f"SELECT * FROM merge WHERE diffusion_evs = '{ev_penetration}' AND curtailment = '{curtailment}' LIMIT {L_LIMIT}, {U_LIMIT}"
    df = pd.read_sql_query(query, conn)
    fig = px.line(df, x=df.index, y='value', title=f'Data Visualization (EV Penetration: {ev_penetration}%, Curtailment: {curtailment})')
    return fig

@app.callback(
    Output('violin-graph', 'figure'),
    [Input('ev-dropdown', 'value'),
     Input('curtailment-dropdown', 'value')]
)
def update_violin_plot(ev_penetration, curtailment):
    query = f"SELECT * FROM merge WHERE diffusion_evs = '{ev_penetration}' AND curtailment = '{curtailment}' LIMIT {L_LIMIT}, {U_LIMIT}"
    df = pd.read_sql_query(query, conn)
    fig = px.violin(df, y='value', box=True, points="all", title=f'Violin plot (EV Penetration: {ev_penetration}%, Curtailment: {curtailment})')
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
    