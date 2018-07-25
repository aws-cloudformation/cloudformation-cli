from uluru.filters import java_class_name, resource_type_name


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
