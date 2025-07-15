import pytest
import hashlib
from types import SimpleNamespace

from solathon import PublicKey
from your_module import SolanaTransactionVerifier, PROGRAM_PUBKEY

# Dummy classes to fake a get_transaction response
class DummyInstr:
    def __init__(self, program_id_index, data):
        self.program_id_index = program_id_index
        self.data = data

class DummyMessage:
    def __init__(self, account_keys, instructions):
        self.account_keys = account_keys
        self.instructions = instructions

class DummyTransaction:
    def __init__(self, message):
        self.message = message

class DummyMeta:
    def __init__(self, err=None):
        self.err = err

class DummyValue:
    def __init__(self, transaction, meta):
        self.transaction = transaction
        self.meta = meta

class DummyResponse:
    def __init__(self, val):
        self.value = val


@pytest.fixture
def minimal_idl():
    """A pared-down IDL for two instructions."""
    return {
        "instructions": [
            {"name": "initialize_user", "args": []},
            {
                "name": "chat_query",
                "args": [
                    {"name": "query_text", "type": "string"},
                    {"name": "query_index", "type": "u64"},
                ],
            },
        ]
    }


@pytest.mark.asyncio
async def test_verify_initialize_user_success(minimal_idl, monkeypatch):
    # Build expected discriminator
    disc = hashlib.sha256(b"global:initialize_user").digest()[:8]
    # Fake get_transaction to return exactly that instruction
    async def fake_get_transaction(sig, commitment, max_supported_transaction_version):
        instr = DummyInstr(0, disc)
        msg = DummyMessage([PROGRAM_PUBKEY], [instr])
        tx = DummyTransaction(msg)
        meta = DummyMeta(err=None)
        return DummyResponse(DummyValue(tx, meta))

    client = SimpleNamespace(get_transaction=fake_get_transaction)
    verifier = SolanaTransactionVerifier(client, minimal_idl)

    ok = await verifier.verify_transaction_with_retry(
        tx_signature="fake_sig",
        expected_instruction="initialize_user",
        expected_data={},  # no args to check
        max_retries=1
    )
    assert ok is True


@pytest.mark.asyncio
async def test_verify_chat_query_success(minimal_idl, monkeypatch):
    # Prepare a chat_query payload
    query_text = "hello world"
    query_index = 99
    from borsh_construct import CStruct, String, U64

    schema = CStruct("query_text"/String, "query_index"/U64)
    payload = schema.build({"query_text": query_text, "query_index": query_index})
    disc = hashlib.sha256(b"global:chat_query").digest()[:8]
    data = disc + payload

    async def fake_get_transaction(sig, commitment, max_supported_transaction_version):
        instr = DummyInstr(0, data)
        msg = DummyMessage([PROGRAM_PUBKEY], [instr])
        tx = DummyTransaction(msg)
        meta = DummyMeta(err=None)
        return DummyResponse(DummyValue(tx, meta))

    client = SimpleNamespace(get_transaction=fake_get_transaction)
    verifier = SolanaTransactionVerifier(client, minimal_idl)

    ok = await verifier.verify_transaction_with_retry(
        tx_signature="fake_sig2",
        expected_instruction="chat_query",
        expected_data={"query_text": query_text, "query_index": query_index},
        max_retries=1
    )
    assert ok is True


@pytest.mark.asyncio
async def test_verify_mismatch_fails(minimal_idl, monkeypatch):
    # Discriminator for a different instruction
    disc = hashlib.sha256(b"global:initialize_user").digest()[:8]
    data = disc  # but we’ll ask for “chat_query”
    async def fake_get_transaction(sig, commitment, max_supported_transaction_version):
        instr = DummyInstr(0, data)
        msg = DummyMessage([PROGRAM_PUBKEY], [instr])
        return DummyResponse(DummyValue(DummyTransaction(msg), DummyMeta(err=None)))

    client = SimpleNamespace(get_transaction=fake_get_transaction)
    verifier = SolanaTransactionVerifier(client, minimal_idl)

    ok = await verifier.verify_transaction_with_retry(
        tx_signature="fake_sig3",
        expected_instruction="chat_query",
        expected_data={"query_text": "x", "query_index": 1},
        max_retries=1
    )
    assert ok is False
