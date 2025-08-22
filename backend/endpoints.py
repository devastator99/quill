import base64
import base58  # Added missing import
import json
import logging
import os
import uuid as uuid_lib
from collections import defaultdict
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import asyncio
import jwt
import nacl.signing
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, HttpUrl
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import NoResultFound

from solathon import PublicKey, Transaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom exceptions
class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass

class ProcessingError(Exception):
    """Raised when document processing fails."""
    pass

class NotFoundError(Exception):
    """Raised when a requested resource is not found."""
    pass

from config import DATABASE_URL, OPENAI_API_KEY, OPENAI_API_BASE
from database import get_db
from schema import (
    LoginData,
    UnsignedTransactionResponse,
    UploadDocBlockchainRequest,
    PurchaseTokensBlockchainRequest,
    ShareDocumentBlockchainRequest,
    ChatQueryBlockchainRequest,
)
from models import (
    PdfUploads,
    TempChunks,
    FinalChunks,
)
from tasks import celery_app
from solana_utils import transaction_builder, transaction_verifier
from utils import (
    generate_pdf_hash,
    get_expiration_timestamp,
    load_file_to_documents,
    validate_file_type,
    split_by_structure,
    store_upload_metadata,
    store_temp_chunks,
    estimate_time_for_processing,
)
from utils import get_summary_and_questions

# Assuming celery_app is imported from a tasks module
# from tasks import celery_app
# For now, I'll comment it out as tasks.py is not yet refactored.
# You will need to uncomment and adjust this import once tasks.py is available.


class WebSocketManager:
    def __init__(self):
        self.clients = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        async with self.lock:
            self.clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.clients.discard(websocket)

    async def broadcast(self, message: str):
        async with self.lock:
            for client in self.clients:
                await client.send_text(message)


ws_manager = WebSocketManager()

router = APIRouter()

connected_clients: List[WebSocket] = (
    []
)  # This needs to be managed globally or via a dependency


