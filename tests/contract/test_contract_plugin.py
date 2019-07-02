from rpdk.core.contract.contract_plugin import ContractPlugin


def test_contract_plugin_fixture_resource_client():
    resource_client = object()
    plugin = ContractPlugin(resource_client)
    assert plugin.resource_client.__wrapped__(plugin) is resource_client
