import base58
import asyncio
import json
import os
from typing import List, Tuple

from fastapi import FastAPI
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.rpc.commitment import Commitment
from anchorpy import Idl, Program, Provider, Context
from anchorpy.coder.instruction import AnchorInstructionCoder

from config import PROGRAM_ID, MAX_RETRIES, RETRY_DELAY, SOLANA_RPC_URL

app = FastAPI()

# On‐chain program ID as PublicKey
PROGRAM_PUBKEY = PublicKey(PROGRAM_ID)

# Shared Solana RPC client
shared_solana_client = AsyncClient(SOLANA_RPC_URL)

# Load the IDL
idl_path = os.path.join(os.path.dirname(__file__), "socratictoken.json")
try:
    with open(idl_path, "r") as f:
        idl = Idl.from_json(json.load(f))
except FileNotFoundError:
    raise FileNotFoundError(f"IDL file not found at {idl_path}")
except Exception as e:
    raise Exception(f"Error loading IDL: {e}")

# A no-op wallet for building unsigned transactions
class NoOpWallet:
    def public_key(self) -> PublicKey:
        return PublicKey("11111111111111111111111111111111")
    def sign_transaction(self, tx: Transaction) -> Transaction:
        return tx

# AnchorPy setup
provider = Provider(shared_solana_client, NoOpWallet())
program = Program(idl, PROGRAM_PUBKEY, provider)


class SolanaTransactionBuilder:
    def __init__(self, program: Program, client: AsyncClient):
        self.program = program
        self.client = client

    async def build_upload_document_transaction(
        self,
        user_public_key: str,
        pdf_hash: str,
        access_level: int,
        document_index: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        document_record_pda, _ = PublicKey.find_program_address(
            [b"document", user_pubkey.to_bytes(), document_index.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.upload_document(
            pdf_hash, access_level, document_index,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "document_record": document_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_chat_query_transaction(
        self,
        user_public_key: str,
        query_text: str,
        query_index: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        query_record_pda, _ = PublicKey.find_program_address(
            [b"query", user_pubkey.to_bytes(), query_index.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.chat_query(
            query_text, query_index,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "query_record": query_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_initialize_user_transaction(
        self,
        user_public_key: str
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.initialize_user(
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_purchase_tokens_transaction(
        self,
        user_public_key: str,
        sol_amount: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        treasury_pda, _ = PublicKey.find_program_address(
            [b"treasury"],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.purchase_tokens(
            sol_amount,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "user": user_pubkey,
                    "treasury": treasury_pda,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_share_document_transaction(
        self,
        user_public_key: str,
        document_index: int,
        new_access_level: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        document_record_pda, _ = PublicKey.find_program_address(
            [b"document", user_pubkey.to_bytes(), document_index.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.share_document(
            new_access_level,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "document_record": document_record_pda,
                    "user": user_pubkey,
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_generate_quiz_transaction(
        self,
        user_public_key: str,
        document_hash: str,
        timestamp: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        quiz_record_pda, _ = PublicKey.find_program_address(
            [b"quiz", user_pubkey.to_bytes(), timestamp.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.generate_quiz(
            document_hash, timestamp,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "quiz_record": quiz_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_stake_tokens_transaction(
        self,
        user_public_key: str,
        amount: int,
        timestamp: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        stake_record_pda, _ = PublicKey.find_program_address(
            [b"stake", user_pubkey.to_bytes(), timestamp.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.stake_tokens(
            amount, timestamp,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "stake_record": stake_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111111"),
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]

    async def build_unstake_tokens_transaction(
        self,
        user_public_key: str,
        timestamp: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        user_pubkey = PublicKey(user_public_key)
        user_account_pda, _ = PublicKey.find_program_address(
            [b"user", user_pubkey.to_bytes()],
            PROGRAM_PUBKEY
        )
        stake_record_pda, _ = PublicKey.find_program_address(
            [b"stake", user_pubkey.to_bytes(), timestamp.to_bytes(8, "little")],
            PROGRAM_PUBKEY
        )

        instruction = self.program.instruction.unstake_tokens(
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "stake_record": stake_record_pda,
                    "user": user_pubkey,
                }
            ),
        )

        tx = Transaction()
        tx.fee_payer = user_pubkey
        tx.add(instruction)
        recent = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent.value.blockhash
        return tx, [user_pubkey]


class SolanaTransactionVerifier:
    def __init__(self, program: Program, client: AsyncClient):
        self.program = program
        self.client = client

    async def verify_transaction_with_retry(
        self,
        tx_signature: str,
        expected_instruction: str,
        expected_data: dict,
        max_retries: int = MAX_RETRIES
    ) -> bool:
        for attempt in range(max_retries):
            try:
                if await self._verify_transaction(tx_signature, expected_instruction, expected_data):
                    return True
            except Exception as e:
                print(f"Verification attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
        return False

    async def _verify_transaction(
        self,
        tx_signature: str,
        expected_instruction: str,
        expected_data: dict
    ) -> bool:
        resp = await self.client.get_transaction(
            tx_signature,
            commitment=Commitment("confirmed"),
            max_supported_transaction_version=0
        )
        if not resp.value or (resp.value.meta and resp.value.meta.err):
            return False

        message = resp.value.transaction.message
        program_instruction = None
        for instr in message.instructions:
            pid = message.account_keys[instr.program_id_index]
            if str(pid) == str(PROGRAM_PUBKEY):
                program_instruction = instr
                break
        if not program_instruction:
            return False

        data = base58.b58decode(program_instruction.data)
        coder = AnchorInstructionCoder(self.program.idl)
        try:
            decoded = coder.decode(data)
        except:
            return False
        if not decoded or decoded.name != expected_instruction:
            return False

        return self._verify_instruction_data(decoded.data, expected_data, expected_instruction)

    def _verify_instruction_data(self, actual: dict, expected: dict, name: str) -> bool:
        if name == "upload_document":
            return (
                actual.get("pdf_hash") == expected.get("pdf_hash")
                and actual.get("access_level") == expected.get("access_level")
                and actual.get("document_index") == expected.get("document_index")
            )
        if name == "chat_query":
            return (
                actual.get("query_text") == expected.get("query_text")
                and actual.get("query_index") == expected.get("query_index")
            )
        if name == "initialize_user":
            return True
        if name == "purchase_tokens":
            return actual.get("sol_amount") == expected.get("sol_amount")
        if name == "share_document":
            return actual.get("new_access_level") == expected.get("new_access_level")
        if name == "generate_quiz":
            return (
                actual.get("document_hash") == expected.get("document_hash")
                and actual.get("timestamp") == expected.get("timestamp")
            )
        if name == "stake_tokens":
            return (
                actual.get("amount") == expected.get("amount")
                and actual.get("timestamp") == expected.get("timestamp")
            )
        if name == "unstake_tokens":
            return True
        return False


# Instantiate builder & verifier
transaction_builder = SolanaTransactionBuilder(program, shared_solana_client)
transaction_verifier = SolanaTransactionVerifier(program, shared_solana_client)


@app.on_event("shutdown")
async def shutdown_event():
    await shared_solana_client.close()
