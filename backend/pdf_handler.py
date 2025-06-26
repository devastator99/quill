from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.pgvector import PGVector
from langchain.chat_models import ChatOpenAI
import tempfile, os

async def process_pdf(file, user_id):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
        tf.write(await file.read())
        path = tf.name

    docs = PyPDFLoader(path).load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    vector_store = PGVector.from_documents(
        chunks,
        embeddings,
        collection_name="pdf_chunks",
        connection_string=os.getenv("DATABASE_URL")
    )

    llm = ChatOpenAI(temperature=0.3, openai_api_key=os.getenv("OPENAI_API_KEY"))
    result = []

    for chunk in chunks:
        prompt = f"Text:\n{chunk.page_content}\n\nSummarize and ask 2-3 Socratic questions."
        response = llm.invoke(prompt)
        lines = response.content.strip().split('\n')
        summary = lines[0]
        questions = [line.strip("-• ") for line in lines[1:] if line.strip()]
        result.append({
            "chunk_id": chunk.metadata.get("chunk_id", "unknown"),
            "text_snippet": chunk.page_content[:200],
            "summary": summary,
            "socratic_questions": questions
        })

    return result
