from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    HTTPException,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import re
import uuid as uuid_lib
from typing import List, Optional, Tuple
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.pgvector import PGVector
from langchain.schema import Document
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    JSON,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from tempfile import NamedTemporaryFile
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
import fitz
import pandas as pd
import mimetypes
import magic
from models import TempChunks, FinalChunks, PdfUploads, Base
from celery_worker import celery_app
from solana.keypair import Keypair
import base64
from solana.publickey import PublicKey
import nacl.signing
from anchorpy import Idl, Program, Provider, InstructionCoder , Context
from solana.rpc.async_api import AsyncClient
import hashlib
import asyncio
from datetime import datetime, timedelta
from solana.transaction import Transaction
from solana.rpc.commitment import Commitment
from anchorpy.coder.instruction import AnchorInstructionCoder
from typing import List, Tuple

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize FastAPI app
app = FastAPI(title="Socratic")

# Solana setup
PROGRAM_ID = PublicKey("5AhcUJj8WtAqR6yfff76HyZFX7LWovRZ1bcgN9n3Rwa7")
idl = Idl.from_json(open("socratictoken.json").read())
# Initialize shared AsyncClient for Solana
shared_solana_client = AsyncClient(SOLANA_RPC_URL)

provider = Provider(
    shared_solana_client, None
)  # No wallet needed for verification
program = Program(idl, PROGRAM_ID, provider)

MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
TX_CONFIRMATION_TIMEOUT = 60  # seconds
SOLANA_RPC_URL = "https://api.devnet.solana.com"

