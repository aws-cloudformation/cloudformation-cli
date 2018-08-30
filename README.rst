AWS CloudFormation Resource Provider Development Kit
====================================================

The CloudFormation Resource Provider Development Kit (RPDK) allows you to author your own resource providers that can be used by CloudFormation.

Usage
-----

Quickstart
^^^^^^^^^^

.. code-block:: bash

    pip3 install uluru-cli
    uluru-cli generate \
        examples/aws-kinesis-stream.yaml

Installation
^^^^^^^^^^^^

This tool can be installed using `pip <https://pypi.org/project/pip/>`_ from
the Python Package Index (PyPI). It requires Python 3.

.. code-block:: bash

    pip3 install uluru-cli


Command: project-settings
^^^^^^^^^^^^^^^^^^^^^^^^^

To output the default project settings for a given language, use the
``project-settings`` command.

.. code-block:: bash

    uluru-cli project-settings \
        --language java \
        --output project.yaml

Command: generate
^^^^^^^^^^^^^^^^^

To generate code, a resource provider definition is required. You can customize
certain, language-specific project settings, otherwise the default settings
are used.

.. code-block:: bash

    uluru-cli generate \
        examples/aws-kinesis-stream.yaml \
        --language java \
        --project-settings examples/java_project.json

Plugin system
-------------

New language plugins can be independently developed. As long as they declare
the appropriate entry point and are installed in the same environment, they can
even be completely separate codebases. For example, a plugin for Groovy might
have the following entry point:

.. code-block:: python

    entry_points={
        "uluru.languages": ["groovy = uluru-groovy:GroovyLanguagePlugin"],
    },

Plugins must provide the same interface as ``LanguagePlugin`` (in
``plugin_base.py``). And they may inherit from ``LanguagePlugin`` for the helper
methods - but this is not necessary. As long as the class has the same methods,
it will work as a plugin.

Development
-----------

For developing, it's strongly suggested to install the development dependencies
inside a virtual environment. (This isn't required if you just want to use this
tool.)

.. code-block:: bash

    virtualenv -p python3 env
    source env/bin/activate
    pip install -r requirements.txt
    pip install -e .

Before committing code, please execute the ``run_lint`` script. This performs
several steps for your convenience:

* Auto-formatting of all code to make it uniform and PEP8 compliant
* Linting for issues the auto-formatter doesn't catch
* Run all tests and confirm coverage is over a threshold

If you want to generate an HTML coverage report afterwards, run
``coverage html``. The report is output to ``htmlcov/index.html``.

License
-------

This library is licensed under the Apache 2.0 License.
