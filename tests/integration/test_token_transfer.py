import allure
import pytest
from web3 import Web3
from web3.exceptions import ContractCustomError


@allure.feature("ERC20")
@pytest.mark.integration
@pytest.mark.usefixtures("state_snapshot")
class TestTokenTransfer:

    @allure.title("Verification of basic contract metadata after deployment")
    def test_deployment_basic_metadata(self, w3: Web3, token_contract) -> None:
        with allure.step("Verify the contract address exists"):
            assert token_contract.address is not None
            assert w3.is_address(token_contract.address)

        with allure.step("Verify the token name is 'Test Token'"):
            name = token_contract.functions.name().call()
            assert name == "Test Token", f"Expected 'Test Token', but got '{name}'"

        with allure.step("Verify the token symbol is 'TST'"):
            symbol = token_contract.functions.symbol().call()
            assert symbol == "TST", f"Expected 'TST', but got '{symbol}'"

        with allure.step("Verify the decimal symbols number"):
            decimals = token_contract.functions.decimals().call()
            assert decimals == 18, f"Expected 18 decimals, but got {decimals}"

    @allure.story("Token transfer")
    @allure.title("Successful transfer after mint")
    def test_mint_transfer_success(
        self,
        w3: Web3,
        token_contract,
        alice,
        bob,
        deployer,
        transaction_tracker,
        transaction_verifier
    ) -> None:
        token_unit = 10 ** 18

        mint_amount = 1000 * token_unit
        transfer_amount = 100 * token_unit
        with allure.step("Capture balances before"):
            alice_balance_before = token_contract.functions.balanceOf(alice).call()
            bob_balance_before = token_contract.functions.balanceOf(bob).call()

        with allure.step(f"Mint 1000 TST to Alice ({alice})"):
            tx_hash = token_contract.functions.mint(alice, mint_amount).transact({"from": deployer})

        with allure.step(f"Wait for mint receipt and verify transaction success: {tx_hash}"):
            mint_receipt = transaction_tracker.wait_for_receipt(tx_hash)
            transaction_verifier.verify_success(mint_receipt)

        with allure.step(f"Alice transfers {transfer_amount} TST to Bob ({bob})"):
            tx_hash = token_contract.functions.transfer(bob, transfer_amount).transact(
                {"from": alice}
            )

        with allure.step(f"Wait for transfer receipt and verify transaction success: {tx_hash}"):
            transfer_receipt = transaction_tracker.wait_for_receipt(tx_hash)
            transaction_verifier.verify_success(transfer_receipt)

        with allure.step("Verify Alice and Bob balance deltas"):
            alice_balance_after = token_contract.functions.balanceOf(alice).call()
            bob_balance_after = token_contract.functions.balanceOf(bob).call()

            alice_delta = alice_balance_after - (alice_balance_before + mint_amount)
            assert alice_delta == -transfer_amount, f"Expected Alice delta {-transfer_amount}, got {alice_delta}"

            bob_delta = bob_balance_after - bob_balance_before
            assert bob_delta == transfer_amount, f"Expected Bob delta {transfer_amount}, got {bob_delta}"

        with allure.step("Verify Transfer event logs"):
            logs = token_contract.events.Transfer().process_receipt(transfer_receipt)

            assert len(logs) == 1, f"Expected exactly 1 Transfer event, found {len(logs)}"

            event_data = logs[0]["args"]
            assert event_data["from"] == alice, f"Expected event source {alice}, got {event_data['from']}"
            assert event_data["to"] == bob, f"Expected event destination {bob}, got {event_data['to']}"
            assert event_data["value"] == transfer_amount, (
                f"Expected event value {transfer_amount}, got {event_data['value']}"
            )

    @allure.title("Transfer fails when sender has insufficient balance")
    def test_insufficient_balance(self, w3: Web3, token_contract, alice, bob) -> None:
        transfer_amount = 100

        with allure.step(f"Verify Bob ({bob}) has 0 balance"):
            bob_balance_before = token_contract.functions.balanceOf(bob).call()
            assert bob_balance_before == 0, f"Expected Bob to have 0 balance, but got {bob_balance_before}"

        alice_balance_before = token_contract.functions.balanceOf(alice).call()

        with allure.step(f"Bob tries to transfer {transfer_amount} TST to Alice, expecting execution to fail"):
            with pytest.raises(ContractCustomError):
                token_contract.functions.transfer(alice, transfer_amount).transact(
                    {"from": bob}
                )

        with allure.step("Verify that the failed transaction did not mutate any ERC20 state"):
            bob_balance_after = token_contract.functions.balanceOf(bob).call()
            alice_balance_after = token_contract.functions.balanceOf(alice).call()

            assert bob_balance_after == bob_balance_before, (
                f"State mutated! Bob balance changed from {bob_balance_before} to {bob_balance_after}"
            )
            assert alice_balance_after == alice_balance_before, (
                f"State mutated! Alice balance changed from {alice_balance_before} to {alice_balance_after}"
            )

    @allure.story("Token transfer confirmations")
    @allure.title("Successful multi-block transaction confirmation via tracker")
    def test_transaction_multi_confirmation_success(
        self,
        w3: Web3,
        token_contract,
        alice,
        deployer,
        transaction_tracker,
        transaction_verifier
    ) -> None:
        token_unit = 10 ** 18
        mint_amount = 50 * token_unit

        with allure.step(f"Submit mint transaction of {mint_amount} TST to Alice"):
            tx_hash = token_contract.functions.mint(alice, mint_amount).transact({"from": deployer})

        with allure.step(f"Wait for initial receipt and verify transaction success: {tx_hash}"):
            receipt = transaction_tracker.wait_for_receipt(tx_hash)
            transaction_verifier.verify_success(receipt)
            tx_block = receipt["blockNumber"]

        with allure.step("Mine 2 additional Anvil blocks to satisfy confirmation depth"):
            for _ in range(2):
                w3.provider.make_request("evm_mine", [])

        with allure.step("Verify current blockchain head height"):
            current_head = w3.eth.block_number
            assert current_head == tx_block + 2, f"Expected block height {tx_block + 2}, but got {current_head}"

        with allure.step(f"Verify wait_for_confirmations immediately finds 3 blocks for tx: {tx_hash}"):
            transaction_tracker.wait_for_confirmations(
                tx_hash=tx_hash,
                required_confirmations=3,
                timeout=5
            )
