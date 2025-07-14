from pydantic import BaseModel
from typing import List, Optional


class LoginData(BaseModel):
    publicKey: str
    signature: str


class UnsignedTransactionRequest(BaseModel):
    user_public_key: str
    instruction_data: dict


class UnsignedTransactionResponse(BaseModel):
    unsigned_transaction: str  # Base64 no base58 encoded transaction
    accounts_to_sign: List[str]  # Public keys that need to sign
    transaction_message: str
    expires_at: int  # Unix timestamp


class SignedTransactionRequest(BaseModel):
    signed_transaction: str  # Base64 no base58 encoded signed transaction
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
