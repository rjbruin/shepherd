import os
import re
from flask import Flask, render_template, request, redirect, flash, jsonify
import json

app = Flask(__name__)
app.secret_key = 'Marte Fleur is lief!'

import application.api as api
import application.config as config
import application.models

CONFIG = config.Configuration()


def _add_enabled_columns(order, columns):
    # Insert new keys after given order, sorted by name
    for key, state in order:
        columns.remove(key)
    columns = list(zip(columns, [True] * len(columns)))
    order += sorted(columns, key=lambda c: c[0])

    return order

def gather_train_columns(models, order=[]):
    # Get set of all keys in models
    keys = set()
    for model in models:
        model_keys = list(model.keys())
        model_keys.remove('evaluations')
        keys.update(model_keys)
    model_keys = list(keys)

    return list(_add_enabled_columns(list(order), model_keys))

def gather_eval_columns(models, order=[]):
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

def view(view):
    # Discover models
    view_config = CONFIG.get('views')[view]
    models = application.models.discover_models(CONFIG.get('model_home'))
    train_columns = gather_train_columns(models, view_config['train_columns'])
    eval_columns = gather_eval_columns(models, view_config['eval_columns'])

    # Render
    data = {
        'header': view.capitalize(),
        'view': view_config,
        'active_page': view,
        'models': models,
        'train_columns': train_columns,
        'eval_columns': eval_columns,
        'show_delete': True if view != 'overview' else False
    }
    data.update(CONFIG.get_headers())
    return render_template('view.html', data=data)

def not_found():
    return render_template('not_found.html', data=CONFIG.get_headers())

# ============================================================================ #
# AJAX Routing
# ============================================================================ #

def _json_response_with_msg(succes_and_msg):
    success, msg = succes_and_msg
    return jsonify({'success': success, 'msg': msg})

@app.route("/views/<string:viewname>", methods=['DELETE'])
def view_delete_ajax_route(viewname):
    return _json_response_with_msg(api.delete_view(viewname))

@app.route("/views/<string:viewname>/columns", methods=['POST'])
def view_update_columns(viewname):
    train_columns = request.json['train_columns']
    train_states = request.json['train_states']
    eval_columns = request.json['eval_columns']
    eval_states = request.json['eval_states']
    return _json_response_with_msg(api.update_columns(
        viewname, train_columns, train_states, eval_columns, eval_states
    ))

# ============================================================================ #
# Routing
# ============================================================================ #

@app.route("/settings")
def settings_route():
    data =  {
        'config': CONFIG.get_all(),
        'active_page': 'settings'
    }
    data.update(CONFIG.get_headers())
    return render_template('settings.html', data=data)

@app.route("/")
def home_route():
    data = {
        'views': CONFIG.get('views'),
        'active_page': 'home',
        'show_welcome': CONFIG.get('show_welcome'),
    }
    data.update(CONFIG.get_headers())
    return render_template('home.html', data=data)

@app.route("/views/<string:viewname>")
def view_route(viewname):
    if viewname in CONFIG.get('views'):
        return view(viewname)
    else:
        return not_found()

@app.route("/views/new", methods=['GET'])
def view_new_route():
    data = {
        'active_page': 'create_new'
    }
    data.update(CONFIG.get_headers())
    return render_template('create_view.html', data=data)

@app.route("/views", methods=['POST'])
def view_new_submit_route():
    viewname = request.form['view_name']
    success, msg = api.create_view(viewname, CONFIG.get('view_template'))
    if success:
        flash(msg, 'success')
        return redirect('/views/{}'.format(viewname))
    else:
        flash(msg, 'danger')
        return redirect('/views/new')
