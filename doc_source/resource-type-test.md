# Testing resource types using contract tests<a name="resource-type-test"></a>

As you model and develop your resource type, you can have the CloudFormation CLI perform tests to ensure the resource type is behaving as expected during each event in the resource lifecycle\. The CloudFormation CLI performs a suite of tests, each written to test a requirement contained in the resource type handler contract\.

## Testing resource types locally using SAM<a name="resource-type-develop-test"></a>

Once you've implemented the desired handlers for your resource, you can also test the resource locally using the AWS SAM command line interface \(CLI\), to make sure your resource behaves as expected, debug what's wrong, and fix any issues\. 

To start testing, use the SAM CLI to start the Local Lambda Service\. Run the following command in a terminal separate from your resource type workspace, or as a background process\.

```
$ sam local start-lambda
```

If you have functions defined in your SAM template, it will provide an endpoint to invoke these functions locally\. This is especially helpful because it allows for remote debugging to step through resource type invocations in real time\.

```
Starting the Local Lambda Service. You can now invoke your Lambda Functions defined in your template through the endpoint.
2020-01-15 15:27:19  * Running on http://127.0.0.1:3001/ (Press CTRL+C to quit)
```

Alternatively, you can also specify using the public Lambda Service and invoke functions deployed in your account\. Be aware, however, that using the local service allows for more iteration\. To specify a debug port for remote debugging, use the `-d` option:

```
sam local start-lambda -d PORT
```

Once you have the Lamdba service started, use the `[test](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-cli-test.html)` command to perform contract tests:

```
cfn test
```

The CloudFormation CLI selects the appropriate contract tests to execute, based on the handlers specified in your resource type schema\. If a test fail, the CloudFormation CLI outputs a detailed trace of the failure, including the related assertion failure and mismatched values\.

For more information on testing using AWS SAM CLI, see [Testing and Debugging Serverless Applications](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-test-and-debug.html) in the *AWS Serverless Application Model Developer Guide*\.

## How the CloudFormation CLI constructs and executes contract tests<a name="resource-type-test-how"></a>

