from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Depends
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
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON
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
# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize FastAPI app
app = FastAPI(title="Socratic")

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
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=10,        # Connection pool size
    max_overflow=20,     # Allow extra connections if needed
    echo=False           # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create database tables
Base.metadata.create_all(bind=engine)

connected_clients = []


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


class ChunkResponse(BaseModel):
    chunk_id: str
    text_snippet: str
    summary: str
    socratic_questions: List[str]
    page_number: Optional[int]
    filename: Optional[str]
    confidence: Optional[float]


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []


@app.post("/upload_doc/", response_model=dict)
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to upload a document, extract and chunk its text,
    and initiate background processing for embedding and Socratic question generation.
    Returns upload status and processing information.
    """
    # ✅ Check file type (using our enhanced validation)
    validate_file_type(file)
    print("validated")
    # ✅ Generate unique upload ID
    upload_id = str(uuid_lib.uuid4())
    print("upload_id", upload_id)
    # ✅ Save uploaded file temporarily with proper extension
    try:
        file_ext = os.path.splitext(file.filename)[-1].lower() if file.filename else ".tmp"
        if not file_ext:
            file_ext = ".tmp"
            
        with NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving file: {str(e)}")

    try:
        # ✅ Extract text using our multi-format loader
        documents = load_file_to_documents(tmp_path, file.filename)
        print("documents", documents)
        # ✅ Use intelligent structure-aware chunking
        structured_chunks = split_by_structure(documents)
        print("structured_chunks", structured_chunks)
        # ✅ Store upload metadata in database
        store_upload_metadata(upload_id, file.filename, len(structured_chunks), db)
        print("stored_upload_metadata")
        # ✅ Store temporary chunks for background processing
        store_temp_chunks(upload_id, structured_chunks, db)
        print("stored_temp_chunks")
        # ✅ Launch background processing task
        celery_app.send_task("tasks.process_chunks", args=[upload_id])
        print("launched_task")
        
        # ✅ Generate preview chunks with real summaries and questions
        preview_chunks = []
        for i, chunk in enumerate(structured_chunks[:3]):
            try:
                # Generate real summary and questions for preview
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
                # Fallback to placeholder if generation fails
                preview_chunks.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": chunk.page_content[:300] + ("..." if len(chunk.page_content) > 300 else ""),
                    "summary": "Preview generation in progress...",
                    "socratic_questions": ["Preview questions will be available shortly..."],
                    "filename": file.filename,
                    "page_number": chunk.metadata.get("page", i + 1),
                    "confidence": 0.5
                })

        # ✅ Clean up temp file
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
                "Semantic search"
            ]
        }
        
    except Exception as e:
        # Clean up on error
        if 'tmp_path' in locals():
            os.unlink(tmp_path)
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}")


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
            model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="pdf_chunks",
        )

        # Search for relevant context from uploaded PDFs
        relevant_docs = vectorstore.similarity_search(
            request.message,
            k=3  # Get top 3 most relevant chunks
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
            base_url=os.getenv("OPENAI_API_BASE")
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
            response=response.content,
            conversation_id=conversation_id,
            sources=sources
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
        'application/pdf',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
        'text/markdown',
        'text/plain'  # for .md files that might be detected as plain text
    ]
    
    # Additional check for file extension if MIME type is not conclusive
    if file.filename:
        file_ext = os.path.splitext(file.filename)[-1].lower()
        if file_ext in ['.md', '.markdown'] and mime_type in ['text/plain', 'text/markdown']:
            return  # Allow markdown files
        elif file_ext in ['.csv'] and mime_type in ['text/plain', 'text/csv']:
            return  # Allow CSV files
        elif file_ext in ['.xlsx', '.xls'] and 'spreadsheet' in mime_type.lower():
            return  # Allow Excel files
        elif file_ext == '.pdf' and mime_type == 'application/pdf':
            return  # Allow PDF files
    
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
    # Look for patterns like "CHAPTER 1", "Chapter One", etc.
    chapter_regex = re.compile(
        r"(CHAPTER\s+\d+|Chapter\s+[A-Z][a-z]+)", re.IGNORECASE)
    parts = chapter_regex.split(text)

    documents = []
    for i in range(1, len(parts), 2):  # Skip the first non-matching part
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        full_text = f"{title}\n\n{content}"
        documents.append(Document(page_content=full_text,
                         metadata={"section": title}))

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
            timeout=30  # Add timeout to prevent hanging
        )
        
        response = llm.invoke(prompt).content.strip()
        
        # Parse the structured response
        summary = ""
        questions = []
        confidence = 0.8
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("QUESTION"):
                question_text = line.split(":", 1)[-1].strip()
                if question_text and not question_text.startswith("[") and not question_text.endswith("]"):
                    questions.append(question_text)
        
        # Fallback parsing if structured format wasn't followed
        if not summary or not questions:
            response_lines = [line.strip() for line in response.split('\n') if line.strip()]
            if response_lines:
                summary = summary or response_lines[0]
                # Extract questions from remaining lines
                for line in response_lines[1:]:
                    if ('?' in line and len(line) > 10 and 
                        not line.lower().startswith('summary') and
                        not line.startswith('QUESTION')):
                        clean_question = line.strip('- •').strip()
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
                "What questions does this text raise for further exploration?"
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
            "What implications or applications can be drawn from this content?"
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
    detailed_message = f"Processed {upload.processed_chunks} of {upload.total_chunks} chunks"
    
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
        "error_log": upload.error_log
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
        temp_chunks = db.query(TempChunks).filter(
            TempChunks.upload_id == upload_uuid
        ).order_by(TempChunks.chunk_index).limit(3).all()
        
        preview_chunks = []
        for i, chunk in enumerate(temp_chunks):
            try:
                # Generate real-time summary and questions
                summary, questions, confidence = get_summary_and_questions(chunk.text_)
                preview_chunks.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": chunk.text_[:300] + ("..." if len(chunk.text_) > 300 else ""),
                    "summary": summary,
                    "socratic_questions": questions,
                    "filename": upload.filename,
                    "page_number": chunk.page_number or (i + 1),
                    "confidence": confidence
                })
            except Exception as e:
                print(f"Error generating preview for chunk {i}: {e}")
                # Fallback preview
                preview_chunks.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": chunk.text_[:300] + ("..." if len(chunk.text_) > 300 else ""),
                    "summary": "Preview generation in progress...",
                    "socratic_questions": ["Preview questions will be available shortly..."],
                    "filename": upload.filename,
                    "page_number": chunk.page_number or (i + 1),
                    "confidence": 0.5
                })
        
        return {
            "upload_id": upload_id,
            "status": upload.status,
            "preview_chunks": preview_chunks,
            "total_available": len(temp_chunks)
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving preview chunks: {str(e)}")


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
        final_chunks = db.query(FinalChunks).filter(FinalChunks.upload_id == str(upload_uuid)).all()
        
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
                    questions = [q.strip() for q in questions.split('\n') if q.strip()]
            elif not isinstance(questions, list):
                questions = []
            
            chunks_response.append({
                "chunk_id": str(chunk.id),
                "text_snippet": chunk.text_snippet,
                "summary": chunk.summary or "Summary not available",
                "socratic_questions": questions,
                "filename": upload.filename,
                "page_number": chunk.page_number or 1,
                "confidence": chunk.confidence or 0.8
            })
        
        return {
            "upload_id": upload_id,
            "status": upload.status,
            "chunks": chunks_response,
            "total_chunks": len(chunks_response)
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chunks: {str(e)}")


@app.get("/chunks/{upload_id}")
def get_chunks(upload_id: str, include_preview: bool = True, db: Session = Depends(get_db)):
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
            final_chunks = db.query(FinalChunks).filter(FinalChunks.upload_id == str(upload_uuid)).all()
            
            for chunk in final_chunks:
                # Ensure socratic_questions is always a list
                questions = chunk.socratic_questions
                if isinstance(questions, str):
                    try:
                        import json
                        questions = json.loads(questions)
                    except:
                        questions = [q.strip() for q in questions.split('\n') if q.strip()]
                elif not isinstance(questions, list):
                    questions = []
                
                chunks_response.append({
                    "chunk_id": str(chunk.id),
                    "text_snippet": chunk.text_snippet,
                    "summary": chunk.summary or "Summary not available",
                    "socratic_questions": questions,
                    "filename": upload.filename,
                    "page_number": chunk.page_number or 1,
                    "confidence": chunk.confidence or 0.8,
                    "type": "final"
                })
            
            total_chunks = len(final_chunks)
            
        elif upload.status in ["PROCESSING", "PENDING"] and include_preview:
            # Get preview chunks from temp data
            temp_chunks = db.query(TempChunks).filter(
                TempChunks.upload_id == upload_uuid
            ).order_by(TempChunks.chunk_index).limit(5).all()  # Show up to 5 preview chunks
            
            for i, chunk in enumerate(temp_chunks):
                try:
                    # Generate real-time summary and questions for preview
                    summary, questions, confidence = get_summary_and_questions(chunk.text_)
                    chunks_response.append({
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.text_[:300] + ("..." if len(chunk.text_) > 300 else ""),
                        "summary": summary,
                        "socratic_questions": questions,
                        "filename": upload.filename,
                        "page_number": chunk.page_number or (i + 1),
                        "confidence": confidence,
                        "type": "preview"
                    })
                except Exception as e:
                    print(f"Error generating preview for chunk {i}: {e}")
                    # Fallback preview
                    chunks_response.append({
                        "chunk_id": f"preview_{upload_id}_{i}",
                        "text_snippet": chunk.text_[:300] + ("..." if len(chunk.text_) > 300 else ""),
                        "summary": "Preview generation in progress...",
                        "socratic_questions": ["Preview questions will be available shortly..."],
                        "filename": upload.filename,
                        "page_number": chunk.page_number or (i + 1),
                        "confidence": 0.5,
                        "type": "preview"
                    })
            
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
            "has_more": upload.status == "PROCESSING" and len(chunks_response) < upload.total_chunks
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chunks: {str(e)}")


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
            "celery_backend": os.getenv("CELERY_RESULT_BACKEND")
        }
    except Exception as e:
        return {
            "error": str(e),
            "upload_id": upload_id,
            "celery_broker": os.getenv("CELERY_BROKER_URL"),
            "celery_backend": os.getenv("CELERY_RESULT_BACKEND")
        }
