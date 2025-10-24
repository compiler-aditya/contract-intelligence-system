"""RAG question answering endpoint"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
import asyncio
from typing import AsyncGenerator

from app.core.database import get_db
from app.models.schemas import AskRequest, AskResponse, Citation
from app.models.document import Document, ProcessingStatus
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about contracts using RAG

    - **question**: Question to ask about the contracts
    - **document_ids**: Optional list of document IDs to search in
    - Returns answer with citations from the documents
    """
    # Validate document IDs if provided
    if request.document_ids:
        for doc_id in request.document_ids:
            try:
                uuid.UUID(doc_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document ID format: {doc_id}"
                )

        # Check if documents exist and are processed
        result = await db.execute(
            select(Document).where(Document.id.in_([uuid.UUID(d) for d in request.document_ids]))
        )
        documents = result.scalars().all()

        if len(documents) != len(request.document_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more documents not found"
            )

        # Check if all documents are processed
        unprocessed = [str(d.id) for d in documents if d.status != ProcessingStatus.COMPLETED]
        if unprocessed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Documents not ready: {', '.join(unprocessed)}"
            )

        # Ensure documents are indexed in vector store
        rag_service = RAGService()
        for doc in documents:
            if not rag_service.vector_store.document_exists(str(doc.id)):
                # Index the document
                rag_service.index_document(
                    document_id=str(doc.id),
                    text=doc.text_content,
                    metadata={"filename": doc.filename}
                )

    # Answer the question
    rag_service = RAGService()
    try:
        answer, citations = rag_service.answer_question(
            question=request.question,
            document_ids=request.document_ids
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}"
        )

    # Format citations
    formatted_citations = [
        Citation(
            document_id=c["document_id"],
            text=c["text"],
            char_start=c.get("char_start"),
            char_end=c.get("char_end")
        )
        for c in citations
    ]

    return AskResponse(
        answer=answer,
        citations=formatted_citations,
        confidence=0.85 if citations else 0.0
    )


@router.get("/ask/stream")
async def ask_question_stream(
    question: str,
    document_ids: str = None,  # Comma-separated list
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question with streaming response (SSE)

    - **question**: Question to ask about the contracts
    - **document_ids**: Optional comma-separated list of document IDs
    - Streams the answer token by token using Server-Sent Events
    """
    # Parse document IDs
    doc_id_list = None
    if document_ids:
        doc_id_list = [d.strip() for d in document_ids.split(",")]

        # Validate document IDs
        for doc_id in doc_id_list:
            try:
                uuid.UUID(doc_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document ID format: {doc_id}"
                )

        # Check if documents exist
        result = await db.execute(
            select(Document).where(Document.id.in_([uuid.UUID(d) for d in doc_id_list]))
        )
        documents = result.scalars().all()

        if len(documents) != len(doc_id_list):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more documents not found"
            )

        # Ensure documents are indexed
        rag_service = RAGService()
        for doc in documents:
            if not rag_service.vector_store.document_exists(str(doc.id)):
                rag_service.index_document(
                    document_id=str(doc.id),
                    text=doc.text_content,
                    metadata={"filename": doc.filename}
                )

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        rag_service = RAGService()

        # Retrieve relevant chunks
        relevant_chunks = rag_service.vector_store.query(
            query_text=question,
            document_ids=doc_id_list,
            n_results=5
        )

        if not relevant_chunks:
            yield f"data: {json.dumps({'token': 'I cannot answer this based on the available contract documents.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Build context
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

Provide a clear, concise answer:"""

        # Stream from OpenAI
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            stream = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal contract analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    await asyncio.sleep(0)  # Allow other tasks to run

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
