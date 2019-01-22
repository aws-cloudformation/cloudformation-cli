package com.aws.cfn;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.RequestStreamHandler;
import com.aws.cfn.proxy.CallbackAdapter;
import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.ProgressStatus;
import com.aws.cfn.exceptions.TerminalException;
import com.aws.cfn.metrics.MetricsPublisher;
import com.aws.cfn.proxy.RequestContext;
import com.aws.cfn.resource.SchemaValidator;
import com.aws.cfn.resource.exceptions.ValidationException;
import com.aws.cfn.scheduler.CloudWatchScheduler;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.inject.Guice;
import com.google.inject.Inject;
import com.google.inject.Injector;
import org.apache.commons.io.IOUtils;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Date;
import java.util.Map;

import static com.sun.corba.se.impl.util.Utility.printStackTrace;

public abstract class LambdaWrapper<T> implements RequestStreamHandler, RequestHandler<Request<T>, Response> {

    private final CallbackAdapter callbackAdapter;
    private final MetricsPublisher metricsPublisher;
    private final CloudWatchScheduler scheduler;
    private final SchemaValidator validator;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private LambdaLogger logger;

    /**
     * This .ctor provided for Lambda runtime which will not automatically invoke Guice injector
     */
    public LambdaWrapper() {
        final Injector injector = Guice.createInjector(new LambdaModule());
        this.callbackAdapter = injector.getInstance(CallbackAdapter.class);
        this.metricsPublisher = injector.getInstance(MetricsPublisher.class);
        this.scheduler = new CloudWatchScheduler();
        this.validator = injector.getInstance(SchemaValidator.class);
        configureObjectMapper(this.objectMapper);
    }

    /**
     * This .ctor provided for testing
     */
    @Inject
    public LambdaWrapper(final CallbackAdapter callbackAdapter,
                         final MetricsPublisher metricsPublisher,
                         final CloudWatchScheduler scheduler,
                         final SchemaValidator validator) {
        this.callbackAdapter = callbackAdapter;
        this.metricsPublisher = metricsPublisher;
        this.scheduler = scheduler;
        this.validator = validator;
        configureObjectMapper(this.objectMapper);
    }

    /**
     * Configures the specified ObjectMapper with the (de)serialization behaviours we want gto enforce
     * @param objectMapper
     */
    private void configureObjectMapper(final ObjectMapper objectMapper) {
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    }

    public Response handleRequest(final Request request,
                                  final Context context) {
        return null;
    }


