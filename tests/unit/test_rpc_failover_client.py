from unittest.mock import MagicMock

import pytest

from evm.errors import RPCError, RPCTransportError
from evm.rpc.failover_client import RpcFailoverClient


class TestRpcFailoverClient:

    def test_primary_success(self):
        primary = MagicMock()
        fallback = MagicMock()

        primary.call.return_value = ["log"]

        client = RpcFailoverClient(
            clients=[primary, fallback]
        )

        result = client.call(
            "eth_getLogs",
            [{"fromBlock": "0x1"}],
        )

        assert result == ["log"]

        primary.call.assert_called_once()
        fallback.call.assert_not_called()

    def test_fallback_used_when_primary_transport_fails(self):
        primary = MagicMock()
        fallback = MagicMock()

        primary.call.side_effect = RPCTransportError(
            "primary unavailable"
        )
        fallback.call.return_value = ["log"]

        client = RpcFailoverClient(
            clients=[primary, fallback]
        )

        result = client.call(
            "eth_getLogs",
            [],
        )

        assert result == ["log"]

        primary.call.assert_called_once()
        fallback.call.assert_called_once()

    def test_all_providers_failed(self):
        primary = MagicMock()
        fallback = MagicMock()

        primary.call.side_effect = RPCTransportError(
            "primary unavailable"
        )

        fallback.call.side_effect = RPCTransportError(
            "fallback unavailable"
        )

        client = RpcFailoverClient(
            clients=[primary, fallback]
        )

        with pytest.raises(
            RPCError,
            match="All RPC providers failed",
        ):
            client.call("eth_getLogs", [])

    def test_programming_error_does_not_trigger_fallback(self):
        primary = MagicMock()
        fallback = MagicMock()

        primary.call.side_effect = TypeError(
            "programming error"
        )

        client = RpcFailoverClient(
            clients=[primary, fallback]
        )

        with pytest.raises(TypeError):
            client.call("eth_getLogs", [])

        fallback.call.assert_not_called()