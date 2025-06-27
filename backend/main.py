from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List
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


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []


@app.post("/upload_pdf/", response_model=List[ChunkResponse])
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to upload a PDF, extract and chunk its text,
    embed and store in pgvector, and query LLM for Socratic reflection.
    """
    # Check file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported.")

    # Save uploaded file temporarily
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving file: {str(e)}")

    # Extract text using LangChain PDF loader
    try:
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading PDF: {str(e)}")

    # Split into overlapping chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700, chunk_overlap=100)
    chunks: List[Document] = splitter.split_documents(documents)

    # Embed and store in PGVector
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=embeddings,
            collection_name="pdf_chunks",
        )
        vectorstore.add_documents(chunks)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Embedding or DB error: {str(e)}")

    # Setup Groq API for LLM
    os.environ["OPENAI_API_KEY"] = os.getenv("GROQ_API_KEY")
    os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"

    llm = ChatOpenAI(
        model="mixtral-8x7b-32768",
        temperature=0.3,
    )

    results: List[ChunkResponse] = []

    for i, chunk in enumerate(chunks):
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

        # Parse response (assumes LLM formats well)
        response_lines = response.content.strip().split("\n")
        summary = response_lines[0] if response_lines else ""
        questions = [line.strip("- ").strip() for line in response_lines[1:]
                     if line.strip() and not line.strip().startswith("1.")
                     and not line.strip().startswith("2.")]

        results.append(ChunkResponse(
            chunk_id=chunk_id,
            text_snippet=chunk.page_content[:300] + "...",  # limit size
            summary=summary.strip(),
            socratic_questions=questions,
        ))

    # Clean up temp file
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
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
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

        os.environ["OPENAI_API_KEY"] = os.getenv("GROQ_API_KEY")
        os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"

        print("GROQ_API_KEY:", os.getenv("GROQ_API_KEY"))  # should NOT be None


        llm = ChatOpenAI(
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # or another supported model
            temperature=0.7,
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
