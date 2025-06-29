from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.pgvector import PGVector
from langchain.schema import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from tempfile import NamedTemporaryFile
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
import fitz
import pandas as pd
import mimetypes
import magic

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize FastAPI app
app = FastAPI(title="PDF Socratic LLM Processor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Setup SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
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


@app.post("/upload_doc/", response_model=List[ChunkResponse])
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to upload a PDF, extract and chunk its text,
    embed and store in pgvector, and query LLM for Socratic reflection.
    """
    # ✅ Check file type
    validate_file_type(file)

    # ✅ Save uploaded file temporarily
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving file: {str(e)}")

    # ✅ Extract text using LangChain PDF loader
    try:
        documents = load_file_to_documents(tmp_path, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading PDF: {str(e)}")

    # ✅ Split into overlapping chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=100)
    chunks: List[Document] = splitter.split_documents(documents)

    # ✅ Initialize LLM
    llm = ChatOpenAI(
        model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE")
    )

    results: List[ChunkResponse] = []

    # ✅ Enrich each chunk with metadata + LLM output
    for i, chunk in enumerate(chunks):
        chunk.metadata["filename"] = file.filename
        chunk.metadata["page_number"] = chunk.metadata.get("page", i + 1)
        chunk_id = str(uuid.uuid4())

        prompt = (
            f"Here is a text snippet:\n\n{chunk.page_content}\n\n"
            "1. Summarize it in one sentence.\n"
            "2. Then pose 2–3 open-ended, thought-provoking questions that would help a learner reflect on the ideas in the text (Socratic method)."
        )

        try:
            response = await llm.ainvoke(prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

        response_lines = response.content.strip().split("\n")
        summary = response_lines[0] if response_lines else ""
        questions = [
            line.strip("- ").strip() for line in response_lines[1:]
            if line.strip() and not line.startswith("1.") and not line.startswith("2.")
        ]

        confidence = 1.0 if summary and questions else 0.5

        chunk.metadata["summary"] = summary.strip()
        chunk.metadata["socratic_questions"] = questions
        chunk.metadata["llm_confidence"] = confidence

        results.append(ChunkResponse(
            chunk_id=chunk_id,
            text_snippet=chunk.page_content[:300] + "...",
            summary=summary.strip(),
            socratic_questions=questions,
            filename=file.filename,
            page_number=chunk.metadata["page_number"],
            confidence=confidence
        ))

    # ✅ Embed and store in PGVector with enriched metadata
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="pdf_chunks",
        )
        vectorstore.add_documents(chunks)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Embedding or DB error: {str(e)}")

    # ✅ Clean up temp file
    os.unlink(tmp_path)

    return results


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
        conversation_id = request.conversation_id or str(uuid.uuid4())

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
    mime_type = magic.from_buffer(file.file.read(2048), mime=True)
    file.file.seek(0)
    allowed_types = ['application/pdf', 'text/csv',
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     'text/markdown']
    if mime_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