@router.post("/upload_doc/prepare", response_model=UnsignedTransactionResponse)
async def prepare_upload_document_transaction(
    request: UploadDocBlockchainRequest, db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for document upload"""
    try:
        # Build unsigned transaction
        transaction, signers = (
            await transaction_builder.build_upload_document_transaction(
                request.user_public_key,
                request.pdf_hash,
                request.access_level,
                request.document_index,
            )
        )

        # Serialize transaction
        serialized_tx = base64.b64encode(transaction.serialize()).decode("utf-8")

        return UnsignedTransactionResponse(
            unsigned_transaction=serialized_tx,
            accounts_to_sign=[str(signer) for signer in signers],
            transaction_message=f"Upload document with hash {request.pdf_hash[:16]}...",
            expires_at=get_expiration_timestamp(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to prepare transaction: {str(e)}"
        )


@router.post("/upload_doc/verify", response_model=dict)
async def verify_and_process_upload(
    file: UploadFile = File(...),
    transaction_signature: str = Form(None, description="Transaction signature (currently not used)"),
    pdf_hash: str = Form(None, description="PDF hash (currently not used)"),
    access_level: int = Form(None, description="Access level (currently not used)"),
    document_index: int = Form(None, description="Document index (currently not used)"),
    user_public_key: str = Form(None, description="User public key (currently not used)"),
    db: Session = Depends(get_db),
):
    """Process document upload (verification currently disabled)"""
    try:
        # Validate file type
        validate_file_type(file)
        
        # Read file content
        file_content = await file.read()
        
        # Generate actual PDF hash (verification disabled)
        # actual_hash = generate_pdf_hash(file_content)
        # if actual_hash != pdf_hash:
        #     raise HTTPException(status_code=400, detail="PDF hash mismatch")
            
        # Reset file pointer for processing
        file.file.seek(0)

        # Continue with original upload logic
        upload_id = str(uuid_lib.uuid4())

        file_ext = (
            os.path.splitext(file.filename)[-1].lower() if file.filename else ".tmp"
        )
        if not file_ext:
            file_ext = ".tmp"

        with NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                tmp.write(chunk)
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
        try:
            celery_app.send_task("tasks.process_chunks", args=[upload_id])
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Task submission failed: {str(e)}"
            )

        # Generate preview chunks
        preview_chunks = []
        for i, chunk in enumerate(structured_chunks[:3]):
            try:
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
            "message": f"Successfully initiated processing of {file.filename} (verification disabled)",
            # "transaction_signature": transaction_signature,  # Verification disabled
            "total_chunks": len(structured_chunks),
            "estimated_time": estimate_time_for_processing(len(structured_chunks)),
            "preview_chunks": preview_chunks,
            "file_type": file_ext.upper().replace(".", ""),
            "blockchain_verified": False,  # Verification disabled
            "supported_operations": [
                "Text extraction",
                "Intelligent chunking",
                "Socratic question generation",
                "Vector embedding",
                "Semantic search",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        raise HTTPException(
            status_code=500, detail=f"Error processing upload: {str(e)}"
        )


@router.post(
    "/prepare-purchase-tokens-transaction", response_model=UnsignedTransactionResponse
)
async def prepare_purchase_tokens_transaction(
    request: PurchaseTokensBlockchainRequest, db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for purchase_tokens instruction"""
    try:
        transaction, accounts_to_sign = (
            await transaction_builder.build_purchase_tokens_transaction(
                user_public_key=request.user_public_key, sol_amount=request.sol_amount
            )
        )

        encoded_tx = base64.b64encode(transaction.serialize()).decode("utf-8")
        return UnsignedTransactionResponse(
            unsigned_transaction=encoded_tx,
            accounts_to_sign=[str(acc) for acc in accounts_to_sign],
            transaction_message="Purchase tokens transaction",
            expires_at=get_expiration_timestamp(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare purchase tokens transaction: {e}",
        )


@router.post(
    "/prepare-share-document-transaction", response_model=UnsignedTransactionResponse
)
async def prepare_share_document_transaction(
    request: ShareDocumentBlockchainRequest, db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for share_document instruction"""
    try:
        transaction, accounts_to_sign = (
            await transaction_builder.build_share_document_transaction(
                user_public_key=request.user_public_key,
                document_index=request.document_index,
                new_access_level=request.new_access_level,
            )
        )

        encoded_tx = base64.b64encode(transaction.serialize()).decode("utf-8")
        return UnsignedTransactionResponse(
            unsigned_transaction=encoded_tx,
            accounts_to_sign=[str(acc) for acc in accounts_to_sign],
            transaction_message="Share document transaction",
            expires_at=get_expiration_timestamp(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to prepare share document transaction: {e}"
        )


@router.post("/chat/prepare", response_model=UnsignedTransactionResponse)
async def prepare_chat_query_transaction(
    request: ChatQueryBlockchainRequest, db: Session = Depends(get_db)
):
    """Prepare unsigned transaction for chat query"""
    try:
        # Build unsigned transaction
        transaction, signers = await transaction_builder.build_chat_query_transaction(
            request.user_public_key, request.query_text, request.query_index
        )

        # Serialize transaction
        serialized_tx = base64.b64encode(transaction.serialize()).decode("utf-8")

        return UnsignedTransactionResponse(
            unsigned_transaction=serialized_tx,
            accounts_to_sign=[str(signer) for signer in signers],
            transaction_message=f"Chat query: {request.query_text[:50]}...",
            expires_at=get_expiration_timestamp(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to prepare transaction: {str(e)}"
        )


@router.post("/chat/verify")
async def verify_and_process_chat(
    transaction_signature: str = None,
    message: str = None,
    query_text: str = None,
    query_index: int = None,
    user_public_key: str = None,
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Process chat query (verification currently disabled)"""
    try:
        # Verification is currently disabled
        # expected_data = {"query_text": query_text, "query_index": query_index}
        # is_verified = await transaction_verifier.verify_transaction_with_retry(
        #     transaction_signature, "chat_query", expected_data
        # )
        # if not is_verified:
        #     raise HTTPException(
        #         status_code=400, detail="Transaction verification failed"
        #     )

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
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
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
            # "transaction_signature": transaction_signature,  # Verification disabled
            "blockchain_verified": False,  # Verification disabled
            "query_index": query_index,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")


@router.post(
    "/login",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid signature or credentials"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
    summary="User Login",
    description="Authenticate user using Solana wallet signature and return JWT token",
)
async def login(data: LoginData) -> Dict[str, str]:
    """
    Authenticate a user using their Solana wallet signature and return a JWT token.
    
    Args:
        data (LoginData): The login request data containing public key and signature
        
    Returns:
        Dict[str, str]: A dictionary containing the JWT token
        
    Raises:
        HTTPException: If authentication fails or an error occurs
    """
    try:
        # Input validation
        if not all([data.publicKey, data.signature]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Public key and signature are required"
            )
            
        # Constants
        AUTH_MESSAGE = "Login to DocChatApp"
        TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "30"))
        SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        
        if not SECRET_KEY:
            logger.error("JWT_SECRET_KEY not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )

        # Verify signature
        try:
            pubkey_bytes = PublicKey(data.publicKey).to_bytes()
            signature_bytes = base58.b58decode(data.signature)
            message_bytes = AUTH_MESSAGE.encode()

            verify_key = nacl.signing.VerifyKey(pubkey_bytes)
            verify_key.verify(message_bytes, signature_bytes)
        except (ValueError, nacl.exceptions.BadSignatureError) as e:
            logger.warning(f"Signature verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        # Create JWT payload with additional claims
        expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": data.publicKey,
            "exp": expiration,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        # Generate JWT token with secure settings
        encoded_jwt = jwt.encode(
            to_encode,
            SECRET_KEY,
            algorithm="HS256"
        )
        
        logger.info(f"Successfully generated JWT for public key: {data.publicKey[:8]}...")
        
        return {
            "token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login"
        )


class WebSocketMessage(BaseModel):
    """WebSocket message model for chat."""
    type: str  # e.g., 'message', 'typing', 'presence'
    content: Optional[Dict[str, Any]] = None
    sender: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


@router.websocket(
    "/ws/chat",
    name="Chat WebSocket"
)
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Handle WebSocket connections for real-time chat.
    
    This endpoint manages the WebSocket connection lifecycle, including:
    - Connection establishment
    - Message broadcasting
    - Error handling
    - Connection cleanup
    
    Args:
        websocket: The WebSocket connection instance
        
    Raises:
        WebSocketDisconnect: When the client disconnects
        WebSocketException: For WebSocket protocol errors
    """
    # Accept the WebSocket connection
    await ws_manager.connect(websocket)
    client_id = id(websocket)
    logger.info(f"New WebSocket connection established: {client_id}")
    
    try:
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connection_established",
            "message": "Successfully connected to chat server",
            "client_id": str(client_id),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=300  # 5 minutes timeout
                )
                
                # Parse and validate message
                try:
                    message = json.loads(data)
                    if not isinstance(message, dict):
                        raise ValueError("Message must be a JSON object")
                    
                    # Broadcast message to all connected clients
                    await ws_manager.broadcast({
                        "type": "message",
                        "content": message.get("content", ""),
                        "sender": message.get("sender", "anonymous"),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON received: {data}")
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format",
                        "details": str(e)
                    })
                except ValueError as e:
                    logger.warning(f"Invalid message format: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid message format",
                        "details": str(e)
                    })
                
            except asyncio.TimeoutError:
                # Send ping to check if client is still alive
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Ping failed for client {client_id}: {e}")
                    break
                    
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket client disconnected: {client_id}, code: {e.code}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": "Internal server error",
                "details": str(e)
            })
        except:
            pass  # Client may have already disconnected
    finally:
        # Ensure proper cleanup
        try:
            await ws_manager.disconnect(websocket)
            logger.info(f"WebSocket connection closed for client {client_id}")
        except Exception as e:
            logger.error(f"Error during WebSocket cleanup: {str(e)}")


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "PDF Socratic LLM Processor with Solana integration is running",
    }


@router.get("/upload_status/{upload_id}")
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


@router.post("/debug/process_chunks/{upload_id}")
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


@router.get("/chunks/{upload_id}")
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


@router.get("/final_chunks/{upload_id}")
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


@router.post("/upload_doc/abort/{upload_id}")
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


@router.get("/preview_chunks/{upload_id}")
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
