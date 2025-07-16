import pytest
import base64
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import Session
from solathon import PublicKey
from solathon import Transaction
import nacl.signing
import base58
import asyncio

from main import router
from endpoints import WebSocketManager
from utils import get_summary_and_questions
from schema import (
    LoginData,
    UploadDocBlockchainRequest,
    PurchaseTokensBlockchainRequest,
    ShareDocumentBlockchainRequest,
    ChatQueryBlockchainRequest
)
from models import PdfUploads, TempChunks
from database import get_db

# Mock database dependency
@pytest.fixture
def mock_db_session():
    db = MagicMock(spec=Session)
    yield db

# Mock FastAPI app
@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    
    @app.dependency_override(get_db)
    def override_get_db():
        db = MagicMock(spec=Session)
        return db
    
    return TestClient(app)

# Async HTTP client for testing
@pytest.fixture
async def async_client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    
    @app.dependency_override(get_db)
    async def override_get_db():
        db = MagicMock(spec=Session)
        return db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Mock Solana public key and transaction
@pytest.fixture
def mock_public_key():
    return str(PublicKey(b"1" * 32))

@pytest.fixture
def mock_transaction():
    tx = Transaction()
    tx.add(MagicMock())  # Mock instruction
    return tx

# Mock WebSocket manager
@pytest.fixture
def mock_ws_manager():
    return WebSocketManager()

# Test /health endpoint
@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "PDF Socratic LLM Processor with Solana integration is running"
    }

# Test /login endpoint
@pytest.mark.asyncio
async def test_login_success(async_client, mock_public_key):
    # Generate valid signature
    signing_key = nacl.signing.SigningKey.generate()
    message = "Login to DocChatApp".encode()
    signature = signing_key.sign(message).signature
    signature_b58 = base58.b58encode(signature).decode()

    with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
        response = await async_client.post(
            "/login",
            json={"publicKey": mock_public_key, "signature": signature_b58}
        )
    
    assert response.status_code == 200
    assert "token" in response.json()

