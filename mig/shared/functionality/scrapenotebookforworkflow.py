import ast
import json

import shared.returnvalues as returnvalues

from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
from shared.safeinput import REJECT_UNSET
from shared.workflows import scrape_for_workflow_objects

CELL_TYPE, CODE, SOURCE = 'cell_type', 'code', 'source'

def signature():
    """Signaure of the main function"""

    defaults = {
        'vgrid_name': REJECT_UNSET,
        'wf_notebook': '',
        'wf_notebookfilename': REJECT_UNSET,
    }
    return ['registernotebook', defaults]

def main(client_id, user_arguments_dict):
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    logger.debug('DELETE ME - START OF SCRAPING NOTEBOOK')
    logger.debug('user_arguments_dict: \n%s' % user_arguments_dict)

    defaults = signature()[1]

    vgrid_name, note_book_name = 'vgrid_name', 'wf_notebookfilename'

    # put filename in list
    user_arguments_dict[note_book_name] = [user_arguments_dict[note_book_name]]

    logger.debug('DELETE ME - defaults: %s ' % defaults)

    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )


    logger.debug('DELETE ME - accepted: %s ' % accepted)

    vgrid = accepted[vgrid_name][-1]
    name = accepted[note_book_name][-1]

    logger.debug('DELETE ME - notebook name: %s ' % name)


    # TODO get this loading in proper strings, not unicode
    notebook = json.loads(accepted["wf_notebook"][-1])
    if not isinstance(notebook, dict):
        output_objects.append({'object_type': 'error_text', 'text':
            'Notebook is not formatted correctly'
                               })

    cells = notebook['cells']
    metadata = notebook['metadata']

    # Check notebook is in python
    if metadata['kernelspec']['language'].encode('ascii') != 'python'.encode('ascii'):
        output_objects.append({'object_type': 'error_text', 'text':
            'Notebook is not written in python, instead is %s' % metadata['kernelspec']['language'].encode('ascii')
                               })

    output_objects.append({'object_type': 'text', 'text':
        'Registering JupyetLab Notebook and attempting to scrape valid '
        'workflow patterns and recipes...'
    })

    code = ''
    for cell_dict in cells:
        # only look at code cells
        if cell_dict[CELL_TYPE] == CODE:
            for code_line in cell_dict[SOURCE]:
                # better to keep all as one string or to add it line by line?
                code += code_line.encode('ascii')
            # add extra newline to break up different code blocks
            code += "\n"

    status, msg = scrape_for_workflow_objects(configuration, client_id, vgrid, code, name)

    output_objects.append({'object_type': 'text', 'text':msg})

    output_objects.append({'object_type': 'text', 'text':
        'Finished scraping notebook'
    })

    return (output_objects, returnvalues.OK)