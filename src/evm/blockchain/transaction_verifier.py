from web3.types import TxReceipt

from evm.errors import TransactionRevertedError


class TransactionVerifier:

    def verify_success(self, receipt: TxReceipt) -> None:
        if "status" not in receipt:
            raise ValueError("Receipt status missing")
        elif receipt["status"] != 1:
            raise TransactionRevertedError