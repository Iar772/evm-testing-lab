# w3
# token_artifact
# token_contract
# anvil_snapshot
import json
from pathlib import Path

import allure
import pytest
from web3 import Web3

from evm.blockchain.transaction_tracker import TransactionTracker
from evm.blockchain.transaction_verifier import TransactionVerifier


@pytest.fixture(scope="session")
def w3():
    client =  Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    if not client.is_connected():
        raise ValueError("test setup should fail clearly")
    return client

@pytest.fixture(scope="session")
def load_foundry_artifact():
    path = Path("out/TestToken.sol/TestToken.json")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Artifact file not found at: {path}")

    with path.open("r", encoding="utf-8") as file:
        try:
            artifact = json.load(file)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format in artifact") from e

    if "abi" not in artifact:
        raise KeyError("Artifact is missing the 'abi' key")

    if "bytecode" not in artifact or "object" not in artifact["bytecode"]:
        raise KeyError("Artifact is missing 'bytecode.object'")
    return artifact

@pytest.fixture(scope="session")
def token_artifact(load_foundry_artifact):
    abi = load_foundry_artifact["abi"]
    bytecode = load_foundry_artifact["bytecode"]["object"]

    if bytecode == "0x" or not bytecode:
        raise ValueError(
            "Contract creation bytecode is empty"
        )

    deployed_bytecode = load_foundry_artifact.get("deployedBytecode", {}).get("object", "")

    return {
        "abi": abi,
        "bytecode": bytecode,
        "deployed_bytecode": deployed_bytecode,
    }

@pytest.fixture(scope="session")
def deployer(w3: Web3):
    return w3.eth.accounts[0]

@pytest.fixture(scope="session")
@allure.step("Create token contract from artifact")
def token_contract(w3: Web3, token_artifact: dict, deployer):
    contract_factory = w3.eth.contract(
        abi=token_artifact["abi"],
        bytecode=token_artifact["bytecode"],
    )

    tx_hash = contract_factory.constructor().transact(
        {"from":deployer}
    )

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    assert receipt["status"] == 1
    assert receipt["contractAddress"] is not None

    return w3.eth.contract(
        address=receipt["contractAddress"],
        abi=token_artifact["abi"],
    )

@pytest.fixture
def alice(w3: Web3):
    return w3.eth.accounts[1]

@pytest.fixture
def bob(w3: Web3):
    return w3.eth.accounts[2]


@pytest.fixture
def state_snapshot(w3: Web3):
    # --- PHASE 1: SETUP ---
    with allure.step("EVM State Isolation: Create snapshot"):
        response = w3.provider.make_request("evm_snapshot", [])

        snapshot_id = response.get("result") if isinstance(response, dict) else response

        if snapshot_id is None:
            raise RuntimeError(
                f"EVM Setup Error: Failed to create snapshot. Raw RPC response: {response}"
            )

        allure.attach(
            str(snapshot_id),
            name="Created Snapshot ID",
            attachment_type=allure.attachment_type.TEXT
        )

    yield snapshot_id

    with allure.step("EVM State Isolation: Revert to snapshot"):
        revert_response = w3.provider.make_request("evm_revert", [snapshot_id])

        revert_result = revert_response.get("result") if isinstance(revert_response, dict) else revert_response

        if revert_result is not True:
            raise RuntimeError(
                f"EVM Teardown Error: Failed to revert state to snapshot {snapshot_id}. "
                f"Expected True, got {revert_result}. Raw RPC response: {revert_response}"
            )

@pytest.fixture(scope="session")
def transaction_tracker(w3):
    return TransactionTracker(w3)

@pytest.fixture(scope="session")
def transaction_verifier():
    return TransactionVerifier()
