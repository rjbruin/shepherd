import os
from flask import Flask, render_template
import json


app = Flask(__name__)

CONFIG_FILE = ".spconfig"
DEFAULT_CONFIG = {
    'model_folder': './data'
}
CONFIG = None
DATA = {
    'title': 'Shepherd 0.0'
}


@app.before_first_request
def initialize():
    global CONFIG
    # Create config if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)

    # Load configuration
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)

@app.route("/settings")
def settings():
    data =  {
        'config': CONFIG
    }
    print(CONFIG)
    data.update(DATA.copy())
    return render_template('settings.html', data=data)

@app.route("/")
def overview():
    data = {
        'header': 'Overview'
    }
    data.update(DATA.copy())
    return render_template('overview.html', data=data)
