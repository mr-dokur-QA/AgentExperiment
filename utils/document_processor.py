import os
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
import base64
from urllib.parse import urlparse, urljoin
import PyPDF2
from docx import Document
from bs4 import BeautifulSoup
import markdown
from config import Config

class DocumentProcessor:
    """Document processor for TestGenius chatbot"""
    
    def __init__(self):
        """Initialize document processor"""
        self.documents_folder = Config.ensure_documents_folder()
        self.confluence_server = Config.CONFLUENCE_SERVER
        self.confluence_username = Config.CONFLUENCE_USERNAME
        self.confluence_api_token = Config.CONFLUENCE_API_TOKEN
    
    def save_jira_content(self, ticket_data: Dict[str, Any], filename_prefix: str = None) -> str:
        """Save Jira ticket content to markdown file"""
        if not filename_prefix:
            filename_prefix = f"jira-{ticket_data['key']}"
        
        filename = f"{filename_prefix}-content.md"
        filepath = os.path.join(self.documents_folder, filename)
        
        # Format Jira content as markdown
        content = self._format_jira_as_markdown(ticket_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _format_jira_as_markdown(self, ticket_data: Dict[str, Any]) -> str:
        """Format Jira ticket data as markdown"""
        content = f"""# Jira Ticket: {ticket_data['key']}

## Summary
{ticket_data['summary']}

## Details
- **Issue Type**: {ticket_data['issue_type']}
- **Status**: {ticket_data['status']}
- **Priority**: {ticket_data['priority']}
- **Assignee**: {ticket_data['assignee']}
- **Reporter**: {ticket_data['reporter']}
- **Project**: {ticket_data['project']} ({ticket_data['project_key']})
- **Created**: {ticket_data['created']}
- **Updated**: {ticket_data['updated']}

## Description
{ticket_data['description'] or 'No description provided'}

"""
        
        # Add Epic Link if present
        if ticket_data.get('epic_link'):
            content += f"## Epic Link\n{ticket_data['epic_link']}\n\n"
        
        # Add Parent if present
        if ticket_data.get('parent'):
            parent = ticket_data['parent']
            content += f"## Parent\n- **Key**: {parent['key']}\n- **Summary**: {parent['summary']}\n- **Type**: {parent['issue_type']}\n\n"
        
        # Add Subtasks if present
        if ticket_data.get('subtasks'):
            content += "## Subtasks\n"
            for subtask in ticket_data['subtasks']:
                content += f"- **{subtask['key']}**: {subtask['summary']} ({subtask['status']})\n"
            content += "\n"
        
        # Add Components if present
        if ticket_data.get('components'):
            content += f"## Components\n{', '.join(ticket_data['components'])}\n\n"
        
        # Add Labels if present
        if ticket_data.get('labels'):
            content += f"## Labels\n{', '.join(ticket_data['labels'])}\n\n"
        
        # Add Fix Versions if present
        if ticket_data.get('fix_versions'):
            content += f"## Fix Versions\n{', '.join(ticket_data['fix_versions'])}\n\n"
        
        # Add Attachments if present
        if ticket_data.get('attachments'):
            content += "## Attachments\n"
            for attachment in ticket_data['attachments']:
                content += f"- **{attachment['filename']}** ({attachment['size']} bytes) - {attachment['content_type']}\n"
                content += f"  - Created: {attachment['created']} by {attachment['author']}\n"
            content += "\n"
        
        return content
    
    def identify_prd_attachments(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify PRD attachments from Jira ticket"""
        prd_attachments = []
        
        if not ticket_data.get('attachments'):
            return prd_attachments
        
        # Common PRD file patterns
        prd_patterns = [
            r'.*prd.*\.pdf$',
            r'.*product.*requirement.*\.pdf$',
            r'.*requirement.*document.*\.pdf$',
            r'.*functional.*spec.*\.pdf$',
            r'.*business.*requirement.*\.pdf$',
            r'.*prd.*\.docx?$',
            r'.*product.*requirement.*\.docx?$',
            r'.*requirement.*document.*\.docx?$'
        ]
        
        for attachment in ticket_data['attachments']:
            filename_lower = attachment['filename'].lower()
            
            for pattern in prd_patterns:
                if re.match(pattern, filename_lower, re.IGNORECASE):
                    prd_attachments.append(attachment)
                    break
        
        return prd_attachments
    
    def identify_hld_lld_attachments(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify HLD/LLD attachments from Jira ticket"""
        design_attachments = []
        
        if not ticket_data.get('attachments'):
            return design_attachments
        
        # Common HLD/LLD file patterns
        design_patterns = [
            r'.*hld.*\.pdf$',
            r'.*high.*level.*design.*\.pdf$',
            r'.*lld.*\.pdf$',
            r'.*low.*level.*design.*\.pdf$',
            r'.*technical.*design.*\.pdf$',
            r'.*architecture.*\.pdf$',
            r'.*design.*document.*\.pdf$',
            r'.*hld.*\.docx?$',
            r'.*lld.*\.docx?$',
            r'.*design.*\.docx?$'
        ]
        
        for attachment in ticket_data['attachments']:
            filename_lower = attachment['filename'].lower()
            
            for pattern in design_patterns:
                if re.match(pattern, filename_lower, re.IGNORECASE):
                    design_attachments.append(attachment)
                    break
        
        return design_attachments
    
    def process_attachment(self, attachment: Dict[str, Any], jira_client, attachment_type: str, source_ticket: str, attachment_number: int) -> Optional[str]:
        """Process and save attachment content"""
        try:
            # Download attachment content
            content_bytes = jira_client.download_attachment(
                attachment['download_url'], 
                attachment['filename']
            )
            
            # Extract text content based on file type
            text_content = self._extract_text_from_bytes(
                content_bytes, 
                attachment['filename'], 
                attachment.get('content_type', '')
            )
            
            if not text_content:
                return None
            
            # Generate filename
            filename = f"{attachment_type}-from-{source_ticket}-attachment{attachment_number}-content.md"
            filepath = os.path.join(self.documents_folder, filename)
            
            # Format content as markdown
            markdown_content = f"""# {attachment_type.upper()} Document: {attachment['filename']}

**Source**: Jira Ticket {source_ticket}
**File Type**: {attachment.get('content_type', 'unknown')}
**Size**: {attachment['size']} bytes
**Created**: {attachment['created']} by {attachment['author']}

## Content

{text_content}
"""
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return filepath
            
        except Exception as e:
            print(f"Error processing attachment {attachment['filename']}: {str(e)}")
            return None
    
    def _extract_text_from_bytes(self, content_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
        """Extract text content from file bytes"""
        try:
            # PDF files
            if filename.lower().endswith('.pdf') or 'pdf' in content_type.lower():
                return self._extract_pdf_text(content_bytes)
            
            # Word documents
            elif filename.lower().endswith(('.docx', '.doc')) or 'word' in content_type.lower():
                return self._extract_docx_text(content_bytes)
            
            # Text files
            elif filename.lower().endswith(('.txt', '.md')) or 'text' in content_type.lower():
                return content_bytes.decode('utf-8', errors='ignore')
            
            # HTML files
            elif filename.lower().endswith('.html') or 'html' in content_type.lower():
                return self._extract_html_text(content_bytes)
            
            else:
                # Try to decode as text
                try:
                    return content_bytes.decode('utf-8', errors='ignore')
                except:
                    return None
                    
        except Exception as e:
            print(f"Error extracting text from {filename}: {str(e)}")
            return None
    
    def _extract_pdf_text(self, content_bytes: bytes) -> Optional[str]:
        """Extract text from PDF bytes"""
        try:
            import io
            pdf_file = io.BytesIO(content_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting PDF text: {str(e)}")
            return None
    
    def _extract_docx_text(self, content_bytes: bytes) -> Optional[str]:
        """Extract text from DOCX bytes"""
        try:
            import io
            docx_file = io.BytesIO(content_bytes)
            doc = Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting DOCX text: {str(e)}")
            return None
    
    def _extract_html_text(self, content_bytes: bytes) -> Optional[str]:
        """Extract text from HTML bytes"""
        try:
            html_content = content_bytes.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
            
        except Exception as e:
            print(f"Error extracting HTML text: {str(e)}")
            return None
    
    def fetch_confluence_page(self, page_url: str, source_ticket: str, page_number: int) -> Optional[str]:
        """Fetch and save Confluence page content"""
        try:
            # Extract page ID from URL
            page_id = self._extract_confluence_page_id(page_url)
            if not page_id:
                return None
            
            # Fetch page content via Confluence API
            api_url = f"{self.confluence_server}/rest/api/content/{page_id}?expand=body.storage,version"
            
            auth_string = f"{self.confluence_username}:{self.confluence_api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Accept': 'application/json'
            }
            
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            page_data = response.json()
            
            # Extract content
            title = page_data.get('title', 'Unknown Page')
            content_html = page_data.get('body', {}).get('storage', {}).get('value', '')
            
            # Convert HTML to text
            soup = BeautifulSoup(content_html, 'html.parser')
            text_content = soup.get_text()
            
            # Generate filename
            filename = f"conf-from-{source_ticket}-page{page_number}-content.md"
            filepath = os.path.join(self.documents_folder, filename)
            
            # Format content as markdown
            markdown_content = f"""# Confluence Page: {title}

**Source**: {page_url}
**Referenced from**: Jira Ticket {source_ticket}
**Version**: {page_data.get('version', {}).get('number', 'Unknown')}

## Content

{text_content}
"""
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return filepath
            
        except Exception as e:
            print(f"Error fetching Confluence page {page_url}: {str(e)}")
            return None
    
    def _extract_confluence_page_id(self, page_url: str) -> Optional[str]:
        """Extract page ID from Confluence URL"""
        # Pattern for page ID in URL
        patterns = [
            r'/pages/(\d+)/',
            r'pageId=(\d+)',
            r'/(\d+)/'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_url)
            if match:
                return match.group(1)
        
        return None
    
    def consolidate_documents(self, document_files: List[str]) -> str:
        """Consolidate all document files into final-content.md"""
        final_content = "# Consolidated Content for Test Documentation Generation\n\n"
        
        for doc_file in document_files:
            if os.path.exists(doc_file):
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    final_content += f"\n---\n\n{content}\n\n"
        
        # Save consolidated content
        final_filepath = os.path.join(self.documents_folder, "final-content.md")
        with open(final_filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return final_filepath
    
    def save_markdown_file(self, content: str, filename: str) -> str:
        """Save markdown content to file"""
        filepath = os.path.join(self.documents_folder, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def list_saved_documents(self) -> List[str]:
        """List all saved document files"""
        if not os.path.exists(self.documents_folder):
            return []
        
        return [f for f in os.listdir(self.documents_folder) if f.endswith('.md')]
    
    def save_user_content(self, content: str, filename: str) -> str:
        """Save user-provided content to a markdown file"""
        filepath = os.path.join(self.documents_folder, filename)
        
        # Format content as markdown with metadata
        markdown_content = f"""# User-Provided Document

**Source**: User Input
**Created**: {self._get_current_timestamp()}

## Content

{content}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return filepath
    
    def fetch_document_from_url(self, url: str, content_type: str, ticket_key: str) -> Optional[str]:
        """Fetch document content from a URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine content type from response or URL
            detected_content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in detected_content_type or url.lower().endswith('.pdf'):
                text_content = self._extract_pdf_text(response.content)
            elif 'word' in detected_content_type or url.lower().endswith(('.doc', '.docx')):
                text_content = self._extract_docx_text(response.content)
            elif 'html' in detected_content_type or url.lower().endswith('.html'):
                text_content = self._extract_html_text(response.content)
            else:
                # Try to decode as text
                text_content = response.text
            
            if not text_content:
                return None
            
            # Generate filename
            filename = f"user-provided-{content_type}-{ticket_key}-from-url.md"
            filepath = os.path.join(self.documents_folder, filename)
            
            # Format content as markdown
            markdown_content = f"""# {content_type.title()} Document from URL

**Source**: {url}
**Ticket**: {ticket_key}
**Content Type**: {detected_content_type}
**Fetched**: {self._get_current_timestamp()}

## Content

{text_content}
"""
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return filepath
            
        except Exception as e:
            print(f"Error fetching document from URL {url}: {str(e)}")
            return None
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 