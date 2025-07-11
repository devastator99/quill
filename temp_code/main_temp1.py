import os
import re
import uuid
import logging
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

import magic
import fitz
import pandas as pd
from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File,
    HTTPException, Depends, status, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings
from sqlalchemy import create_engine, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector

from models import TempChunks, FinalChunks, PdfUploads  # your existing models


# ─── Configuration ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_API_BASE: Optional[str] = None
    DATABASE_URL: str
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CORS_ALLOW_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()


# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("socratic-api")


# ─── Database ──────────────────────────────s────────────────────────────────────

try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.critical(f"Could not initialize database engine: {e}")
    raise


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Database session error: {exc}")
        raise
    finally:
        db.close()


# ─── FastAPI App & Middleware ──────────────────────────────────────────────────

app = FastAPI(title="Socratic")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global LLM & VectorStore (initialized on startup) ─────────────────────────

embeddings: HuggingFaceEmbeddings
vectorstore: PGVector
llm: ChatOpenAI

@app.on_event("startup")
def on_startup():
    global embeddings, vectorstore, llm
    logger.info("Initializing embeddings, vector store, and LLM client...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = PGVector(
        connection_string=settings.DATABASE_URL,
        embedding_function=embeddings,
        collection_name="pdf_chunks"
    )
    llm = ChatOpenAI(
        model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )


# ─── Models for API I/O ────────────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    chunk_id: str
    text_snippet: str
    summary: str
    socratic_questions: List[str]
    page_number: Optional[int]
    filename: Optional[str]
    confidence: Optional[float]


class UploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str
    total_chunks: int
    estimated_time: str
    preview_chunks: List[ChunkResponse]
    file_type: str
    supported_operations: List[str]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []


# ─── Utility Functions ────────────────────────────────────────────────────────

def validate_file_type(file: UploadFile):
    chunk = file.file.read(2048)
    file.file.seek(0)
    mime_type = magic.from_buffer(chunk, mime=True)
    ext = os.path.splitext(file.filename or "")[-1].lower()

    allowed = {
        ".pdf": "application/pdf",
        ".csv": ["text/csv", "text/plain"],
        ".xlsx": "spreadsheet",
        ".xls": "spreadsheet",
        ".md": ["text/markdown", "text/plain"]
    }

    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension {ext}"
        )

    rules = allowed[ext]
    if isinstance(rules, list):
        if mime_type not in rules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Detected MIME type {mime_type} not allowed for {ext}"
            )
    else:
        if rules not in mime_type and not (isinstance(rules, list) and any(r in mime_type for r in rules)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Detected MIME type {mime_type} not allowed for {ext}"
            )


