"""Uluru CLI."""
import os.path

from setuptools import setup

readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'README.rst'))
with open(readme_path, encoding='utf-8') as f:
    readme = f.read()

setup(
    name='uluru-cli',
    version='0.1',
    description=__doc__,
    long_description=readme,
    author='AWS CloudFormation',
    author_email='no-reply@amazon.com',
    url='https://aws.amazon.com/cloudformation/',
    license='All rights reserved',
    packages=['uluru'],
    package_data={
        'uluru': ['data/*', 'templates/*']
    },
    install_requires=[
        'jinja2',
        'jsonschema',
    ],
    zip_safe=True,
    entry_points={
        'console_scripts': ['uluru-cli = uluru.cli:main']
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Code Generators',
        'Operating System :: OS Independent',
    ],
    keywords='AWS CloudFormation')
