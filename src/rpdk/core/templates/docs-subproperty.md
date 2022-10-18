{% autoescape false %}
# {{ type_name }} {{ subproperty_name }}
{% if schema.description %}

{{ schema.description }}
{% endif %}

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
{% if schema.properties %}
{% for propname, prop in schema.properties.items() %}
{% if not prop.readonly %}
    "<a href="#{{ propname.lower() }}" title="{{ propname }}">{{ propname }}</a>" : <i>{{ prop.jsontype }}</i>{% if not loop.last %},{% endif %}

{% endif %}
{% endfor %}
{% endif %}
}
</pre>

### YAML

<pre>
{% if schema.properties %}
{% for propname, prop in schema.properties.items() %}
{% if not prop.readonly %}
<a href="#{{ propname.lower() }}" title="{{ propname }}">{{ propname }}</a>: <i>{{ prop.yamltype }}</i>
{% endif %}
{% endfor %}
{% endif %}
</pre>
{% if schema.properties %}

## Properties

{% for propname, prop in schema.properties.items() %}
{% if not prop.readonly %}
#### {{ propname | escape_markdown }}
{% if prop.description %}

{{ prop.description }}
{% endif %}

_Required_: {% if propname in schema.required %}Yes{% else %}No{% endif %}


_Type_: {{ prop.longformtype }}
{% if prop.allowedvalues %}

_Allowed Values_: {% for allowedvalue in prop.allowedvalues %}<code>{{ allowedvalue }}</code>{% if not loop.last %} | {% endif %}{% endfor %}

{% endif %}
{% if prop.minLength %}

_Minimum_: <code>{{ prop.minLength }}</code>
{% endif %}
{% if prop.maxLength %}

_Maximum_: <code>{{ prop.maxLength }}</code>
{% endif %}
{% if prop.pattern %}

_Pattern_: <code>{{ prop.pattern }}</code>
{% endif %}
{% if prop.createonly %}

_Update requires_: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)
{% else %}

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)
{% endif %}

{% endif %}
{% endfor %}
{% endif %}
{% endautoescape %}
