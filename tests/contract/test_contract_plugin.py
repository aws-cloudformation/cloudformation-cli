from rpdk.contract.contract_plugin import ContractPlugin


def test_contract_plugin_fixtures():
    transport = object()
    test_resource = object()
    resource_def = object()
    plugin = ContractPlugin(transport, test_resource, resource_def)
    assert plugin.transport.__wrapped__(plugin) is transport
    assert plugin.test_resource.__wrapped__(plugin) is test_resource
    assert plugin.resource_def.__wrapped__(plugin) is resource_def
