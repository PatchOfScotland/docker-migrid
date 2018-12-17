#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridworkflows - data-driven workflows for owners and members
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.
#
# -- END_HEADER ---
#


"""
Register a jupyter notebook containing workflow patterns as a vGrid workflow.
Will check that the notebook is correctly formatted, i.e. it contains the
minimal required number of fields, including cells, metadata and nbformat.
In addition the cells must contain a 'source' key

The result is a saved json formatted file which contains the format:

TODO finish description
"""
import json

import shared.returnvalues as returnvalues
from shared.defaults import csrf_field, wp_id_length, wp_id_charset
from shared.pwhash import generate_random_ascii
from shared.init import initialize_main_variables
from shared.handlers import safe_handler, get_csrf_limit
from shared.functional import validate_input_and_cert
from shared.workflows import create_workflow_pattern


def signature():
    return ['', {}]


def handle_form_input(file, user_arguments_dict, configuration):
    """Retrieve the jupyter notebook file"""
    pass

def get_recipes_parameters_from_nb(json_nb):
    """Returns a dict of cells that contain recipes and parameters from the ipynb notebook.
    This is based on whether the cell dictionary has a key with
    the follwing format:
         'metadata': {'tags': ['recipe']}
    or
        'metadata': {'tags': ['parameters']}
    This is based on ipynb cell tagging.
    e.g. https://github.com/jupyterlab/jupyterlab-celltags"""

    rp_cells = {'recipes': [], 'parameters': {}}
    if 'cells' in json_nb and isinstance(json_nb['cells']):
        for cell in json_nb['cells']:
            if 'metadata' in cell and isinstance(cell['metadata'], dict):
                tags = cell['metadata'].get('tags')
                for tag in tags:
                    if tag == 'recipe':
                        rp_cells['recipes'].append(cell)
                    if tag == 'parameters':
                        # Extract variable declarations
                        rp_cells['parameters'].update(get_declarations_dict(cell['source']))
    return rp_cells


def get_declarations_dict(code):
    """Returns a dictionary with the variable declartions in the list
    Expects that code is a list of strings"""
    declarations = {}
    for line in code:
        if isinstance(line, str):
            line = line.replace(" ", "")
            lines = line.split("=")
            if len(lines) == 2:
                declarations.update({lines[0]: lines[1]})
            else:
                # TODO error report that either none or multiple = where present
                pass
    return declarations


def main(client_id, user_arguments_dict):
    (configuration, logger, output_objects, op_name) = \
            initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    validate_args = {}
    # validate_args = dict([(key, user_arguments_dict.get(key, val)) for \
    #                       (key, val) in defaults.items()])

    # Allow csrf_field from upload
    validate_args[csrf_field] = user_arguments_dict.get(csrf_field,
                                                        ['AllowMe'])

    (validate_status, accepted) = validate_input_and_cert(
        validate_args,
        defaults,
        output_objects,
    client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.info("reqjupyterpattern as User: %s accepted %s" %
                (client_id, accepted))

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
            CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Validate that the notebook is there
    upload_key, upload_name = 'jupyter-notebook', 'jupyter-notebookfilename'
    if upload_key not in user_arguments_dict:
        output_objects.append({'object_type': 'error_text',
                               'text': 'No jupyter notebook was provided'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not isinstance(user_arguments_dict[upload_key], list) and \
            len(user_arguments_dict[upload_key]) == 1:
        output_objects.append({'object_type': 'error_text',
                               'text': 'Only a single notebook can be uploaded'
                                       'at a time'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO check correct format of upload, .ipynb
    # Parse file format as json string
    # Remove trailing commas
    # TODO, ask jonas about standard way of sanitizing input on migrid
    formatted = user_arguments_dict[upload_key][0]
    json_nb = None
    try:
        json_nb = json.loads(formatted, encoding='utf-8')
    except Exception, err:
        logger.error("Failed to json load %s for %s uploaded by %s" %
                     (err, user_arguments_dict[upload_name], client_id))

    if json_nb is None:
        output_objects.append({'object_type': 'error_text',
                               'text': 'Failed to parse the uploaded '
                                       'notebook'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Validate that the notebook has the minimum amount of content,
    # with the correct types
    # TODO check for cell_type, code
    # TODO check for 'source' in each cell
    req_keys = [('cells', list), ('metadata', dict), ('nbformat', int)]
    incorrect_keys = {'missing': [], 'invalid': []}
    for key in req_keys:
        if key[0] not in json_nb:
            incorrect_keys['missing'].append(key[0])
        if key[0] in json_nb and not isinstance(json_nb[key[0]], key[1]):
            incorrect_keys['invalid'].append(key[0])

    if incorrect_keys['missing']:
        output_keys = ' '.join(incorrect_keys['missing'])
        output_objects.append({'object_type': 'error_text',
                               'text': 'Missing required fields in Notebook: '
                                       '%s' % output_keys})

    if incorrect_keys['invalid']:
        output_keys = ' '.join(incorrect_keys['invalid'])
        correct_types = '\n'.join([' is a '.join(key) for key in req_keys
                                  if key[0] in incorrect_keys['invalid']])
        output_objects.append({'object_type': 'error_text',
                               'text': 'The notebook had invalid fields: %s '
                                       ' requires that %s' %
                                       (output_keys, correct_types)})

    if incorrect_keys['missing'] or incorrect_keys['invalid']:
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info("After invalid return")
    # Detect which kernel to use (what language is used)
    # As specified at
    # https://nbformat.readthedocs.io/en/latest
    # /format_description.html?highlight=language_info
    # language_info['name'] tells which language is used in the notebook
    if 'language_info' not in json_nb['metadata'] or 'name' not in \
            json_nb['metadata']['language_info']:
        output_objects.append({'object_type': 'error_text',
                               'text': 'The notebooks language is not '
                                       'specified. Please ensure that '
                                       'the notebook has a defined language'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    lang = str(json_nb['metadata']['language_info']['name'])
    logger.info("After language_info check")

    # TODO, make configuration.valid_jupyter_pattern_langauges
    valid_languages = ['python']
    if lang not in valid_languages:
        output_objects.append({'object_type': 'error_text',
                               'text': 'The provided notebook language %s'
                                       ' is not available. Please use one'
                                       ' of the following once: %s' %
                                       (lang, ' '.join(valid_languages))})
        return (output_objects, returnvalues.CLIENT_ERROR)
    
    # Extract recipe and parameter cells from notebook
    recipes_n_parameters = get_recipes_parameters_from_nb(json_nb)
    if not recipes_n_parameters['recipes']:
        output_objects.append({'object_type': 'error_text',
                        'text': 'No recipe cells were found '
                                'found in %s' %
                                user_arguments_dict[upload_name]})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'header', 'text':
                           ' Registering jupyter notebook'})

    # Generate checksum of pattern instead as an id
    # Unique workflow pattern id
    wp_id = generate_random_ascii(wp_id_length, charset=wp_id_charset)

    pattern_notebook = {
        'notebook': {
            'language': lang
        },
        'owner': client_id,
        'name': user_arguments_dict[upload_name],
        'recipes': recipes_n_parameters['recipes'],
        'input': [],
        'output': [],
        'type_filter': [],
        'variables': recipes_n_parameters['parameters']
    }

    created, msg = create_workflow_pattern(client_id, pattern_notebook, configuration)
    if not created:
        output_objects.append({'object_type': 'error_text',
                               'text': msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text',
                           'text': 'Successfully registered the notebook %s '
                                   'as a pattern' %
                                   user_arguments_dict[upload_name]})
    return (output_objects, returnvalues.OK)