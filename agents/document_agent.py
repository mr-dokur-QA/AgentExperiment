from typing import Dict, List, Optional, Any
from agents import Agent, function_tool
from pydantic import BaseModel
from utils.document_processor import DocumentProcessor
from utils.jira_client import JiraClient

class ProcessedDocument(BaseModel):
    """Structured output for processed documents"""
    filepath: str
    document_type: str  # 'jira', 'prd', 'hld', 'lld', 'confluence'
    source_ticket: str
    filename: str
    success: bool
    error_message: Optional[str] = None

class DocumentProcessingResult(BaseModel):
    """Result of document processing operation"""
    processed_documents: List[ProcessedDocument]
    total_documents: int
    successful_documents: int
    failed_documents: int
    final_content_path: Optional[str] = None
    missing_documents: List[str] = []
    user_provided_content: List[str] = []

class MissingDocumentRequest(BaseModel):
    """Request for missing document from user"""
    document_type: str  # 'prd', 'confluence', 'design'
    ticket_key: str
    message: str
    options: List[str]  # Available options for user

class DocumentContext:
    """Context for document processing operations"""
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.jira_client = JiraClient()
        self.processed_files = []
        self.missing_documents = []
        self.user_provided_content = []

@function_tool
def process_jira_content(ticket_data: Dict[str, Any], context: DocumentContext) -> ProcessedDocument:
    """Process and save Jira ticket content"""
    try:
        filepath = context.doc_processor.save_jira_content(ticket_data)
        context.processed_files.append(filepath)
        
        return ProcessedDocument(
            filepath=filepath,
            document_type="jira",
            source_ticket=ticket_data['key'],
            filename=f"jira-{ticket_data['key']}-content.md",
            success=True
        )
    except Exception as e:
        return ProcessedDocument(
            filepath="",
            document_type="jira",
            source_ticket=ticket_data['key'],
            filename="",
            success=False,
            error_message=str(e)
        )

@function_tool
def check_for_missing_documents(ticket_data: Dict[str, Any], context: DocumentContext) -> List[MissingDocumentRequest]:
    """Check for missing critical documents and prepare user requests"""
    missing_requests = []
    
    # Check for PRD attachments
    prd_attachments = context.doc_processor.identify_prd_attachments(ticket_data)
    if not prd_attachments:
        missing_requests.append(MissingDocumentRequest(
            document_type="prd",
            ticket_key=ticket_data['key'],
            message=f"No PRD (Product Requirements Document) found in {ticket_data['key']}. This is important for comprehensive test documentation.",
            options=[
                "Provide PRD content as text",
                "Provide PRD file path/URL", 
                "Skip PRD and continue with available information",
                "Check parent Epic for PRD"
            ]
        ))
        context.missing_documents.append("PRD")
    
    # Check for Confluence links
    confluence_links = context.jira_client.extract_confluence_links(ticket_data.get('description', ''))
    if not confluence_links:
        missing_requests.append(MissingDocumentRequest(
            document_type="confluence",
            ticket_key=ticket_data['key'],
            message=f"No Confluence page links found in {ticket_data['key']}. Additional documentation could improve test coverage.",
            options=[
                "Provide Confluence page URL(s)",
                "Provide additional documentation as text",
                "Skip Confluence and continue with available information"
            ]
        ))
        context.missing_documents.append("Confluence")
    
    # Check for design documents
    design_attachments = context.doc_processor.identify_hld_lld_attachments(ticket_data)
    if not design_attachments:
        missing_requests.append(MissingDocumentRequest(
            document_type="design",
            ticket_key=ticket_data['key'],
            message=f"No HLD/LLD (High/Low Level Design) documents found in {ticket_data['key']}. Design docs help create better test cases.",
            options=[
                "Provide design document file path/URL",
                "Provide design specifications as text",
                "Skip design docs and continue with available information"
            ]
        ))
        context.missing_documents.append("Design Documents")
    
    return missing_requests