@pytest.mark.asyncio
async def test_login_invalid_signature(async_client, mock_public_key):
    response = await async_client.post(
        "/login",
        json={"publicKey": mock_public_key, "signature": "invalid-signature"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"

# Test /upload_doc/prepare endpoint
@pytest.mark.asyncio
async def test_upload_doc_prepare(async_client, mock_public_key, mock_transaction):
    request_data = UploadDocBlockchainRequest(
        user_public_key=mock_public_key,
        pdf_hash="deadbeef" * 8,
        access_level=1,
        document_index=0
    )
    
    with patch("solana_utils.transaction_builder.build_upload_document_transaction", 
              new=AsyncMock(return_value=(mock_transaction, [mock_public_key]))):
        response = await async_client.post("/upload_doc/prepare", json=request_data.dict())
    
    assert response.status_code == 200
    assert response.json()["unsigned_transaction"]
    assert response.json()["accounts_to_sign"] == [mock_public_key]
    assert "Upload document with hash" in response.json()["transaction_message"]

@pytest.mark.asyncio
async def test_upload_doc_prepare_error(async_client, mock_public_key):
    request_data = UploadDocBlockchainRequest(
        user_public_key=mock_public_key,
        pdf_hash="deadbeef" * 8,
        access_level=1,
        document_index=0
    )
    
    with patch("solana_utils.transaction_builder.build_upload_document_transaction", 
              new=AsyncMock(side_effect=Exception("Solana error"))):
        response = await async_client.post("/upload_doc/prepare", json=request_data.dict())
    
    assert response.status_code == 500
    assert "Failed to prepare transaction" in response.json()["detail"]

# Test /upload_doc/verify endpoint
@pytest.mark.asyncio
async def test_upload_doc_verify_success(async_client, mock_db_session, mock_public_key):
    # Mock file
    file_content = b"test pdf content"
    mock_file = MagicMock()
    mock_file.read = AsyncMock(return_value=file_content)
    mock_file.filename = "test.pdf"
    mock_file.seek = AsyncMock()
    
    # Mock dependencies
    with patch("utils.generate_pdf_hash", return_value="deadbeef" * 8), \
         patch("utils.validate_file_type"), \
         patch("solana_utils.transaction_verifier.verify_transaction_with_retry", 
               new=AsyncMock(return_value=True)), \
         patch("utils.load_file_to_documents", return_value=[MagicMock(page_content="test content")]), \
         patch("utils.split_by_structure", return_value=[MagicMock(page_content="test content")]), \
         patch("utils.store_upload_metadata"), \
         patch("utils.store_temp_chunks"), \
         patch("tasks.celery_app.send_task"), \
         patch("main.get_summary_and_questions", 
               return_value=("Summary", ["Q1?", "Q2?"], 0.8)):
        
        response = await async_client.post(
            "/upload_doc/verify",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            data={
                "transaction_signature": "sig",
                "pdf_hash": "deadbeef" * 8,
                "access_level": "1",
                "document_index": "0",
                "user_public_key": mock_public_key
            }
        )
    
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"
    assert len(response.json()["preview_chunks"]) <= 3

@pytest.mark.asyncio
async def test_upload_doc_verify_missing_params(async_client):
    response = await async_client.post("/upload_doc/verify", files={"file": ("test.pdf", b"content")})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required blockchain parameters"

# Test /chat/prepare endpoint
@pytest.mark.asyncio
async def test_chat_prepare(async_client, mock_public_key, mock_transaction):
    request_data = ChatQueryBlockchainRequest(
        user_public_key=mock_public_key,
        query_text="What is this?",
        query_index=0
    )
    
    with patch("solana_utils.transaction_builder.build_chat_query_transaction", 
              new=AsyncMock(return_value=(mock_transaction, [mock_public_key]))):
        response = await async_client.post("/chat/prepare", json=request_data.dict())
    
    assert response.status_code == 200
    assert response.json()["unsigned_transaction"]
    assert response.json()["accounts_to_sign"] == [mock_public_key]
    assert "Chat query" in response.json()["transaction_message"]

# Test /chat/verify endpoint
@pytest.mark.asyncio
async def test_chat_verify_success(async_client, mock_db_session, mock_public_key):
    with patch("solana_utils.transaction_verifier.verify_transaction_with_retry", 
              new=AsyncMock(return_value=True)), \
         patch("langchain_community.vectorstores.pgvector.PGVector.similarity_search", 
               return_value=[MagicMock(page_content="context")]), \
         patch("langchain_openai.ChatOpenAI.ainvoke", 
               new=AsyncMock(return_value=MagicMock(content="AI response"))):
        
        response = await async_client.post(
            "/chat/verify",
            data={
                "transaction_signature": "sig",
                "message": "What is this?",
                "query_text": "What is this?",
                "query_index": "0",
                "user_public_key": mock_public_key
            }
        )
    
    assert response.status_code == 200
    assert response.json()["response"] == "AI response"
    assert response.json()["blockchain_verified"] == True

# Test /upload_status/{upload_id} endpoint
def test_upload_status_success(client, mock_db_session):
    upload_id = str(uuid.uuid4())
    mock_upload = MagicMock()
    mock_upload.status = "PROCESSING"
    mock_upload.total_chunks = 10
    mock_upload.processed_chunks = 5
    mock_upload.filename = "test.pdf"
    mock_upload.created_at = MagicMock(isoformat=lambda: "2025-07-15T00:00:00")
    mock_upload.error_log = None
    mock_db_session.query().filter().first.return_value = mock_upload
    
    response = client.get(f"/upload_status/{upload_id}")
    
    assert response.status_code == 200
    assert response.json()["upload_id"] == upload_id
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["progress"] == 50

def test_upload_status_invalid_id(client):
    response = client.get("/upload_status/invalid-uuid")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid upload ID format"

# Test /debug/process_chunks/{upload_id} endpoint
def test_debug_process_chunks_success(client, mock_db_session):
    upload_id = str(uuid.uuid4())
    mock_upload = MagicMock(status="PENDING")
    mock_db_session.query().filter().first.return_value = mock_upload
    mock_task = MagicMock(id="task-123")
    
    with patch("tasks.celery_app.send_task", return_value=mock_task):
        response = client.post(f"/debug/process_chunks/{upload_id}")
    
    assert response.status_code == 200
    assert response.json()["task_id"] == "task-123"

# Test /chunks/{upload_id} endpoint
def test_chunks_completed(client, mock_db_session):
    upload_id = str(uuid.uuid4())
    mock_upload = MagicMock(status="COMPLETED", filename="test.pdf", total_chunks=2, processed_chunks=2)
    mock_chunk = MagicMock(id=uuid.uuid4(), text_snippet="text", summary="Summary", 
                          socratic_questions=["Q1?"], page_number=1, confidence=0.8)
    mock_db_session.query().filter().all.return_value = [mock_chunk]
    mock_db_session.query().filter().first.return_value = mock_upload
    
    response = client.get(f"/chunks/{upload_id}")
    
    assert response.status_code == 200
    assert len(response.json()["chunks"]) == 1
    assert response.json()["chunk_type"] == "final"

# Test /preview_chunks/{upload_id} endpoint
def test_preview_chunks(client, mock_db_session):
    upload_id = str(uuid.uuid4())
    mock_upload = MagicMock(status="PROCESSING", filename="test.pdf")
    mock_chunk = MagicMock(text_="test content", page_number=1)
    mock_db_session.query().filter().all.return_value = [mock_chunk]
    mock_db_session.query().filter().first.return_value = mock_upload
    
    with patch("main.get_summary_and_questions", return_value=("Summary", ["Q1?"], 0.8)):
        response = client.get(f"/preview_chunks/{upload_id}")
    
    assert response.status_code == 200
    assert len(response.json()["preview_chunks"]) == 1
    assert response.json()["preview_chunks"][0]["summary"] == "Summary"

# Test /upload_doc/abort/{upload_id} endpoint
def test_abort_upload_success(client, mock_db_session):
    upload_id = str(uuid.uuid4())
    mock_upload = MagicMock(status="PROCESSING")
    mock_db_session.query().filter().first.return_value = mock_upload
    
    response = client.post(f"/upload_doc/abort/{upload_id}")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Upload aborted"
    assert mock_upload.status == "ABORTED"

# Test WebSocket /ws/chat endpoint
@pytest.mark.asyncio
async def test_websocket_chat(async_client, mock_ws_manager):
    with patch.object(mock_ws_manager, "connect", new=AsyncMock()), \
         patch.object(mock_ws_manager, "disconnect", new=AsyncMock()), \
         patch.object(mock_ws_manager, "broadcast", new=AsyncMock()):
        
        async with async_client.websocket_connect("/ws/chat") as websocket:
            await websocket.send_text("Hello")
            await websocket.receive_text()
        
        assert mock_ws_manager.connect.called
        assert mock_ws_manager.broadcast.called

# Test get_summary_and_questions function
def test_get_summary_and_questions():
    with patch("langchain_openai.ChatOpenAI.invoke", 
              return_value=MagicMock(content="SUMMARY: Test summary\nQUESTION 1: Q1?\nQUESTION 2: Q2?")):
        summary, questions, confidence = get_summary_and_questions("test text")
    
    assert summary == "Test summary"
    assert questions == ["Q1?", "Q2?"]
    assert confidence == 0.8

def test_get_summary_and_questions_error():
    with patch("langchain_openai.ChatOpenAI.invoke", side_effect=Exception("LLM error")):
        summary, questions, confidence = get_summary_and_questions("test text")
    
    assert summary.startswith("Analysis of text content")
    assert len(questions) == 3
    assert confidence == 0.2

if __name__ == "__main__":
    pytest.main(["-v"])