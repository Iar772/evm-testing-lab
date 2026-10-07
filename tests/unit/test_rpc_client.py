from unittest.mock import Mock

import pytest

from evm.errors import MalformedRpcResponseError, RPCError
from evm.rpc.client import RpcClient


class TestRpcClient:
    def test_call_success_with_explicit_params(self) -> None:
        provider = Mock()
        provider.make_request.return_value = {"result": "0x123"}
        client = RpcClient(provider=provider)

        result = client.call("eth_getBlockByNumber", ["latest", False])

        assert result == "0x123"
        provider.make_request.assert_called_once_with("eth_getBlockByNumber", ["latest", False])

    def test_call_defaults_none_params_to_empty_list(self) -> None:
        provider = Mock()
        provider.make_request.return_value = {"result": "0x1"}
        client = RpcClient(provider=provider)

        result = client.call("eth_blockNumber")

        assert result == "0x1"
        provider.make_request.assert_called_once_with("eth_blockNumber", [])

    def test_call_raises_rpc_error_when_error_field_present(self) -> None:
        provider = Mock()
        provider.make_request.return_value = {
            "error": {"code": -32601, "message": "Method not found"}
        }
        client = RpcClient(provider=provider)

        with pytest.raises(RPCError) as exc_info:
            client.call("unknown_method")

        assert "code: -32601" in str(exc_info.value)
        assert "message: Method not found" in str(exc_info.value)
        provider.make_request.assert_called_once_with("unknown_method", [])

    @pytest.mark.parametrize(
        "falsy_valid_result",
        [
            [],
            None,
            0,
            "",
            False,
        ],
    )
    def test_call_accepts_falsy_valid_results(self, falsy_valid_result) -> None:
        provider = Mock()
        provider.make_request.return_value = {"result": falsy_valid_result}
        client = RpcClient(provider=provider)

        result = client.call("some_method")

        assert result == falsy_valid_result
        provider.make_request.assert_called_once_with("some_method", [])

    def test_call_raises_malformed_response_when_result_missing(self) -> None:
        provider = Mock()
        provider.make_request.return_value = {}
        client = RpcClient(provider=provider)

        with pytest.raises(MalformedRpcResponseError) as exc_info:
            client.call("eth_blockNumber")

        assert "RPC response has no result" in str(exc_info.value)
        provider.make_request.assert_called_once_with("eth_blockNumber", [])


    @pytest.mark.parametrize(
        ("rpc_value", "expected"),
        [
            ("0x1", 1),
            ("0x89", 137),
            ("0x2105", 8453)
        ],
    )
    def test_get_chain_id_parses_hex_correctly(
        self,
        rpc_value: str,
        expected: int,
    ) -> None:
        provider = Mock()
        provider.make_request.return_value = {"result": rpc_value}
        client = RpcClient(provider=provider)

        chain_id = client.get_chain_id()

        assert chain_id == expected
        provider.make_request.assert_called_once_with("eth_chainId", [])

