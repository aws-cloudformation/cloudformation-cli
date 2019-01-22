package com.aws.cfn.scheduler;

import com.amazonaws.services.cloudwatchevents.model.PutTargetsRequest;
import com.amazonaws.services.cloudwatchevents.model.Target;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.mockito.ArgumentMatcher;

import java.util.List;

@Data
@AllArgsConstructor
public class PutTargetsRequestMatcher implements ArgumentMatcher<PutTargetsRequest> {

    private final String rule;
    private final ArgumentMatcher<List<Target>> targetArgumentMatcher;

    @Override
    public boolean matches(final PutTargetsRequest argument) {
        return
            argument.getRule().startsWith(rule) &&
            targetArgumentMatcher.matches(argument.getTargets());
    }
}