The CloudFormation CLI uses [PyTest](https://docs.pytest.org/en/latest/), an open\-source testing framework, to execute the contract tests\. 

The tests themselves are located in the [suite](https://github.com/aws-cloudformation/cloudformation-cli/tree/master/src/rpdk/core/contract/suite) folder of the CloudFormation CLi repostitory on GitHub\. Each test is adorned with the appropriate `pytest` markers\. For example, tests applicable to the `create` handler are adorned with the `@pytest.mark.create` marker\. This enables the CloudFormation CLI to execute only those tests appropriate for a resource type, based on the handlers specified in the resource type's schema\. For example, suppose a resource type's schema specified `create`, `read`, and `delete` handlers\. In this case, the CloudFormation CLI would not perform any test marked with only the `@pytest.mark.update` or `@pytest.mark.list`, since those handlers were not implemented\.

To test `create` and `update` handlers, the CloudFormation CLI uses the resource type's schema and [Hypothesis](https://hypothesis.readthedocs.io/en/latest/), an open\-source Python library used to generate testing strategies\. The resource type schema is walked to generate a strategy for valid resource models, and the strategy is used to generate models for tests\.

Tests create, update, and delete resources to test various aspects of the resource handler contract during handler operations\. The CloudFormation CLI uses PyTest `fixtures` to decrease the amount of time the contract tests take to perform\. Using fixtures enable the tests within a test module to share resources, rather than have to create a new resource for each test\. Currently, the contract tests employ the following fixtures:
+ `created_resource` in the `[handler\_create](https://github.com/aws-cloudformation/cloudformation-cli/blob/master/src/rpdk/core/contract/suite/handler_create.py#L22)` test module
+ `updated_resource` in the `[handler\_update](https://github.com/aws-cloudformation/cloudformation-cli/blob/master/src/rpdk/core/contract/suite/handler_update.py#L15)` test module
+ `deleted_resource` in `[handler\_delete](https://github.com/aws-cloudformation/cloudformation-cli/blob/master/src/rpdk/core/contract/suite/handler_delete.py#L26)` test module

## Specifying input data for use in contract tests<a name="resource-type-test-input-data"></a>

By default, the CloudFormation CLI performs resource contract tests using input properties generated from the patterns you define in your resource type schema\. However, most resources are complex enough that the input properties for creating or updating those resources requires an understanding of the resource being provisioned\. To address this, you can specify the input the CloudFormation CLI uses when performing its contract tests\. 

The CloudFormation CLI offers two ways for you to specify the input data for it to use when performing contract tests:
+ Overrides file

  Using an `overrides` file provides a light\-weight way of specifying input data for certain specific properties for the CloudFormation CLI to use during both create and update operations testing\.
+ Input files

  You can also use multiple `input` files to specify contract test input data if:
  + You want or need to specify different input data for create and update operations, or invalid data with which to test\.
  + You want to specify multiple different input data sets\.

### Specifying input data using an override file<a name="resource-type-test-overrides"></a>

Using an override file enables you to overwrite input values for specific resource properties\. Input values specified in the override file are used in contract testing for both create and update operations\. You can only specify a single override file, and only specify a single input value for each resource property\. For any properties for which you do not specify values, the CloudFormation CLI uses generated input\.

Because the input data specified in the `overrides.json` file is used by the CloudFormation CLI during testing of create and update operations, you cannot include input values for create\-only properties in the file, as this would lead to contract test failures during update operations\. For more information, see [createOnlyProperties](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-schema.html#schema-properties-createonlyproperties)\.

To override the input data used for specific properties during contract testing, add an `overrides.json` file to the root directory of your resource type project\. The `overrides.json` file should contain only the resource properties to be used in testing\. Use the following syntax:

```
{
    "CREATE": {
        "/property_name": "property_value" # optional_comment
    }
}
```

For example:

```
{
    "CREATE": {
        "/SubnetId": "subnet-0bc6136e" # This should be a real subnet that exists in the account you're testing against.
    }
}
```

You can also use output values from other stacks when specifying input data\. For example, suppose you had a stack that contained an export value named `SubnetExport`:

```
Resources:
    VPC:
        Type: "AWS::EC2::VPC"
        Properties:
            CidrBlock: "10.0.0.0/16"
    Subnet:
        Type: "AWS::EC2::Subnet"
        Properties:
           CidrBlock: "10.0.0.0/24"
           VpcId: !Ref VPC
Outputs:
    SubnetId:
        Value: !Ref Subnet
        Export:
            Name: SubnetExport
```

You could then specify that export value as input data using the export value name using the following syntax:

```
{
  "CREATE": {
    "/SubnetId": “{{SubnetExport}}"
  }
}
```

For more information, see [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html)\.

### Specifying input data using input files<a name="resource-type-test-inputs"></a>

Use `input` files to specify different kinds of input data for the CloudFormation CLI to use: create input, update input, and invalid input\. Each kind of data is specified in a separate file\. You can also specify multiple sets of input data for contract tests\. 

To specify `input` files for the CloudFormation CLI to use in contract testing, add an `inputs` folder to the root directory of your resource type project\. Then add your input files\.

Specify which kind of input data a file contains by using the following naming conventions, where **n** is an integer:
+ `inputs_n_create.json`: Use files with `_create.json` for specifying inputs for creating the resource\. This includes input values for create\-only properties\. For more information, see [createOnlyProperties](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-schema.html#schema-properties-createonlyproperties)\.
+ `inputs_n_update.json`: Use files with `_update.json` for specifying inputs for updating the resource\.
+ `inputs_n_invalid.json`: Use files with `_invalid.json` for specifying invalid inputs to test when creating or updating the resource\.

To specify multiple sets of input data for contract tests, increment the integer in the file names to order your input data sets\. For example, your first set of input files should be named `inputs_1_create.json`, `inputs_1_update.json`, and `inputs_1_invalid.json`\. Your next set would be named `inputs_2_create.json`, `inputs_2_update.json`, and `inputs_2_invalid.json`, and so on\.

Each input file is a JSON file containing only the resource properties to be used in testing\. Below is an example of an input file data set\. 

```
{
   "AlarmName": "Name",
   "AlarmDescription": "TestAlarmDimensions Description",
   "Namespace": "CloudWatchNamespace",
   "MetricName": "Fault",
   "Dimensions": [
      {
         "Name": "MethodName",
         "Value": "Value"
      }
   ],
   "Statistic": "Average",
   "Period": 60,
   "EvaluationPeriods": 5,
   "Threshold": 0.01,
   "ComparisonOperator": "GreaterThanOrEqualToThreshold"
}
```

If you specify an `inputs` folder, the CloudFormation CLI uses only the input data included in that folder\. Therefore, you must specify create, update, and invalid data files for the CloudFormation CLI to successfully complete the contract tests\.

If you specify both input files and an overrides files, the CloudFormation CLI ignores the overrides file and just uses the input data specified in the `inputs` folder\.

You can also use output values from other stacks when specifying input data\. For example, suppose you had a stack that contained an export value named `SubnetExport`:

```
Resources:
    VPC:
        Type: "AWS::EC2::VPC"
        Properties:
            CidrBlock: "10.0.0.0/16"
    Subnet:
        Type: "AWS::EC2::Subnet"
        Properties:
           CidrBlock: "10.0.0.0/24"
           VpcId: !Ref VPC
Outputs:
    SubnetId:
        Value: !Ref Subnet
        Export:
            Name: SubnetExport
```

You could then specify that export value as input data using the export value name using the following syntax:

```
{
   "SubnetId": "{{SubnetExport}}",
   . . . 
}
```

For more information, see [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html)\.