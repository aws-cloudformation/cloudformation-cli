import json
from io import StringIO
from unittest.mock import patch

import pytest

from rpdk.contract.transports import LocalLambdaTransport

FUNCTION_NAME = "WGTIDN"
DUMMY = "GCCIKL"
# invalid port is used to ensure it fails if incorrectly mocked
INVALID_PORT = 65535 + 2
SANTA = "🎅"


@pytest.mark.parametrize("url", [(None, INVALID_PORT), None])
def test_local_lambda_transport(url):
    request_payload = {"payload": SANTA, "requestContext": {}}
    response_payload = {"ret": DUMMY}

    response_stream = StringIO()
    json.dump(response_payload, response_stream)
    response_stream.seek(0)

    transport = LocalLambdaTransport("http://localhost/dummy.php", FUNCTION_NAME)
    with patch.object(
        transport.client, "invoke", return_value={"Payload": response_stream}
    ) as mock_invoke:
        response = transport(request_payload, url)

    assert response == response_payload

    mock_invoke.assert_called_once()
    args, kwargs = mock_invoke.call_args
    assert not args
    assert set(kwargs.keys()) == {"FunctionName", "Payload"}
    assert kwargs["FunctionName"] == FUNCTION_NAME
    assert SANTA in kwargs["Payload"].decode("utf-8")
