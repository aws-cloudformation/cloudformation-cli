# AWS::Color::Red

a test schema

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "AWS::Color::Red",
    "Properties" : {
        "<a href="#propertya" title="PropertyA">PropertyA</a>" : <i><a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a></i>,
        "<a href="#propertyj" title="PropertyJ">PropertyJ</a>" : <i>String</i>,
        "<a href="#multiproperty" title="MultiProperty">MultiProperty</a>" : <i><a href="properties2.md">Properties2</a>, <a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a>, Map</i>,
        "<a href="#multiproperty2" title="MultiProperty2">MultiProperty2</a>" : <i>Integer, Map</i>
    }
}
</pre>

### YAML

<pre>
Type: AWS::Color::Red
Properties:
    <a href="#propertya" title="PropertyA">PropertyA</a>: <i><a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a></i>
    <a href="#propertyj" title="PropertyJ">PropertyJ</a>: <i>String</i>
    <a href="#multiproperty" title="MultiProperty">MultiProperty</a>: <i><a href="properties2.md">Properties2</a>, <a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a>, Map</i>
    <a href="#multiproperty2" title="MultiProperty2">MultiProperty2</a>: <i>Integer, Map</i>
</pre>

## Properties

#### PropertyA

_Required_: No

_Type_: <a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyJ

_Required_: No

_Type_: String

_Minimum_: <code>13</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### MultiProperty

_Required_: No

_Type_: <a href="properties2.md">Properties2</a>, <a href="properties4.md">Properties4</a>, <a href="properties3.md">Properties3</a>, Map

_Update requires_: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

#### MultiProperty2

_Required_: No

_Type_: Integer, Map

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the MultiProperty.
