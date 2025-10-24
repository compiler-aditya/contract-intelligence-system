"""RAG service for question answering"""
from typing import List, Dict, Optional, Tuple
from openai import OpenAI

from app.core.config import settings
from app.services.vector_store import VectorStore


class RAGService:
    """Retrieval-Augmented Generation service for contract Q&A"""

    def __init__(self):
        self.vector_store = VectorStore()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def answer_question(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        n_results: int = 5
    ) -> Tuple[str, List[Dict]]:
        """
        Answer a question using RAG

        Args:
            question: Question to answer
            document_ids: Optional list of document IDs to search in
            n_results: Number of chunks to retrieve

        Returns:
            Tuple of (answer, citations)
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured for RAG")

        # Retrieve relevant chunks
        relevant_chunks = self.vector_store.query(
            query_text=question,
            document_ids=document_ids,
            n_results=n_results
        )

        if not relevant_chunks:
            return "I cannot answer this based on the available contract documents.", []

        # Build context from chunks
        context_parts = []
        for idx, chunk in enumerate(relevant_chunks, 1):
            doc_id = chunk["metadata"].get("document_id", "unknown")
            context_parts.append(f"[Document {doc_id}, Chunk {idx}]\n{chunk['text']}")

        context = "\n\n".join(context_parts)

        # Build prompt
        prompt = f"""You are a legal contract analyst. Answer questions about contracts based ONLY on the provided context.

Context from contracts:
{context}

Question: {question}

Instructions:
1. Answer based ONLY on the provided context
2. If the answer is not in the context, say "I cannot answer this based on the available contract documents."
3. Be precise and cite specific clauses when possible
4. If multiple contracts are referenced, specify which contract contains the information

Provide a clear, concise answer:"""

        # Get answer from LLM
        try:
            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal contract analyst. Answer questions based only on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            answer = response.choices[0].message.content

        except Exception as e:
            raise ValueError(f"Error generating answer: {str(e)}")

        # Build citations
        citations = []
        for chunk in relevant_chunks:
            citations.append({
                "document_id": chunk["metadata"].get("document_id"),
                "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "char_start": chunk["metadata"].get("start_char"),
                "char_end": chunk["metadata"].get("end_char"),
                "chunk_index": chunk["metadata"].get("chunk_index")
            })

        return answer, citations

    def index_document(self, document_id: str, text: str, metadata: Optional[Dict] = None):
        """
        Index a document in the vector store

        Args:
            document_id: Document ID
            text: Document text
            metadata: Optional metadata
        """
        # Check if already indexed
        if self.vector_store.document_exists(document_id):
            # Remove old version
            self.vector_store.delete_document(document_id)

        # Add to vector store
        self.vector_store.add_document(document_id, text, metadata)

    def remove_document(self, document_id: str):
        """
        Remove a document from the vector store

        Args:
            document_id: Document ID to remove
        """
        self.vector_store.delete_document(document_id)
