from evm.config import ChainConfig
from evm.errors import WrongNetworkError
from evm.rpc.client import RpcClient


class EvmClient:
    def __init__(self, rpc: RpcClient, config: ChainConfig) -> None:
        self.rpc = rpc
        self.config = config
        self._validate_network()

    def _validate_network(self) -> None:
        current_chain_id = self.rpc.get_chain_id()
        if current_chain_id != self.config.chain_id:
            raise WrongNetworkError(
                f"Wrong network! Expected '{self.config.name}' (ID: {self.config.chain_id}), "
                f"but provider returned ID: {current_chain_id}."
            )