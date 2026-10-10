from unittest.mock import MagicMock

import pytest

from evm.blockchain.log_scanner import LogScanner


@pytest.fixture
def mock_log_source():
    return MagicMock()


@pytest.fixture
def scanner_factory(mock_log_source):
    def _create_scanner(chunk_size: int = 100, chain_id: int = 1):
        return LogScanner(
            log_source=mock_log_source,
            chain_id=chain_id,
            chunk_size=chunk_size,
        )
    return _create_scanner


class TestLogScanner:

    def test_scan_single_chunk(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=10)
        expected_logs = [{"blockNumber": 1, "transactionHash": "0x1", "logIndex": 0}]
        mock_log_source.get_logs.return_value = expected_logs

        result = scanner.scan(from_block=1, to_block=5)

        assert result == expected_logs
        mock_log_source.get_logs.assert_called_once_with({"fromBlock": 1, "toBlock": 5})

    def test_scan_multiple_chunks(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=2)
        mock_log_source.get_logs.side_effect = [
            [{"transactionHash": "0x1", "logIndex": 0}],
            [{"transactionHash": "0x2", "logIndex": 0}],
        ]

        result = scanner.scan(from_block=1, to_block=4)

        assert result == [
            {"transactionHash": "0x1", "logIndex": 0},
            {"transactionHash": "0x2", "logIndex": 0},
        ]
        assert mock_log_source.get_logs.call_count == 2
        mock_log_source.get_logs.assert_any_call({"fromBlock": 1, "toBlock": 2})
        mock_log_source.get_logs.assert_any_call({"fromBlock": 3, "toBlock": 4})

    def test_scan_last_partial_chunk(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=3)
        mock_log_source.get_logs.side_effect = [
            [{"transactionHash": "0x1", "logIndex": 0}],
            [{"transactionHash": "0x2", "logIndex": 0}],
        ]

        result = scanner.scan(from_block=1, to_block=5)

        assert result == [
            {"transactionHash": "0x1", "logIndex": 0},
            {"transactionHash": "0x2", "logIndex": 0},
        ]
        assert mock_log_source.get_logs.call_count == 2
        mock_log_source.get_logs.assert_any_call({"fromBlock": 1, "toBlock": 3})
        mock_log_source.get_logs.assert_any_call({"fromBlock": 4, "toBlock": 5})

    def test_scan_single_block(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=5)
        expected_logs = [{"transactionHash": "0x1", "logIndex": 0}]
        mock_log_source.get_logs.return_value = expected_logs

        result = scanner.scan(from_block=42, to_block=42)

        assert result == expected_logs
        mock_log_source.get_logs.assert_called_once_with({"fromBlock": 42, "toBlock": 42})

    def test_scan_invalid_range(self, scanner_factory):
        scanner = scanner_factory()

        with pytest.raises(ValueError, match="from_block must not be greater than to_block"):
            scanner.scan(from_block=100, to_block=99)

    @pytest.mark.parametrize("bad_chunk_size", [0, -5])
    def test_scan_invalid_chunk_size(self, mock_log_source, bad_chunk_size):
        with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
            LogScanner(log_source=mock_log_source, chain_id=1, chunk_size=bad_chunk_size)

    def test_scan_empty_successful_chunk(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=5)
        mock_log_source.get_logs.side_effect = [
            [],
            [{"transactionHash": "0x1", "logIndex": 0}],
        ]

        result = scanner.scan(from_block=1, to_block=10)

        assert result == [{"transactionHash": "0x1", "logIndex": 0}]
        assert mock_log_source.get_logs.call_count == 2

    def test_scan_middle_chunk_failure(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=2)
        mock_log_source.get_logs.side_effect = [
            [{"transactionHash": "0x1", "logIndex": 0}],
            TimeoutError("RPC timeout"),
            [{"transactionHash": "0x2", "logIndex": 0}],
        ]

        with pytest.raises(TimeoutError, match="RPC timeout"):
            scanner.scan(from_block=1, to_block=6)

        assert mock_log_source.get_logs.call_count == 2

    def test_scan_same_tx_different_log_index_preserved(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=10)
        tx_logs = [
            {"transactionHash": "0xabc", "logIndex": 1, "address": "0xContract"},
            {"transactionHash": "0xabc", "logIndex": 2, "address": "0xContract"}
        ]
        mock_log_source.get_logs.return_value = tx_logs

        result = scanner.scan(from_block=1, to_block=10)

        assert len(result) == 2
        assert result[0]["logIndex"] == 1
        assert result[1]["logIndex"] == 2
        assert result == tx_logs

    def test_duplicate_logs_removed_by_scanner_logic(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=5)
        duplicate_log = {"transactionHash": "0xddd", "logIndex": 0}
        mock_log_source.get_logs.side_effect = [
            [duplicate_log],
            [duplicate_log]
        ]

        result = scanner.scan(from_block=1, to_block=10)

        assert len(result) == 1
        assert result == [duplicate_log]

    def test_scan_with_optional_filters(self, mock_log_source, scanner_factory):
        scanner = scanner_factory(chunk_size=10)
        mock_log_source.get_logs.return_value = []

        scanner.scan(
            from_block=1,
            to_block=10,
            address="0xContract",
            topics=["0xTopicY"]
        )

        mock_log_source.get_logs.assert_called_once_with({
            "fromBlock": 1,
            "toBlock": 10,
            "address": "0xContract",
            "topics": ["0xTopicY"]
        })
