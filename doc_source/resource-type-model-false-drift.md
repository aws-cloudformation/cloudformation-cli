# Preventing false drift detection results for resource types<a name="resource-type-model-false-drift"></a>

When AWS CloudFormation performs drift detection on a resource, it looks up the value for each resource property as specified in the stack template, and compares that value with the current resource property value returned by the resource `read` handler\. A resource is then considered to have drifted if one or more of its properties have been deleted, or had their value changed\. In some cases, however, the resource may not be able to return the exact same value in the `read` handler as was specified in the stack template, even though the value is essentially the same and should not be considered as drifted\.

To prevent these cases from being incorrectly reported as drifted resources, you can specify a *property transform* in your resource schema\. The property transform provides a way for CloudFormation to accurately compare the resource property value specified in the template with the value returned from the `read` handler\. During drift detection, if CloudFormation finds a property where the template value differs from the value returned by the `read` handler, it determines if a property transform has been defined for that property in the resource schema\. If it has, CloudFormation applies that property transform to the value specified in the template, and then compares it to the `read` handler value again\. If these two values match, the property is not considered to have drifted, and is marked as `IN_SYNC`\.

For more information about drift detection, see [Detecting unmanaged configuration changes to stacks and resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html) in the *CloudFormation User Guide*\.

## Defining a property transform for drift detection operations<a name="resource-type-model-false-drift-property-transform"></a>

Use the `propertyTransform` element to define a property transform for a given resource property\. 

```
"propertyTransform": { 
  "property_path": "transform"
}
```

Where:
+ *property\_path* is the path to the resource property in the resource schema\.
+ *transform* is the transform to perform on the resource property value specified in the stack template\.

  Property transforms are written in [JSONata](https://docs.jsonata.org/overview.html), an open\-source, lightweight query and transformation language for JSON data\.

For example, consider the `[AWS::Route53::HostedZone](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-hostedzone.html#cfn-route53-hostedzone-name) resource`\. For the `[Name](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-hostedzone.html#cfn-route53-hostedzone-name)` property, users can specify a domain name with or without a trailing `.` in their templates\. However, assume the Route 53 service always returns the domain name with a trailing `.`\. This means that if a user specified a domain name without the trailing `.` in their template, created the stack, and then performed drift detection on the stack, CloudFormation would erroneously report the `AWS::Route53::HostedZone` resource as drifted\. To prevent this from happening, the resource developer would add a `propertyTransform` element to the resource schema to enable CloudFormation to determine if both property values were actually the same:

```
"propertyTransform": { 
  "/properties/Name": "$join([Name, \".\"])"
}
```

### Specifying multiple transforms for a property<a name="resource-type-model-false-drift-property-transform-mulitple"></a>

You can specify multiple transforms for CloudFormation to attempt by using the `$OR` operator\. If you specify multiple transforms, CloudFormation tries them all, in the order they are specified, until it finds one that results in the property values matching, or it has tried them all\.

For example, for the following property transform, CloudFormation would attempt two transforms to determine whether or not the property value has actually drifted:
+ Append `.` to the template property value, and determine if the updated value now matches the property value returned by the resource `read` handler\. If it does, CloudFormation reports the property as `IN_SYNC`\. If not, CloudFormation performs the next transform\.
+ Append the string `test` to the template property value, and determine if the updated value now matches the property value returned by the resource `read` handler\. If it does, CloudFormation reports the property as `IN_SYNC`\. If not, CloudFormation reports the property\-\-and the resource\-\-as `MODIFIED`\.

```
"propertyTransform": { 
  "/properties/Name": "$join([Name, \".\"]) $OR $join([Name, \"test\"])"
}
```