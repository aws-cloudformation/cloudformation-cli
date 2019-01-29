// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;
import java.util.List;
import java.util.Set;

public class {{ pojo_name|uppercase_first_letter }} {
    {% for name, type in properties.items() %}
    private {{ type }} {{ name|lowercase_first_letter }};

    @JsonProperty("{{ name }}")
    public {{ type }} get{{ name|uppercase_first_letter }}() {
        return this.{{ name|lowercase_first_letter }};
    }

    public void set{{ name|uppercase_first_letter }}({{ type }} {{ name|lowercase_first_letter }}) {
        this.{{ name|lowercase_first_letter }} = {{ name|lowercase_first_letter }};
    }

    {% endfor %}
}
