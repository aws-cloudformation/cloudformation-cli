// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import java.util.Map;
import java.util.List;
import java.util.Set;

public class {{ pojo_name|uppercase_first_letter }} {

    {% for name, type in properties.items() %}
    private {{ type }} {{ name|lowercase_first_letter }};

    {% endfor %}

    {% for name, type in properties.items() %}
    {%- set lower = name|lowercase_first_letter %}
    {%- set upper = name|uppercase_first_letter %}
    public {{ type }} get{{ upper }}() {
        return this.{{ lower }};
    }

    public void set{{ upper }}({{ type }} {{ lower }}) {
        this.{{ lower }} = {{ lower }};
    }

    public {{ pojo_name }} with{{ upper }}({{ type }} {{ lower }}) {
        this.{{ lower }} = {{ lower }};
        return this;
    }
    {% endfor %}

    public {{ pojo_name }}() { }
}
