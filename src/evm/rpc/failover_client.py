from typing import Any

from evm.errors import RPCError, RPCTransportError
from evm.rpc.client import RpcClient


class RpcFailoverClient:
    def __init__(
        self,
        clients: list[RpcClient],
    ) -> None:
        if not clients:
            raise ValueError(
                "At least one RPC client is required"
            )

        self.clients = clients

    def call(
        self,
        method: str,
        params: list | None = None,
    ) -> Any:
        last_error: RPCTransportError | None = None

        for client in self.clients:
            try:
                return client.call(
                    method=method,
                    params=params,
                )

            except RPCTransportError as exc:
                last_error = exc

        raise RPCError(
            f"All RPC providers failed for method {method}"
        ) from last_error

    def get_logs(
        self,
        filter_params: dict,
    ) -> list:
        rpc_filter = dict(filter_params)

        from_block = rpc_filter.get("fromBlock")
        to_block = rpc_filter.get("toBlock")

        if isinstance(from_block, int):
            rpc_filter["fromBlock"] = hex(from_block)

        if isinstance(to_block, int):
            rpc_filter["toBlock"] = hex(to_block)

        result = self.call(
            method="eth_getLogs",
            params=[rpc_filter],
        )

        if not isinstance(result, list):
            raise TypeError(
                "eth_getLogs result must be a list"
            )

        return result