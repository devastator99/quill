import os
import re
import uuid as uuid_lib
import hashlib
from datetime import datetime, timedelta
from typing import List
from tempfile import NamedTemporaryFile

import fitz
import pandas as pd
import magic

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from models import TempChunks, PdfUploads # Assuming these models are defined in models.py

def generate_pdf_hash(content: bytes) -> str:
    """Generate SHA256 hash of PDF content"""
    return hashlib.sha256(content).hexdigest()

def get_expiration_timestamp(minutes: int = 5) -> int:
    """Get expiration timestamp for transactions"""
    return int((datetime.now() + timedelta(minutes=minutes)).timestamp())

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

def validate_file_type(file):
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
        from fastapi import HTTPException
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
