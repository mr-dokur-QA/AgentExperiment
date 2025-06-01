from typing import Dict, List, Optional, Any
from agents import Agent, function_tool
from pydantic import BaseModel
from utils.jira_client import JiraClient

class JiraTicketInfo(BaseModel):
    """Structured output for Jira ticket information"""
    key: str
    summary: str
    issue_type: str
    status: str
    priority: str
    description: str
    epic_link: Optional[str] = None
    parent: Optional[Dict[str, str]] = None
    attachments: List[Dict[str, Any]] = []
    has_prd_attachments: bool = False
    has_design_attachments: bool = False
    confluence_links: List[str] = []

class JiraContext:
    """Context for Jira operations"""
    def __init__(self):
        self.jira_client = JiraClient()
        self.processed_tickets = {}

@function_tool
def extract_ticket_key(input_text: str, context: JiraContext) -> str:
    """Extract Jira ticket key from URL or direct input"""
    return context.jira_client.extract_ticket_key(input_text)

@function_tool
def fetch_ticket_details(ticket_key: str, context: JiraContext) -> JiraTicketInfo:
    """Fetch comprehensive ticket details from Jira"""
    try:
        ticket_data = context.jira_client.get_ticket_details(ticket_key)
        
        # Analyze attachments
        prd_attachments = context.jira_client.identify_prd_attachments(ticket_data)
        design_attachments = context.jira_client.identify_hld_lld_attachments(ticket_data)
        confluence_links = context.jira_client.extract_confluence_links(ticket_data.get('description', ''))
        
        # Store in context for later use
        context.processed_tickets[ticket_key] = ticket_data
        
        return JiraTicketInfo(
            key=ticket_data['key'],
            summary=ticket_data['summary'],
            issue_type=ticket_data['issue_type'],
            status=ticket_data['status'],
            priority=ticket_data['priority'],
            description=ticket_data['description'],
            epic_link=ticket_data.get('epic_link'),
            parent=ticket_data.get('parent'),
            attachments=ticket_data.get('attachments', []),
            has_prd_attachments=len(prd_attachments) > 0,
            has_design_attachments=len(design_attachments) > 0,
            confluence_links=confluence_links
        )
    except Exception as e:
        raise Exception(f"Failed to fetch ticket {ticket_key}: {str(e)}")

@function_tool
def find_parent_epic(ticket_key: str, context: JiraContext) -> Optional[JiraTicketInfo]:
    """Find and fetch parent Epic for a given ticket"""
    try:
        epic_data = context.jira_client.find_parent_epic(ticket_key)
        if epic_data:
            return fetch_ticket_details(epic_data['key'], context)
        return None
    except Exception as e:
        print(f"Warning: Could not find parent Epic for {ticket_key}: {str(e)}")
        return None

@function_tool
def determine_document_type(ticket_info: JiraTicketInfo) -> str:
    """Determine whether to create Test Plan or Test Cases based on ticket type"""
    if ticket_info.issue_type.lower() == 'epic':
        return "Test Plan"
    else:
        return "Test Cases"

def create_jira_agent() -> Agent[JiraContext]:
    """Create the Jira specialist agent"""
    return Agent[JiraContext](
        name="JiraAgent",
        instructions="""
        You are a Jira specialist agent responsible for:
        1. Extracting ticket keys from user input
        2. Fetching comprehensive ticket details
        3. Finding parent Epics for non-Epic tickets
        4. Analyzing attachments and links
        5. Determining appropriate document type (Test Plan vs Test Cases)
        
        Always provide structured, accurate information about Jira tickets.
        If you encounter errors, explain them clearly and suggest alternatives.
        """,
        model="gpt-4",
        tools=[
            extract_ticket_key,
            fetch_ticket_details,
            find_parent_epic,
            determine_document_type
        ],
        output_type=JiraTicketInfo
    ) 