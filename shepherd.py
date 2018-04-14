import os
import re
from flask import Flask, render_template, request, redirect, flash, jsonify
import json


app = Flask(__name__)
app.secret_key = 'Marte Fleur is lief!'

# ============================================================================ #
# App configuration defaults
# ============================================================================ #

CONFIG_FILE = ".spconfig"
VIEW_TEMPLATE = {
    'train_columns': [('name', True), ('dataset', True)],
    'eval_columns': [],
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

def _add_enabled_columns(order, columns):
    # Insert new keys after given order, sorted by name
    for key, state in order:
        columns.remove(key)
    columns = list(zip(columns, [True] * len(columns)))
    order += sorted(columns, key=lambda c: c[0])

    return order

def train_columns(models, order=[]):
    # Get set of all keys in models
    keys = set()
    for model in models:
        model_keys = list(model.keys())
        model_keys.remove('evaluations')
        keys.update(model_keys)
    model_keys = list(keys)

    return list(_add_enabled_columns(list(order), model_keys))

def eval_columns(models, order=[]):
    # Get set of all metrics in models
    metrics = set()
    for model in models:
        for eval in model['evaluations']:
            metrics.update(set(eval['results'].keys()))
    model_metrics = list(metrics)

    return list(_add_enabled_columns(list(order), model_metrics))

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
    train_keys = train_columns(models, view_config['train_columns'])
    eval_metrics = eval_columns(models, view_config['eval_columns'])

    # Render
    data = {
        'header': view.capitalize(),
        'viewname': view,
        'active_page': view,
        'models': models,
        'train_columns': train_keys,
        'eval_metrics': eval_metrics,
        'show_delete': True if view != 'overview' else False
    }
    data.update(get_data())
    return render_template('view.html', data=data)

def create_view(viewname):
    global CONFIG
    CONFIG['views'][viewname] = VIEW_TEMPLATE.copy()
    CONFIG['views_order'].append(viewname)
    save_config()

def delete_view(viewname):
    if viewname is 'overview':
        return False, "Overview cannot be deleted."
    global CONFIG
    try:
        del CONFIG['views'][viewname]
        CONFIG['views_order'].remove(viewname)
        save_config()
    except Exception:
        return False, "Something went wrong! Please contact an administrator."
    return True, "View deleted. Redirecting to homepage..."

def update_columns(viewname, train_columns, train_states, eval_columns, eval_states):
    global CONFIG
    if viewname not in CONFIG['views']:
        return False, "View does not exist!"

    train_order = list(zip(train_columns, train_states))
    CONFIG['views'][viewname]['train_columns'] = train_order
    eval_order = list(zip(eval_columns, eval_states))
    CONFIG['views'][viewname]['eval_columns'] = eval_order

    return True, "View updated."

def not_found():
    return render_template('not_found.html', data=DATA)

# ============================================================================ #
# AJAX Routing
# ============================================================================ #

def _json_response_with_msg(succes_and_msg):
    success, msg = succes_and_msg
    return jsonify({'success': success, 'msg': msg})

@app.route("/views/<string:viewname>", methods=['DELETE'])
def view_delete_ajax_route(viewname):
    return _json_response_with_msg(delete_view(viewname))

@app.route("/views/<string:viewname>/columns", methods=['POST'])
def view_update_columns(viewname):
    train_columns = request.json['train_columns']
    train_states = request.json['train_states']
    eval_columns = request.json['eval_columns']
    eval_states = request.json['eval_states']
    return _json_response_with_msg(update_columns(
        viewname, train_columns, train_states, eval_columns, eval_states
    ))

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
    if viewname == 'overview':
        return overview_route()
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
    flash("View created!", 'success')
    return redirect('/views/{}'.format(viewname))