@function_tool
def process_user_provided_content(content_type: str, content: str, ticket_key: str, context: DocumentContext) -> ProcessedDocument:
    """Process content provided by user for missing documents"""
    try:
        if content_type.lower() == "prd":
            filepath = context.doc_processor.save_user_content(content, f"user-provided-prd-{ticket_key}.md")
        elif content_type.lower() == "confluence":
            filepath = context.doc_processor.save_user_content(content, f"user-provided-confluence-{ticket_key}.md")
        elif content_type.lower() == "design":
            filepath = context.doc_processor.save_user_content(content, f"user-provided-design-{ticket_key}.md")
        else:
            filepath = context.doc_processor.save_user_content(content, f"user-provided-{content_type}-{ticket_key}.md")
        
        context.processed_files.append(filepath)
        context.user_provided_content.append(content_type)
        
        return ProcessedDocument(
            filepath=filepath,
            document_type=f"user-provided-{content_type.lower()}",
            source_ticket=ticket_key,
            filename=f"user-provided-{content_type.lower()}-{ticket_key}.md",
            success=True
        )
    except Exception as e:
        return ProcessedDocument(
            filepath="",
            document_type=f"user-provided-{content_type.lower()}",
            source_ticket=ticket_key,
            filename="",
            success=False,
            error_message=str(e)
        )

@function_tool
def process_user_provided_url(url: str, content_type: str, ticket_key: str, context: DocumentContext) -> ProcessedDocument:
    """Process URL provided by user (Confluence page, file URL, etc.)"""
    try:
        if "confluence" in url.lower():
            filepath = context.doc_processor.fetch_confluence_page(url, ticket_key, 1)
        else:
            # Try to fetch as a general document URL
            filepath = context.doc_processor.fetch_document_from_url(url, content_type, ticket_key)
        
        if filepath:
            context.processed_files.append(filepath)
            context.user_provided_content.append(content_type)
            
            return ProcessedDocument(
                filepath=filepath,
                document_type=f"user-provided-{content_type.lower()}",
                source_ticket=ticket_key,
                filename=f"user-provided-{content_type.lower()}-{ticket_key}",
                success=True
            )
        else:
            return ProcessedDocument(
                filepath="",
                document_type=f"user-provided-{content_type.lower()}",
                source_ticket=ticket_key,
                filename="",
                success=False,
                error_message="Could not fetch content from URL"
            )
    except Exception as e:
        return ProcessedDocument(
            filepath="",
            document_type=f"user-provided-{content_type.lower()}",
            source_ticket=ticket_key,
            filename="",
            success=False,
            error_message=str(e)
        )

@function_tool
def process_prd_attachments(ticket_data: Dict[str, Any], context: DocumentContext) -> List[ProcessedDocument]:
    """Process PRD attachments from Jira ticket"""
    results = []
    prd_attachments = context.doc_processor.identify_prd_attachments(ticket_data)
    
    if not prd_attachments:
        # No PRD attachments found - this will be handled by check_for_missing_documents
        return results
    
    for i, attachment in enumerate(prd_attachments, 1):
        try:
            filepath = context.doc_processor.process_attachment(
                attachment, context.jira_client, "prd", ticket_data['key'], i
            )
            
            if filepath:
                context.processed_files.append(filepath)
                results.append(ProcessedDocument(
                    filepath=filepath,
                    document_type="prd",
                    source_ticket=ticket_data['key'],
                    filename=attachment['filename'],
                    success=True
                ))
            else:
                results.append(ProcessedDocument(
                    filepath="",
                    document_type="prd",
                    source_ticket=ticket_data['key'],
                    filename=attachment['filename'],
                    success=False,
                    error_message="Could not extract content"
                ))
        except Exception as e:
            results.append(ProcessedDocument(
                filepath="",
                document_type="prd",
                source_ticket=ticket_data['key'],
                filename=attachment['filename'],
                success=False,
                error_message=str(e)
            ))
    
    return results

