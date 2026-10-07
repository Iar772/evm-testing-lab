from dataclasses import dataclass


@dataclass(frozen=True)
class ChainConfig:
    """
    Class to describe a chain configuration
    :param chain_id: The id of the chain
    :param name: The name of the chain
    """
    name: str
    chain_id: int