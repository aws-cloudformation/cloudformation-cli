# AWS::Color::Red

a test schema

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "AWS::Color::Red",
    "Properties" : {
        "<a href="#property1" title="property1">property1</a>" : <i>String, Double, Map, [ <a href="obj2def.md">obj2def</a>, ... ]</i>,
        "<a href="#obj1" title="obj1">obj1</a>" : <i><a href="obj2def.md">obj2def</a></i>,
        "<a href="#arr1" title="arr1">arr1</a>" : <i>[ <a href="obj2def.md">obj2def</a>, ... ]</i>
    }
}
</pre>

### YAML

<pre>
Type: AWS::Color::Red
Properties:
    <a href="#property1" title="property1">property1</a>: <i>String, Double, Map,
      - <a href="obj2def.md">obj2def</a></i>
    <a href="#obj1" title="obj1">obj1</a>: <i><a href="obj2def.md">obj2def</a></i>
    <a href="#arr1" title="arr1">arr1</a>: <i>
      - <a href="obj2def.md">obj2def</a></i>
</pre>

## Properties

#### property1

some description

_Required_: No

_Type_: String, Double, Map, List of <a href="obj2def.md">obj2def</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### obj1

_Required_: No

_Type_: <a href="obj2def.md">obj2def</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### arr1

_Required_: No

_Type_: List of <a href="obj2def.md">obj2def</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the enum1.

### Fn::GetAtt

The `Fn::GetAtt` intrinsic function returns a value for a specified attribute of this type. The following are the available attributes and sample return values.

For more information about using the `Fn::GetAtt` intrinsic function, see [Fn::GetAtt](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html).

#### str3
