from rpdk.core.contract.contract_plugin import ContractPlugin


def test_contract_plugin_fixtures():
    plugin = ContractPlugin()
    assert plugin.resource_client.__wrapped__(plugin) is None
