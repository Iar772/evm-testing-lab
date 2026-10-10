from typing import Any

from requests import RequestException

from evm.errors import MalformedRpcResponseError, RPCError, RPCTransportError


class RpcClient:
    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def call(
        self,
        method: str,
        params: list | None = None,
    ) -> Any:
        actual_params = [] if params is None else params

        try:
            response = self.provider.make_request(
                method,
                actual_params,
            )
        except (OSError, RequestException) as exc:
            raise RPCTransportError(
                f"RPC transport failure while calling {method}"
            ) from exc

        if "error" in response:
            raise RPCError(
                f"RPC error: code: {response['error']['code']}, "
                f"message: {response['error']['message']}"
            )

        if "result" not in response:
            raise MalformedRpcResponseError(
                "RPC response has no result"
            )

        return response["result"]

    def get_chain_id(self) -> int:
        result = self.call("eth_chainId", [])
        return int(result, 16)