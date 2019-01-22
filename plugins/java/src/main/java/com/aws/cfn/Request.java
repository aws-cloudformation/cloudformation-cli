package com.aws.cfn;

public class Request<T> {
    T resource;

    int invocation;

    public T getResource() {
        return resource;
    }

    public void setResource(final T resource) {
        this.resource = resource;
    }

    public int getInvocation() {
        return invocation;
    }

    public void setInvocation(final int invocation) {
        this.invocation = invocation;
    }

    public Request(final T resource, final int invocation) {
        this.resource = resource;
        this.invocation = invocation;
    }

    public Request() {
    }
}
