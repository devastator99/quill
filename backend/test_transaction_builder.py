import pytest
import hashlib
import borsh_construct as borsh
from solathon import PublicKey

from solana_utils import SolanaTransactionBuilder, PROGRAM_PUBKEY

# Dummy constants for tests
TEST_BLOCKHASH = "TEST_BLOCKHASH"
DUMMY_PDA = PublicKey("1" * 32)       
SYSTEM_PROGRAM = PublicKey("1" * 32)
USER_KEY = "User11111111111111111111111111111111111"


@pytest.fixture
def dummy_client(monkeypatch):
    """A fake Solana client that always returns TEST_BLOCKHASH."""
    class DummyClient:
        async def get_latest_blockhash(self):
            class BH:
                pass
            bh = BH()
            bh.value = type("V", (), {"blockhash": TEST_BLOCKHASH})
            return bh

    return DummyClient()


@pytest.fixture(autouse=True)
def patch_find_program_address(monkeypatch):
    """Stub out PDA derivation to always return DUMMY_PDA."""
    monkeypatch.setattr(
        PublicKey,
        "find_program_address",
        staticmethod(lambda seeds, program_id: (DUMMY_PDA, 0)),
    )


@pytest.fixture
def builder(dummy_client):
    return SolanaTransactionBuilder(dummy_client)


@pytest.mark.asyncio
async def test_build_initialize_user_transaction(builder):
    tx, signers = await builder.build_initialize_user_transaction(USER_KEY)

    # fee payer & blockhash
    assert tx.fee_payer == PublicKey(USER_KEY)
    assert tx.recent_blockhash == TEST_BLOCKHASH

    # only one instruction
    assert len(tx.instructions) == 1
    instr = tx.instructions[0]

    # program ID
    assert instr.program_id == PROGRAM_PUBKEY

    # accounts: [user_pda (writable), user_key(signer), system_program]
    acct_tuples = [(a.pubkey, a.is_signer, a.is_writable) for a in instr.accounts]
    assert acct_tuples == [
        (DUMMY_PDA, False, True),
        (PublicKey(USER_KEY), True, False),
        (SYSTEM_PROGRAM, False, False),
    ]

    # data == discriminator only
    disc = hashlib.sha256(b"global:initialize_user").digest()[:8]
    assert instr.data == disc

    # signer list
    assert signers == [PublicKey(USER_KEY)]


@pytest.mark.asyncio
async def test_build_upload_document_transaction(builder):
    pdf_hash = "QmTestHash"
    access_level = 7
    document_index = 42

    tx, signers = await builder.build_upload_document_transaction(
        USER_KEY, pdf_hash, access_level, document_index
    )

    # fee payer & blockhash
    assert tx.fee_payer == PublicKey(USER_KEY)
    assert tx.recent_blockhash == TEST_BLOCKHASH

    instr = tx.instructions[0]
    assert instr.program_id == PROGRAM_PUBKEY

    # accounts: [user_pda, doc_pda, user_key, system_program]
    acct_tuples = [(a.pubkey, a.is_signer, a.is_writable) for a in instr.accounts]
    assert acct_tuples == [
        (DUMMY_PDA, False, True),
        (DUMMY_PDA, False, True),
        (PublicKey(USER_KEY), True, False),
        (SYSTEM_PROGRAM, False, False),
    ]

    # build expected data: discriminator + Borsh-serialized args
    upload_args = borsh.CStruct(
        "pdf_hash" / borsh.String,
        "access_level" / borsh.U8,
        "document_index" / borsh.U64,
    )
    expected_payload = upload_args.build({
        "pdf_hash": pdf_hash,
        "access_level": access_level,
        "document_index": document_index,
    })
    expected_data = hashlib.sha256(b"global:upload_document").digest()[:8] + expected_payload
    assert instr.data == expected_data

    assert signers == [PublicKey(USER_KEY)]


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name, args, discriminator_name, schema", [
    ("build_chat_query_transaction",
     dict(user_public_key=USER_KEY, query_text="hello", query_index=3),
     "chat_query",
     borsh.CStruct("query_text"/borsh.String, "query_index"/borsh.U64)),
    ("build_purchase_tokens_transaction",
     dict(user_public_key=USER_KEY, sol_amount=1000),
     "purchase_tokens",
     borsh.CStruct("amount"/borsh.U64)),
    ("build_share_document_transaction",
     dict(user_public_key=USER_KEY, document_index=1, new_access_level=2),
     "share_document",
     borsh.CStruct("new_access_level"/borsh.U8)),
    ("build_generate_quiz_transaction",
     dict(user_public_key=USER_KEY, document_hash="docHash", timestamp=123456),
     "generate_quiz",
     borsh.CStruct("document_hash"/borsh.String, "timestamp"/borsh.U64)),
    ("build_stake_tokens_transaction",
     dict(user_public_key=USER_KEY, amount=500),
     "stake_tokens",
     borsh.CStruct("amount"/borsh.U64)),
    ("build_unstake_tokens_transaction",
     dict(user_public_key=USER_KEY, amount=250),
     "unstake_tokens",
     borsh.CStruct("amount"/borsh.U64)),
])
async def test_various_builders(builder, method_name, args, discriminator_name, schema):
    """Parametrized test for all remaining build_* methods."""
    method = getattr(builder, method_name)
    tx, signers = await method(**args)

    # Fee payer & signer
    assert tx.fee_payer == PublicKey(USER_KEY)
    assert signers == [PublicKey(USER_KEY)]

    instr = tx.instructions[0]
    # check discriminator + serialized payload
    payload = schema.build({k: args[k] if k in args else args["sol_amount"] for k in schema.subcons._fields})
    disc = hashlib.sha256(f"global:{discriminator_name}".encode()).digest()[:8]
    assert instr.data == disc + payload

    # ensure program_id is correct
    assert instr.program_id == PROGRAM_PUBKEY
