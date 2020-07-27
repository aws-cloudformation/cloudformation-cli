# AWS CloudFormation CLI

The CloudFormation CLI (cfn) allows you to author your own resource providers that can be used by CloudFormation.

## Usage

### Documentation

Primary documentation for the CloudFormation CLI can be found at the [AWS Documentation](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-types.html) site.

### Installation

This tool can be installed using [pip](https://pypi.org/project/pip/) from the Python Package Index (PyPI). It requires Python 3. The tool requires at least one language plugin. The language plugins are also available on PyPI and as such can be installed all at once:

```bash
pip install cloudformation-cli cloudformation-cli-java-plugin cloudformation-cli-go-plugin cloudformation-cli-python-plugin
```


### Command: init

To create a project in the current directory, use the `init` command. A wizard will guide you through the creation.

```bash
cfn init
```

### Command: generate

To refresh auto-generated code, use the `generate` command. Usually, plugins try to integrate this command in the native build flow, so please consult a plugin's README to see if this is necessary.

```bash
cfn generate
```

### Command: test

To run the contract tests, use the `test` command.

```bash
cfn test
cfn test -- -k contract_delete_update #to run a single test
cfn test --enforce-timeout 60 #set the RL handler timeout to 60 seconds and CUD handler timeout to 120 seconds.
cfn test --enforce-timeout 60 -- -k contract_delete_update # combine args
```


## Development

For developing, it's strongly suggested to install the development dependencies inside a virtual environment. (This isn't required if you just want to use this tool.)

```bash
python3 -m venv env
source env/bin/activate
pip install -e . -r requirements.txt
pre-commit install
```

You will also need to install a language plugin, such as [the Java language plugin](https://github.com/aws-cloudformation/cloudformation-cli-java-plugin), also via `pip install`. For example, assuming the plugin is checked out in the same parent directory as this repository:

```bash
pip install -e ../cloudformation-cli-java-plugin
```

Linting and running unit tests is done via [pre-commit](https://pre-commit.com/), and so is performed automatically on commit. The continuous integration also runs these checks. Manual options are available so you don't have to commit):

```bash
# run all hooks on all files, mirrors what the CI runs
pre-commit run --all-files
# run unit tests only. can also be used for other hooks, e.g. black, flake8, pylint-local
pre-commit run pytest-local
```

If you want to generate an HTML coverage report afterwards, run `coverage html`. The report is output to `htmlcov/index.html`.

## Plugin system

New language plugins can be independently developed. As long as they declare the appropriate entry point and are installed in the same environment, they can even be completely separate codebases. For example, a plugin for Groovy might have the following entry point:

```python
entry_points={
    "rpdk.v1.languages": ["groovy = rpdk.groovy:GroovyLanguagePlugin"],
},
```

Plugins must provide the same interface as `LanguagePlugin` (in `plugin_base.py`). And they may inherit from `LanguagePlugin` for the helper methods - but this is not necessary. As long as the class has the same methods, it will work as a plugin.

### Supported plugins

| Language | Status            | Github                                                                                                      | PyPI                                                                                       |
| -------- | ----------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Java     | Available         | [cloudformation-cli-java-plugin](https://github.com/aws-cloudformation/cloudformation-cli-java-plugin/)     | [cloudformation-cli-java-plugin](https://pypi.org/project/cloudformation-cli-java-plugin/)     |
| Go       | Available         | [cloudformation-cli-go-plugin](https://github.com/aws-cloudformation/cloudformation-cli-go-plugin/)         | [cloudformation-cli-go-plugin](https://pypi.org/project/cloudformation-cli-go-plugin/)         |
| Python   | Available         | [cloudformation-cli-python-plugin](https://github.com/aws-cloudformation/cloudformation-cli-python-plugin/) | [cloudformation-cli-python-plugin](https://pypi.org/project/cloudformation-cli-python-plugin/) |

## License

This library is licensed under the Apache 2.0 License.
