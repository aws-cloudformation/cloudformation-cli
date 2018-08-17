import os
from uluru.filters import resource_service_name, resource_type_name


def generate(env, resource_def, project_settings):
    resource_name = resource_type_name(resource_def["Type"])
    curdl = ['Create', 'Update', 'Read', 'Delete', 'List']
    output_directory = project_settings["output_directory"]
    package_name_prefix = project_settings["PackageNamePrefix"]
    project_directory = package_name_prefix \
        if package_name_prefix == package_name_prefix.replace(".", "/") \
        else package_name_prefix.replace(".", "/")

    project_settings.setdefault('Client', {})
    java_client_keys = ['Client', 'Builder', 'ResourceModel']
    for key in java_client_keys:
        project_settings['Client'].setdefault(key, key.upper())

    source_directory = os.path.join(output_directory, "src", project_directory)
    test_directory = os.path.join(output_directory, "tst")

    print('Creating output directory...')
    os.system('mkdir -p ' + source_directory + '/{handlers,models,utils} '
              + test_directory + '/{unit,integration}')

    # destination files
    handler_file = os.path.join(source_directory, "handlers", "{}{}Handler.java")
    # % (resource name, handler_type)
    models_file = os.path.join(source_directory, "models/{}Model.java")
    # % resource_name
    utils_file = os.path.join(source_directory, "utils/{}.java")
    # % utils_class_name
    unit_file = os.path.join(test_directory, "unit/{}HandlerUnitTests.java")
    # % handler_type
    unit_testbase_file = os.path.join(test_directory, "unit/TestBase.java")
    integ_file = os.path.join(test_directory, "integration/{}IntegrationTests.java")
    # % resource_name
    # not sure how to format long line above

    # dictionary maps template_path: output_path
    templates_and_outputs = {
        'handlers/{}Handler.java'.format(handler_type): handler_file.format(resource_name, handler_type)
        for handler_type in curdl
    }  # not sure how to format long line above
    templates_and_outputs.update({
        'models/ResourceModel.java': models_file.format(resource_name),
        'utils/ClientBuilder.java': utils_file.format(
            resource_service_name(resource_def["Type"]) + 'ClientBuilder'),
        'utils/ResourceResponseReturner.java': utils_file.format('ResourceResponseReturner'),
        'unit/TestBase.java': unit_testbase_file,
        'integration/IntegrationTests.java': integ_file.format(resource_name),
    })
    templates_and_outputs.update({
        'unit/{}HandlerUnitTests.java'.format(handler_type): unit_file.format(handler_type)
        for handler_type in curdl
    })  # not sure how to format long lines above

    # writes a jinja subclass to the templates folder and adds the subresource
    # template:output pair to the dictionary.
    try:
        for definition_name, definition_properties in resource_def['Definitions'].items():
            # not sure how to format long line above
            definition_properties = definition_properties["Properties"]
            template_path = 'models/ResourceModel.java'
            template = env.get_template(template_path)
            def_output_path = os.path.join(source_directory, 'models/{}Model.java'.format(definition_name))
            # not sure how to format long line above
            with open(def_output_path, 'w', encoding='utf-8') as f:
                f.write(template.render(
                    **resource_def,
                    **project_settings,
                    resource_name=definition_name,
                    resource_properties=definition_properties,
                ))
    except KeyError as e:
        print("ERROR: " + e)

    for template_path, output_path in templates_and_outputs.items():
        template = env.get_template(template_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template.render(
                **resource_def,
                **project_settings,
                resource_name=resource_type_name(resource_def["Type"]),
                resource_properties=resource_def["Properties"],
            ))
