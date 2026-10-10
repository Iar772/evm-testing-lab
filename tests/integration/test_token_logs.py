import allure
import pytest
from web3.datastructures import AttributeDict

from evm.blockchain.log_scanner import LogScanner


@allure.feature("ERC20")
@pytest.mark.integration
class TestTokenLogs:
    def test_transfer_logs(
        self,
        w3,
        token_contract,
        deployer,
        alice,
        bob,
        log_scanner: LogScanner,
        state_snapshot,
        transaction_verifier
    ) -> None:
        with allure.step("Get start block number"):
            start_block = w3.eth.block_number

        with allure.step("Mint tokens to Alice: 1000"):
            mint_tx = token_contract.functions.mint(alice, 1000).transact({"from": deployer})
            receipt = w3.eth.wait_for_transaction_receipt(mint_tx)
            transaction_verifier.verify_success(receipt)

        with allure.step("Transfer 100 tokens from Alice to Bob (Tx1)"):
            tx1 = token_contract.functions.transfer(bob, 100).transact({"from": alice})
            receipt = w3.eth.wait_for_transaction_receipt(tx1)
            transaction_verifier.verify_success(receipt)

        with allure.step("Transfer 200 tokens from Alice to Bob (Tx2)"):
            tx2 = token_contract.functions.transfer(bob, 200).transact({"from": alice})
            receipt = w3.eth.wait_for_transaction_receipt(tx2)
            transaction_verifier.verify_success(receipt)

        with allure.step("Get end block number"):
            end_block = w3.eth.block_number

        with allure.step(f"Scan block range from {start_block} to {end_block}"):
            transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
            raw_logs = log_scanner.scan(
                from_block=start_block,
                to_block=end_block,
                address=token_contract.address,
                topics=[transfer_topic],
            )

        with allure.step("Filter and decode Transfer logs"):
            transfer_events = []
            for log in raw_logs:

                formatted_log = AttributeDict(
                    {
                        "blockNumber": int(log["blockNumber"], 16) if
                        isinstance(log["blockNumber"], str) else log["blockNumber"],
                        "transactionHash": log["transactionHash"],
                        "address": log["address"],
                        "topics": log["topics"],
                        "data": log["data"],
                        "logIndex": int(log["logIndex"], 16) if
                        isinstance(log["logIndex"], str) else log["logIndex"],
                        "transactionIndex": int(log["transactionIndex"], 16) if
                        isinstance(log["transactionIndex"], str) else log["transactionIndex"],
                        "blockHash": log["blockHash"],
                    }
                )
                decoded_log = token_contract.events.Transfer().process_log(formatted_log)
                transfer_events.append(decoded_log)

            target_events = [
                ev for ev in transfer_events
                if ev["args"]["from"] == alice and ev["args"]["to"] == bob
            ]

        with allure.step("Verify expected events and their attributes"):
            assert len(target_events) == 2, f"Expected 2 Transfer events, got {len(target_events)}"

            event1 = target_events[0]["args"]
            assert event1["from"] == alice, f"Expected from: {alice}, got {event1['from']}"
            assert event1["to"] == bob, f"Expected to: {bob}, got {event1['to']}"
            assert event1["value"] == 100, f"Expected value: 100, got {event1['value']}"

            event2 = target_events[1]["args"]
            assert event2["from"] == alice, f"Expected from: {alice}, got {event2['from']}"
            assert event2["to"] == bob, f"Expected to: {bob}, got {event2['to']}"
            assert event2["value"] == 200, f"Expected value: 200, got {event2['value']}"
