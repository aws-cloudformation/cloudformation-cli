{# """Resource and subresource POJO model to pass into the handlers""" #}
{# Necessary variables for generation:
	resource_name (name of the subresource as specified in the resource schema)
	resource_properties (dictionary of properties for this subresource)
#}
{# {% set resource_name = Type|resource_type_resource %} #}
package {{ packageNamePrefix }}.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public class {{ resource_name }}Model {

	{% for property_name, property_details in resource_properties.items() %}
	{% set property_variable = property_name|lowercase_first_letter %}
	{% set property_type = property_details.Type|property_type_json_to_java %}
	@JsonProperty("{{ property_name }}")
	private {{ property_type }} {{ property_variable }};

	{% endfor %}

	@JsonCreator
	public {{ resource_name }}Model (
	{% for property_name, property_details in resource_properties.items() %}
	{% set property_variable = property_name|lowercase_first_letter %}
	{% set property_type = property_details.Type|property_type_json_to_java %}
			@JsonProperty("{{ property_name }}") {{ property_type }} {{ property_variable }} {%- if not loop.last %},{% endif %}

	{% endfor %}
	) {
		{% for property_name, property_details in resource_properties.items() %}
		{% set property_variable = property_name|lowercase_first_letter %}
		this.{{ property_variable }} = {{ property_variable }};
		{% endfor %}

	}

	{% for property_name, property_details in resource_properties.items() %}
	{% set property_variable = property_name|lowercase_first_letter %}
	{% set property_type = property_details.Type|property_type_json_to_java %}
	public {{ property_type }} get{{ property_name }}() {
		return {{ property_variable }};
	}

	public void set{{ property_name }}({{ property_type }} {{ property_variable }}) {
		this.{{ property_variable }} = {{ property_variable }};
	}

	public {{ resource_name }}Model with{{ property_name }}({{ property_type }} {{ property_variable }}) {
		this.{{ property_variable }} = {{ property_variable }};
		return this;
	}

	{% endfor %}

	public validate() {
		//todo - this method will check that all the schema rules are validated.
	}
}
