# {{ type_name }}

Congratulations on starting development! Next steps:

1. Write the JSON schema describing your resource, `{{ schema_path.name }}`
2. The RPDK will automatically generate the correct resource model from the
   schema whenever the project is built via Maven. You can also do this manually
   with the following command: `{{ executable }} generate`
3. Implement your resource handlers


Please don't modify files under `target/generated-sources/rpdk`, as they will be
automatically overwritten.

The code use [Lombok](https://projectlombok.org/), and [you may have to install
IDE integrations](https://projectlombok.org/) to enable auto-complete for
Lombok-annotated classes.
