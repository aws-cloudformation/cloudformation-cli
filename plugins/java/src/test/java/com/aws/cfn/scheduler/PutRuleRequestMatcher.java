package com.aws.cfn.scheduler;

import com.amazonaws.services.cloudwatchevents.model.PutRuleRequest;
import lombok.AllArgsConstructor;
import lombok.Data;
import org.mockito.ArgumentMatcher;

@Data
@AllArgsConstructor
public class PutRuleRequestMatcher implements ArgumentMatcher<PutRuleRequest> {

    private String name;
    private String scheduleExpression;
    private String state;

    @Override
    public boolean matches(final PutRuleRequest argument) {
        return
            argument.getDescription() == null &&
            argument.getEventPattern() == null &&
            argument.getName().startsWith(name) &&
            argument.getRoleArn() == null &&
            argument.getScheduleExpression().equals(scheduleExpression) &&
            argument.getState().equals(state);
    }
}
