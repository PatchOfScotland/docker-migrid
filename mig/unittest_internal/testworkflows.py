import unittest
import os
import nbformat
from shared.conf import get_configuration_object
from shared.vgrid import vgrid_set_triggers
from shared.serial import load
from shared.workflows import reset_workflows, WORKFLOW_PATTERN, \
    WORKFLOW_RECIPE, WORKFLOW_ANY, get_workflow_with, \
    delete_workflow, create_workflow, update_workflow, \
    get_workflow_trigger, get_task_parameter_path


class WorkflowsFunctionsTest(unittest.TestCase):

    def setUp(self):
        self.created_workflows = []
        self.username = 'FooBar'
        self.test_vgrid = 'Generic'
        self.test_pattern_name = 'pattern_name'
        self.test_recipe_name = 'recipe_name'
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        self.configuration = get_configuration_object()
        self.logger = self.configuration.logger
        (trigger_status, trigger_msg) = vgrid_set_triggers(self.configuration,
                                                           self.test_vgrid, [])
        self.assertTrue(trigger_status)

    def tearDown(self):
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        configuration = get_configuration_object()
        test_vgrid = 'Generic'
        # Also clear vgrid_dir of any patterns and recipes
        self.assertTrue(reset_workflows(configuration, vgrid=test_vgrid))
        self.assertEqual(
            get_workflow_trigger(configuration, test_vgrid)[0], [])

    def test_create_workflow_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])
        self.assertEqual(workflow[0]['input_file'],
                         pattern_attributes['input_file'])
        self.assertEqual(workflow[0]['output'], pattern_attributes['output'])
        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

        self.assertEqual(len(workflow[0]['trigger_recipes']), 1)
        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger_name = next(iter(list(
            workflow[0]['trigger_recipes'][trigger_id])))
        self.assertEqual(trigger_name, self.test_recipe_name)

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)

        # Expect an empty trigger template since the specified recipe doesn't
        # exist yet.
        self.assertEqual(trigger['vgrid_name'], self.test_vgrid)
        for path in pattern_attributes['input_paths']:
            self.assertEqual(trigger['path'], path)
        self.assertEqual(trigger['templates'], [])

    def test_pattern_create_with_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20},
                              'persistence_id': 'persistence0123456789'}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertFalse(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertEqual(workflow, [])

        # Assert that no trigger was created
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid)
        self.assertFalse(trigger)

    def test_pattern_create_with_duplicate_name(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        recipe_name = 'recipe_name_1'
        pattern_2_attributes = {'name': self.test_pattern_name,
                                'vgrid': self.test_vgrid,
                                'input_paths': ['input_dir/*txt'],
                                'input_file': 'hdf5_input',
                                'output': {'processed_data':
                                               'pattern_1_output/*.hdf5'},
                                'recipes': [recipe_name],
                                'variables': {'iterations': 35}}

        created, pattern_id_1 = create_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **pattern_2_attributes)
        self.logger.info(pattern_id_1)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

    def test_pattern_create_with_duplicate_attributes(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        created, pattern_id_2 = create_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **pattern_attributes)
        self.logger.info(pattern_id_2)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])

        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

    def test_create_workflow_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(recipe_attributes[k], v)

    def test_recipe_create_with_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb',
                             'persistence_id': 'persistence0123456789'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertFalse(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertEqual(workflow, [])

    def test_recipe_create_with_duplicate_name(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        created, recipe_id_2 = create_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **recipe_attributes)
        self.logger.info(recipe_id_2)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(recipe_attributes[k], v)

    def test_create_read_delete_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])
        self.assertEqual(workflow[0]['input_file'],
                         pattern_attributes['input_file'])
        self.assertEqual(workflow[0]['output'], pattern_attributes['output'])
        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

        # Test triggers
        self.assertEqual(len(workflow[0]['trigger_recipes']), 1)
        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger_name = next(iter(list(
            workflow[0]['trigger_recipes'][trigger_id])))
        self.assertEqual(trigger_name, self.test_recipe_name)

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)

        # Expect an empty trigger template since the specified recipe doesn't
        # exist yet.
        self.assertEqual(trigger['vgrid_name'], self.test_vgrid)
        for path in pattern_attributes['input_paths']:
            self.assertEqual(trigger['path'], path)
        self.assertEqual(trigger['templates'], [])

        delete_attributes = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertEqual(workflow, [])

        # Ensure trigger is gone
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertFalse(trigger)

    def test_create_read_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(recipe_attributes[k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertEqual(workflow, [])

    def test_update_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})

        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        # Assert empty trigger
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        self.assertEqual(trigger['templates'], [])

        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid,
                          'persistence_id': pattern_id}

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_attributes)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        u_workflow = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})
        self.assertEqual(len(u_workflow), 1)
        self.assertEqual(u_workflow[0]['name'], new_attributes['name'])

        # Ensure trigger is the same
        u_trigger_id = next(iter(list(u_workflow[0]['trigger_recipes'])))
        self.assertEqual(trigger_id, u_trigger_id)
        u_trigger, msg = get_workflow_trigger(self.configuration,
                                              self.test_vgrid,
                                              u_trigger_id)

        self.assertDictEqual(trigger, u_trigger)

    def test_update_pattern_without_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid}

        updated, msg = update_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **new_attributes)
        self.logger.info(msg)
        self.assertFalse(updated)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])

    def test_update_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)

        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid,
                          'persistence_id': recipe_id}
        # Try update without persistence_id
        updated, u_recipe_id = update_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **new_attributes)
        self.logger.info(u_recipe_id)
        self.assertTrue(updated)
        self.assertEqual(recipe_id, u_recipe_id)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **{'persistence_id': u_recipe_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], new_attributes['name'])

    def test_update_recipe_without_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid}
        # Try update without persistence_id
        updated, u_recipe_id = update_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **new_attributes)
        self.logger.info(u_recipe_id)
        self.assertFalse(updated)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **{'persistence_id': recipe_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], recipe_attributes['name'])

    def test_clear_user_workflows(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}
        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Get every workflow in vgrid
        workflows = get_workflow_with(self.configuration,
                                      client_id=self.username,
                                      user_query=True,
                                      workflow_type=WORKFLOW_ANY,
                                      **{'vgrid': self.test_vgrid})

        self.assertIsNotNone(workflows)
        # Verify that the created objects exist
        self.assertEqual(len(workflows), 2)
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

        workflows = get_workflow_with(self.configuration,
                                      client_id=self.username,
                                      user_query=True,
                                      workflow_type=WORKFLOW_ANY,
                                      **{'vgrid': self.test_vgrid})
        self.assertEqual(workflows, [])

    def test_delete_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     self.username,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})

        self.assertEqual(len(workflow), 1)
        trigger_id = next(iter(workflow[0]['trigger_recipes']))
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)

        deletion_attributes = {'persistence_id': pattern_id,
                               'vgrid': self.test_vgrid}
        deleted, deleted_id = delete_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **deletion_attributes)
        self.logger.info(deleted_id)
        self.assertTrue(deleted)
        self.assertEqual(pattern_id, deleted_id)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)
        self.assertEqual(workflow, [])

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertFalse(trigger)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_pattern_without_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        deletion_attributes = {'vgrid': self.test_vgrid}
        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertFalse(deleted)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        deletion_attributes = {'persistence_id': recipe_id,
                               'vgrid': self.test_vgrid}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)

        self.assertEqual(workflow, [])

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_recipe_without_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        deletion_attributes = {'vgrid': self.test_vgrid}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertFalse(deleted)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_workflow_create_pattern_associate_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes'].keys()), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.logger.warning(trigger)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertNotEqual(trigger['templates'], [])
        # TODO, convert templates stings to object that we can check has

    def test_workflow_create_recipe_associate_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        # Validate that the trigger is empty since the recipe doesn't yet exist
        # Test that the trigger is valid
        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes'].keys()), 1)
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.logger.warning(trigger)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertEqual(trigger['templates'], [])

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        u_trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(trigger_id, u_trigger_id)
        self.assertEqual(len(patterns[0]['trigger_recipes'].keys()), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertNotEqual(trigger['templates'], [])
        # TODO, convert templates stings to object that we can check has

    def test_workflow_update_pattern_trigger_recipe(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes'].keys()), 1)
        # No recipe provided == None
        self.assertEqual(patterns[0]['trigger_recipes'][trigger_id], {})

        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain an empty template since no
        # recipe is associated
        self.assertEqual(trigger['templates'], [])

        # Create new recipe
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Update pattern to use the recipe, test that it is associated
        new_pattern = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid,
            'recipes': [self.test_recipe_name]
        }

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_pattern)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        # Test that the pattern is now updated with the correct recipe
        u_patterns = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})

        # Test that the trigger is correctly updated
        self.assertEqual(len(u_patterns), 1)
        self.assertEqual(len(u_patterns[0]['trigger_recipes'].keys()), 1)
        u_trigger_id = next(iter(u_patterns[0]['trigger_recipes']))

        self.assertEqual(trigger_id, u_trigger_id)
        # Get the updated trigger
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertTrue(trigger)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        self.assertNotEqual(trigger['templates'], [])

    # Test updated pattern with new input_paths and recipe.
    def test_update_pattern_paths_recipe(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {},
                              'recipes': ['non_existing_recipe']}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes'].keys()), 1)
        # Recipe didn't exist before pattern was created == placeholder name
        # key is ready to be replaced with recipe_id
        self.assertEqual(patterns[0]['trigger_recipes'][trigger_id],
                         {'non_existing_recipe': {}})

        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain an empty template since no
        # recipe is associated
        self.assertEqual(trigger['templates'], [])

        # Create new recipe
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Update pattern with new input paths and existing recipe
        new_attributes = {'persistence_id': pattern_id,
                          'vgrid': self.test_vgrid,
                          'input_paths': ['new_input_path/*.hdf5'],
                          'recipes': [self.test_recipe_name]}

        # Result -> Delete trigger associated with old input_paths,
        # then delete removed recipe reference from pattern
        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                WORKFLOW_PATTERN,
                                                **new_attributes)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)
        # Ensure that the old trigger is deleted
        u_trigger, u_msg = get_workflow_trigger(self.configuration,
                                                self.test_vgrid,
                                                trigger_id)
        self.assertFalse(u_trigger)

        u_patterns = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})

        trigger_id = next(iter(u_patterns[0]['trigger_recipes']))
        self.assertEqual(len(u_patterns[0]['trigger_recipes'].keys()), 1)
        # No recipe provided == None
        self.assertEqual(u_patterns[0]['trigger_recipes'][trigger_id], {})

    # Test that the pattern parameter file is correctly made and updated
    def test_create_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.logger.info(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertTrue(set(pattern_attributes['variables'].items())
                        .issubset(set(parameters.items())))
        self.assertTrue(set(pattern_attributes['output'])
                        .issubset(set(parameters)))

    def test_update_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertTrue(set(pattern_attributes['variables'].items())
                        .issubset(set(parameters.items())))
        self.assertTrue(set(pattern_attributes['output'])
                        .issubset(set(parameters)))

        # Update workflow
        new_attributes = {'persistence_id': pattern_id,
                          'vgrid': self.test_vgrid,
                          'input_file': 'new_attribute',
                          'output': {'processed_data': 'new_path/bla.npy',
                                     'another_output': 'second_path/bla2.npy'},
                          'variables': {'iterations': 1000,
                                        'additional': 'test'}}

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_attributes)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        u_workflow = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id,
                                          'vgrid': self.test_vgrid})
        self.assertIsNotNone(u_workflow)
        self.assertEqual(len(u_workflow), 1)
        # Assert that the parameter file is updated
        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 u_workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(new_attributes['input_file'], parameters)
        for k, v in new_attributes['variables'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], v)

        for k, v in new_attributes['output'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], os.path.join(self.test_vgrid,
                                                         v))

    def test_delete_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data': 'pattern_0_output/*.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertTrue(set(pattern_attributes['variables'].items())
                        .issubset(set(parameters.items())))
        self.assertTrue(set(pattern_attributes['output'])
                        .issubset(set(parameters)))

        delete_attributes = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **delete_attributes)
        self.assertTrue(deleted)
        self.assertEqual(pattern_id, msg)
        self.assertFalse(os.path.exists(parameter_path))




    # def test_recipe_pattern_association_creation_pattern_first(self):
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                               'processed_data': 'pattern_0_output/*.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     notebook = nbformat.v4.new_notebook()
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    # def test_recipe_pattern_association_creation_recipe_first(self):
    #     notebook = nbformat.v4.new_notebook()
    #
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                               'processed_data': 'pattern_0_output/*.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    # def test_recipe_pattern_association_deletion(self):
    #
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                               'processed_data': 'pattern_0_output/*.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     notebook = nbformat.v4.new_notebook()
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    #     deletion_attributes = {
    #         'persistence_id': pattern_id,
    #         'vgrid': self.test_vgrid
    #     }
    #
    #     deleted, msg = delete_workflow(self.configuration,
    #                                    self.username,
    #                                    workflow_type=WORKFLOW_PATTERN,
    #                                    **deletion_attributes)
    #
    #     self.logger.info(msg)
    #     self.assertTrue(deleted)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 0)


if __name__ == '__main__':
    unittest.main()
