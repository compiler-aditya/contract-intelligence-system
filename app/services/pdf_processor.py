"""PDF processing service for text extraction"""
import PyPDF2
import pdfplumber
from typing import Tuple, Dict, List
import os
from pathlib import Path


class PDFProcessor:
    """Service for processing PDF files and extracting text"""

    @staticmethod
    def extract_text_with_pypdf2(file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF using PyPDF2

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)

                text_parts = []
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}")

                full_text = "\n\n".join(text_parts)
                return full_text, page_count

        except Exception as e:
            raise ValueError(f"Error extracting text with PyPDF2: {str(e)}")

    @staticmethod
    def extract_text_with_pdfplumber(file_path: str) -> Tuple[str, int, Dict]:
        """
        Extract text from PDF using pdfplumber (better for complex layouts)

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (extracted_text, page_count, metadata)
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)

                text_parts = []
                page_metadata = []

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}")

                    # Extract page metadata
                    page_metadata.append({
                        "page": page_num,
                        "width": page.width,
                        "height": page.height,
                    })

                full_text = "\n\n".join(text_parts)
                metadata = {
                    "total_pages": page_count,
                    "pages": page_metadata
                }

                return full_text, page_count, metadata

        except Exception as e:
            raise ValueError(f"Error extracting text with pdfplumber: {str(e)}")

    @staticmethod
    def extract_text(file_path: str, method: str = "pdfplumber") -> Tuple[str, int]:
        """
        Extract text from PDF using specified method

        Args:
            file_path: Path to the PDF file
            method: Extraction method ('pdfplumber' or 'pypdf2')

        Returns:
            Tuple of (extracted_text, page_count)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if method == "pdfplumber":
            text, page_count, _ = PDFProcessor.extract_text_with_pdfplumber(file_path)
            return text, page_count
        elif method == "pypdf2":
            return PDFProcessor.extract_text_with_pypdf2(file_path)
        else:
            # Fallback: try pdfplumber first, then pypdf2
            try:
                text, page_count, _ = PDFProcessor.extract_text_with_pdfplumber(file_path)
                return text, page_count
            except Exception:
                return PDFProcessor.extract_text_with_pypdf2(file_path)

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks for RAG

        Args:
            text: Input text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks

        Returns:
            List of chunks with metadata
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            chunks.append({
                "text": chunk_text,
                "start_char": start,
                "end_char": min(end, len(text)),
                "chunk_index": len(chunks)
            })

            start += (chunk_size - overlap)

        return chunks
