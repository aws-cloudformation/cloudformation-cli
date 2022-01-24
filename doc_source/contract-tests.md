# Contract tests<a name="contract-tests"></a>

As part of testing your resource, the CloudFormation CLI performs a suite of tests, each written to test a requirement contained in the [resource type handler contract](resource-type-test-contract.md)\. Each handler invocation is expected to follow the general requirements for that handler listed in the contract\. This topic lists tests that explicitly test some of the more specific requirements\.

## `create` handler tests<a name="contract-tests-create"></a>

The CloudFormation CLI performs the following contract tests for `create` handlers\.


| Test | Description |
| --- | --- |
|  **contract\_create\_create**  |  Creates a resource, waits for the resource creation to complete, and then creates the resource again with the expectation that the second create operation will fail with the `AlreadyExists` error code\. This test is not run for resources if the primary identifier or any additional identifiers are read\-only\.  |
|  **contract\_create\_read**  |  Creates a resource, waits for the resource creation to complete, and then reads the created resource to ensure that the input to the `create` handler is equal to the output from the `read` handler\. The comparison ignores any read\-only/generated properties in the `read` output, as create input cannot specify these\. It also ignores any write\-only properties in the create input, as these are removed from read output to avoid security issues\.  |
|  **contract\_create\_delete**  |  Creates a resource, waits for the resource creation to complete, and then deletes the created resource\. It also checks if the create input is equal to the create output \(which is then used for delete input\), with the exception of readOnly and writeOnly properties\.  |
|  **contract\_create\_list**  |  Creates a resource, waits for the resource creation to complete, and then lists out the resources with the expectation that the created resource exists in the returned list\.  |

## `update` handler tests<a name="contract-tests-update"></a>

The CloudFormation CLI performs the following contract tests for `update` handlers\.


| Test | Description |
| --- | --- |
|  **contract\_update\_read**  |  Creates a resource, updates the resource, and then reads the resource to check that the update was made by comparing the read output with the update input\. The comparison excludes read\-only and write\-only properties because they cannot be included in the update input and read output, respectively\.  |
|  **contract\_update\_list**  |  Creates a resource, updates the resource, and then lists the resource to check that the updated resource exists in the returned list\.  |
|  **contract\_update\_without\_create**  |  Updates a resource without creating it first\. The test expects the update operation to fail with the `NotFound` error code\.  |

## `delete` handler tests<a name="contract-tests-delete"></a>

The CloudFormation CLI performs the following contract tests for `delete` handlers\.


| Test | Description |
| --- | --- |
|  **contract\_delete\_create**  |  Creates a resource, deletes the resource, and then creates the resource again with the expectation that the deletion was successful and a new resource can be created\. The CloudFormation CLI performs this contract test for resources with create\-only primary identifiers\.  |
|  **contract\_delete\_update**  |  Creates a resource, deletes the resource, and then updates the resource with the expectation that the update operation will fail with the `NotFound` error code\.  |
|  **contract\_delete\_read**  |  Creates a resource, deletes the resource, and then reads the resource with the expectation that the read operation will fail with the `NotFound` error code\.  |
|  **contract\_delete\_list**  |  Creates a resource, deletes the resource, and then lists the resource with the expectation that the returned list does not contain the deleted resource\.  |
|  **contract\_delete\_delete**  |  Creates a resource, deletes the resource, and then deletes the resource again with the expectation that the second delete operation will fail with the `NotFound` error code\.  |
