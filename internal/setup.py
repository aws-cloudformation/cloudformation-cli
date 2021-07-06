from setuptools import setup

setup(
    name="AWSCloudFormationRPDK",
    version="1.0",
    packages=["rpdk.core"],
    package_dir={"": "src"},
    include_package_data=True,
    entry_points={
        "console_scripts": ["cfn-cli = rpdk.core.cli:main", "cfn = rpdk.core.cli:main"]
    },
    # Not all tests passed in Brazil due to some test dependency versions missing in Brazil
    # Since all test are run in GitHub/CodeBuild, only verify one test
    options={
        "brazil_test": {
            "addopts": "tests/test_cli.py",
        },
    },
    root_script_source_version="default-only",
    check_format=True,
)
