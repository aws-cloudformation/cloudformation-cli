package com.aws.cfn.scheduler;

import com.amazonaws.services.cloudwatchevents.model.Target;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.mockito.ArgumentMatcher;

@Data
@AllArgsConstructor
public class TargetMatcher implements ArgumentMatcher<Target> {

    private final String arn;
    private final String id;
    private final Object input;

    @Override
    public boolean matches(final Target argument) {
        return
            argument.getArn().equals(arn) &&
            argument.getId().startsWith(id) &&
            argument.getInput().equals(input);
    }
}
