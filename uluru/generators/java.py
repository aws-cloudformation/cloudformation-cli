
def generate(env, resource_spec, project_settings):
    template = env.get_template('handlers/CreateHandler.java')
    with open('out.java', 'w', encoding='utf-8') as f:
        f.write(template.render(**resource_spec, **project_settings))
