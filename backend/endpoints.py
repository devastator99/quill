import base64
import os
import uuid as uuid_lib
from typing import List, Optional, Tuple
from tempfile import NamedTemporaryFile

import jwt
from datetime import datetime, timedelta
import nacl.signing
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session
from solana.publickey import PublicKey
from solana.transaction import Transaction
from collections import defaultdict
import asyncio
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_openai import ChatOpenAI

from config import DATABASE_URL, OPENAI_API_KEY, OPENAI_API_BASE
from database import get_db
from schema import (
    LoginData,
    UnsignedTransactionResponse,
    UploadDocBlockchainRequest,
    PurchaseTokensBlockchainRequest,
    ShareDocumentBlockchainRequest,
    ChatQueryBlockchainRequest,
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
    transaction_signature: str = None,
    pdf_hash: str = None,
    access_level: int = None,
    document_index: int = None,
    user_public_key: str = None,
    db: Session = Depends(get_db),
):
    """Verify transaction and process document upload"""
    if not all(
        [
            transaction_signature,
            pdf_hash,
            access_level is not None,
            document_index is not None,
            user_public_key,
        ]
    ):
        raise HTTPException(
            status_code=400, detail="Missing required blockchain parameters"
        )

    try:
        # Verify the transaction
        expected_data = {
            "pdf_hash": pdf_hash,
            "access_level": access_level,
            "document_index": document_index,
        }

        is_verified = await transaction_verifier.verify_transaction_with_retry(
            transaction_signature, "upload_document", expected_data
        )

        if not is_verified:
            raise HTTPException(
                status_code=400, detail="Transaction verification failed"
            )

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
    transaction_signature: str,
    message: str,
    query_text: str,
    query_index: int,
    user_public_key: str,
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Verify transaction and process chat query"""
    try:
        # Verify the transaction
        expected_data = {"query_text": query_text, "query_index": query_index}

        is_verified = await transaction_verifier.verify_transaction_with_retry(
            transaction_signature, "chat_query", expected_data
        )

        if not is_verified:
            raise HTTPException(
                status_code=400, detail="Transaction verification failed"
            )

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
            "transaction_signature": transaction_signature,
            "blockchain_verified": True,
            "query_index": query_index,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")


@router.post("/login")
async def login(data: LoginData):
    public_key = data.publicKey
    signature = data.signature
    message = "Login to DocChatApp"
    try:
        pubkey_bytes = PublicKey(public_key).to_bytes()
        signature_bytes = base58.b58decode(signature)
        message_bytes = message.encode()

        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(message_bytes, signature_bytes)

        # Define JWT secret key and algorithm (should be in config/env vars)
        SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key") # TODO: Move to config.py or environment variable
        ALGORITHM = "HS256"

        # Create JWT payload
        to_encode = {
            "sub": public_key,
            "exp": datetime.utcnow() + timedelta(minutes=30)  # Token expires in 30 minutes
        }

        # Generate JWT token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return {"token": encoded_jwt}
    except Exception as e:
        print(f"Verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature")


@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast(data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


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
