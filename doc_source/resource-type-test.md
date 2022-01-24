# Testing resource types using contract tests<a name="resource-type-test"></a>

As you model and develop your resource type, you should have the CloudFormation CLI perform tests to ensure that the resource type is behaving as expected during each event in the resource lifecycle\. The CloudFormation CLI performs a suite of tests called contract tests to enforce CloudFormation’s [handler contract](resource-type-test-contract.md)\. Developing and registering your resource type in CloudFormation signifies an agreement that your resource is compliant and doesn't break any framework expectations\. All resources that fail contract tests are blocked from publishing into our registry\.

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

Once you have the Lambda service started, use the `[test](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-cli-test.html)` command to perform contract tests:

```
cfn test
```

The CloudFormation CLI selects the appropriate contract tests to execute, based on the handlers specified in your resource type schema\. If a test fails, the CloudFormation CLI outputs a detailed trace of the failure, including the related assertion failure and mismatched values\.

For more information on testing using AWS SAM CLI, see [Testing and Debugging Serverless Applications](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-test-and-debug.html) in the *AWS Serverless Application Model Developer Guide*\.

## How the CloudFormation CLI constructs and executes contract tests<a name="resource-type-test-how"></a>

The CloudFormation CLI uses [PyTest](https://docs.pytest.org/en/latest/), an open\-source testing framework, to execute the contract tests\.

The tests themselves are located in the [suite](https://github.com/aws-cloudformation/cloudformation-cli/tree/master/src/rpdk/core/contract/suite) folder of the CloudFormation CLI repository on GitHub\. Each test is adorned with the appropriate `pytest` markers\. For example, tests applicable to the `create` handler are adorned with the `@pytest.mark.create` marker\. This enables the CloudFormation CLI to execute only those tests appropriate for a resource type, based on the handlers specified in the resource type's schema\. For example, suppose a resource type's schema specified `create`, `read`, and `delete` handlers\. In this case, the CloudFormation CLI would not perform any test marked with only the `@pytest.mark.update` or `@pytest.mark.list`, since those handlers were not implemented\.

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
    "/SubnetId": "{{SubnetExport}}"
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

## Viewing contract test logs<a name="debug-contract-test"></a>

It's important to note that contract tests are not run during private type registration \(unless the resource contains one of the following namespaces: `aws`, `amzn`, `alexa`, `amazon`, `awsquickstart`\), but failing contract tests does block a publisher’s ability to publish their type\. This is because public resources are consumed by other external customers and need to maintain a high quality bar\. For this reason, it is important to debug your contract test failures early on in the resource development process\.

Running contract tests generates two types of logs\. Using both helps expedite the debugging process\.
+ **Lambda logs** show logs from your handlers and provide more details on the input and output for each handler call\.
+ **Test logs** show the result of running the test suite, including which tests have failed or passed, as well as a traceback if a test has failed\.

Because there are multiple ways to invoke contract tests against your resource, there are different places to find logs depending on which method you are using\.
+ If you run contract tests locally, logs are divided into the following two sections:
  + Lambda logs are in the terminal tab in which you ran `sam local start-lambda`\.
  + Test logs are in the terminal tab in which you ran `cfn test`\.
+ If you run contract tests via type registration \(`cfn submit`\), logs are uploaded in two areas\. Note that contract tests are only run during type registration if your type name includes one of the following namespaces: `aws`, `amzn`, `alexa`, `amazon`, `awsquickstart`\.
  + Lambda logs are delivered to a CloudWatch log group in your account\. The log group adheres to the following naming pattern:

    `<Hyphenated TypeName>-ContractTests-<RegistrationToken>`

    For example, `aws-cloudwatch-alarm-ContractTests-ca7096d7-ccb3-4c7d-ad51-78d0a1a300ca`\.
  + To receive test logs in an Amazon S3 bucket, you have to modify the IAM role that is created by CloudFormation, which adheres to the following naming pattern:

    `CloudFormationManagedUplo-LogAndMetricsDeliveryRol-<RandomId>`

    Add the following inline policy:

    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            },
            {
                "Action": [
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey"
                ],
                "Resource": "*",
                "Effect": "Allow"
            }
        ]
    }
    ```

    Also add the following trust policy:

    ```
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": [
              "cloudformation.amazonaws.com",
              "resources.cloudformation.amazonaws.com"
            ]
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    ```

    Invoking `cfn submit --role-arn <arn for above IAM role>` uploads your test logs to an Amazon S3 bucket named `cloudformationmanageduploadinfrast-artifactbucket-<RandomId>` under the following path:

    `CloudFormation/ContractTestResults/<TypeName>/<ContractTestInvocationToken>.zip`

    Download the zip file to see your test logs\.
+ If you run contract tests against your registered type via `TestType`, both logs are condensed and uploaded to an Amazon S3 bucket in your account\. You must specify the [https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_TestType.html#API_TestType_RequestParameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_TestType.html#API_TestType_RequestParameters) parameter when invoking `TestType` to receive logs in your account\.

## Testing resource types manually<a name="manual-testing"></a>

Running contract tests with the `cfn-test` command uses the AWS SAM CLI, so it's possible to attach a debugger from your IDE by specifying a port when you start the local Lambda service\. However, we don't recommend this approach because the debugger detaches after each individual handler invocation completes\.

Instead, you can mimic the scenarios modeled in contract tests by invoking the handlers with the [https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-invoke.html](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-invoke.html) command\. This allows you to step through each handler invocation without interruption\. You first need to define test templates that AWS SAM can run against the resource handlers\. Create the test templates in a separate folder in the resource directory and name the folder `sam-tests`\.

The test templates must adhere to the following format:

```
{
  "credentials": {
    "accessKeyId": "<Access Key Id>",
    "secretAccessKey": "<Secret Access key>",
    "sessionToken": "<Session Token>"
  },
  "action": "<Action>",
  "request": {
    "clientRequestToken": "<Random UUID>",
    "desiredResourceState": <ResourceModel json>,
    "logicalResourceIdentifier": "<Logical Id>"
  },
  "callbackContext": <CallbackContext json>
}
```
+ For **credentials**, use temporary credentials of your personal AWS account\. To retrieve these, run `aws sts get-session-token`\.
+ For **action**, specify the handler you want to test\. Allowed values: `CREATE`, `READ`, `DELETE`, `UPDATE`, `LIST`\.
+ For **clientRequestToken**, specify a random UUID string\. To retrieve this, use any UUID generator tool\.
+ For **desiredResourceState**, specify the properties of the resource required for the request that follow the resource schema\.
+ For **logicalResourceIdentifier**, specify a logical ID to assign to your resource instance\. You can use this in subsequent handler invocations for the same resource\.
+ For **callbackContext**, the request begins with a null value for callback context\. For handlers with stabilization logic, the subsequent requests have callback context from the previous request’s response\.

Once you've written the input files, do the following to debug your handlers:

1. Ensure that Docker is downloaded and installed on your machine, and that you've added the resource directory to Docker\.

1. In one terminal, start the local Lambda service by running `sam local start-lambda`\.

1. In your IDE, create a remote configuration and add a port number\. Add a breakpoint in the appropriate handler you are invoking\.

1. In another terminal, invoke the handler by running `sam local invoke TestEntrypoint --event sam-tests/<input filename> -d <PORT number>`\.

1. Step through the code to debug any handler errors\.

For more information about testing using the AWS SAM CLI, see [Testing and Debugging Serverless Applications](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-test-and-debug.html) in the *AWS Serverless Application Model Developer Guide*\.
