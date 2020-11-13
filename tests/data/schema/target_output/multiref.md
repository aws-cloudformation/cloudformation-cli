# AWS::Color::Red

a test schema

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "AWS::Color::Red",
    "Properties" : {
        "<a href="#primaryid" title="primaryID">primaryID</a>" : <i>String</i>,
        "<a href="#propertywithmultipleconstraints" title="PropertyWithMultipleConstraints">PropertyWithMultipleConstraints</a>" : <i>String</i>,
        "<a href="#propertywithmultipleprimitives" title="PropertyWithMultiplePrimitives">PropertyWithMultiplePrimitives</a>" : <i>Integer, String, Map</i>,
        "<a href="#propertywithtwocomplextypes" title="PropertyWithTwoComplexTypes">PropertyWithTwoComplexTypes</a>" : <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a></i>,
        "<a href="#propertywithmultiplecomplextypes" title="PropertyWithMultipleComplexTypes">PropertyWithMultipleComplexTypes</a>" : <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a></i>,
        "<a href="#propertywithmultiplecomplextypesandoneprimitive" title="PropertyWithMultipleComplexTypesAndOnePrimitive">PropertyWithMultipleComplexTypesAndOnePrimitive</a>" : <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a>, Map</i>,
        "<a href="#propertywithcomplextypeandprimitive" title="PropertyWithComplexTypeAndPrimitive">PropertyWithComplexTypeAndPrimitive</a>" : <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a></i>,
        "<a href="#multiproperty3" title="MultiProperty3">MultiProperty3</a>" : <i>Integer, Map</i>
    }
}
</pre>

### YAML

<pre>
Type: AWS::Color::Red
Properties:
    <a href="#primaryid" title="primaryID">primaryID</a>: <i>String</i>
    <a href="#propertywithmultipleconstraints" title="PropertyWithMultipleConstraints">PropertyWithMultipleConstraints</a>: <i>String</i>
    <a href="#propertywithmultipleprimitives" title="PropertyWithMultiplePrimitives">PropertyWithMultiplePrimitives</a>: <i>Integer, String, Map</i>
    <a href="#propertywithtwocomplextypes" title="PropertyWithTwoComplexTypes">PropertyWithTwoComplexTypes</a>: <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a></i>
    <a href="#propertywithmultiplecomplextypes" title="PropertyWithMultipleComplexTypes">PropertyWithMultipleComplexTypes</a>: <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a></i>
    <a href="#propertywithmultiplecomplextypesandoneprimitive" title="PropertyWithMultipleComplexTypesAndOnePrimitive">PropertyWithMultipleComplexTypesAndOnePrimitive</a>: <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a>, Map</i>
    <a href="#propertywithcomplextypeandprimitive" title="PropertyWithComplexTypeAndPrimitive">PropertyWithComplexTypeAndPrimitive</a>: <i><a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a></i>
    <a href="#multiproperty3" title="MultiProperty3">MultiProperty3</a>: <i>Integer, Map</i>
</pre>

## Properties

#### primaryID

_Required_: No

_Type_: String

_Update requires_: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

#### PropertyWithMultipleConstraints

_Required_: No

_Type_: String

_Minimum_: <code>13</code>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyWithMultiplePrimitives

_Required_: No

_Type_: Integer, String, Map

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyWithTwoComplexTypes

_Required_: No

_Type_: <a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyWithMultipleComplexTypes

_Required_: No

_Type_: <a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyWithMultipleComplexTypesAndOnePrimitive

_Required_: No

_Type_: <a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>, <a href="complextypewithmultipleprimitives.md">ComplexTypeWithMultiplePrimitives</a>, <a href="complextypewithcircularref.md">ComplexTypeWithCircularRef</a>, Map

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### PropertyWithComplexTypeAndPrimitive

_Required_: No

_Type_: <a href="complextypewithoneprimitive.md">ComplexTypeWithOnePrimitive</a>

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

#### MultiProperty3

_Required_: No

_Type_: Integer, Map

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the primaryID.
