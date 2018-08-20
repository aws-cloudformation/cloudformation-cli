from uluru.filters import (
    java_class_name,
    lowercase_first_letter,
    resource_service_name,
    resource_type_name
)


def test_java_class_name_valid():
    assert java_class_name('com.example.MyClass') == 'MyClass'


def test_java_class_name_invalid():
    import_name = 'com_example_MyClass'
    assert java_class_name(import_name) == import_name


def test_resource_type_name_valid():
    assert resource_type_name('AWS::ECS::Instance') == 'Instance'


def test_resource_type_name_invalid():
    resource_type = 'AWS_ECS_Instance'
    assert resource_type_name(resource_type) == resource_type


def test_resource_service_name_valid():
    assert resource_service_name('AWS::ECS::Instance') == 'ECS'


def test_resource_service_name_invalid():
    resource_type = 'AWS_ECS_Instance'
    assert resource_service_name(resource_type) == resource_type


def test_lowercase_first_letter():
    assert lowercase_first_letter('CreateHandler') == 'createHandler'


def test_lowercase_first_letter_edge():
    s = 'createHandler'
    assert lowercase_first_letter(s) == s
    assert lowercase_first_letter("") == ""
