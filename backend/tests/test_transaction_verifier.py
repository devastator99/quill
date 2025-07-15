import unittest
import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from solathon import PublicKey
from your_module import SolanaTransactionVerifier, PROGRAM_PUBKEY
from borsh_construct import CStruct, String, U64

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


class TestSolanaTransactionVerifier(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.minimal_idl = {
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

    async def test_verify_initialize_user_success(self):
        # Build expected discriminator
        disc = hashlib.sha256(b"global:initialize_user").digest()[:8]
        # Fake get_transaction to return exactly that instruction
        async def fake_get_transaction(sig, commitment, max_supported_transaction_version):
            instr = DummyInstr(0, disc)
            msg = DummyMessage([PROGRAM_PUBKEY], [instr])
            tx = DummyTransaction(msg)
            meta = DummyMeta(err=None)
            return DummyResponse(DummyValue(tx, meta))

        with patch('your_module.SolanaClient') as MockSolanaClient:
            mock_client_instance = MockSolanaClient.return_value
            mock_client_instance.get_transaction.side_effect = fake_get_transaction
            client = mock_client_instance
            verifier = SolanaTransactionVerifier(client, self.minimal_idl)

            ok = await verifier.verify_transaction_with_retry(
                tx_signature="fake_sig",
                expected_instruction="initialize_user",
                expected_data={},  # no args to check
                max_retries=1
            )
            self.assertTrue(ok)

    async def test_verify_chat_query_success(self):
        # Prepare a chat_query payload
        query_text = "hello world"
        query_index = 99

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

        with patch('your_module.SolanaClient') as MockSolanaClient:
            mock_client_instance = MockSolanaClient.return_value
            mock_client_instance.get_transaction.side_effect = fake_get_transaction
            client = mock_client_instance
            verifier = SolanaTransactionVerifier(client, self.minimal_idl)

            ok = await verifier.verify_transaction_with_retry(
                tx_signature="fake_sig2",
                expected_instruction="chat_query",
                expected_data={"query_text": query_text, "query_index": query_index},
                max_retries=1
            )
            self.assertTrue(ok)

    async def test_verify_mismatch_fails(self):
        # Discriminator for a different instruction
        disc = hashlib.sha256(b"global:initialize_user").digest()[:8]
        data = disc  # but we’ll ask for “chat_query”
        async def fake_get_transaction(sig, commitment, max_supported_transaction_version):
            instr = DummyInstr(0, data)
            msg = DummyMessage([PROGRAM_PUBKEY], [instr])
            return DummyResponse(DummyValue(DummyTransaction(msg), DummyMeta(err=None)))

        with patch('your_module.SolanaClient') as MockSolanaClient:
            mock_client_instance = MockSolanaClient.return_value
            mock_client_instance.get_transaction.side_effect = fake_get_transaction
            client = mock_client_instance
            verifier = SolanaTransactionVerifier(client, self.minimal_idl)

            ok = await verifier.verify_transaction_with_retry(
                tx_signature="fake_sig3",
                expected_instruction="chat_query",
                expected_data={"query_text": "x", "query_index": 1},
                max_retries=1
            )
            self.assertFalse(ok)

if __name__ == '__main__':
    unittest.main()
