// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import lombok.Data;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;

public abstract class BaseConfiguration {

    protected String schemaFilename;

    public InputStream resourceSchema() {
        final File file = new File(String.format(schemaFilename));
        try {
            return new FileInputStream(file);
        } catch (final FileNotFoundException e) {
            e.printStackTrace();
            return null;
        }
    }

}
