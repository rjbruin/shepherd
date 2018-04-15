import shepherd


def create_view(viewname, view_template):
    if viewname == 'new':
        return False, "\"New\" is an illegal view name. Please enter a different name for the new view."
    shepherd.CONFIG.configuration['views'][viewname] = view_template.copy()
    shepherd.CONFIG.configuration['views_order'].append(viewname)
    shepherd.CONFIG.save_config()
    return True, "View created."

def delete_view(viewname):
    if viewname is 'overview':
        return False, "Overview cannot be deleted."
    try:
        del shepherd.CONFIG.configuration['views'][viewname]
        shepherd.CONFIG.configuration['views_order'].remove(viewname)
        shepherd.CONFIG.save_config()
    except Exception:
        return False, "Something went wrong! Please contact an administrator."
    return True, "View deleted. Redirecting to homepage..."

def update_columns(viewname, train_columns, train_states, eval_columns, eval_states):
    if viewname not in shepherd.CONFIG.configuration['views']:
        return False, "View does not exist!"

    train_order = list(zip(train_columns, train_states))
    shepherd.CONFIG.configuration['views'][viewname]['train_columns'] = train_order
    eval_order = list(zip(eval_columns, eval_states))
    shepherd.CONFIG.configuration['views'][viewname]['eval_columns'] = eval_order
    shepherd.CONFIG.save_config()

    return True, "View updated."
