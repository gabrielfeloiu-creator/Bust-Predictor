from flask import Flask, jsonify
from scorer import get_scored_players
import pandas as pd
from flask_cors import CORS
import numpy as np
import os

app = Flask(__name__)
CORS(app)

def prepare_player_data(df):
    df = df.replace({np.nan: None})
    lod = df.to_dict(orient='records')
    return lod


@app.route('/api/players', methods=['GET'])
def get_players():
    df = get_scored_players()
    players = prepare_player_data(df)
    return jsonify(players)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
