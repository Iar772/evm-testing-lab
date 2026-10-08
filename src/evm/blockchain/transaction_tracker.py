import time
from collections.abc import Callable

from web3 import Web3
from web3.exceptions import TimeExhausted
from web3.types import TxReceipt

from evm.errors import TransactionTrackingTimeoutError


class TransactionTracker:
    def __init__(self, w3: Web3, sleep_fn: Callable[[float], None] = time.sleep):
        self.w3 = w3
        self.sleep_fn = sleep_fn


    def wait_for_receipt(self, tx_hash: str, timeout: int = 30, poll_interval: float = 0.5) -> TxReceipt:
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                transaction_hash=tx_hash,
                timeout=timeout,
                poll_latency=poll_interval
            )
            return receipt
        except TimeExhausted as exc:
            raise TransactionTrackingTimeoutError(
                "Transaction receipt timed out"
            ) from exc

    def wait_for_confirmations(
        self,
        tx_hash: str,
        required_confirmations: int,
        timeout: int = 30,
        poll_interval: float = 0.5
    ) -> TxReceipt:
        if required_confirmations < 1:
            raise ValueError("Required transaction confirmations is less than 1")
        receipt = self.wait_for_receipt(tx_hash, timeout, poll_interval)
        tx_block = receipt["blockNumber"]

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            head_block = self.w3.eth.block_number
            confirmations = head_block - tx_block + 1
            if confirmations >= required_confirmations:
                return receipt
            self.sleep_fn(poll_interval)
        raise TransactionTrackingTimeoutError(
            f"Transaction {tx_hash} timed out while waiting for "
f"          {required_confirmations} confirmations"
        )