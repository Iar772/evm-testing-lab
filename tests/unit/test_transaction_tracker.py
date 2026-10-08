from unittest.mock import MagicMock, PropertyMock

import pytest
from web3.exceptions import TimeExhausted

from evm.blockchain.transaction_tracker import TransactionTracker
from evm.errors import TransactionTrackingTimeoutError


class TestTransactionTracker:
    @pytest.fixture
    def mock_w3(self):
        return MagicMock()

    @pytest.fixture
    def mock_sleep(self):
        return MagicMock()

    @pytest.fixture
    def tracker(self, mock_w3, mock_sleep):
        return TransactionTracker(w3=mock_w3, sleep_fn=mock_sleep)

    def test_wait_for_receipt_success(self, tracker, mock_w3):
        expected_receipt = {"blockNumber": 100, "status": 1}
        mock_w3.eth.wait_for_transaction_receipt.return_value = expected_receipt

        receipt = tracker.wait_for_receipt(tx_hash="0x123", timeout=30)

        assert receipt == expected_receipt
        mock_w3.eth.wait_for_transaction_receipt.assert_called_once_with(
            transaction_hash="0x123",
            timeout=30,
            poll_latency=0.5
        )

    def test_wait_for_receipt_timeout(self, tracker, mock_w3):
        mock_w3.eth.wait_for_transaction_receipt.side_effect = TimeExhausted

        with pytest.raises(TransactionTrackingTimeoutError, match="Transaction receipt timed out"):
            tracker.wait_for_receipt(tx_hash="0x123", timeout=10)

    def test_invalid_required_confirmations(self, tracker):
        with pytest.raises(ValueError, match="Required transaction confirmations is less than 1"):
            tracker.wait_for_confirmations(tx_hash="0x123", required_confirmations=0)

    def test_one_confirmation_boundary(self, tracker, mock_w3, mock_sleep):
        tx_block = 100
        receipt = {"blockNumber": tx_block, "status": 1}

        tracker.wait_for_receipt = MagicMock(return_value=receipt)
        type(mock_w3.eth).block_number = PropertyMock(return_value=tx_block)

        tracker.wait_for_confirmations(tx_hash="0x123", required_confirmations=1)

        mock_sleep.assert_not_called()

    def test_multi_confirmation_polling(self, tracker, mock_w3, mock_sleep):
        tx_block = 100
        receipt = {"blockNumber": tx_block, "status": 1}
        tracker.wait_for_receipt = MagicMock(return_value=receipt)

        type(mock_w3.eth).block_number = PropertyMock(side_effect=[100, 101, 102])

        tracker.wait_for_confirmations(
            tx_hash="0x123", required_confirmations=3, poll_interval=0.5
        )

        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_confirmation_timeout(self, tracker, mock_w3, mock_sleep, monkeypatch):
        tx_block = 100
        receipt = {"blockNumber": tx_block, "status": 1}
        tracker.wait_for_receipt = MagicMock(return_value=receipt)

        type(mock_w3.eth).block_number = PropertyMock(return_value=tx_block)

        mock_monotonic = MagicMock(side_effect=[0, 0, 35])
        monkeypatch.setattr("time.monotonic", mock_monotonic)

        with pytest.raises(TransactionTrackingTimeoutError):
            tracker.wait_for_confirmations(tx_hash="0x123", required_confirmations=2, timeout=30)