def get_db() -> Session:
    """Dependency to get DB session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    await shared_solana_client.close()


class LoginData(BaseModel):
    publicKey: str
    signature: str


class UnsignedTransactionRequest(BaseModel):
    user_public_key: str
    instruction_data: dict


class UnsignedTransactionResponse(BaseModel):
    unsigned_transaction: str  # Base64 encoded transaction
    accounts_to_sign: List[str]  # Public keys that need to sign
    transaction_message: str
    expires_at: int  # Unix timestamp


class SignedTransactionRequest(BaseModel):
    signed_transaction: str  # Base64 encoded signed transaction
    transaction_signature: str


# Modified request models for blockchain integration
class UploadDocBlockchainRequest(BaseModel):
    user_public_key: str
    pdf_hash: str
    access_level: int
    document_index: int


class ChatQueryBlockchainRequest(BaseModel):
    user_public_key: str
    message: str
    query_text: str
    query_index: int
    conversation_id: Optional[str] = None


class InitializeUserBlockchainRequest(BaseModel):
    user_public_key: str


class PurchaseTokensBlockchainRequest(BaseModel):
    user_public_key: str
    sol_amount: int


class ShareDocumentBlockchainRequest(BaseModel):
    user_public_key: str
    document_index: int
    new_access_level: int


class TransactionVerificationRequest(BaseModel):
    transaction_signature: str
    expected_instruction: str
    expected_data: dict


# added for solana integration.
class UploadDocRequest(BaseModel):
    tx_signature: str
    pdf_hash: str
    access_level: int
    document_index: int


class ChatRequest(BaseModel):
    message: str
    tx_signature: str
    query_text: str
    query_index: int
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup SQLAlchemy engine and session
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Allow extra connections if needed
    echo=False,  # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create database tables
Base.metadata.create_all(bind=engine)

connected_clients = []




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
        """Build unsigned transaction for upload_document instruction"""
        user_pubkey = PublicKey(user_public_key)
        
        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID 
        )
        
        document_record_pda, document_record_bump = PublicKey.find_program_address(
            [b"document", bytes(user_pubkey), document_index.to_bytes(8, 'little')], 
            PROGRAM_ID
        )
        
        # Build instruction
        instruction = self.program.instruction["upload_document"](
            pdf_hash=pdf_hash,
            access_level=access_level,
            document_index = document_index,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "document_record": document_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )
        
        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)
        
        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        
        return transaction, [user_pubkey]
    
    async def build_chat_query_transaction(
        self,
        user_public_key: str,
        query_text: str,
        query_index: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for chat_query instruction"""
        user_pubkey = PublicKey(user_public_key)
        
        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        
        query_record_pda, query_record_bump = PublicKey.find_program_address(
            [b"query", bytes(user_pubkey), query_index.to_bytes(8, 'little')], 
            PROGRAM_ID
        )
        
        # Build instruction
        instruction = self.program.instruction["chat_query"](
            query_text=query_text,
            query_index=query_index,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "query_record": query_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )
        
        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)
        
        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        
        return transaction, [user_pubkey]

    async def build_initialize_user_transaction(
        self,
        user_public_key: str
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for initialize_user instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["initialize_user"](
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

    async def build_purchase_tokens_transaction(
        self,
        user_public_key: str,
        sol_amount: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for purchase_tokens instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        treasury_pda, treasury_bump = PublicKey.find_program_address(
            [b"treasury"], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["purchase_tokens"](
            sol_amount=sol_amount,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "user": user_pubkey,
                    "treasury": treasury_pda,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

    async def build_share_document_transaction(
        self,
        user_public_key: str,
        document_index: int,
        new_access_level: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for share_document instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        document_record_pda, document_record_bump = PublicKey.find_program_address(
            [b"document", bytes(user_pubkey), document_index.to_bytes(8, "little")], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["share_document"](
            new_access_level=new_access_level,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "document_record": document_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

    async def build_generate_quiz_transaction(
        self,
        user_public_key: str,
        document_hash: str,
        timestamp: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for generate_quiz instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        quiz_record_pda, quiz_record_bump = PublicKey.find_program_address(
            [b"quiz", bytes(user_pubkey), timestamp.to_bytes(8, "little")], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["generate_quiz"](
            document_hash=document_hash,
            timestamp=timestamp,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "quiz_record": quiz_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

    async def build_stake_tokens_transaction(
        self,
        user_public_key: str,
        stake_amount: int,
        stake_duration: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for stake_tokens instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        stake_record_pda, stake_record_bump = PublicKey.find_program_address(
            [b"stake", bytes(user_pubkey), stake_duration.to_bytes(8, "little")], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["stake_tokens"](
            stake_amount=stake_amount,
            stake_duration=stake_duration,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "stake_record": stake_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

    async def build_unstake_tokens_transaction(
        self,
        user_public_key: str,
        stake_amount: int,
        stake_duration: int
    ) -> Tuple[Transaction, List[PublicKey]]:
        """Build unsigned transaction for unstake_tokens instruction"""
        user_pubkey = PublicKey(user_public_key)

        # Derive PDAs
        user_account_pda, user_account_bump = PublicKey.find_program_address(
            [b"user", bytes(user_pubkey)], PROGRAM_ID
        )
        stake_record_pda, stake_record_bump = PublicKey.find_program_address(
            [b"stake", bytes(user_pubkey), stake_duration.to_bytes(8, "little")], PROGRAM_ID
        )

        # Build instruction
        instruction = self.program.instruction["unstake_tokens"](
            stake_amount=stake_amount,
            stake_duration=stake_duration,
            ctx=Context(
                accounts={
                    "user_account": user_account_pda,
                    "stake_record": stake_record_pda,
                    "user": user_pubkey,
                    "system_program": PublicKey("11111111111111111111111111111112"),
                },
                signers=[user_pubkey],
            ),
        )

        # Create transaction
        transaction = Transaction()
        transaction.add(instruction)

        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash

        return transaction, [user_pubkey]

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
        """Verify transaction with retry logic for transient failures"""
        for attempt in range(max_retries):
            try:
                result = await self._verify_transaction(tx_signature, expected_instruction, expected_data)
                if result:
                    return True
            except Exception as e:
                print(f"Transaction verification attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    raise
        return False
    
    async def _verify_transaction(
        self,
        tx_signature: str,
        expected_instruction: str,
        expected_data: dict
    ) -> bool:
        """Internal method to verify a single transaction"""
        try:
            # Get transaction details
            tx_response = await self.client.get_transaction(
                tx_signature,
                commitment=Commitment("confirmed"),
                max_supported_transaction_version=0
            )
            
            if not tx_response.value:
                return False
            
            tx = tx_response.value
            if tx.meta and tx.meta.err:
                print(f"Transaction failed: {tx.meta.err}")
                return False
            
            # Parse transaction message
            message = tx.transaction.message
            
            # Find instruction for our program
            program_instruction = None
            for instruction in message.instructions:
                program_id_index = instruction.program_id_index
                program_id = message.account_keys[program_id_index]
                
                if str(program_id) == str(PROGRAM_ID):
                    program_instruction = instruction
                    break
            
            if not program_instruction:
                print("No instruction found for our program")
                return False
            
            # Decode instruction data
            instruction_data = base64.b64decode(program_instruction.data)
            coder = AnchorInstructionCoder(self.program.idl)
            
            try:
                decoded_instruction = coder.decode(instruction_data)
            except Exception as e:
                print(f"Failed to decode instruction: {e}")
                return False
            
            if not decoded_instruction or decoded_instruction.name != expected_instruction:
                print(f"Expected instruction {expected_instruction}, got {decoded_instruction.name if decoded_instruction else 'None'}")
                return False
            
            # Verify instruction data matches expected data
            return self._verify_instruction_data(decoded_instruction.data, expected_data, expected_instruction)
            
        except Exception as e:
            print(f"Transaction verification error: {e}")
            return False

    def _verify_instruction_data(self, actual_data: dict, expected_data: dict, instruction_name: str) -> bool:
        """Verify that instruction data matches expected values"""
        if instruction_name == "upload_document":
            return (
                actual_data.get("pdf_hash") == expected_data.get("pdf_hash") and
                actual_data.get("access_level") == expected_data.get("access_level") and
                actual_data.get("document_index") == expected_data.get("document_index")
            )
        elif instruction_name == "chat_query":
            return (
                actual_data.get("query_text") == expected_data.get("query_text") and
                actual_data.get("query_index") == expected_data.get("query_index")
            )
        elif instruction_name == "initialize_user":
            # No specific data to verify for initialize_user, just presence of instruction
            return True
        elif instruction_name == "purchase_tokens":
            return (
                actual_data.get("sol_amount") == expected_data.get("sol_amount")
            )
        elif instruction_name == "share_document":
            return (
                actual_data.get("new_access_level") == expected_data.get("new_access_level")
            )
        elif instruction_name == "generate_quiz":
            return (
                actual_data.get("document_hash") == expected_data.get("document_hash") and
                actual_data.get("timestamp") == expected_data.get("timestamp")
            )
        elif instruction_name == "stake_tokens":
            return (
                actual_data.get("stake_amount") == expected_data.get("stake_amount") and
                actual_data.get("stake_duration") == expected_data.get("stake_duration")
            )
        elif instruction_name == "unstake_tokens":
            return (
                actual_data.get("stake_amount") == expected_data.get("stake_amount") and
                actual_data.get("stake_duration") == expected_data.get("stake_duration")
            )
        return False

# Initialize Solana components
transaction_builder = SolanaTransactionBuilder(program, shared_solana_client)
transaction_verifier = SolanaTransactionVerifier(program, shared_solana_client)

# Utility functions
def generate_pdf_hash(content: bytes) -> str:
    """Generate SHA256 hash of PDF content"""
    return hashlib.sha256(content).hexdigest()

def get_expiration_timestamp(minutes: int = 5) -> int:
    """Get expiration timestamp for transactions"""
    return int((datetime.now() + timedelta(minutes=minutes)).timestamp())

# Modified endpoints for blockchain integration

@app.post("/upload_doc/prepare", response_model=UnsignedTransactionResponse)
async def prepare_upload_document_transaction(
    request: UploadDocBlockchainRequest,
    db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for document upload"""
    try:
        # Build unsigned transaction
        transaction, signers = await transaction_builder.build_upload_document_transaction(
            request.user_public_key,
            request.pdf_hash,
            request.access_level,
            request.document_index
        )
        
        # Serialize transaction
        serialized_tx = base64.b64encode(transaction.serialize()).decode('utf-8')
        
        return UnsignedTransactionResponse(
            unsigned_transaction=serialized_tx,
            accounts_to_sign=[str(signer) for signer in signers],
            transaction_message=f"Upload document with hash {request.pdf_hash[:16]}...",
            expires_at=get_expiration_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare transaction: {str(e)}")

@app.post("/upload_doc/verify", response_model=dict)
async def verify_and_process_upload(
    file: UploadFile = File(...),
    transaction_signature: str = None,
    pdf_hash: str = None,
    access_level: int = None,
    document_index: int = None,
    user_public_key: str = None,
    db: Session = Depends(get_db)
):
    """Verify transaction and process document upload"""
    if not all([transaction_signature, pdf_hash, access_level is not None, document_index is not None, user_public_key]):
        raise HTTPException(status_code=400, detail="Missing required blockchain parameters")
    
    try:
        # Verify the transaction
        expected_data = {
            "pdf_hash": pdf_hash,
            "access_level": access_level,
            "document_index": document_index
        }
        
        is_verified = await transaction_verifier.verify_transaction_with_retry(
            transaction_signature,
            "upload_document",
            expected_data
        )
        
        if not is_verified:
            raise HTTPException(status_code=400, detail="Transaction verification failed")
        
        # Validate file type
        validate_file_type(file)
        
        # Generate actual PDF hash and verify it matches
        file_content = await file.read()
        actual_hash = generate_pdf_hash(file_content)
        
        if actual_hash != pdf_hash:
            raise HTTPException(status_code=400, detail="PDF hash mismatch")
        
        # Reset file pointer for processing
        file.file.seek(0)
        
        # Continue with original upload logic
        upload_id = str(uuid_lib.uuid4())
        
        file_ext = os.path.splitext(file.filename)[-1].lower() if file.filename else ".tmp"
        if not file_ext:
            file_ext = ".tmp"
            
        with NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        # Extract text using our multi-format loader
        documents = load_file_to_documents(tmp_path, file.filename)
        
        # Use intelligent structure-aware chunking
        structured_chunks = split_by_structure(documents)
        
        # Store upload metadata in database
        store_upload_metadata(upload_id, file.filename, len(structured_chunks), db)
        
        # Store temporary chunks for background processing
        store_temp_chunks(upload_id, structured_chunks, db)
        
        # Launch background processing task
        celery_app.send_task("tasks.process_chunks", args=[upload_id])
        
        # Generate preview chunks
        preview_chunks = []
        for i, chunk in enumerate(structured_chunks[:3]):
            try:
                summary, questions, confidence = get_summary_and_questions(chunk.page_content)
                preview_chunks.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": chunk.page_content[:300] + ("..." if len(chunk.page_content) > 300 else ""),
                    "summary": summary,
                    "socratic_questions": questions,
                    "filename": file.filename,
                    "page_number": chunk.metadata.get("page", i + 1),
                    "confidence": confidence
                })
            except Exception as e:
                print(f"Error generating preview for chunk {i}: {e}")
                preview_chunks.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": chunk.page_content[:300] + ("..." if len(chunk.page_content) > 300 else ""),
                    "summary": "Preview generation in progress...",
                    "socratic_questions": ["Preview questions will be available shortly..."],
                    "filename": file.filename,
                    "page_number": chunk.metadata.get("page", i + 1),
                    "confidence": 0.5
                })
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return {
            "upload_id": upload_id,
            "status": "PROCESSING",
            "message": f"Successfully verified blockchain transaction and initiated processing of {file.filename}",
            "transaction_signature": transaction_signature,
            "total_chunks": len(structured_chunks),
            "estimated_time": estimate_time_for_processing(len(structured_chunks)),
            "preview_chunks": preview_chunks,
            "file_type": file_ext.upper().replace(".", ""),
            "blockchain_verified": True,
            "supported_operations": [
                "Text extraction",
                "Intelligent chunking", 
                "Socratic question generation",
                "Vector embedding",
                "Semantic search"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'tmp_path' in locals():
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")

@app.post("/prepare-purchase-tokens-transaction", response_model=UnsignedTransactionResponse)
async def prepare_purchase_tokens_transaction(
    request: PurchaseTokensBlockchainRequest,
    db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for purchase_tokens instruction"""
    try:
        transaction, accounts_to_sign = await transaction_builder.build_purchase_tokens_transaction(
            user_public_key=request.user_public_key,
            sol_amount=request.sol_amount
        )

        encoded_tx = base64.b64encode(transaction.serialize()).decode('utf-8')
        return UnsignedTransactionResponse(
            unsigned_transaction=encoded_tx,
            accounts_to_sign=[str(acc) for acc in accounts_to_sign],
            transaction_message="Purchase tokens transaction",
            expires_at=get_expiration_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare purchase tokens transaction: {e}")


@app.post("/prepare-share-document-transaction", response_model=UnsignedTransactionResponse)
async def prepare_share_document_transaction(
    request: ShareDocumentBlockchainRequest,
    db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for share_document instruction"""
    try:
        transaction, accounts_to_sign = await transaction_builder.build_share_document_transaction(
            user_public_key=request.user_public_key,
            document_index=request.document_index,
            new_access_level=request.new_access_level
        )

        encoded_tx = base64.b64encode(transaction.serialize()).decode('utf-8')
        return UnsignedTransactionResponse(
            unsigned_transaction=encoded_tx,
            accounts_to_sign=[str(acc) for acc in accounts_to_sign],
            transaction_message="Share document transaction",
            expires_at=get_expiration_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare share document transaction: {e}")


@app.post("/chat/prepare", response_model=UnsignedTransactionResponse)
async def prepare_chat_query_transaction(
    request: ChatQueryBlockchainRequest,
    db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for chat query"""
    try:
        # Build unsigned transaction
        transaction, signers = await transaction_builder.build_chat_query_transaction(
            request.user_public_key,
            request.query_text,
            request.query_index
        )
        
        # Serialize transaction
        serialized_tx = base64.b64encode(transaction.serialize()).decode('utf-8')
        
        return UnsignedTransactionResponse(
            unsigned_transaction=serialized_tx,
            accounts_to_sign=[str(signer) for signer in signers],
            transaction_message=f"Chat query: {request.query_text[:50]}...",
            expires_at=get_expiration_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare transaction: {str(e)}")

@app.post("/chat/verify")
async def verify_and_process_chat(
    transaction_signature: str,
    message: str,
    query_text: str,
    query_index: int,
    user_public_key: str,
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Verify transaction and process chat query"""
    try:
        # Verify the transaction
        expected_data = {
            "query_text": query_text,
            "query_index": query_index
        }
        
        is_verified = await transaction_verifier.verify_transaction_with_retry(
            transaction_signature,
            "chat_query",
            expected_data
        )
        
        if not is_verified:
            raise HTTPException(status_code=400, detail="Transaction verification failed")
        
        # Continue with original chat logic
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="pdf_chunks",
        )
        
        # Search for relevant context
        relevant_docs = vectorstore.similarity_search(message, k=3)
        
        # Prepare context
        context = ""
        sources = []
        if relevant_docs:
            context = "\n\nRelevant context from uploaded documents:\n"
            for i, doc in enumerate(relevant_docs, 1):
                context += f"{i}. {doc.page_content[:500]}...\n"
                sources.append(f"Document chunk {i}")
        
        llm = ChatOpenAI(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        prompt = f"""You are a helpful AI assistant with access to uploaded document content. 
        Answer the user's question using the provided context when relevant. 
        If the context doesn't contain relevant information, provide a general helpful response.
        
        User Question: {message}
        {context}
        
        Please provide a clear, helpful response. If you used information from the uploaded documents, 
        mention that you're referencing the uploaded content."""
        
        # Get response from LLM
        response = await llm.ainvoke(prompt)
        
        # Generate conversation ID if not provided
        conversation_id = conversation_id or str(uuid_lib.uuid4())
        
        return {
            "response": response.content,
            "conversation_id": conversation_id,
            "sources": sources,
            "transaction_signature": transaction_signature,
            "blockchain_verified": True,
            "query_index": query_index
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

# Keep all the original utility functions and endpoints
@app.post("/login")
async def login(data: LoginData):
    public_key = data.publicKey
    signature = data.signature
    message = "Login to DocChatApp"
    try:
        pubkey_bytes = PublicKey(public_key).to_bytes()
        signature_bytes = base64.b64decode(signature)
        message_bytes = message.encode()

        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(message_bytes, signature_bytes)
        return {"token": "your_jwt_token_here"}
    except Exception as e:
        print(f"Verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in connected_clients:
                await client.send_text(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "PDF Socratic LLM Processor with Solana integration is running"}

# Keep all original utility functions
def load_file_to_documents(file_path: str, filename: str) -> List[Document]:
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".pdf":
        return load_pdf_with_pymupdf(file_path, filename)
    elif ext in [".csv", ".xlsx", ".xls"]:
        return load_spreadsheet(file_path, filename)
    elif ext == ".md":
        return load_markdown(file_path, filename)
    else:
        raise ValueError("Unsupported file format")

def load_pdf_with_pymupdf(file_path: str, filename: str) -> List[Document]:
    doc = fitz.open(file_path)
    documents = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if not text.strip():
            continue
        metadata = {"source": filename, "page": i + 1}
        documents.append(Document(page_content=text, metadata=metadata))
    return documents

def load_spreadsheet(file_path: str, filename: str) -> List[Document]:
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Error loading spreadsheet: {e}")

    content = df.to_string(index=False)
    return [Document(page_content=content, metadata={"source": filename})]

def load_markdown(file_path: str, filename: str) -> List[Document]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise ValueError(f"Error reading markdown file: {e}")
    return [Document(page_content=content, metadata={"source": filename})]

def validate_file_type(file: UploadFile):
    file_content = file.file.read(2048)
    file.file.seek(0)
    
    mime_type = magic.from_buffer(file_content, mime=True)
    
    allowed_types = [
        'application/pdf',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/markdown',
        'text/plain'
    ]
    
    if file.filename:
        file_ext = os.path.splitext(file.filename)[-1].lower()
        if file_ext in ['.md', '.markdown'] and mime_type in ['text/plain', 'text/markdown']:
            return
        elif file_ext in ['.csv'] and mime_type in ['text/plain', 'text/csv']:
            return
        elif file_ext in ['.xlsx', '.xls'] and 'spreadsheet' in mime_type.lower():
            return
        elif file_ext == '.pdf' and mime_type == 'application/pdf':
            return
    
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Detected MIME type: {mime_type}. Supported types: PDF, CSV, Excel (.xlsx/.xls), Markdown (.md)"
        )

def split_by_structure(documents: List[Document]) -> List[Document]:
    text = "\n".join([doc.page_content for doc in documents])
    if text.count("CHAPTER") > 2 or "Table of Contents" in text:
        return split_into_chapters(text)
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000, chunk_overlap=200)
        return splitter.split_documents(documents)

def split_into_chapters(text: str) -> List[Document]:
    chapter_regex = re.compile(
        r"(CHAPTER\s+\d+|Chapter\s+[A-Z][a-z]+)", re.IGNORECASE)
    parts = chapter_regex.split(text)

    documents = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        full_text = f"{title}\n\n{content}"
        documents.append(Document(page_content=full_text,
                         metadata={"section": title}))

    return documents

def store_temp_chunks(upload_id: str, chunks: List[Document], db: Session):
    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
    for idx, doc in enumerate(chunks):
        chunk_uuid = uuid_lib.uuid4()
        temp = TempChunks(
            upload_id=upload_uuid,
            chunk_id=chunk_uuid,
            chunk_index=idx,
            text_=doc.page_content,
            page_number=doc.metadata.get("page", idx + 1),
            section=doc.metadata.get("section", "")
        )
        db.add(temp)
    db.commit()

def store_upload_metadata(upload_id: str, filename: str, total_chunks: int, db: Session):
    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
    upload = PdfUploads(
        id=upload_uuid,
        filename=filename,
        total_chunks=total_chunks,
        status="PROCESSING"
    )
    db.add(upload)
    db.commit()

def estimate_time_for_processing(chunk_count: int) -> str:
    estimate_seconds = chunk_count * 3
    if estimate_seconds < 60:
        return f"{estimate_seconds} seconds"
    elif estimate_seconds < 3600:
        minutes = estimate_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = estimate_seconds // 3600
        minutes = (estimate_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

@app.post("/login")
async def login(data: LoginData):
    public_key = data.publicKey
    signature = data.signature
    message = "Login to DocChatApp"
    try:
        # Convert the public key string to a PublicKey object and then to bytes
        pubkey_bytes = PublicKey(public_key).to_bytes()
        signature_bytes = base64.b64decode(signature)
        message_bytes = message.encode()

        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(message_bytes, signature_bytes)
        return {"token": "your_jwt_token_here"}  # TODO: Need proper JWT Generation
    except Exception as e:
        print(f"Verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in connected_clients:
                await client.send_text(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)



class ChunkResponse(BaseModel):
    chunk_id: str
    text_snippet: str
    summary: str
    socratic_questions: List[str]
    page_number: Optional[int]
    filename: Optional[str]
    confidence: Optional[float]


# class ChatRequest(BaseModel):
#     message: str
#     conversation_id: str = None


# class ChatResponse(BaseModel):
#     response: str
#     conversation_id: str
#     sources: List[str] = []


# Solana transaction verification functions
async def verify_upload_transaction(
    tx_signature: str,
    expected_pdf_hash: str,
    expected_access_level: int,
    expected_document_index: int,
    user_public_key: str,
) -> bool:
    client = AsyncClient("https://api.devnet.solana.com")
    tx = await client.get_transaction(tx_signature)
    if tx["result"] is None:
        return False

    message = tx["result"]["transaction"]["message"]
    instructions = message["instructions"]
    ix = instructions[0]  # Assuming single instruction
    program_id_index = ix["programIdIndex"]
    program_id = message["accountKeys"][program_id_index]

    if program_id != str(PROGRAM_ID):
        return False

    ix_data = base64.b64decode(ix["data"])
    coder = InstructionCoder(idl)
    decoded_ix = coder.decode(ix_data)

    if decoded_ix is None or decoded_ix.name != "uploadDocument":
        return False

    args = decoded_ix.data
    if (
        args.pdf_hash == expected_pdf_hash
        and args.access_level == expected_access_level
        and args.document_index == expected_document_index
    ):
        signers = message["accountKeys"][
            : len(tx["result"]["transaction"]["signatures"])
        ]
        return user_public_key in signers
    return False


@app.post("/upload_doc/", response_model=dict)
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    validate_file_type(file)
    print("validated")
    upload_id = str(uuid_lib.uuid4())
    print("upload_id", upload_id)
    try:
        file_ext = (
            os.path.splitext(file.filename)[-1].lower() if file.filename else ".tmp"
        )
        if not file_ext:
            file_ext = ".tmp"

        with NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    try:
        # Extract text using our multi-format loader
        documents = load_file_to_documents(tmp_path, file.filename)
        print("documents", documents)
        # Use intelligent structure-aware chunking
        structured_chunks = split_by_structure(documents)
        print("structured_chunks", structured_chunks)
        # Store upload metadata in database
        store_upload_metadata(upload_id, file.filename, len(structured_chunks), db)
        print("stored_upload_metadata")
        # Store temporary chunks for background processing
        store_temp_chunks(upload_id, structured_chunks, db)
        print("stored_temp_chunks")
        # Launch background processing task
        celery_app.send_task("tasks.process_chunks", args=[upload_id])
        print("launched_task")

        # Generate preview chunks with real summaries and questions
        preview_chunks = []
        for i, chunk in enumerate(structured_chunks[:3]):
            try:
                # Generate real summary and questions for preview
                summary, questions, confidence = get_summary_and_questions(
                    chunk.page_content
                )
                preview_chunks.append(
                    {
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.page_content[:300]
                        + ("..." if len(chunk.page_content) > 300 else ""),
                        "summary": summary,
                        "socratic_questions": questions,
                        "filename": file.filename,
                        "page_number": chunk.metadata.get("page", i + 1),
                        "confidence": confidence,
                    }
                )
            except Exception as e:
                print(f"Error generating preview for chunk {i}: {e}")
                # Fallback to placeholder if generation fails
                preview_chunks.append(
                    {
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.page_content[:300]
                        + ("..." if len(chunk.page_content) > 300 else ""),
                        "summary": "Preview generation in progress...",
                        "socratic_questions": [
                            "Preview questions will be available shortly..."
                        ],
                        "filename": file.filename,
                        "page_number": chunk.metadata.get("page", i + 1),
                        "confidence": 0.5,
                    }
                )

        # Clean up temp file
        os.unlink(tmp_path)

        return {
            "upload_id": upload_id,
            "status": "PROCESSING",
            "message": f"Successfully initiated processing of {file.filename}",
            "total_chunks": len(structured_chunks),
            "estimated_time": estimate_time_for_processing(len(structured_chunks)),
            "preview_chunks": preview_chunks,
            "file_type": file_ext.upper().replace(".", ""),
            "supported_operations": [
                "Text extraction",
                "Intelligent chunking",
                "Socratic question generation",
                "Vector embedding",
                "Semantic search",
            ],
        }

    except Exception as e:
        # Clean up on error
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


def estimate_time_for_processing(chunk_count: int) -> str:
    """Estimate processing time based on chunk count"""
    estimate_seconds = chunk_count * 3  # Assume 3 seconds per chunk
    if estimate_seconds < 60:
        return f"{estimate_seconds} seconds"
    elif estimate_seconds < 3600:
        minutes = estimate_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = estimate_seconds // 3600
        minutes = (estimate_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


@app.post("/upload_doc/abort/{upload_id}")
def abort_upload(upload_id: str, db: Session = Depends(get_db)):
    try:
        upload_uuid = uuid_lib.UUID(upload_id)
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    upload.status = "ABORTED"
    db.commit()
    return {"message": "Upload aborted"}


@app.post("/chat/", response_model=ChatResponse)
async def chat_with_context(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat endpoint that uses the vector store to provide context-aware responses
    based on uploaded PDFs.
    """
    try:
        # Setup embeddings for similarity search
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="pdf_chunks",
        )

        # Search for relevant context from uploaded PDFs
        relevant_docs = vectorstore.similarity_search(
            request.message, k=3  # Get top 3 most relevant chunks
        )

        # Prepare context from relevant documents
        context = ""
        sources = []
        if relevant_docs:
            context = "\n\nRelevant context from uploaded documents:\n"
            for i, doc in enumerate(relevant_docs, 1):
                context += f"{i}. {doc.page_content[:500]}...\n"
                sources.append(f"Document chunk {i}")

        llm = ChatOpenAI(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
        )

        # Create a comprehensive prompt
        prompt = f"""You are a helpful AI assistant with access to uploaded document content. 
        Answer the user's question using the provided context when relevant. 
        If the context doesn't contain relevant information, provide a general helpful response.
        
        User Question: {request.message}
        {context}
        
        Please provide a clear, helpful response. If you used information from the uploaded documents, 
        mention that you're referencing the uploaded content."""

        # Get response from LLM
        response = await llm.ainvoke(prompt)

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid_lib.uuid4())

        return ChatResponse(
            response=response.content, conversation_id=conversation_id, sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "message": "PDF Socratic LLM Processor is running"}


def load_file_to_documents(file_path: str, filename: str) -> List[Document]:
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".pdf":
        return load_pdf_with_pymupdf(file_path, filename)
    elif ext in [".csv", ".xlsx", ".xls"]:
        return load_spreadsheet(file_path, filename)
    elif ext == ".md":
        return load_markdown(file_path, filename)
    else:
        raise ValueError("Unsupported file format")


def load_pdf_with_pymupdf(file_path: str, filename: str) -> List[Document]:
    doc = fitz.open(file_path)
    documents = []
    for i, page in enumerate(doc):
        text = page.get_text("text")  # gets text even from OCR-scanned PDFs
        if not text.strip():
            continue
        metadata = {"source": filename, "page": i + 1}
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def load_spreadsheet(file_path: str, filename: str) -> List[Document]:
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError(f"Error loading spreadsheet: {e}")

    content = df.to_string(index=False)
    return [Document(page_content=content, metadata={"source": filename})]


def load_markdown(file_path: str, filename: str) -> List[Document]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise ValueError(f"Error reading markdown file: {e}")
    return [Document(page_content=content, metadata={"source": filename})]


def validate_file_type(file: UploadFile):
    # Read a sample of the file to determine MIME type
    file_content = file.file.read(2048)
    file.file.seek(0)  # Reset file pointer

    mime_type = magic.from_buffer(file_content, mime=True)

    allowed_types = [
        "application/pdf",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "text/markdown",
        "text/plain",  # for .md files that might be detected as plain text
    ]

    # Additional check for file extension if MIME type is not conclusive
    if file.filename:
        file_ext = os.path.splitext(file.filename)[-1].lower()
        if file_ext in [".md", ".markdown"] and mime_type in [
            "text/plain",
            "text/markdown",
        ]:
            return  # Allow markdown files
        elif file_ext in [".csv"] and mime_type in ["text/plain", "text/csv"]:
            return  # Allow CSV files
        elif file_ext in [".xlsx", ".xls"] and "spreadsheet" in mime_type.lower():
            return  # Allow Excel files
        elif file_ext == ".pdf" and mime_type == "application/pdf":
            return  # Allow PDF files

    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Detected MIME type: {mime_type}. Supported types: PDF, CSV, Excel (.xlsx/.xls), Markdown (.md)",
        )


def split_by_structure(documents: List[Document]) -> List[Document]:
    text = "\n".join([doc.page_content for doc in documents])
    if text.count("CHAPTER") > 2 or "Table of Contents" in text:
        return split_into_chapters(text)
    else:
        splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
        return splitter.split_documents(documents)


def split_into_chapters(text: str) -> List[Document]:
    # Look for patterns like "CHAPTER 1", "Chapter One", etc.
    chapter_regex = re.compile(r"(CHAPTER\s+\d+|Chapter\s+[A-Z][a-z]+)", re.IGNORECASE)
    parts = chapter_regex.split(text)

    documents = []
    for i in range(1, len(parts), 2):  # Skip the first non-matching part
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        full_text = f"{title}\n\n{content}"
        documents.append(Document(page_content=full_text, metadata={"section": title}))

    return documents


def store_temp_chunks(upload_id: str, chunks: List[Document], db: Session):
    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
    print("----")
    print("upload_uuid", upload_uuid)
    for idx, doc in enumerate(chunks):
        chunk_uuid = uuid_lib.uuid4()
        temp = TempChunks(
            upload_id=upload_uuid,
            chunk_id=chunk_uuid,
            chunk_index=idx,
            text_=doc.page_content,
            page_number=doc.metadata.get("page", idx + 1),
            section=doc.metadata.get("section", ""),
        )
        db.add(temp)
    db.commit()


def store_upload_metadata(
    upload_id: str, filename: str, total_chunks: int, db: Session
):
    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
    upload = PdfUploads(
        id=upload_uuid,
        filename=filename,
        total_chunks=total_chunks,
        status="PROCESSING",
    )
    db.add(upload)
    db.commit()


def estimate_time(upload) -> str:
    remaining = upload.total_chunks - upload.processed_chunks
    estimate = remaining * 3  # assume 3 sec per chunk
    if estimate < 60:
        return f"{estimate} seconds"
    else:
        return f"{estimate // 60}–{(estimate + 59) // 60} mins"


def get_summary_and_questions(text: str) -> Tuple[str, List[str], float]:
    """
    Generate a summary and Socratic questions for a given text chunk.
    Returns a tuple of (summary, questions_list, confidence_score)
    """
    try:
        # Limit text length to avoid token limits
        text_snippet = text[:2000] if len(text) > 2000 else text

        prompt = (
            f"Analyze this text and provide:\n\n"
            f"Text: {text_snippet}\n\n"
            f"Format your response exactly as follows:\n"
            f"SUMMARY: [One clear sentence summarizing the main point]\n"
            f"QUESTION 1: [First Socratic question]\n"
            f"QUESTION 2: [Second Socratic question]\n"
            f"QUESTION 3: [Third Socratic question (optional)]\n\n"
            f"Make the questions thought-provoking and open-ended to encourage deeper thinking."
        )

        llm = ChatOpenAI(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            timeout=30,  # Add timeout to prevent hanging
        )

        response = llm.invoke(prompt).content.strip()

        # Parse the structured response
        summary = ""
        questions = []
        confidence = 0.8

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("QUESTION"):
                question_text = line.split(":", 1)[-1].strip()
                if (
                    question_text
                    and not question_text.startswith("[")
                    and not question_text.endswith("]")
                ):
                    questions.append(question_text)

        # Fallback parsing if structured format wasn't followed
        if not summary or not questions:
            response_lines = [
                line.strip() for line in response.split("\n") if line.strip()
            ]
            if response_lines:
                summary = summary or response_lines[0]
                # Extract questions from remaining lines
                for line in response_lines[1:]:
                    if (
                        "?" in line
                        and len(line) > 10
                        and not line.lower().startswith("summary")
                        and not line.startswith("QUESTION")
                    ):
                        clean_question = line.strip("- •").strip()
                        if clean_question:
                            questions.append(clean_question)

        # Ensure we have reasonable output
        if not summary:
            summary = f"This text discusses {text_snippet[:100]}..."
            confidence = 0.3

        if not questions:
            questions = [
                "What are the key implications of this content?",
                "How might this information be applied in practice?",
                "What questions does this text raise for further exploration?",
            ]
            confidence = min(confidence, 0.4)

        # Limit to 3 questions max
        questions = questions[:3]

        return summary, questions, confidence

    except Exception as e:
        print(f"Error in get_summary_and_questions: {e}")
        # Return fallback values
        fallback_summary = f"Analysis of text content ({len(text)} characters)"
        fallback_questions = [
            "What are the main concepts presented in this text?",
            "How does this information relate to broader themes?",
            "What implications or applications can be drawn from this content?",
        ]
        return fallback_summary, fallback_questions, 0.2


@app.get("/upload_status/{upload_id}")
def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    """Get the current processing status of an upload with comprehensive information"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id)
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        print("upload", upload)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Calculate progress percentage
    progress = 0
    if upload.total_chunks > 0:
        progress = int((upload.processed_chunks / upload.total_chunks) * 100)

    # Determine processing stage and message
    processing_stage = "Initializing..."
    detailed_message = (
        f"Processed {upload.processed_chunks} of {upload.total_chunks} chunks"
    )

    if upload.status == "PROCESSING":
        if progress < 10:
            processing_stage = "Extracting text and creating chunks..."
        elif progress < 50:
            processing_stage = "Generating summaries and Socratic questions..."
        elif progress < 90:
            processing_stage = "Creating embeddings and storing results..."
        else:
            processing_stage = "Finalizing processing..."
    elif upload.status == "COMPLETED":
        processing_stage = "Processing complete!"
        detailed_message = f"Successfully processed all {upload.total_chunks} chunks"
    elif upload.status == "FAILED":
        processing_stage = "Processing failed"
        detailed_message = f"Processing failed at chunk {upload.processed_chunks} of {upload.total_chunks}"
    elif upload.status == "ABORTED":
        processing_stage = "Processing aborted"
        detailed_message = f"Processing was aborted at chunk {upload.processed_chunks} of {upload.total_chunks}"

    # Calculate estimated time remaining
    estimated_time_remaining = "N/A"
    if upload.status == "PROCESSING" and upload.total_chunks > upload.processed_chunks:
        remaining_chunks = upload.total_chunks - upload.processed_chunks
        estimated_seconds = remaining_chunks * 3  # 3 seconds per chunk estimate
        if estimated_seconds < 60:
            estimated_time_remaining = f"{estimated_seconds} seconds"
        elif estimated_seconds < 3600:
            minutes = estimated_seconds // 60
            estimated_time_remaining = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = estimated_seconds // 3600
            minutes = (estimated_seconds % 3600) // 60
            estimated_time_remaining = f"{hours}h {minutes}m"

    return {
        "upload_id": upload_id,
        "status": upload.status,
        "progress": progress,
        "message": detailed_message,
        "processing_stage": processing_stage,
        "processed_chunks": upload.processed_chunks,
        "total_chunks": upload.total_chunks,
        "estimated_time_remaining": estimated_time_remaining,
        "filename": upload.filename,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "error_log": upload.error_log,
    }


@app.get("/preview_chunks/{upload_id}")
def get_preview_chunks(upload_id: str, db: Session = Depends(get_db)):
    """Get preview chunks with real-time summary and question generation for an upload"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id)

        # Get upload info
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Get first 3 temp chunks for preview
        temp_chunks = (
            db.query(TempChunks)
            .filter(TempChunks.upload_id == upload_uuid)
            .order_by(TempChunks.chunk_index)
            .limit(3)
            .all()
        )

        preview_chunks = []
        for i, chunk in enumerate(temp_chunks):
            try:
                # Generate real-time summary and questions
                summary, questions, confidence = get_summary_and_questions(chunk.text_)
                preview_chunks.append(
                    {
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.text_[:300]
                        + ("..." if len(chunk.text_) > 300 else ""),
                        "summary": summary,
                        "socratic_questions": questions,
                        "filename": upload.filename,
                        "page_number": chunk.page_number or (i + 1),
                        "confidence": confidence,
                    }
                )
            except Exception as e:
                print(f"Error generating preview for chunk {i}: {e}")
                # Fallback preview
                preview_chunks.append(
                    {
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.text_[:300]
                        + ("..." if len(chunk.text_) > 300 else ""),
                        "summary": "Preview generation in progress...",
                        "socratic_questions": [
                            "Preview questions will be available shortly..."
                        ],
                        "filename": upload.filename,
                        "page_number": chunk.page_number or (i + 1),
                        "confidence": 0.5,
                    }
                )

        return {
            "upload_id": upload_id,
            "status": upload.status,
            "preview_chunks": preview_chunks,
            "total_available": len(temp_chunks),
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving preview chunks: {str(e)}"
        )


@app.get("/final_chunks/{upload_id}")
def get_final_chunks(upload_id: str, db: Session = Depends(get_db)):
    """Get the final processed chunks for an upload"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id)

        # Get upload info
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Get final chunks
        final_chunks = (
            db.query(FinalChunks)
            .filter(FinalChunks.upload_id == str(upload_uuid))
            .all()
        )

        chunks_response = []
        for chunk in final_chunks:
            # Ensure socratic_questions is always a list
            questions = chunk.socratic_questions
            if isinstance(questions, str):
                # If it's a string, try to parse it or split it
                try:
                    import json

                    questions = json.loads(questions)
                except:
                    questions = [q.strip() for q in questions.split("\n") if q.strip()]
            elif not isinstance(questions, list):
                questions = []

            chunks_response.append(
                {
                    "chunk_id": str(chunk.id),
                    "text_snippet": chunk.text_snippet,
                    "summary": chunk.summary or "Summary not available",
                    "socratic_questions": questions,
                    "filename": upload.filename,
                    "page_number": chunk.page_number or 1,
                    "confidence": chunk.confidence or 0.8,
                }
            )

        return {
            "upload_id": upload_id,
            "status": upload.status,
            "chunks": chunks_response,
            "total_chunks": len(chunks_response),
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving chunks: {str(e)}"
        )


@app.get("/chunks/{upload_id}")
def get_chunks(
    upload_id: str, include_preview: bool = True, db: Session = Depends(get_db)
):
    """
    Unified endpoint to get chunks for an upload.
    Returns preview chunks for processing uploads, final chunks for completed uploads.
    """
    try:
        upload_uuid = uuid_lib.UUID(upload_id)

        # Get upload info
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        chunks_response = []
        total_chunks = 0

        if upload.status == "COMPLETED":
            # Get final processed chunks
            final_chunks = (
                db.query(FinalChunks)
                .filter(FinalChunks.upload_id == str(upload_uuid))
                .all()
            )

            for chunk in final_chunks:
                # Ensure socratic_questions is always a list
                questions = chunk.socratic_questions
                if isinstance(questions, str):
                    try:
                        import json

                        questions = json.loads(questions)
                    except:
                        questions = [
                            q.strip() for q in questions.split("\n") if q.strip()
                        ]
                elif not isinstance(questions, list):
                    questions = []

                chunks_response.append(
                    {
                        "chunk_id": str(chunk.id),
                        "text_snippet": chunk.text_snippet,
                        "summary": chunk.summary or "Summary not available",
                        "socratic_questions": questions,
                        "filename": upload.filename,
                        "page_number": chunk.page_number or 1,
                        "confidence": chunk.confidence or 0.8,
                        "type": "final",
                    }
                )

            total_chunks = len(final_chunks)

        elif upload.status in ["PROCESSING", "PENDING"] and include_preview:
            # Get preview chunks from temp data
            temp_chunks = (
                db.query(TempChunks)
                .filter(TempChunks.upload_id == upload_uuid)
                .order_by(TempChunks.chunk_index)
                .limit(5)
                .all()
            )  # Show up to 5 preview chunks

            for i, chunk in enumerate(temp_chunks):
                try:
                    # Generate real-time summary and questions for preview
                    summary, questions, confidence = get_summary_and_questions(
                        chunk.text_
                    )
                    chunks_response.append(
                        {
                            "chunk_id": f"preview_{upload_id}_{i}",
                            "text_snippet": chunk.text_[:300]
                            + ("..." if len(chunk.text_) > 300 else ""),
                            "summary": summary,
                            "socratic_questions": questions,
                            "filename": upload.filename,
                            "page_number": chunk.page_number or (i + 1),
                            "confidence": confidence,
                            "type": "preview",
                        }
                    )
                except Exception as e:
                    print(f"Error generating preview for chunk {i}: {e}")
                    # Fallback preview
                    chunks_response.append(
                        {
                            "chunk_id": f"preview_{upload_id}_{i}",
                            "text_snippet": chunk.text_[:300]
                            + ("..." if len(chunk.text_) > 300 else ""),
                            "summary": "Preview generation in progress...",
                            "socratic_questions": [
                                "Preview questions will be available shortly..."
                            ],
                            "filename": upload.filename,
                            "page_number": chunk.page_number or (i + 1),
                            "confidence": 0.5,
                            "type": "preview",
                        }
                    )

            total_chunks = len(temp_chunks)

        # Calculate progress for additional context
        progress = 0
        if upload.total_chunks > 0:
            progress = int((upload.processed_chunks / upload.total_chunks) * 100)

        return {
            "upload_id": upload_id,
            "status": upload.status,
            "chunks": chunks_response,
            "total_chunks": total_chunks,
            "total_expected": upload.total_chunks,
            "processed_chunks": upload.processed_chunks,
            "progress": progress,
            "filename": upload.filename,
            "chunk_type": "final" if upload.status == "COMPLETED" else "preview",
            "has_more": upload.status == "PROCESSING"
            and len(chunks_response) < upload.total_chunks,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving chunks: {str(e)}"
        )


@app.post("/debug/process_chunks/{upload_id}")
def debug_process_chunks(upload_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to manually trigger process_chunks task"""
    try:
        # Verify upload exists
        upload_uuid = uuid_lib.UUID(upload_id)
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Try to send the task
        task = celery_app.send_task("tasks.process_chunks", args=[upload_id])

        return {
            "message": "Task sent successfully",
            "task_id": task.id,
            "upload_id": upload_id,
            "upload_status": upload.status,
            "celery_broker": os.getenv("CELERY_BROKER_URL"),
            "celery_backend": os.getenv("CELERY_RESULT_BACKEND"),
        }
    except Exception as e:
        return {
            "error": str(e),
            "upload_id": upload_id,
            "celery_broker": os.getenv("CELERY_BROKER_URL"),
            "celery_backend": os.getenv("CELERY_RESULT_BACKEND"),
        }
