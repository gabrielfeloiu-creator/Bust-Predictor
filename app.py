from flask import Flask, jsonify, send_from_directory
from scorer import get_scored_players
import pandas as pd
from flask_cors import CORS
import numpy as np
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('frontend', path)
def prepare_player_data(df):
    df = df.replace({np.nan: None})
    lod = df.to_dict(orient='records')
    return lod


@app.route('/api/players', methods=['GET'])
def get_players():
    df = get_scored_players()
    players = prepare_player_data(df)
    return jsonify(players)


