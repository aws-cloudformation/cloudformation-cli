from requests import post

from rpdk.core.contract.callback import CallbackServer


def test_callback_server_valid():
    posted_event = {"event": "test"}
    with CallbackServer() as listener:
        post("http://{}:{}".format(*listener.server_address), json=posted_event)
    recorded_event = listener.events.popleft()
    assert recorded_event == posted_event


def test_callback_server_fail():
    with CallbackServer() as listener:
        post("http://{}:{}".format(*listener.server_address), data="Just Text")
    event = listener.events.popleft()
    assert "callback with invalid content type" in event["error"]
