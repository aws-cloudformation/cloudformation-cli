## Provider Definition Schema

The Resource Provider Definition Schema is a _meta-schema_ which extends [draft-07](https://json-schema.org/draft-07/json-schema-release-notes.html) of [JSON Schema](https://json-schema.org/) to define a validating document against which resource schemas can be authored.

### Changes

We have taken an opinion on certain aspects of the core JSON Schema and introduced certain constrains and changes from the core schema. In the context of this project, we are not building arbitrary documents, but rather, defining a very specific shape and semantic for cloud resources. 

* **`readOnly`**: the readOnly field as defined in JSON Schema does not align with our determination that this is actually a restriction with semantic meaning. A property may be readOnly when specified for a particular resource (for example it's `Arn`), but when that same property is _referenced_ (using `$ref` tokens) from a dependency, the dependency must be allowed to specify an input for that property, and as such, it is no longer `readOnly` in that context. 
* **`writeOnly`**: see above
* **sub properties**: to simplify definition authoring, we have restricted the use of sub-properties and require that sub-property objects are defined in the `definitions` block of the document 

### Constraints

* **`$id`**: an `$id` property is not valid for a resource property
* **`$schema`**: an `$schema` property is not valid for a resource property
* **`propertyNames`**: use of `propertyNames` implies a set of properties without a defined shape and is disallowed. To constrain property names, use `patternProperties` statements with defined shapes
* **`if`, `then`, `else`, `not`**: these imperative constructs can lead to confusion both in authoring a resource definition, and for customers authoring a resource description against your schema. Also this construct is not widely supported by validation tools and is disallowed here.

