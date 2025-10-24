"""Vector store service for RAG"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from openai import OpenAI
import uuid

from app.core.config import settings


class VectorStore:
    """Vector store for storing and retrieving document chunks"""

    def __init__(self):
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="contracts",
            metadata={"description": "Contract document chunks for RAG"}
        )

        # Initialize OpenAI for embeddings
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using OpenAI

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        response = self.openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text
        )

        return response.data[0].embedding

    def add_document(self, document_id: str, text: str, metadata: Optional[Dict] = None):
        """
        Add a document to the vector store

        Args:
            document_id: Unique document identifier
            text: Full document text
            metadata: Optional metadata for the document
        """
        from app.services.pdf_processor import PDFProcessor

        # Chunk the document
        chunks = PDFProcessor.chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )

        # Prepare data for vector store
        chunk_ids = []
        chunk_texts = []
        chunk_metadatas = []
        chunk_embeddings = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{idx}"
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk["text"])

            chunk_metadata = {
                "document_id": document_id,
                "chunk_index": idx,
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"],
                **(metadata or {})
            }
            chunk_metadatas.append(chunk_metadata)

            # Get embedding
            if self.openai_client:
                embedding = self._get_embedding(chunk["text"])
                chunk_embeddings.append(embedding)

        # Add to vector store
        if chunk_embeddings:
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadatas,
                embeddings=chunk_embeddings
            )
        else:
            # Use ChromaDB's default embedding function
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadatas
            )

    def query(
        self,
        query_text: str,
        document_ids: Optional[List[str]] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Query the vector store for relevant chunks

        Args:
            query_text: Query text
            document_ids: Optional list of document IDs to filter by
            n_results: Number of results to return

        Returns:
            List of relevant chunks with metadata
        """
        # Get query embedding
        if self.openai_client:
            query_embedding = self._get_embedding(query_text)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"document_id": {"$in": document_ids}} if document_ids else None
            )
        else:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"document_id": {"$in": document_ids}} if document_ids else None
            )

        # Format results
        formatted_results = []
        if results and results["documents"]:
            for idx in range(len(results["documents"][0])):
                formatted_results.append({
                    "text": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                    "distance": results["distances"][0][idx] if results.get("distances") else None
                })

        return formatted_results

    def delete_document(self, document_id: str):
        """
        Delete all chunks for a document

        Args:
            document_id: Document ID to delete
        """
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"document_id": document_id}
        )

        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])

    def document_exists(self, document_id: str) -> bool:
        """
        Check if document exists in vector store

        Args:
            document_id: Document ID to check

        Returns:
            True if document exists
        """
        results = self.collection.get(
            where={"document_id": document_id},
            limit=1
        )

        return bool(results and results["ids"])
