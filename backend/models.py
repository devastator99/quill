import uuid as uuid_lib
import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import CheckConstraint, DateTime, Double, Enum, ForeignKeyConstraint, Index, Integer, JSON, PrimaryKeyConstraint, String, Text, UniqueConstraint, Uuid, text
from pgvector.sqlalchemy.vector import VECTOR
from typing import Any, List, Optional


class Base(DeclarativeBase):
    pass


class FinalChunks(Base):
    __tablename__ = 'final_chunks'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='final_chunks_pkey'),
        Index('ix_final_chunks_id', 'id'),
        Index('ix_final_chunks_upload_id', 'upload_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_id: Mapped[Optional[str]] = mapped_column(String)
    text_snippet: Mapped[Optional[str]] = mapped_column(Text)
    embedding: Mapped[Optional[dict]] = mapped_column(JSON)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    socratic_questions: Mapped[Optional[dict]] = mapped_column(JSON)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    confidence: Mapped[Optional[float]] = mapped_column(Double(53))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text('now()'))


class LangchainPgCollection(Base):
    __tablename__ = 'langchain_pg_collection'
    __table_args__ = (
        PrimaryKeyConstraint('uuid', name='langchain_pg_collection_pkey'),
    )

    uuid: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    cmetadata: Mapped[Optional[dict]] = mapped_column(JSON)

    langchain_pg_embedding: Mapped[List['LangchainPgEmbedding']] = relationship(
        'LangchainPgEmbedding', back_populates='collection')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('email', name='users_email_key')
    )

    id: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(Text)
    auth_provider: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text('CURRENT_TIMESTAMP'))

    pdf_uploads: Mapped[List['PdfUploads']] = relationship(
        'PdfUploads', back_populates='user')
    conversations: Mapped[List['Conversations']] = relationship(
        'Conversations', back_populates='user')


class LangchainPgEmbedding(Base):
    __tablename__ = 'langchain_pg_embedding'
    __table_args__ = (
        ForeignKeyConstraint(['collection_id'], ['langchain_pg_collection.uuid'],
                             ondelete='CASCADE', name='langchain_pg_embedding_collection_id_fkey'),
        PrimaryKeyConstraint('uuid', name='langchain_pg_embedding_pkey')
    )

    uuid: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    collection_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR)
    document: Mapped[Optional[str]] = mapped_column(String)
    cmetadata: Mapped[Optional[dict]] = mapped_column(JSON)
    custom_id: Mapped[Optional[str]] = mapped_column(String)

    collection: Mapped[Optional['LangchainPgCollection']] = relationship(
        'LangchainPgCollection', back_populates='langchain_pg_embedding')


class PdfUploads(Base):
    __tablename__ = 'pdf_uploads'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.id'],
                             ondelete='SET NULL', name='fk_pdf_uploads_user'),
        PrimaryKeyConstraint('id', name='pdf_uploads_pkey')
    )

    id: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    filename: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum('INITIATED', 'PROCESSING', 'COMPLETED',
                                        'FAILED', name='upload_status'), server_default=text("'INITIATED'::upload_status"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=text('CURRENT_TIMESTAMP'))
    user_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)
    total_chunks: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'))
    processed_chunks: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'))
    error_log: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[Optional['Users']] = relationship(
        'Users', back_populates='pdf_uploads')
    conversations: Mapped[List['Conversations']] = relationship(
        'Conversations', back_populates='doc')
    pdf_chunks: Mapped[List['PdfChunks']] = relationship(
        'PdfChunks', back_populates='upload')
    temp_chunks: Mapped[List['TempChunks']] = relationship(
        'TempChunks', back_populates='upload')


class Conversations(Base):
    __tablename__ = 'conversations'
    __table_args__ = (
        ForeignKeyConstraint(['doc_id'], ['pdf_uploads.id'],
                             ondelete='CASCADE', name='fk_conversations_upload'),
        ForeignKeyConstraint(['user_id'], [
                             'users.id'], ondelete='SET NULL', name='conversations_user_id_fkey'),
        PrimaryKeyConstraint('id', name='conversations_pkey')
    )

    id: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text('CURRENT_TIMESTAMP'))
    doc_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)

    doc: Mapped[Optional['PdfUploads']] = relationship(
        'PdfUploads', back_populates='conversations')
    user: Mapped[Optional['Users']] = relationship(
        'Users', back_populates='conversations')
    messages: Mapped[List['Messages']] = relationship(
        'Messages', back_populates='conversation')


class PdfChunks(Base):
    __tablename__ = 'pdf_chunks'
    __table_args__ = (
        ForeignKeyConstraint(['upload_id'], ['pdf_uploads.id'],
                             ondelete='CASCADE', name='pdf_chunks_upload_id_fkey'),
        PrimaryKeyConstraint('chunk_id', name='pdf_chunks_pkey'),
        Index('idx_pdf_chunks_embedding', 'embedding'),
        Index('idx_pdf_chunks_page_number', 'page_number')
    )

    chunk_id: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    text_snippet: Mapped[str] = mapped_column(Text)
    upload_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR(384))
    socratic_questions: Mapped[Optional[dict]] = mapped_column(JSON)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    confidence: Mapped[Optional[float]] = mapped_column(Double(53))

    upload: Mapped[Optional['PdfUploads']] = relationship(
        'PdfUploads', back_populates='pdf_chunks')


class Messages(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        CheckConstraint(
            "role = ANY (ARRAY['user'::text, 'assistant'::text])", name='messages_role_check'),
        ForeignKeyConstraint(['conversation_id'], [
                             'conversations.id'], ondelete='CASCADE', name='messages_conversation_id_fkey'),
        PrimaryKeyConstraint('id', name='messages_pkey'),
        Index('idx_messages_conversation_id', 'conversation_id')
    )

    id: Mapped[uuid_lib.UUID] = mapped_column(Uuid, primary_key=True)
    conversation_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(Uuid)
    role: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    sources: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text('CURRENT_TIMESTAMP'))

    conversation: Mapped[Optional['Conversations']] = relationship(
        'Conversations', back_populates='messages')


class TempChunks(Base):
    __tablename__ = 'temp_chunks'
    __table_args__ = (
        ForeignKeyConstraint(['upload_id'], ['pdf_uploads.id'],
                             ondelete='CASCADE', name='temp_chunks_upload_id_fkey'),
        PrimaryKeyConstraint('id', name='temp_chunks_pkey')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_id: Mapped[uuid_lib.UUID] = mapped_column(Uuid)
    chunk_id: Mapped[uuid_lib.UUID] = mapped_column(Uuid)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text_: Mapped[str] = mapped_column('text', Text)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    section: Mapped[Optional[str]] = mapped_column(Text)

    upload: Mapped['PdfUploads'] = relationship(
        'PdfUploads', back_populates='temp_chunks')