def load_pdf(file_path: str, filename: str) -> List[Document]:
    doc = fitz.open(file_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(Document(page_content=text, metadata={"source": filename, "page": i}))
    return pages


def load_spreadsheet(file_path: str, filename: str) -> List[Document]:
    try:
        df = pd.read_csv(file_path) if filename.lower().endswith(".csv") else pd.read_excel(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error loading spreadsheet: {e}")
    content = df.to_csv(index=False) if filename.lower().endswith(".csv") else df.to_string(index=False)
    return [Document(page_content=content, metadata={"source": filename})]


def load_markdown(file_path: str, filename: str) -> List[Document]:
    try:
        with open(file_path, encoding="utf-8") as f:
            return [Document(page_content=f.read(), metadata={"source": filename})]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading markdown: {e}")


def load_file_to_documents(tmp_path: str, filename: str) -> List[Document]:
    ext = os.path.splitext(filename.lower())[-1]
    if ext == ".pdf":
        return load_pdf(tmp_path, filename)
    if ext in [".csv", ".xlsx", ".xls"]:
        return load_spreadsheet(tmp_path, filename)
    if ext in [".md", ".markdown"]:
        return load_markdown(tmp_path, filename)
    raise HTTPException(status_code=400, detail=f"Unsupported file extension {ext}")


def split_documents(docs: List[Document]) -> List[Document]:
    full_text = "\n".join(d.page_content for d in docs)
    if full_text.count("CHAPTER") > 2 or "Table of Contents" in full_text:
        # custom chapter split
        pattern = re.compile(r"(CHAPTER\s+\d+|Chapter\s+[A-Z][a-z]+)", re.IGNORECASE)
        parts = pattern.split(full_text)
        out = []
        for i in range(1, len(parts), 2):
            title, body = parts[i].strip(), parts[i+1].strip() if i+1 < len(parts) else ""
            out.append(Document(page_content=f"{title}\n\n{body}", metadata={"section": title}))
        return out
    # fallback to character splitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    return splitter.split_documents(docs)


def estimate_time_for_processing(n_chunks: int) -> str:
    secs = n_chunks * 3
    if secs < 60:
        return f"{secs} seconds"
    if secs < 3600:
        mins = secs // 60
        return f"{mins} minute{'s' if mins != 1 else ''}"
    hrs = secs // 3600
    mins = (secs % 3600) // 60
    return f"{hrs}h {mins}m"


def get_summary_and_questions(text: str) -> Tuple[str, List[str], float]:
    snippet = text[:2000]
    prompt = (
        f"Analyze this text and provide:\n\n"
        f"Text: {snippet}\n\n"
        "Format:\n"
        "SUMMARY: [one clear sentence]\n"
        "QUESTION 1: ...\n"
        "QUESTION 2: ...\n"
        "QUESTION 3: (optional)\n"
    )
    try:
        resp = llm.invoke(prompt).content.strip().splitlines()
        summary = next((l.split("SUMMARY:")[1].strip() for l in resp if "SUMMARY:" in l), "")
        questions = [l.split(":",1)[1].strip()
                     for l in resp if l.startswith("QUESTION")][:3]
        if not summary or not questions:
            raise ValueError("Incomplete parse")
        return summary, questions, 0.8
    except Exception as e:
        logger.warning(f"Socratic parse fallback: {e}")
        fallback = [
            "What are the main ideas here?",
            "How could this be applied?",
            "What questions remain?"
        ]
        return f"This discusses: {snippet[:100]}...", fallback, 0.3


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
async def health_check():
    return {"status": "healthy", "message": "PDF Socratic LLM Processor is running"}


@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            msg = await ws.receive_text()
            for client in list(connected_clients):
                try:
                    await client.send_text(msg)
                except:
                    connected_clients.remove(client)
    except WebSocketDisconnect:
        connected_clients.remove(ws)


@app.post("/upload_doc/", response_model=UploadResponse)
async def upload_doc(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    validate_file_type(file)
    upload_id = str(uuid.uuid4())

    # save to temp file
    suffix = os.path.splitext(file.filename or "")[-1] or ".tmp"
    tmp = NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.close()

        # load & chunk
        docs = load_file_to_documents(tmp.name, file.filename or "")
        chunks = split_documents(docs)

        # store metadata & temp
        upload_rec = PdfUploads(
            id=upload_id, filename=file.filename, total_chunks=len(chunks), status="PROCESSING"
        )
        db.add(upload_rec)
        db.commit()

        for idx, doc in enumerate(chunks):
            temp = TempChunks(
                upload_id=upload_id,
                chunk_id=str(uuid.uuid4()),
                chunk_index=idx,
                text_=doc.page_content,
                page_number=doc.metadata.get("page", idx + 1),
                section=doc.metadata.get("section", "")
            )
            db.add(temp)
        db.commit()

        # kick off celery
        from celery_worker import celery_app
        celery_app.send_task("tasks.process_chunks", args=[upload_id])

        # build preview
        preview = []
        for i, chunk in enumerate(chunks[:3]):
            summary, questions, conf = get_summary_and_questions(chunk.page_content)
            preview.append({
                "chunk_id": f"preview_{upload_id}_{i}",
                "text_snippet": chunk.page_content[:300] + ("..." if len(chunk.page_content) > 300 else ""),
                "summary": summary,
                "socratic_questions": questions,
                "filename": file.filename,
                "page_number": chunk.metadata.get("page", i + 1),
                "confidence": conf
            })

        return UploadResponse(
            upload_id=upload_id,
            status="PROCESSING",
            message=f"Successfully initiated processing of {file.filename}",
            total_chunks=len(chunks),
            estimated_time=estimate_time_for_processing(len(chunks)),
            preview_chunks=preview,
            file_type=suffix.replace(".", "").upper(),
            supported_operations=[
                "Text extraction", "Intelligent chunking", "Socratic question generation",
                "Vector embedding", "Semantic search"
            ]
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error in /upload_doc/: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during upload")
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass


@app.post("/upload_doc/abort/{upload_id}")
def abort_upload(upload_id: str, db: Session = Depends(get_db)):
    try:
        upload = db.query(PdfUploads).get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        upload.status = "ABORTED"
        db.commit()
        return {"message": "Upload aborted"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error aborting upload {upload_id}: {exc}")
        raise HTTPException(status_code=500, detail="Could not abort upload")


@app.post("/chat/", response_model=ChatResponse)
async def chat_with_context(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        docs = vectorstore.similarity_search(req.message, k=3)
        context = ""
        sources = []
        if docs:
            context = "\n\n".join(f"{i+1}. {d.page_content[:200]}..." for i,d in enumerate(docs))
            sources = [f"chunk_{i+1}" for i in range(len(docs))]

        prompt = (
            f"You are a helpful AI assistant. Use the context below if relevant:\n\n"
            f"{context}\n\nUser Question: {req.message}"
        )
        resp = await llm.ainvoke(prompt)
        conv_id = req.conversation_id or str(uuid.uuid4())
        return ChatResponse(response=resp.content, conversation_id=conv_id, sources=sources)

    except Exception as exc:
        logger.error(f"Chat error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chat processing failed")


@app.get("/upload_status/{upload_id}")
def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    try:
        upload = db.query(PdfUploads).get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        pct = int((upload.processed_chunks or 0) / upload.total_chunks * 100) if upload.total_chunks else 0
        stage = {
            "PENDING": "Waiting to start",
            "PROCESSING": "Processing",
            "COMPLETED": "Completed",
            "FAILED": "Failed",
            "ABORTED": "Aborted"
        }.get(upload.status, "Unknown")

        return {
            "upload_id": upload_id,
            "status": upload.status,
            "progress": pct,
            "processing_stage": stage,
            "processed_chunks": upload.processed_chunks,
            "total_chunks": upload.total_chunks,
            "estimated_time_remaining": estimate_time_for_processing(upload.total_chunks - (upload.processed_chunks or 0))
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error in status for {upload_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve status")


@app.get("/chunks/{upload_id}")
def get_chunks(upload_id: str, include_preview: bool = True, db: Session = Depends(get_db)):
    try:
        upload = db.query(PdfUploads).get(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        if upload.status == "COMPLETED":
            rows = db.query(FinalChunks).filter_by(upload_id=upload_id).all()
            out = []
            for c in rows:
                qs = c.socratic_questions if isinstance(c.socratic_questions, list) else []
                out.append({
                    "chunk_id": c.id,
                    "text_snippet": c.text_snippet,
                    "summary": c.summary,
                    "socratic_questions": qs,
                    "page_number": c.page_number,
                    "confidence": c.confidence,
                    "type": "final"
                })
            return {"upload_id": upload_id, "status": "COMPLETED", "chunks": out}

        if include_preview:
            temps = db.query(TempChunks).filter_by(upload_id=upload_id).order_by(TempChunks.chunk_index).limit(5).all()
            out = []
            for i,t in enumerate(temps):
                summary, qs, conf = get_summary_and_questions(t.text_)
                out.append({
                    "chunk_id": f"preview_{upload_id}_{i}",
                    "text_snippet": t.text_[:300] + ("..." if len(t.text_)>300 else ""),
                    "summary": summary,
                    "socratic_questions": qs,
                    "page_number": t.page_number,
                    "confidence": conf,
                    "type": "preview"
                })
            return {"upload_id": upload_id, "status": upload.status, "chunks": out}

        return {"upload_id": upload_id, "status": upload.status, "chunks": []}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching chunks for {upload_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve chunks")
