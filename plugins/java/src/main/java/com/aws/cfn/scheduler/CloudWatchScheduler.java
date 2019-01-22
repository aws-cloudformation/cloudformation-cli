package com.aws.cfn.scheduler;

import com.amazonaws.services.cloudwatchevents.AmazonCloudWatchEvents;
import com.amazonaws.services.cloudwatchevents.model.DeleteRuleRequest;
import com.amazonaws.services.cloudwatchevents.model.PutRuleRequest;
import com.amazonaws.services.cloudwatchevents.model.PutTargetsRequest;
import com.amazonaws.services.cloudwatchevents.model.RemoveTargetsRequest;
import com.amazonaws.services.cloudwatchevents.model.RuleState;
import com.amazonaws.services.cloudwatchevents.model.Target;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.util.StringUtils;
import com.aws.cfn.LambdaModule;
import com.aws.cfn.proxy.RequestContext;
import com.google.inject.Guice;
import com.google.inject.Inject;
import com.google.inject.Injector;
import lombok.Data;
import org.json.JSONObject;

import java.util.UUID;

@Data
public class CloudWatchScheduler {

    private LambdaLogger logger;
    private final CronHelper cronHelper;
    private final AmazonCloudWatchEvents client;

    /**
     * This .ctor provided for Lambda runtime which will not automatically invoke Guice injector
     */
    public CloudWatchScheduler() {
        final Injector injector = Guice.createInjector(new LambdaModule());
        this.client = injector.getInstance(AmazonCloudWatchEvents.class);
        this.cronHelper = new CronHelper();
    }

    /**
     * This .ctor provided for testing
     */
    @Inject
    public CloudWatchScheduler(final AmazonCloudWatchEvents client,
                               final CronHelper cronHelper) {
        this.client = client;
        this.cronHelper = cronHelper;
    }

    /**
     * Schedule a re-invocation of the executing handler no less than 1 minute from now
     * @param functionArn       the ARN oft he Lambda function to be invoked
     * @param minutesFromNow    the minimum minutes from now that the re-invocation will occur. CWE provides only
     *                          minute-granularity
     * @param callbackContext   additional context which the handler can provide itself for re-invocation
     */
    public void rescheduleAfterMinutes(final String functionArn,
                                       final int minutesFromNow,
                                       final RequestContext callbackContext) {

        // generate a cron expression; minutes must be a positive integer
        final String cronRule = this.cronHelper.generateOneTimeCronExpression(Math.max(minutesFromNow, 1));

        final UUID rescheduleId = UUID.randomUUID();
        final String ruleName = String.format("reinvoke-handler-%s", rescheduleId);
        final String targetId = String.format("reinvoke-target-%s", rescheduleId);

        // record the CloudWatchEvents objects for cleanup on the callback
        callbackContext.setCloudWatchEventsRuleName(ruleName);
        callbackContext.setCloudWatchEventsTargetId(targetId);

        final String jsonContext = new JSONObject(callbackContext).toString();
        this.log(String.format("Scheduling re-invoke at %s (%s)\n", cronRule, rescheduleId));

        final PutRuleRequest putRuleRequest = new PutRuleRequest()
            .withName(ruleName)
            .withScheduleExpression(cronRule)
            .withState(RuleState.ENABLED);
        this.client.putRule(putRuleRequest);

        final Target target = new Target()
            .withArn(functionArn)
            .withId(targetId)
            .withInput(jsonContext);
        final PutTargetsRequest putTargetsRequest = new PutTargetsRequest()
            .withTargets(target)
            .withRule(putRuleRequest.getName());
        this.client.putTargets(putTargetsRequest);
    }

    /**
     * After a re-invocation, the CWE rule which generated the reinvocation should be scrubbed
     * @param cloudWatchEventsRuleName  the name of the CWE rule which triggered a re-invocation
     * @param cloudWatchEventsTargetId  the target of the CWE rule which triggered a re-invocation
     */
    public void cleanupCloudWatchEvents(final String cloudWatchEventsRuleName,
                                        final String cloudWatchEventsTargetId) {

        try {
            if (!StringUtils.isNullOrEmpty(cloudWatchEventsRuleName)) {
                final DeleteRuleRequest deleteRuleRequest = new DeleteRuleRequest()
                    .withName(cloudWatchEventsRuleName);
                this.client.deleteRule(deleteRuleRequest);
            }
        } catch (final Exception e) {
            this.log(String.format("Error cleaning CloudWatchEvents (ruleName=%s): %s",
                cloudWatchEventsRuleName,
                e.getMessage()));
        }

        try {
            if (!StringUtils.isNullOrEmpty(cloudWatchEventsTargetId)) {
                final RemoveTargetsRequest removeTargetsRequest = new RemoveTargetsRequest()
                    .withIds(cloudWatchEventsTargetId);
                this.client.removeTargets(removeTargetsRequest);
            }
        } catch (final Exception e) {
            this.log(String.format("Error cleaning CloudWatchEvents Target (targetId=%s): %s",
                cloudWatchEventsTargetId,
                e.getMessage()));
        }
    }

    /**
     * null-safe logger redirect
     * @param message A string containing the event to log.
     */
    private void log(final String message) {
        if (this.logger != null) {
            this.logger.log(message);
        }
    }
}