    public void handleRequest(final InputStream inputStream,
                              final OutputStream outputStream,
                              final Context context) throws IOException, TerminalException {
        this.logger = context.getLogger();
        this.scheduler.setLogger(context.getLogger());

        ProgressEvent handlerResponse = null;
        HandlerRequest<T> request = null;

        try {
            if (inputStream == null) {
                throw new TerminalException("No request object received");
            }

            // decode the input request
            final String input = IOUtils.toString(inputStream, "UTF-8");
            final JSONObject o = new JSONObject(input);
            request = this.objectMapper.readValue(o.toString(), HandlerRequest.class);

            handlerResponse = processInvocation(request, context);
        } catch (final Exception e) {
            // Exceptions are wrapped as a consistent error response to the caller (i.e; CloudFormation)
            e.printStackTrace(); // for root causing - logs to LambdaLogger by default

            this.metricsPublisher.publishExceptionMetric(
                Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant()),
                request.getAction(),
                e);

            handlerResponse = new ProgressEvent();
            handlerResponse.setMessage(e.getMessage());
            handlerResponse.setStatus(ProgressStatus.Failed);
            if (request != null && request.getRequestData() != null) {
                handlerResponse.setResourceModel(request.getRequestData().getResourceProperties());
            }
        } finally {
            // A response will be output on all paths, though CloudFormation will
            // not block on invoking the handlers, but rather listen for callbacks
            writeResponse(outputStream, createProgressResponse(handlerResponse));
        }
    }

    public ProgressEvent processInvocation(final HandlerRequest<T> request,
                                           final Context context) throws IOException, TerminalException {

        if (request == null || request.getRequestContext() == null) {
            throw new TerminalException("Invalid request object received");
        }

        final RequestContext requestContext = request.getRequestContext();

        // If this invocation was triggered by a 're-invoke' CloudWatch Event, clean it up
        if (requestContext.getCloudWatchEventsRuleName() != null &&
            !requestContext.getCloudWatchEventsRuleName().isEmpty()) {
            this.scheduler.cleanupCloudWatchEvents(
                requestContext.getCloudWatchEventsRuleName(),
                requestContext.getCloudWatchEventsTargetId());
        }

        // MetricsPublisher is initialised with the resource type name for metrics namespace
        this.metricsPublisher.setResourceTypeName(request.getResourceType());

        this.metricsPublisher.publishInvocationMetric(
            Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant()),
            request.getAction());

        // validate incoming model - any error is a terminal failure on the invocation
        try {
            validateModel(request.getRequestData().getResourceProperties());
        } catch (final ValidationException e) {
            // TODO: we'll need a better way to expose the stack of causing exceptions for user feedback
            throw new TerminalException(
                String.format("Model validation failed (%s)", e.getMessage()),
                e);
        }

        // TODO: implement decryption of request and returned callback context
        // using KMS Key accessible by the Lambda execution Role

        // TODO: implement the handler invocation inside a time check which will abort and automatically
        // reschedule a callback if the handler does not respond within the 15 minute invocation window

        // TODO: ensure that any credential expiry time is also considered in the time check to
        // automatically fail a request if the handler will not be able to complete within that period,
        // such as before a FAS token expires

        final Date startTime = Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant());

        final ProgressEvent handlerResponse = invokeHandler(
            request,
            request.getAction(),
            requestContext);
        if (handlerResponse != null)
            this.log(String.format("Handler returned %s", handlerResponse.getStatus()));
        else
            this.log("Handler returned null");

        final Date endTime = Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant());

        metricsPublisher.publishDurationMetric(
            Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant()),
            request.getAction(),
            (endTime.getTime() - startTime.getTime()));

        // ensure we got a valid response
        if (handlerResponse == null) {
            throw new TerminalException("Handler failed to provide a response.");
        }

        // When the handler responses InProgress with a callback delay, we trigger a callback to re-invoke
        // the handler for the Resource type to implement stabilization checks and long-poll creation checks
        if (handlerResponse.getStatus() == ProgressStatus.InProgress) {
            final RequestContext callbackContext = new RequestContext();
            callbackContext.setInvocation(requestContext.getInvocation() + 1);
            callbackContext.setCallbackContext(handlerResponse.getCallbackContext());

            this.scheduler.rescheduleAfterMinutes(
                context.getInvokedFunctionArn(),
                handlerResponse.getCallbackDelayMinutes(),
                callbackContext);
        }

        // report the progress status when in non-terminal state (i.e; InProgress) back to configured endpoint
        this.callbackAdapter.reportProgress(request.getBearerToken(),
            handlerResponse.getErrorCode(),
            handlerResponse.getStatus(),
            handlerResponse.getResourceModel(),
            handlerResponse.getMessage());

        // The wrapper will log any context to the configured CloudWatch log group
        if (handlerResponse.getCallbackContext() != null)
            this.log(handlerResponse.getCallbackContext().toString());

        return handlerResponse;
    }

    private Response createProgressResponse(final ProgressEvent progressEvent) {
        final Response response = new Response();
        response.setMessage(progressEvent.getMessage());
        response.setStatus(progressEvent.getStatus());

        if (progressEvent.getResourceModel() != null) {
            response.setResourceModel(new JSONObject(progressEvent.getResourceModel()));
        }

        return response;
    }

    private void writeResponse(final OutputStream outputStream,
                               final Response response) throws IOException {

        outputStream.write(new JSONObject(response).toString().getBytes(Charset.forName("UTF-8")));
        outputStream.close();
    }

    private void validateModel(final T resourceModel) throws ValidationException {
        final InputStream resourceSchema = provideResourceSchema();
        if (resourceSchema == null) {
            throw new ValidationException(String.format("Unable to validate incoming model for %s as no schema was provided.",
                resourceModel.getClass()),
                null,
                null);
        }

        final Map propertiesMap = this.objectMapper.convertValue(resourceModel, Map.class);
        final JSONObject modelObject = new JSONObject(propertiesMap);

        this.validator.validateModel(modelObject, resourceSchema);
    }

    /**
     * Handler implementation should implement this method to provide the schema for validation
     * @return  An InputStream of the resource schema for the provider
     */
    public abstract InputStream provideResourceSchema();

    public abstract ProgressEvent<T> invokeHandler(final HandlerRequest<T> request,
                                                   final Action action,
                                                   final RequestContext context);

    /**
     * null-safe logger redirect
     * @param message A string containing the event to log.
     */
    private void log(final String message) {
        if (this.logger != null) {
            this.logger.log(String.format("%s\n", message));
        }
    }
}
