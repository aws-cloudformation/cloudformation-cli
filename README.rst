Uluru resource provider CLI
===========================

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

To generate code, a resource specification is required. You can customize
certain, language-specific project settings, otherwise the default settings
are used.

.. code-block:: bash

    uluru-cli generate \
        examples/aws-kinesis-stream.yaml \
        --language java \
        --project-settings examples/java_project.json


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

Before submitting code, please execute the ``run_lint`` script. It will execute
all linters (`flake8 <http://flake8.pycqa.org/en/latest/>`_ and
`pylint <https://www.pylint.org/>`_), as well as the unit tests.
