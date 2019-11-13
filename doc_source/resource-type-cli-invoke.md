# invoke<a name="resource-type-cli-invoke"></a>

## Description<a name="resource-type-cli-invoke-description"></a>

Performs contract tests on the specified handler of a resource provider\.

## Synopsis<a name="resource-type-cli-invoke-synopsis"></a>

```
  cfn invoke
[--endpoint <value>]
[--function-name <value>]
[--region <value>]
[--max-reinvoke <value>]
action
request
```

## Options<a name="resource-type-cli-invoke-options"></a>

`--endpoint <value>`

The endpoint at which the type can be invoked\. Alternately, you can also specify an actual Lambda endpoint and function name in your AWS account\.

Default: `http://127.0.0.1.3001`

`--function-name <value>`

The logical lambda function name in the SAM template\. Alternately, you can also specify an actual Lambda endpoint and function name in your AWS account\.

Default: `TestEntrypoint`

`--region <value>`

The region to configure the client to interact with\.

Default: `us-east-1`

`--max-reinvoke <value>`

Maximum number of IN\_PROGRESS re\-invocations allowed before exiting\. If not specified, will continue to re\- invoke until terminal status is reached\.

`action`

Which single handler to invoke\.

Values: `CREATE` \| `READ` \| `UPDATE` \| `DELETE` \| `LIST`

`request`

File path to a JSON file containing the request with which to invoke the function\.

## Output<a name="resource-type-cli-invoke-output"></a>
