from typing import Dict, List, Optional, Any
from agents import Agent, function_tool
from pydantic import BaseModel
from utils.azure_openai_client import AzureOpenAIClient
from utils.document_processor import DocumentProcessor

class GeneratedDocument(BaseModel):
    """Structured output for generated test documents"""
    content: str
    document_type: str  # 'Test Plan' or 'Test Cases'
    ticket_key: str
    validation_score: float  # 0.0 to 1.0
    issues: List[str] = []
    suggestions: List[str] = []
    word_count: int
    section_count: int

class ValidationResult(BaseModel):
    """Document validation result"""
    is_valid: bool
    score: float
    issues: List[str]
    suggestions: List[str]
    missing_sections: List[str] = []

class GenerationContext:
    """Context for document generation operations"""
    def __init__(self):
        self.ai_client = AzureOpenAIClient()
        self.doc_processor = DocumentProcessor()
        self.generated_documents = {}

@function_tool
def generate_test_plan(consolidated_content_path: str, ticket_key: str, context: GenerationContext) -> GeneratedDocument:
    """Generate comprehensive test plan using consolidated content"""
    try:
        content = context.ai_client.generate_test_plan(consolidated_content_path, ticket_key)
        
        # Validate the generated content
        validation = validate_document_content(content, "Test Plan", context)
        
        # Count sections and words
        sections = content.count('#')
        words = len(content.split())
        
        doc = GeneratedDocument(
            content=content,
            document_type="Test Plan",
            ticket_key=ticket_key,
            validation_score=validation.score,
            issues=validation.issues,
            suggestions=validation.suggestions,
            word_count=words,
            section_count=sections
        )
        
        context.generated_documents[ticket_key] = doc
        return doc
        
    except Exception as e:
        raise Exception(f"Failed to generate test plan: {str(e)}")

@function_tool
def generate_test_cases(consolidated_content_path: str, ticket_key: str, context: GenerationContext) -> GeneratedDocument:
    """Generate comprehensive test cases using consolidated content"""
    try:
        content = context.ai_client.generate_test_cases(consolidated_content_path, ticket_key)
        
        # Validate the generated content
        validation = validate_document_content(content, "Test Cases", context)
        
        # Count test cases and words
        test_case_count = content.lower().count('test case')
        words = len(content.split())
        
        doc = GeneratedDocument(
            content=content,
            document_type="Test Cases",
            ticket_key=ticket_key,
            validation_score=validation.score,
            issues=validation.issues,
            suggestions=validation.suggestions,
            word_count=words,
            section_count=test_case_count
        )
        
        context.generated_documents[ticket_key] = doc
        return doc
        
    except Exception as e:
        raise Exception(f"Failed to generate test cases: {str(e)}")

@function_tool
def validate_document_content(content: str, document_type: str, context: GenerationContext) -> ValidationResult:
    """Validate generated test documentation content"""
    validation_result = context.ai_client.validate_generated_content(content, document_type.replace(" ", "_").lower())
    
    # Calculate validation score
    score = 1.0
    if validation_result["issues"]:
        score -= len(validation_result["issues"]) * 0.2
    if validation_result["suggestions"]:
        score -= len(validation_result["suggestions"]) * 0.1
    
    score = max(0.0, min(1.0, score))  # Clamp between 0 and 1
    
    return ValidationResult(
        is_valid=validation_result["is_valid"],
        score=score,
        issues=validation_result["issues"],
        suggestions=validation_result["suggestions"]
    )

@function_tool
def refine_document_with_feedback(ticket_key: str, feedback: str, context: GenerationContext) -> GeneratedDocument:
    """Refine document based on user feedback"""
    if ticket_key not in context.generated_documents:
        raise Exception(f"No document found for ticket {ticket_key}")
    
    current_doc = context.generated_documents[ticket_key]
    
    try:
        updated_content = context.ai_client.get_user_feedback_response(feedback, current_doc.content)
        
        # Validate the updated content
        validation = validate_document_content(updated_content, current_doc.document_type, context)
        
        # Update the document
        updated_doc = GeneratedDocument(
            content=updated_content,
            document_type=current_doc.document_type,
            ticket_key=ticket_key,
            validation_score=validation.score,
            issues=validation.issues,
            suggestions=validation.suggestions,
            word_count=len(updated_content.split()),
            section_count=updated_content.count('#') if current_doc.document_type == "Test Plan" else updated_content.lower().count('test case')
        )
        
        context.generated_documents[ticket_key] = updated_doc
        return updated_doc
        
    except Exception as e:
        raise Exception(f"Failed to refine document: {str(e)}")

@function_tool
def save_final_document(ticket_key: str, context: GenerationContext) -> str:
    """Save the final document to file"""
    if ticket_key not in context.generated_documents:
        raise Exception(f"No document found for ticket {ticket_key}")
    
    doc = context.generated_documents[ticket_key]
    
    try:
        filename = f"FINAL-{doc.document_type.lower().replace(' ', '-')}-{ticket_key}.md"
        filepath = context.doc_processor.save_markdown_file(doc.content, filename)
        return filepath
        
    except Exception as e:
        raise Exception(f"Failed to save document: {str(e)}")

@function_tool
def get_document_metrics(ticket_key: str, context: GenerationContext) -> Dict[str, Any]:
    """Get metrics for the generated document"""
    if ticket_key not in context.generated_documents:
        return {"error": f"No document found for ticket {ticket_key}"}
    
    doc = context.generated_documents[ticket_key]
    
    return {
        "document_type": doc.document_type,
        "word_count": doc.word_count,
        "section_count": doc.section_count,
        "validation_score": doc.validation_score,
        "issues_count": len(doc.issues),
        "suggestions_count": len(doc.suggestions),
        "quality_rating": "Excellent" if doc.validation_score >= 0.9 else "Good" if doc.validation_score >= 0.7 else "Needs Improvement"
    }

def create_generation_agent() -> Agent[GenerationContext]:
    """Create the test document generation specialist agent"""
    return Agent[GenerationContext](
        name="GenerationAgent",
        instructions="""
        You are a test document generation specialist responsible for:
        1. Generating comprehensive Test Plans for Epic tickets
        2. Generating detailed Test Cases for Story/Task tickets
        3. Validating generated content for quality and completeness
        4. Refining documents based on user feedback
        5. Providing document metrics and quality assessments
        
        Always generate high-quality, professional test documentation.
        Follow industry standards and best practices.
        Validate content thoroughly and suggest improvements.
        """,
        model="gpt-4",
        tools=[
            generate_test_plan,
            generate_test_cases,
            validate_document_content,
            refine_document_with_feedback,
            save_final_document,
            get_document_metrics
        ],
        output_type=GeneratedDocument
    ) 