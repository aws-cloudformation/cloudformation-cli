package com.example.provider.handlers;

import com.example.provider.messages.HandlerRequest;
import com.example.provider.messages.HandlerStatus;
import com.example.provider.messages.ProgressEvent;
import com.example.provider.models.{{ pojo_name }};
import com.example.provider.utils.ErrorCodeMapper;

public class {{ operation }}Handler extends Base{{ operation }}Handler {
    @Override
    public ProgressEvent<{{ pojo_name }}> do{{ operation }}(final HandlerRequest<{{ pojo_name }}> request) {
        try {
            /**
             * Custom implementation here
             */
            return new ProgressEvent<{{ pojo_name }}>(request)
                    //.withResource()
                    .withStatus(HandlerStatus.COMPLETE);
        } catch (final Exception e) {
            return new ProgressEvent<{{ pojo_name }}>(request)
                    .withStatus(HandlerStatus.FAILED)
                    .withErrorMessage(e.getMessage())
                    .withErrorCode(ErrorCodeMapper.mapError(request, e));
        }
    }
}
