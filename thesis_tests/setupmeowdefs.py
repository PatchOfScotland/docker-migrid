
import sys
import nbformat

from mig.shared.conf import get_configuration_object
from mig.shared.workflows import create_workflow, WORKFLOW_PATTERN, get_workflow_with, WORKFLOW_ANY, WORKFLOW_RECIPE, delete_workflow

USERNAME = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@migrid.test'
VGRID = "test"

pattern_one = {
    'name': 'pattern_one',
    'vgrid': VGRID,
    'input_paths': ['testing/*'],
    'input_file': 'input',
    'output': {},
    'recipes': ['recipe_one'],
    'variables': {}
}

notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
recipe_one = {
    'name': 'recipe_one',
    'vgrid': VGRID,
    'recipe': notebook,
    'source': 'test.ipynb'
}

def read():
    configuration = get_configuration_object()
    workflow = get_workflow_with(
        configuration,
        client_id=USERNAME,
        user_query=True,
        workflow_type=WORKFLOW_ANY,
        **{}
    )

    print('Got defs: %s' % workflow)

    return workflow

def write_pattern(pattern):
    configuration = get_configuration_object()
    created, pattern_id = create_workflow(
        configuration, 
        USERNAME, 
        WORKFLOW_PATTERN, 
        **pattern
    )

    print("Created: %s, ID: %s" % (created, pattern_id))

def write_recipe(recipe):
    configuration = get_configuration_object()

    created, recipe_id = create_workflow(
        configuration,
        USERNAME,
        WORKFLOW_RECIPE,
        **recipe
    )

    print("Created: %s, ID: %s" % (created, recipe_id))

def clean():
    configuration = get_configuration_object()

    workflows = get_workflow_with(
        configuration,
        client_id=USERNAME,
        user_query=True,
        workflow_type=WORKFLOW_ANY,
        **{}
    )

    for w in workflows:
        deleted, msg = delete_workflow(
            configuration,
            USERNAME,
            workflow_type=w['object_type'],
            **w
        )

        print("Deleted: %s, %s" % (deleted, msg))

def write_empty_notebook():
    write_recipe(recipe_one)

def setup():
    write_pattern(pattern_one)
    write_empty_notebook()

def sequential():
    write_pattern({
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'INPUT_FILE',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {
            'MAX_COUNT': 10
        }
    })

    notebook = nbformat.read('sequential.ipynb', nbformat.NO_CONVERT)
    write_recipe({
        'name': 'recipe_one',
        'vgrid': VGRID,
        'recipe': notebook,
        'source': 'sequential.ipynb'
    })

if __name__ == '__main__':
    args = sys.argv[1:]

    if args and args[0] == "setup":
        setup()

    elif args and args[0] == "seq":
        sequential()

    elif args and args[0] == "reset":
        clean()

    else:
        read()