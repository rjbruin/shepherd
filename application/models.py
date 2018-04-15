import os
import re
import json


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
