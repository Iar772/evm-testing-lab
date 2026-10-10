from typing import Any


class LogScanner:
    def __init__(
        self,
        log_source: Any,
        chain_id: int,
        chunk_size: int,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        self.log_source = log_source
        self.chain_id = chain_id
        self.chunk_size = chunk_size

    def scan(
        self,
        from_block: int,
        to_block: int,
        address: str | None = None,
        topics: list | None = None,
    ) -> list:
        if from_block > to_block:
            raise ValueError(
                "from_block must not be greater than to_block"
            )

        current_from = from_block
        overall_logs = []
        seen = set()

        while current_from <= to_block:
            current_to = min(
                current_from + self.chunk_size - 1,
                to_block,
            )

            filter_params = {
                "fromBlock": current_from,
                "toBlock": current_to,
            }

            if address is not None:
                filter_params["address"] = address

            if topics is not None:
                filter_params["topics"] = topics

            chunk_logs = self.log_source.get_logs(filter_params)

            for log in chunk_logs:
                identity = (
                    self.chain_id,
                    log["transactionHash"],
                    log["logIndex"],
                )

                if identity in seen:
                    continue

                seen.add(identity)
                overall_logs.append(log)

            current_from = current_to + 1

        return overall_logs