from unittest.mock import Mock

import pytest

from evm.blockchain.evm_client import EvmClient
from evm.config import ChainConfig
from evm.errors import WrongNetworkError
from evm.rpc.client import RpcClient


@pytest.fixture
def ethereum_config() -> ChainConfig:
    return ChainConfig(name="Ethereum Mainnet", chain_id=1)


class TestEvmClient:
    def test_init_succeeds_when_network_matches(self, ethereum_config: ChainConfig) -> None:
        mock_rpc = Mock(spec=RpcClient)
        mock_rpc.get_chain_id.return_value = 1

        client = EvmClient(rpc=mock_rpc, config=ethereum_config)

        assert client.config == ethereum_config
        assert client.rpc == mock_rpc
        mock_rpc.get_chain_id.assert_called_once()

    def test_init_raises_wrong_network_error_on_mismatch(self, ethereum_config: ChainConfig) -> None:
        mock_rpc = Mock(spec=RpcClient)
        mock_rpc.get_chain_id.return_value = 137  # Polygon вместо Ethereum Mainnet

        with pytest.raises(WrongNetworkError) as exc_info:
            EvmClient(rpc=mock_rpc, config=ethereum_config)

        error_message = str(exc_info.value)
        assert "Ethereum Mainnet" in error_message
        assert "ID: 1" in error_message
        assert "returned ID: 137" in error_message
        mock_rpc.get_chain_id.assert_called_once()

    def test_init_preserves_timeout_error(
        self,
        ethereum_config: ChainConfig,
    ) -> None:
        mock_rpc = Mock(spec=RpcClient)
        mock_rpc.get_chain_id.side_effect = TimeoutError("RPC timeout")

        with pytest.raises(TimeoutError, match="RPC timeout"):
            EvmClient(
                rpc=mock_rpc,
                config=ethereum_config,
            )
