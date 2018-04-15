import os
import json

import shepherd

# ============================================================================ #
# App configuration defaults
# ============================================================================ #
CONFIG_FILE = ".spconfig"
VIEW_TEMPLATE = {
    'name': "",
    'topic': "",
    'description': "",
    'train_columns': [('name', True), ('dataset', True)],
    'eval_columns': [],
}
CONFIG_TEMPLATE = {
    'model_home': './data',
    'show_welcome': True,
    'views_order': ['overview'],
    'views': {
        'overview': {
            'name': "Overview",
            'topic': "",
            'description': "Show all models known to Shepherd.",
            'train_columns': [('name', True), ('dataset', True)],
            'eval_columns': [],
        }
    },
    'view_template': VIEW_TEMPLATE.copy(),
}

class Configuration:
    configuration = {}
    headers = {
        'title': 'Shepherd 0.0'
    }

    # TODO: take out the headers (DATA) from Configuration

    def __init__(self):
        """Initialize configurations."""
        # Create config file if it doesn't exist
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(CONFIG_TEMPLATE, f)

        # Load configuration
        with open(CONFIG_FILE, 'r') as f:
            self.configuration = json.load(f)
            self.headers = self.get_headers()

    def get_all(self):
        return self.configuration

    def get(self, key):
        return self.configuration[key]

    def set(self, key, value):
        self.configuration[key] = value

    def get_headers(self):
        # Update self.headers with menu links
        view_names = sorted(list(self.configuration['views'].keys()))
        self.headers['view_names'] = view_names
        self.headers['views_order'] = self.configuration['views_order']
        return self.headers.copy()

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.configuration, f)
