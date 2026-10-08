from unittest.mock import MagicMock

import pytest
from web3 import Web3

from evm.blockchain.transaction_verifier import TransactionVerifier
from evm.errors import TransactionRevertedError


class TestTransactionVerifier:
    @pytest.fixture
    def mock_w3(self):
        return MagicMock(spec=Web3)

    @pytest.fixture
    def verifier(self, mock_w3):
        return TransactionVerifier()

    def test_verify_success_status_1(self, verifier):
        valid_receipt = {"status": 1, "blockNumber": 12345}

        verifier.verify_success(valid_receipt)

    def test_verify_success_status_0(self, verifier):
        reverted_receipt = {"status": 0, "blockNumber": 12345}

        with pytest.raises(TransactionRevertedError):
            verifier.verify_success(reverted_receipt)

    def test_verify_success_missing_status(self, verifier):
        missing_status_receipt = {"blockNumber": 12345, "from": "0x...", "to": "0x..."}

        with pytest.raises(ValueError, match="Receipt status missing"):
            verifier.verify_success(missing_status_receipt)
