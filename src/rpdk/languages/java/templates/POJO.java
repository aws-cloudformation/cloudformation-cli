// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import lombok.Data;
import java.util.Map;
import java.util.List;
import java.util.Set;


@Data
public class {{ pojo_name|uppercase_first_letter }} {
    {% for name, type in properties.items() %}
    private {{ type }} {{ name|lowercase_first_letter }};

    {% endfor %}
}
