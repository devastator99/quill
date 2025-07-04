import os
import uuid as uuid_lib
from typing import List, Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from celery_worker import celery_app
from models import TempChunks, FinalChunks, PdfUploads

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Setup SQLAlchemy engine and session for tasks
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task(name="tasks.process_chunks")
def process_chunks(upload_id: str):
    """Process chunks with proper database session management"""
    print(f"🚀 TASK STARTED: process_chunks for upload_id: {upload_id}")
    print(f"📊 Environment check:")
    print(f"   - DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    print(f"   - OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"   - OPENAI_API_BASE: {'SET' if os.getenv('OPENAI_API_BASE') else 'NOT SET'}")
    
    # Use the SessionLocal factory for this task
    db = None
    try:
        print(f"🔌 Creating database session...")
        db = SessionLocal()
        print(f"✅ Database session created successfully")
        
        print(f"📥 Loading temp chunks for upload_id: {upload_id}")
        
        # Load temp chunks
        chunks = load_temp_chunks_from_db(upload_id, db)
        print(f"✅ Loaded {len(chunks)} chunks")
        
        if not chunks:
            print(f"⚠️  No chunks found for upload_id: {upload_id}")
            return
        
        total_chunks = len(chunks)
        processed_count = 0
        print(f"🔄 Starting processing of {total_chunks} chunks...")

        for chunk in chunks:
            try:
                print(f"🔍 Processing chunk {chunk.chunk_index + 1}/{total_chunks}")
                
                # Check if processing should be aborted
                if is_aborted(upload_id, db):
                    print(f"🛑 Processing aborted for upload_id: {upload_id}")
                    break

                print(f"📝 Generating summary and questions for chunk {chunk.chunk_index}")
                
                # Summarize + Socratic Qs
                summary, questions, confidence = get_summary_and_questions(chunk.text_)
                print(f"✅ Generated summary and {len(questions)} questions")
                
                print(f"🧠 Creating embedding for chunk {chunk.chunk_index}")
                # Embed + Store  
                embedding = embed_chunk(chunk.text_)
                print(f"✅ Created embedding with {len(embedding)} dimensions")
                
                upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
                store_final_chunk(upload_uuid, chunk, summary, questions, confidence, embedding, db)
                print(f"💾 Stored final chunk {chunk.chunk_index}")

                # Update progress
                update_progress(upload_id, db)
                processed_count += 1
                
                print(f"✅ Successfully processed chunk {chunk.chunk_index}")
                
            except Exception as e:
                print(f"❌ Error processing chunk {chunk.chunk_index}: {e}")
                print(f"🔍 Error details: {type(e).__name__}: {str(e)}")
                # Store error information but continue processing
                try:
                    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
                    upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
                    if upload:
                        error_msg = f"Error processing chunk {chunk.chunk_index}: {str(e)}"
                        if upload.error_log:
                            upload.error_log += f"\n{error_msg}"
                        else:
                            upload.error_log = error_msg
                        db.commit()
                except Exception as db_error:
                    print(f"❌ Error updating error log: {db_error}")
                
                # Continue with next chunk instead of failing completely
                continue

        # Mark as complete if we processed all chunks successfully
        if processed_count > 0:
            print(f"🎉 Marking upload as complete. Processed {processed_count} chunks.")
            mark_complete(upload_id, db)
            print(f"✅ Processing completed for upload_id: {upload_id}")
        else:
            print(f"⚠️  No chunks were successfully processed for upload_id: {upload_id}")
            
    except Exception as e:
        print(f"💥 Critical error in process_chunks: {e}")
        print(f"🔍 Critical error details: {type(e).__name__}: {str(e)}")
        # Mark upload as failed
        try:
            if db:
                upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
                upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
                if upload:
                    upload.status = "FAILED"
                    upload.error_log = f"Processing failed: {str(e)}"
                    db.commit()
        except Exception as db_error:
            print(f"❌ Error updating failed status: {db_error}")
    finally:
        # Ensure database session is properly closed
        if db:
            try:
                print(f"🔌 Closing database session...")
                db.close()
                print(f"✅ Database session closed successfully")
            except Exception as cleanup_error:
                print(f"❌ Error during cleanup: {cleanup_error}")
        
        print(f"🏁 TASK COMPLETED: process_chunks for upload_id: {upload_id}")


def load_temp_chunks_from_db(upload_id: str, db_session: Session) -> List[TempChunks]:
    """Load temp chunks with better error handling"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
        chunks = db_session.query(TempChunks).filter(
            TempChunks.upload_id == upload_uuid
        ).order_by(TempChunks.chunk_index).all()
        return chunks
    except Exception as e:
        print(f"Error loading temp chunks for upload_id {upload_id}: {e}")
        db_session.rollback()
        raise


def is_aborted(upload_id: str, db: Session) -> bool:
    upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
    upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
    return upload and upload.status == "ABORTED"


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


def embed_chunk(text: str) -> List[float]:
    embedder = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embedder.embed_query(text)


def store_final_chunk(upload_id: uuid_lib.UUID, chunk: TempChunks, summary: str, questions: List[str], confidence: float, embedding: List[float], db: Session):
    """Store final chunk with better error handling"""
    try:
        vector = FinalChunks(
            upload_id=str(upload_id),  # Store as string to match the model
            text_snippet=chunk.text_[:300] + ("..." if len(chunk.text_) > 300 else ""),
            embedding=embedding,
            summary=summary,
            socratic_questions=questions,
            page_number=chunk.page_number,
            confidence=confidence
        )
        db.add(vector)
        db.commit()
    except Exception as e:
        print(f"Error storing final chunk: {e}")
        db.rollback()
        raise


def update_progress(upload_id: str, db: Session):
    """Update progress with better error handling"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if upload:
            upload.processed_chunks += 1
            db.commit()
    except Exception as e:
        print(f"Error updating progress: {e}")
        db.rollback()
        raise


def mark_complete(upload_id: str, db: Session):
    """Mark upload as complete with better error handling"""
    try:
        upload_uuid = uuid_lib.UUID(upload_id) if isinstance(upload_id, str) else upload_id
        upload = db.query(PdfUploads).filter(PdfUploads.id == upload_uuid).first()
        if upload:
            upload.status = "COMPLETED"
            db.commit()
    except Exception as e:
        print(f"Error marking complete: {e}")
        db.rollback()
        raise 