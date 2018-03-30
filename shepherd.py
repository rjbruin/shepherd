import os
import re
from flask import Flask, render_template, request, redirect
import json


app = Flask(__name__)

# ============================================================================ #
# App configuration defaults
# ============================================================================ #

CONFIG_FILE = ".spconfig"
VIEW_TEMPLATE = {
    'train_order': ['name', 'dataset'],
    'train_ignore': [],
    'eval_order': [],
    'eval_ignore': []
}
DEFAULT_CONFIG = {
    'model_home': './data',
    'views_order': ['overview'],
    'views': {
        'overview': VIEW_TEMPLATE.copy()
    }
}
CONFIG = None
DATA = {
    'title': 'Shepherd 0.0'
}


@app.before_first_request
def initialize():
    """Initialize configurations."""
    global CONFIG
    global DATA
    # Create config if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)

    # Load configuration
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)

    DATA = get_data()

def get_data():
    # Update DATA with menu links
    view_names = sorted(list(CONFIG['views'].keys()))
    DATA['views'] = view_names
    DATA['views_order'] = CONFIG['views_order']
    return DATA.copy()

# TODO
# @app.after_request
def save_config():
    global CONFIG
    with open(CONFIG_FILE, 'w') as f:
        json.dump(CONFIG, f)

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

def view(config, view):
    # Discover models
    view_config = config['views'][view]
    models = discover_models(config['model_home'])
    train_keys = train_columns(models, view_config['train_order'], view_config['train_ignore'])
    eval_metrics = eval_columns(models, view_config['eval_order'], view_config['eval_ignore'])

    # Render
    data = {
        'header': view.capitalize(),
        'active_page': view,
        'models': models,
        'train_columns': train_keys,
        'eval_metrics': eval_metrics
    }
    data.update(get_data())
    return render_template('view.html', data=data)

def create_view(viewname):
    global CONFIG
    CONFIG['views'][viewname] = VIEW_TEMPLATE.copy()
    CONFIG['views_order'].append(viewname)
    save_config()

def not_found():
    return render_template('not_found.html', data=DATA)

# ============================================================================ #
# Routing
# ============================================================================ #

@app.route("/settings")
def settings_route():
    data =  {
        'config': CONFIG,
        'active_page': 'settings'
    }
    data.update(get_data())
    return render_template('settings.html', data=data)

@app.route("/")
def overview_route():
    return view(CONFIG, 'overview')

@app.route("/views/<string:viewname>")
def view_route(viewname):
    if viewname in CONFIG['views']:
        return view(CONFIG, viewname)
    else:
        return not_found()

@app.route("/create_view")
def view_new_route():
    data = {
        'active_page': 'create_new'
    }
    data.update(get_data())
    return render_template('create_view.html', data=data)

@app.route("/views", methods=['POST'])
def view_new_submit_route():
    viewname = request.form['view_name']
    create_view(viewname)
    # return view_route(viewname)
    return redirect('/views/{}'.format(viewname))
