"""
Document Processing Service
Handles PDF, DOCX, TXT file processing and text extraction
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import PyPDF2
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and extract text from documents"""
    
    SUPPORTED_FORMATS = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'txt': 'text/plain'
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.upload_dir = Path("uploads/documents")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Process document and extract text
        
        Args:
            file_content: Binary file content
            filename: Original filename
            content_type: MIME type
            
        Returns:
            Processing result with extracted text and analysis
        """
        try:
            # Validate file size
            if len(file_content) > self.MAX_FILE_SIZE:
                return {
                    "success": False,
                    "error": f"File too large. Maximum size: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
                }
            
            # Determine file type
            file_ext = filename.split('.')[-1].lower()
            
            # Extract text based on file type
            if file_ext == 'pdf':
                text = self._extract_pdf_text(file_content)
            elif file_ext in ['docx', 'doc']:
                text = self._extract_docx_text(file_content)
            elif file_ext == 'txt':
                text = file_content.decode('utf-8')
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file format: {file_ext}"
                }
            
            # Analyze text
            analysis = await self._analyze_text(text, filename)
            
            return {
                "success": True,
                "text_content": text,
                "analysis": analysis,
                "file_format": file_ext,
                "file_size": len(file_content),
                "word_count": len(text.split()),
                "character_count": len(text),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        import io
        
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text())
        
        return "\n".join(text)
    
    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        import io
        
        docx_file = io.BytesIO(file_content)
        doc = DocxDocument(docx_file)
        
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        
        return "\n".join(text)
    
    async def _analyze_text(self, text: str, filename: str) -> Dict:
        """Analyze document text for security keywords and technologies"""
        
        words = text.lower().split()
        
        # Technology detection
        tech_keywords = {
            'AWS': ['aws', 'amazon web services', 'ec2', 'lambda', 's3'],
            'Kubernetes': ['kubernetes', 'k8s', 'pods'],
            'Docker': ['docker', 'container'],
            'Database': ['database', 'mysql', 'postgresql', 'mongodb'],
            'API': ['api', 'rest', 'graphql'],
            'Web Application': ['web', 'http', 'https']
        }
        
        technologies = []
        for tech, keywords in tech_keywords.items():
            if any(kw in text.lower() for kw in keywords):
                technologies.append(tech)
        
        # Security keyword detection
        security_terms = [
            'authentication', 'authorization', 'encryption', 'security',
            'vulnerability', 'threat', 'risk', 'compliance'
        ]
        
        security_keywords = [term for term in security_terms if term in text.lower()]
        
        # Key insights
        key_insights = []
        if 'architecture' in text.lower():
            key_insights.append("Contains architectural information")
        if 'security' in text.lower():
            key_insights.append("Contains security considerations")
        
        return {
            "technologies": technologies,
            "security_keywords": security_keywords,
            "key_insights": key_insights,
            "has_architecture_info": 'architecture' in text.lower(),
            "security_concerns": len(security_keywords),
            "complexity_score": min(len(technologies) * 2, 10)
        }


# Global instance
document_processor = DocumentProcessor()