@function_tool
def process_design_attachments(ticket_data: Dict[str, Any], context: DocumentContext) -> List[ProcessedDocument]:
    """Process HLD/LLD attachments from Jira ticket"""
    results = []
    design_attachments = context.doc_processor.identify_hld_lld_attachments(ticket_data)
    
    if not design_attachments:
        # No design attachments found - this will be handled by check_for_missing_documents
        return results
    
    for i, attachment in enumerate(design_attachments, 1):
        try:
            doc_type = "hld" if "hld" in attachment['filename'].lower() or "high" in attachment['filename'].lower() else "lld"
            
            filepath = context.doc_processor.process_attachment(
                attachment, context.jira_client, doc_type, ticket_data['key'], i
            )
            
            if filepath:
                context.processed_files.append(filepath)
                results.append(ProcessedDocument(
                    filepath=filepath,
                    document_type=doc_type,
                    source_ticket=ticket_data['key'],
                    filename=attachment['filename'],
                    success=True
                ))
            else:
                results.append(ProcessedDocument(
                    filepath="",
                    document_type=doc_type,
                    source_ticket=ticket_data['key'],
                    filename=attachment['filename'],
                    success=False,
                    error_message="Could not extract content"
                ))
        except Exception as e:
            results.append(ProcessedDocument(
                filepath="",
                document_type="lld",
                source_ticket=ticket_data['key'],
                filename=attachment['filename'],
                success=False,
                error_message=str(e)
            ))
    
    return results

@function_tool
def process_confluence_links(confluence_links: List[str], source_ticket: str, context: DocumentContext) -> List[ProcessedDocument]:
    """Process Confluence page links"""
    results = []
    
    if not confluence_links:
        # No Confluence links found - this will be handled by check_for_missing_documents
        return results
    
    for i, link in enumerate(confluence_links, 1):
        try:
            filepath = context.doc_processor.fetch_confluence_page(link, source_ticket, i)
            
            if filepath:
                context.processed_files.append(filepath)
                results.append(ProcessedDocument(
                    filepath=filepath,
                    document_type="confluence",
                    source_ticket=source_ticket,
                    filename=f"confluence-page-{i}",
                    success=True
                ))
            else:
                results.append(ProcessedDocument(
                    filepath="",
                    document_type="confluence",
                    source_ticket=source_ticket,
                    filename=f"confluence-page-{i}",
                    success=False,
                    error_message="Could not fetch page"
                ))
        except Exception as e:
            results.append(ProcessedDocument(
                filepath="",
                document_type="confluence",
                source_ticket=source_ticket,
                filename=f"confluence-page-{i}",
                success=False,
                error_message=str(e)
            ))
    
    return results

@function_tool
def consolidate_documents(context: DocumentContext) -> str:
    """Consolidate all processed documents into final content"""
    try:
        final_path = context.doc_processor.consolidate_documents(context.processed_files)
        return final_path
    except Exception as e:
        raise Exception(f"Failed to consolidate documents: {str(e)}")

@function_tool
def get_processing_summary(context: DocumentContext) -> DocumentProcessingResult:
    """Get summary of document processing results"""
    successful_docs = [f for f in context.processed_files if f]
    failed_count = len(context.processed_files) - len(successful_docs)
    
    return DocumentProcessingResult(
        processed_documents=[],  # This would be populated with actual ProcessedDocument objects
        total_documents=len(context.processed_files),
        successful_documents=len(successful_docs),
        failed_documents=failed_count,
        missing_documents=context.missing_documents,
        user_provided_content=context.user_provided_content
    )

def create_document_agent() -> Agent[DocumentContext]:
    """Create the document processing specialist agent"""
    return Agent[DocumentContext](
        name="DocumentAgent",
        instructions="""
        You are a document processing specialist responsible for:
        1. Processing Jira ticket content into markdown
        2. Identifying and processing PRD attachments
        3. Processing HLD/LLD design documents
        4. Fetching and processing Confluence pages
        5. Handling missing documents by asking users for alternatives
        6. Consolidating all documents into final content
        
        IMPORTANT: When critical documents (PRD, Confluence, Design docs) are missing:
        - Use check_for_missing_documents to identify what's missing
        - Present clear options to the user
        - Process user-provided content or URLs
        - Continue gracefully if user chooses to skip
        
        Always process documents systematically and provide clear status updates.
        Handle errors gracefully and suggest alternatives when processing fails.
        """,
        model="gpt-4",
        tools=[
            process_jira_content,
            check_for_missing_documents,
            process_user_provided_content,
            process_user_provided_url,
            process_prd_attachments,
            process_design_attachments,
            process_confluence_links,
            consolidate_documents,
            get_processing_summary
        ],
        output_type=DocumentProcessingResult
    ) 