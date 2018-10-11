{% extends "unit/BaseUnitTests.java" %}
{% set handler_type = "Create" %}
{% set subhandler = Handlers.CreateHandler %}

{% block extra_tests %}
	/** PROVIDER CODE HERE, SAMPLE PROVIDED **/
    @Test
    public void testAlreadyExistingException() {
        when(client."CREATE"()).thenThrow(new AlreadyExistsException("resource already exists"));
        when(client."DESCRIBE"()).thenReturn((getResourceResult));
        when(getResourceResult."DESCRIBE").thenReturn(existingResource);
        testSuccess();
    }
    /** END PROVIDER CODE **/

{% endblock %}
