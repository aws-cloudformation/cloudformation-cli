# test<a name="resource-type-cli-test"></a>

## Description<a name="resource-type-cli-test-description"></a>

Performs contract tests on the handlers of a resource provider\.

## Synopsis<a name="resource-type-cli-test-synopsis"></a>

```
  cfn test
[--endpoint <value>]
[--function-name <value>]
[--region <value>]
[--role-arn <value>]
```

## Options<a name="resource-type-cli-test-options"></a>

`--endpoint <value>`

The endpoint at which the type can be invoked\. Alternately, you can also specify an actual Lambda endpoint and function name in your AWS account\.

Default: `http://127.0.0.1.3001`

`--function-name <value>`

The logical lambda function name in the SAM template\. Alternately, you can also specify an actual Lambda endpoint and function name in your AWS account\.

Default: `TestEntrypoint`

`--region <value>`

The region to use for temporary credentials\.

Default: `us-east-1`

`--role-arn <value>`

The Amazon Resource Name \(ARN\) of the IAM execution role for the contract tests to assume and use when performing operations\.

If you do not specify an execution role, the contract tests use the environment credentials or the credentials specified in the [Boto 3 credentials chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)\.

## Output<a name="resource-type-cli-test-output"></a>
