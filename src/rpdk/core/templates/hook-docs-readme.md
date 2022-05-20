{% autoescape false %}
# {{ type_name }}
{% if schema.description %}

{{ schema.description }}
{% endif %}

## Activation

To activate a hook in your account, use the following JSON as the `Configuration` request parameter for [`SetTypeConfiguration`](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_SetTypeConfiguration.html) API request.

### Configuration

<pre>
{
    "CloudFormationConfiguration": {
        "<a href="https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/hooks-structure.html#hooks-hook-configuration" title="HookConfiguration">HookConfiguration</a>": {
            "<a href="https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/hooks-structure.html#hooks-targetstacks" title="TargetStacks">TargetStacks</a>": "ALL",
            "<a href="https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/hooks-structure.html#hooks-failuremode" title="FailureMode">FailureMode</a>": "FAIL",
            "<a href="https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/hooks-structure.html#hooks-properties" title="Properties">Properties</a>" : {
{% if schema.properties %}
{% for propname, prop in schema.properties.items() %}
{% if not prop.readonly %}
                "<a href="#{{ propname.lower() }}" title="{{ propname }}">{{ propname }}</a>" : <i>{{ prop.jsontype }}</i>{% if not loop.last %},{% endif %}

{% endif %}
{% endfor %}
{% endif %}
            }
        }
    }
}
</pre>

{% endautoescape %}
