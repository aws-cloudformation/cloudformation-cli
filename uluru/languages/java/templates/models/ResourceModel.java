{# """
	Resource and subresource POJO model to pass into the handlers
	Necessary variables for generation:
		@class_name (name of the subresource as specified in the resource schema)
		@resource_properties (dictionary of properties for this subresource)
""" #}

package {{ packageName }}.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import org.apache.commons.lang.builder.EqualsBuilder;
import org.apache.commons.lang.builder.HashCodeBuilder;
import org.apache.commons.lang.builder.ToStringBuilder;

import java.util.Map;
import java.util.List;
import java.util.Set;

public class {{ class_name }} {
	{% for prop_name, prop_type in resource_properties.items() %}
	@JsonProperty("{{ prop_name }}")
	private {{ prop_type }} {{ prop_name|lowercase_first_letter }};

	{% endfor %}
	@JsonCreator
	public {{ class_name }} (
	{% for prop_name, prop_type in resource_properties.items() %}
		@JsonProperty("{{ prop_name }}") {{ prop_type }} {{ prop_name|lowercase_first_letter }}{%- if not loop.last %},{% endif %}
		
	{% endfor %}
	) {
	{% for prop_name, prop_type in resource_properties.items() %}
		this.{{ prop_name|lowercase_first_letter }} = {{ prop_name|lowercase_first_letter }};
	{% endfor %}
	}

	{% for prop_name, prop_type in resource_properties.items() %}
	public {{ prop_type }} get{{ prop_name }}() {
		return {{ prop_name|lowercase_first_letter }};
	}

	public void set{{ prop_name }}({{ prop_type }} {{ prop_name|lowercase_first_letter }}) {
		this.{{ prop_name|lowercase_first_letter }} = {{ prop_name|lowercase_first_letter }};
	}

	public {{ class_name }} with{{ prop_name }}({{ prop_type }} {{ prop_name|lowercase_first_letter }}) {
		this.{{ prop_name|lowercase_first_letter }} = {{ prop_name|lowercase_first_letter }};
		return this;
	}
	{% endfor %}

	@Override
    public String toString() {
        return new ToStringBuilder(this)
		{% for prop_name, prop_type in resource_properties.items() %}
			.append("{{prop_name}}", {{prop_name|lowercase_first_letter}})
		{% endfor %}
			.toString();
    }

    @Override
    public int hashCode() {
        return new HashCodeBuilder()
		{% for prop_name, prop_type in resource_properties.items() %}
			.append({{prop_name|lowercase_first_letter}})
		{% endfor %}
			.toHashCode();
    }

    @Override
    public boolean equals(Object rhs) {
		if (rhs == null) return false;
        if (this == rhs) return true;
        if (rhs.getClass() != {{class_name}}.class) return false;
        final {{class_name}} other = ({{class_name}}) rhs;
        return new EqualsBuilder()
		{% for prop_name, prop_type in resource_properties.items() %}
			.append({{prop_name|lowercase_first_letter}}, other.{{prop_name|lowercase_first_letter}})
		{% endfor %}
            .isEquals();
    }
	
}
