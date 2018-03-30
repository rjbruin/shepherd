import os
import re
from flask import Flask, render_template
import json


app = Flask(__name__)

# ============================================================================ #
# App configuration defaults
# ============================================================================ #

CONFIG_FILE = ".spconfig"
DEFAULT_CONFIG = {
    'model_home': './data',
    'train_order': ['name', 'dataset'],
    'train_ignore': [],
    'eval_order': [],
    'eval_ignore': []
}
CONFIG = None
DATA = {
    'title': 'Shepherd 0.0'
}


@app.before_first_request
def initialize():
    """Initialize configurations."""
    global CONFIG
    # Create config if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)

    # Load configuration
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)

# ============================================================================ #
# Model logic
# ============================================================================ #

def discover_models(model_home):
    """
    Find all model directories in model_home and return as a list of model
    objects.

    Any directory that contains a training config is treated as a model
    directory. Any evaluation configs in the model directory or any subdirectory
    of the model directory is a evaluation instance for that model.

    Arguments:
    - model_home: string path to model home.

    Exceptions:
    - ValueError: if a model directory contains multiple training
        configurations.

    Returns:
    - models: list of model objects.
    """
    # Define helper method to prepend model home
    homeify = lambda path: os.path.join(model_home, path)

    # Gather potential model directories: all directories under model_home
    candidates = os.walk(model_home)

    # Filter for existance of training configs (.sptrain)
    models = []
    for (path, dirs, files) in candidates:
        if any(map(lambda p: re.search(".sptrain", p) != None, files)):
            models.append((path, dirs, files))

    # For each model directory, find and save train and eval information
    models_with_evals = []
    for (path, dirs, files) in models:
        # Find all eval configs (.speval)
        eval_paths = []
        dirs_to_investigate = [path] + dirs
        while len(dirs_to_investigate) > 0:
            # Build path to dir and get names
            dirpath = dirs_to_investigate.pop(0)
            dirnames = os.listdir(dirpath)
            # Find evals
            direvals = filter(lambda p: re.search(".speval", p) != None, dirnames)
            eval_paths.extend(map(lambda p: os.path.join(dirpath, p), direvals))
            # Add subdirectories to stack
            for name in dirnames:
                full_name = os.path.join(dirpath, name)
                if os.path.isdir(homeify(full_name)):
                    dirs_to_investigate.append(os.path.join(full_name))

        # Find path to training config
        train_paths = list(filter(lambda p: re.search(".sptrain", p) != None, files))
        if len(train_paths) > 1:
            raise ValueError("Multiple training configurations are not allowed!")
        # Compose model information from files
        with open(os.path.join(path, train_paths[0]), 'r') as f:
            model = json.load(f)
        model['evaluations'] = []
        for eval_path in eval_paths:
            with open(eval_path, 'r') as f:
                model['evaluations'].append(json.load(f))
        # Store model
        models_with_evals.append(model)

    return models_with_evals

def train_columns(models, order=[], ignore=[]):
    # Get set of all keys in models
    keys = set()
    for model in models:
        model_keys = list(model.keys())
        model_keys.remove('evaluations')
        keys.update(model_keys)
    all_keys = list(keys)

    # Insert new keys after given order
    ordered_keys = []
    for key in order:
        all_keys.remove(key)
        ordered_keys.append(key)
    ordered_keys += sorted(all_keys)

    # Remove keys to ignore
    for key in ignore:
        ordered_keys.remove(key)

    return ordered_keys

def eval_columns(models, order=[], ignore=[]):
    # Get set of all metrics in models
    metrics = set()
    for model in models:
        print(model)
        for eval in model['evaluations']:
            metrics.update(set(eval['results'].keys()))
    all_metrics = list(metrics)

    # Insert new metrics after given order
    ordered_keys = []
    for key in order:
        all_metrics.remove(key)
        ordered_keys.append(key)
    ordered_keys += sorted(all_metrics)

    # Remove metrics to ignore
    for key in ignore:
        ordered_keys.remove(key)

    return ordered_keys

def order_evaluations(models):
    # Order evaluations by sorting
    ordered_models = []
    for model in models:
        evals = sorted(model['evaluations'], key=lambda e: e['model'])
        model['evaluations'] = evals
        ordered_models.append(model)
    return ordered_models

# ============================================================================ #
# Routing
# ============================================================================ #

@app.route("/settings")
def settings():
    data =  {
        'config': CONFIG
    }
    data.update(DATA.copy())
    return render_template('settings.html', data=data)

@app.route("/")
def overview():
    # Discover models
    models = discover_models(CONFIG['model_home'])
    train_keys = train_columns(models, CONFIG['train_order'], CONFIG['train_ignore'])
    eval_metrics = eval_columns(models, CONFIG['eval_order'], CONFIG['eval_ignore'])

    # Render
    data = {
        'header': 'Overview',
        'models': models,
        'train_columns': train_keys,
        'eval_metrics': eval_metrics
    }
    data.update(DATA.copy())
    return render_template('overview.html', data=data)
