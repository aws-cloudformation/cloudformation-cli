Uluru resource provider CLI
===========================

Usage
=====

TODO: add command to write out default project settings

.. code-block:: bash

    uluru-cli generate \
        examples/aws-kinesis-stream.json \
        --project-settings examples/java_project.json

Development
===========

It's strongly suggested to install the development dependencies inside a
virtual environment:

.. code-block:: bash

    virtualenv -p python3 env
    source env/bin/activate
    pip install -r requirements.txt
    pip install -e .

Before submitting code, please lint the code, you can use the ``run_lint``
script, which executes these three commands:

.. code-block:: bash

    isort -y
    flake8 uluru/
    pylint uluru/
