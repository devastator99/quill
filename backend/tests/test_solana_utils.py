import pytest
import asyncio
import hashlib
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import borsh_construct as borsh
from solathon import Client, Transaction, PublicKey
from solathon.core.instructions import Instruction, AccountMeta
from solathon.core.types import Commitment

from solana_utils import SolanaTransactionBuilder, SolanaTransactionVerifier, PROGRAM_PUBKEY


# Mock classes for transaction response simulation
class MockInstruction:
    def __init__(self, program_id_index, data):
        self.program_id_index = program_id_index
        self.data = data


class MockMessage:
    def __init__(self, account_keys, instructions):
        self.account_keys = account_keys
        self.instructions = instructions


class MockTransaction:
    def __init__(self, message):
        self.message = message


class MockMeta:
    def __init__(self, err=None):
        self.err = err


class MockTransactionValue:
    def __init__(self, transaction, meta):
        self.transaction = transaction
        self.meta = meta


class MockTransactionResponse:
    def __init__(self, value):
        self.value = value


class MockBlockhashResponse:
    def __init__(self, blockhash):
        self.value = SimpleNamespace(blockhash=blockhash)


@pytest.fixture
def mock_client():
    """Create a mock Solana client"""
    client = AsyncMock(spec=Client)
    client.get_latest_blockhash.return_value = MockBlockhashResponse("mock_blockhash")
    return client


@pytest.fixture
def sample_idl():
    """Sample IDL for testing"""
    return {
        "instructions": [
            {
                "name": "initialize_user",
                "args": []
            },
            {
                "name": "upload_document",
                "args": [
                    {"name": "pdf_hash", "type": "string"},
                    {"name": "access_level", "type": "u8"},
                    {"name": "document_index", "type": "u64"}
                ]
            },
            {
                "name": "chat_query",
                "args": [
                    {"name": "query_text", "type": "string"},
                    {"name": "query_index", "type": "u64"}
                ]
            },
            {
                "name": "purchase_tokens",
                "args": [
                    {"name": "amount", "type": "u64"}
                ]
            },
            {
                "name": "share_document",
                "args": [
                    {"name": "new_access_level", "type": "u8"}
                ]
            },
            {
                "name": "generate_quiz",
                "args": [
                    {"name": "document_hash", "type": "string"},
                    {"name": "timestamp", "type": "u64"}
                ]
            },
            {
                "name": "stake_tokens",
                "args": [
                    {"name": "amount", "type": "u64"}
                ]
            },
            {
                "name": "unstake_tokens",
                "args": [
                    {"name": "amount", "type": "u64"}
                ]
            }
        ]
    }


@pytest.fixture
def transaction_builder(mock_client):
    """Create a SolanaTransactionBuilder instance"""
    return SolanaTransactionBuilder(mock_client)


@pytest.fixture
def transaction_verifier(mock_client, sample_idl):
    """Create a SolanaTransactionVerifier instance"""
    return SolanaTransactionVerifier(mock_client, sample_idl)


