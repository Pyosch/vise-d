import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc

import pandas as pd
import sqlite3
import atexit

#TODO:
# Add navigation (?) to the dashboard:
# https://dash-bootstrap-components.opensource.faculty.ai/docs/components/nav/


conn = sqlite3.connect('data/240912_inputs_online_tool.db', check_same_thread=False)
database_table = 'inputs_online_tool'

# Register a function to close the connection when the app shuts down
def close_db():
    conn.close()

atexit.register(close_db)

# Fetch data from the database
L_LIMIT = 0
U_LIMIT = 10_000
query = f"SELECT * FROM {database_table} LIMIT {L_LIMIT}, {U_LIMIT}"
# query = f"SELECT * FROM inputs_online_tool LIMIT {L_LIMIT}, {U_LIMIT}"
df = pd.read_sql_query(query, conn)

# Create the Dash app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.CYBORG],# Themes for the website, ALLCAPS
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1.0'}] # Responsive design
                ) 
# Further themes:
# https://www.bootstrapcdn.com/bootswatch/

# APP Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([html.H1("VISE-D Tool")], 
                class_name="text-center mb-4", # https://hackerthemes.com/bootstrap-cheatsheet/ , mb-4 adds whitespace below
                width=12,
                ),
    ]),
    
    dbc.Row([
        dbc.Col([html.H4("EV Penetration:"),
            dcc.Dropdown(options=[{'label': i, 'value': i} for i in sorted(df.diffusion_evs.unique())],
                     multi=False,
                     value=f'{df.diffusion_evs.unique()[0]}', 
                     id='ev-dropdown')
        ], class_name="mb-4"),# width={'size': 6}),
        
        dbc.Col([html.H4("Curtailment:"),
            dcc.Dropdown(options=[{'label': i, 'value': i} for i in df.curtailment.unique()],
                     multi=False,
                     value=f'{df.curtailment.unique()[0]}',
                     id='curtailment-dropdown'),
        ], class_name="mb-4"),
        
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='ev-graph', figure={})
        ])
    ], class_name="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='violin-graph', figure={})
        ])
    ], class_name="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardImg(src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/10/VISE_D_neu-1024x470.png"),
                ],
            # style={"width": "24rem"}
            )
        ], xs=4, sm=4, md=4, lg=4, xl=4),
        
        dbc.Col([
            dbc.Card([
                dbc.CardImg(src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/01/Logo_MWIKEPixel.png")
            ])
        ]), #,xs=5, sm=5, md=5, lg=5, xl=5),
        
    ], justify="center")
    
], fluid=False)


@app.callback(
    Output('ev-graph', 'figure'),
    [Input('ev-dropdown', 'value'),
     Input('curtailment-dropdown', 'value')]
)

def update_graph(ev_penetration, curtailment):
    query = f"SELECT * FROM {database_table} \
        WHERE diffusion_evs = '{ev_penetration}' \
            AND curtailment = '{curtailment}' \
                LIMIT {L_LIMIT}, {U_LIMIT}"
    df = pd.read_sql_query(query, conn)
    fig = px.line(df, 
                  x=df.index, 
                  y='value', 
                  title=f'Data Visualization <br>(EV Penetration: {ev_penetration}%, Curtailment: {curtailment})'
                  )
    return fig

@app.callback(
    Output('violin-graph', 'figure'),
    [Input('ev-dropdown', 'value'),
     Input('curtailment-dropdown', 'value')]
)

def update_violin_plot(ev_penetration, curtailment):
    query = f"SELECT * FROM {database_table} \
        WHERE diffusion_evs = '{ev_penetration}' \
            AND curtailment = '{curtailment}' \
                LIMIT {L_LIMIT}, {U_LIMIT}"
                
    df = pd.read_sql_query(query, conn)
    fig = px.violin(df, 
                    y='value', 
                    box=True, 
                    points="all", 
                    title=f"Violin plot <br>(EV Penetration: {ev_penetration}%, Curtailment: {curtailment})"
                    )
    return fig


if __name__ == '__main__':
    app.run_server(debug=True, port=8050)