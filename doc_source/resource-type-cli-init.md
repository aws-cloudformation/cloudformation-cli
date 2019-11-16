# init<a name="resource-type-cli-init"></a>

## Description<a name="resource-type-cli-init-description"></a>

Generates a new resource project with stub source files\. While the specific folder structure and files generated varies by language, in general the project includes:
+ Resource schema file
+ Handler function source files
+ Unit test files
+ IDE and build files for the specified language

By default, `init` generates the resource project in the current directory\.

## Synopsis<a name="resource-type-cli-init-synopsis"></a>

```
  cfn init
[--force]
```

## Options<a name="resource-type-cli-init-options"></a>

`--force`

Force project files to be overwritten\.

## Output<a name="resource-type-cli-init-output"></a>

The `init` command launches a wizard that walks you through setting up the project, including specifying the resource name\.
