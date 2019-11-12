AWS CloudFormation Resource Provider Development Kit
====================================================

The CloudFormation CLI (cfn) allows you to author your own resource providers that can be used by CloudFormation.

Development
-----------

For developing, it's strongly suggested to install the development dependencies
inside a virtual environment. (This isn't required if you just want to use this
tool.)

.. code-block:: bash

    python3 -m venv env
    source env/bin/activate
    pip install -e . -r requirements.txt
    pre-commit install

You will also need to install a language plugin, such as `the Java language plugin <https://github.com/aws-cloudformation/aws-cloudformation-rpdk-java-plugin>`_, also via `pip install`. For example, assuming the plugin is checked out in the same parent directory as this repository:

.. code-block:: bash

    pip install -e ../aws-cloudformation-rpdk-java-plugin

Linting and running unit tests is done via `pre-commit <https://pre-commit.com/>`_, and so is performed automatically on commit. The continuous integration also runs these checks. Manual options are available so you don't have to commit):

```
# run all hooks on all files, mirrors what the CI runs
pre-commit run --all-files
# run unit tests only. can also be used for other hooks, e.g. black, flake8, pylint-local
pre-commit run pytest-local
```

If you want to generate an HTML coverage report afterwards, run
``coverage html``. The report is output to ``htmlcov/index.html``.

Usage
-----

WARNING: Future Information; we have *not* published to PyPI yet.

Installation
^^^^^^^^^^^^

This tool can be installed using `pip <https://pypi.org/project/pip/>`_ from
the Python Package Index (PyPI). It requires Python 3.

.. code-block:: bash

    pip3 install cfn

Command: init
^^^^^^^^^^^^^

To create a project in the current directory, use the ``init`` command. A wizard will guide you through the creation.

.. code-block:: bash

    cfn init

Command: generate
^^^^^^^^^^^^^^^^^

To refresh auto-generated code, use the ``generate`` command. Usually, plugins try to integrate this command in the native build flow, so please consult a plugin's README to see if this is necessary.

.. code-block:: bash

    cfn generate

Plugin system
-------------

New language plugins can be independently developed. As long as they declare
the appropriate entry point and are installed in the same environment, they can
even be completely separate codebases. For example, a plugin for Groovy might
have the following entry point:

.. code-block:: python

    entry_points={
        "rpdk.v1.languages": ["groovy = rpdk.groovy:GroovyLanguagePlugin"],
    },

Plugins must provide the same interface as ``LanguagePlugin`` (in
``plugin_base.py``). And they may inherit from ``LanguagePlugin`` for the helper
methods - but this is not necessary. As long as the class has the same methods,
it will work as a plugin.

License
-------

This library is licensed under the Apache 2.0 License.
