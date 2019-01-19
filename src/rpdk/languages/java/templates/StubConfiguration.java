package {{ package_name }};

import java.io.InputStream;

class Configuration extends BaseConfiguration {

    public Configuration() {
        super("{{ schema_file_name }}");
    }

    public InputStream resourceSchema() {
        return this.getClass().getClassLoader().getResourceAsStream(schemaFilename);
    }

}