class TestSolanaTransactionBuilder:
    """Test cases for SolanaTransactionBuilder"""

    @pytest.mark.asyncio
    async def test_build_upload_document_transaction(self, transaction_builder):
        """Test building upload document transaction"""
        user_public_key = "11111111111111111111111111111111"
        pdf_hash = "test_hash_123"
        access_level = 1
        document_index = 0

        tx, signers = await transaction_builder.build_upload_document_transaction(
            user_public_key, pdf_hash, access_level, document_index
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert tx.fee_payer == PublicKey(user_public_key)
        assert tx.recent_blockhash == "mock_blockhash"
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 4  # user_account_pda, document_record_pda, user, system_program

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:upload_document").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_chat_query_transaction(self, transaction_builder):
        """Test building chat query transaction"""
        user_public_key = "11111111111111111111111111111111"
        query_text = "What is this document about?"
        query_index = 1

        tx, signers = await transaction_builder.build_chat_query_transaction(
            user_public_key, query_text, query_index
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert tx.fee_payer == PublicKey(user_public_key)
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 4

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:chat_query").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_initialize_user_transaction(self, transaction_builder):
        """Test building initialize user transaction"""
        user_public_key = "11111111111111111111111111111111"

        tx, signers = await transaction_builder.build_initialize_user_transaction(user_public_key)

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert tx.fee_payer == PublicKey(user_public_key)
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 3  # user_account_pda, user, system_program

        # Verify instruction data (should only contain discriminator for initialize_user)
        expected_discriminator = hashlib.sha256(b"global:initialize_user").digest()[:8]
        assert instruction.data == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_purchase_tokens_transaction(self, transaction_builder):
        """Test building purchase tokens transaction"""
        user_public_key = "11111111111111111111111111111111"
        sol_amount = 1000000000  # 1 SOL in lamports

        tx, signers = await transaction_builder.build_purchase_tokens_transaction(
            user_public_key, sol_amount
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 3

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:purchase_tokens").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_share_document_transaction(self, transaction_builder):
        """Test building share document transaction"""
        user_public_key = "11111111111111111111111111111111"
        document_index = 0
        new_access_level = 2

        tx, signers = await transaction_builder.build_share_document_transaction(
            user_public_key, document_index, new_access_level
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 3  # user_account_pda, document_record_pda, user

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:share_document").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_generate_quiz_transaction(self, transaction_builder):
        """Test building generate quiz transaction"""
        user_public_key = "11111111111111111111111111111111"
        document_hash = "quiz_doc_hash"
        timestamp = 1640995200

        tx, signers = await transaction_builder.build_generate_quiz_transaction(
            user_public_key, document_hash, timestamp
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 4

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:generate_quiz").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_stake_tokens_transaction(self, transaction_builder):
        """Test building stake tokens transaction"""
        user_public_key = "11111111111111111111111111111111"
        amount = 500000000

        tx, signers = await transaction_builder.build_stake_tokens_transaction(
            user_public_key, amount
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 3

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:stake_tokens").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_build_unstake_tokens_transaction(self, transaction_builder):
        """Test building unstake tokens transaction"""
        user_public_key = "11111111111111111111111111111111"
        amount = 250000000

        tx, signers = await transaction_builder.build_unstake_tokens_transaction(
            user_public_key, amount
        )

        # Verify transaction structure
        assert isinstance(tx, Transaction)
        assert len(signers) == 1
        assert str(signers[0]) == user_public_key
        assert len(tx.instructions) == 1

        # Verify instruction structure
        instruction = tx.instructions[0]
        assert instruction.program_id == PROGRAM_PUBKEY
        assert len(instruction.accounts) == 3

        # Verify instruction data contains discriminator
        expected_discriminator = hashlib.sha256(b"global:unstake_tokens").digest()[:8]
        assert instruction.data[:8] == expected_discriminator

    @pytest.mark.asyncio
    async def test_invalid_public_key_raises_error(self, transaction_builder):
        """Test that invalid public key raises an error"""
        with pytest.raises(Exception):
            await transaction_builder.build_initialize_user_transaction("invalid_key")


class TestSolanaTransactionVerifier:
    """Test cases for SolanaTransactionVerifier"""

    @pytest.mark.asyncio
    async def test_verify_initialize_user_success(self, transaction_verifier):
        """Test successful verification of initialize_user transaction"""
        # Build expected discriminator
        discriminator = hashlib.sha256(b"global:initialize_user").digest()[:8]
        
        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, discriminator)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=1
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_chat_query_success(self, transaction_verifier):
        """Test successful verification of chat_query transaction"""
        query_text = "test query"
        query_index = 42

        # Build instruction data
        schema = borsh.CStruct("query_text" / borsh.String, "query_index" / borsh.U64)
        payload = schema.build({"query_text": query_text, "query_index": query_index})
        discriminator = hashlib.sha256(b"global:chat_query").digest()[:8]
        instruction_data = discriminator + payload

        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="chat_query",
            expected_data={"query_text": query_text, "query_index": query_index},
            max_retries=1
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_upload_document_success(self, transaction_verifier):
        """Test successful verification of upload_document transaction"""
        pdf_hash = "test_hash"
        access_level = 1
        document_index = 0

        # Build instruction data
        schema = borsh.CStruct(
            "pdf_hash" / borsh.String,
            "access_level" / borsh.U8,
            "document_index" / borsh.U64
        )
        payload = schema.build({
            "pdf_hash": pdf_hash,
            "access_level": access_level,
            "document_index": document_index
        })
        discriminator = hashlib.sha256(b"global:upload_document").digest()[:8]
        instruction_data = discriminator + payload

        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="upload_document",
            expected_data={
                "pdf_hash": pdf_hash,
                "access_level": access_level,
                "document_index": document_index
            },
            max_retries=1
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_transaction_failed_transaction(self, transaction_verifier):
        """Test verification of failed transaction"""
        # Mock get_transaction response with error
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            meta = MockMeta(err="Transaction failed")
            return MockTransactionResponse(MockTransactionValue(None, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=1
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_transaction_no_program_instruction(self, transaction_verifier):
        """Test verification when no instruction for our program is found"""
        other_program = PublicKey("22222222222222222222222222222222")
        discriminator = hashlib.sha256(b"global:initialize_user").digest()[:8]

        # Mock get_transaction response with different program
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, discriminator)
            message = MockMessage([other_program], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=1
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_transaction_wrong_instruction(self, transaction_verifier):
        """Test verification with wrong instruction discriminator"""
        # Use discriminator for different instruction
        discriminator = hashlib.sha256(b"global:chat_query").digest()[:8]

        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, discriminator)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",  # Expecting different instruction
            expected_data={},
            max_retries=1
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_transaction_data_mismatch(self, transaction_verifier):
        """Test verification with mismatched instruction data"""
        query_text = "test query"
        query_index = 42

        # Build instruction data
        schema = borsh.CStruct("query_text" / borsh.String, "query_index" / borsh.U64)
        payload = schema.build({"query_text": query_text, "query_index": query_index})
        discriminator = hashlib.sha256(b"global:chat_query").digest()[:8]
        instruction_data = discriminator + payload

        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="chat_query",
            expected_data={"query_text": "different query", "query_index": 99},  # Different data
            max_retries=1
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_transaction_with_retry_eventually_succeeds(self, transaction_verifier):
        """Test that retry mechanism eventually succeeds"""
        discriminator = hashlib.sha256(b"global:initialize_user").digest()[:8]
        call_count = 0

        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:  # Fail first 2 attempts
                raise Exception("Network error")
            
            # Succeed on 3rd attempt
            instruction = MockInstruction(0, discriminator)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=3
        )
        
        assert result is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_verify_transaction_with_retry_max_retries_exceeded(self, transaction_verifier):
        """Test that retry mechanism fails after max retries"""
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            raise Exception("Persistent network error")

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=2
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_purchase_tokens_transaction(self, transaction_verifier):
        """Test verification of purchase_tokens transaction"""
        amount = 1000000000

        # Build instruction data
        schema = borsh.CStruct("amount" / borsh.U64)
        payload = schema.build({"amount": amount})
        discriminator = hashlib.sha256(b"global:purchase_tokens").digest()[:8]
        instruction_data = discriminator + payload

        # Mock get_transaction response
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        transaction_verifier.client.get_transaction = mock_get_transaction

        result = await transaction_verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="purchase_tokens",
            expected_data={"amount": amount},
            max_retries=1
        )
        
        assert result is True


class TestIntegration:
    """Integration tests for transaction builder and verifier"""

    @pytest.mark.asyncio
    async def test_build_and_verify_initialize_user(self, mock_client, sample_idl):
        """Test building and then verifying an initialize_user transaction"""
        builder = SolanaTransactionBuilder(mock_client)
        verifier = SolanaTransactionVerifier(mock_client, sample_idl)
        
        user_public_key = "11111111111111111111111111111111"
        
        # Build transaction
        tx, signers = await builder.build_initialize_user_transaction(user_public_key)
        
        # Extract instruction data from built transaction
        instruction = tx.instructions[0]
        instruction_data = instruction.data
        
        # Mock get_transaction to return the built instruction
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            mock_instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [mock_instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        verifier.client.get_transaction = mock_get_transaction

        # Verify the transaction
        result = await verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="initialize_user",
            expected_data={},
            max_retries=1
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_build_and_verify_chat_query(self, mock_client, sample_idl):
        """Test building and then verifying a chat_query transaction"""
        builder = SolanaTransactionBuilder(mock_client)
        verifier = SolanaTransactionVerifier(mock_client, sample_idl)
        
        user_public_key = "11111111111111111111111111111111"
        query_text = "What is this about?"
        query_index = 5
        
        # Build transaction
        tx, signers = await builder.build_chat_query_transaction(
            user_public_key, query_text, query_index
        )
        
        # Extract instruction data from built transaction
        instruction = tx.instructions[0]
        instruction_data = instruction.data
        
        # Mock get_transaction to return the built instruction
        async def mock_get_transaction(sig, commitment, max_supported_transaction_version):
            mock_instruction = MockInstruction(0, instruction_data)
            message = MockMessage([PROGRAM_PUBKEY], [mock_instruction])
            transaction = MockTransaction(message)
            meta = MockMeta(err=None)
            return MockTransactionResponse(MockTransactionValue(transaction, meta))

        verifier.client.get_transaction = mock_get_transaction

        # Verify the transaction
        result = await verifier.verify_transaction_with_retry(
            tx_signature="fake_signature",
            expected_instruction="chat_query",
            expected_data={"query_text": query_text, "query_index": query_index},
            max_retries=1
        )
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
