## Resource Modelling

### Purpose

This guide is intended as a guide for [Resource Type](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-types.html) developers to understand both _why_ and _how_ to design effective APIs and their corresponding Resource Type Provider packages.

### Why CloudFormation Support?

From the public [documentation](https://aws.amazon.com/cloudformation/);

> AWS CloudFormation provides a common language for you to model and provision AWS and third party application resources in your cloud environment. AWS CloudFormation allows you to use programming languages or a simple text file to model and provision, in an automated and secure manner, all the resources needed for your applications across all regions and accounts. This gives you a single source of truth for your AWS and third party resources.

What this means in a practical sense is that customers are able to define their infrastructure in a consistent way, manage that definition in their own source control systems, audit the application and change of infrastructure and have that same definition be re-used across AWS regions, and over time. CloudFormation, and other Infrastructure as Code (IaC) tools allow you to build consistent automation and minimise the need to create custom scripts or need to break out into the AWS Console for one-off work.

### Resource Types and Handler Contracts

With the launch of the [CloudFormation Registry](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html), we launched a new way to model Resource Types. Resource Types now require a published schema definition, defined according to the [Resource Schema](https://github.com/aws-cloudformation/aws-cloudformation-resource-schema). This schema defines the **shape** (properties) and **semantics** for how the Resource Type can be used. It also defines **handler** operations which the Resource Type supports, such as `Create`, `Read` and `Delete`.

As a result of the distributed nature of cloud service development, a range of disparity has evolved over time in the way in which service owners think about, and define their APIs and the logical resources which those APIs describe and control. In concert with the schema definition, CloudFormation now also defines a [*contract*](https://github.com/aws-cloudformation/aws-cloudformation-resource-schema) to which Resource Types must comply in order to be shared as public types in the [CloudFormation Registry](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html). This contract aims to smooth over the underlying API disparity so that customers of CloudFormation and other IaC tools can rely on a consistent and repeatable experience from the Resource Types they are consuming.

A canonical example of API disparity is in the way some APIs will allow a `Create` action to return `200`/`Success` when a resource by named identifier already existed at the time the `Create` request was applied. This is a form of "upsert" behavior from database services - create if not exists, or update if it does. Contrast this with many other APIs which will treat a duplicate `Create` request by responding with a `409`/`Conflict` or some other form of `AlreadyExistsException`. This disparity means that customers must account for these divergent behaviours in their own workflows and tooling and manage this over time.

In the new Resource Provider model, the [Resource Type Contract](https://github.com/aws-cloudformation/aws-cloudformation-resource-schema) defines handling for this specific scenario with the following statement;

> A create handler MUST return FAILED with an AlreadyExists error code if the resource already existed prior to the create request.

In order for Resource Type developers to comply with this requirement, how then can they implement their handlers correctly? This, and other topics, are the purpose of this guide.
