package com.aws.cfn.scheduler;

import com.amazonaws.services.cloudwatchevents.AmazonCloudWatchEvents;
import com.amazonaws.services.cloudwatchevents.model.DeleteRuleRequest;
import com.amazonaws.services.cloudwatchevents.model.RemoveTargetsRequest;
import com.aws.cfn.proxy.RequestContext;
import junit.framework.TestCase;
import org.json.JSONObject;
import org.junit.Test;

import java.util.Arrays;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.startsWith;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class CloudWatchSchedulerTest extends TestCase {

    private static final String FUNCTION_ARN = "arn:aws:lambda:region:account-id:function:function-name";

    private CronHelper getCronHelper() {
        return mock(CronHelper.class);
    }

    private AmazonCloudWatchEvents getCloudWatchEvents() {
        return mock(AmazonCloudWatchEvents.class);
    }

    @Test
    public void test_cleanupCloudWatchEvents_NullRuleName() {
        final AmazonCloudWatchEvents client = getCloudWatchEvents();
        final CronHelper cronHelper = getCronHelper();
        final CloudWatchScheduler scheduler = new CloudWatchScheduler(client, cronHelper);

        scheduler.cleanupCloudWatchEvents(null, "targetid");

        verify(client, times(0)).deleteRule(any());

        verify(client, times(1)).removeTargets(any(RemoveTargetsRequest.class));
    }

    @Test
    public void test_cleanupCloudWatchEvents_NullTargetId() {
        final AmazonCloudWatchEvents client = getCloudWatchEvents();
        final CronHelper cronHelper = getCronHelper();
        final CloudWatchScheduler scheduler = new CloudWatchScheduler(client, cronHelper);

        scheduler.cleanupCloudWatchEvents("rulename", null);

        verify(client, times(1)).deleteRule(any(DeleteRuleRequest.class));

        verify(client, times(0)).removeTargets(any());
    }

    @Test
    public void test_cleanupCloudWatchEvents() {
        final AmazonCloudWatchEvents client = getCloudWatchEvents();
        final CronHelper cronHelper = getCronHelper();
        final CloudWatchScheduler scheduler = new CloudWatchScheduler(client, cronHelper);

        scheduler.cleanupCloudWatchEvents("rulename", "targetid");

        verify(client, times(1)).deleteRule(any(DeleteRuleRequest.class));

        verify(client, times(1)).removeTargets(any(RemoveTargetsRequest.class));
    }

    @Test
    public void test_rescheduleAfterMinutes_1MinuteFloor() {
        final AmazonCloudWatchEvents client = getCloudWatchEvents();
        final CronHelper cronHelper = getCronHelper();
        when(cronHelper.generateOneTimeCronExpression(1))
            .thenReturn("cron(41 14 31 10 ? 2019)");
        final CloudWatchScheduler scheduler = new CloudWatchScheduler(client, cronHelper);
        final RequestContext requestContext = mock(RequestContext.class);

        // minutesFromNow will be set to a floor of '1' for cron generation
        scheduler.rescheduleAfterMinutes(FUNCTION_ARN, 0, requestContext);

        verify(requestContext, times(1)).setCloudWatchEventsRuleName(
            startsWith("reinvoke-handler-")
        );
        verify(requestContext, times(1)).setCloudWatchEventsTargetId(
            startsWith("reinvoke-target-")
        );

        final List<TargetMatcher> targetMatchers = Arrays.asList(
            new TargetMatcher(
                FUNCTION_ARN,
                "reinvoke-target-",
                new JSONObject(requestContext).toString())
        );
        verify(client, times(1)).putTargets(
            argThat(new PutTargetsRequestMatcher(
                "reinvoke-handler-",
                new TargetsListMatcher(targetMatchers)))
        );
        verify(client, times(1)).putRule(
            argThat(new PutRuleRequestMatcher(
                "reinvoke-handler-",
                "cron(41 14 31 10 ? 2019)",
                "ENABLED"))
        );

    }
}
