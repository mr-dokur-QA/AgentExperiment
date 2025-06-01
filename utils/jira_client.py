import re
import requests
from jira import JIRA
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import base64
from config import Config

class JiraClient:
    """Jira client for TestGenius chatbot"""
    
    def __init__(self):
        """Initialize Jira client with configuration"""
        self.server = Config.JIRA_SERVER
        self.username = Config.JIRA_USERNAME
        self.api_token = Config.JIRA_API_TOKEN
        
        # Initialize JIRA client
        self.jira = JIRA(
            server=self.server,
            basic_auth=(self.username, self.api_token)
        )
    
    def extract_ticket_key(self, input_text: str) -> Optional[str]:
        """Extract Jira ticket key from URL or direct key input"""
        # Pattern for Jira ticket key (PROJECT-123 format)
        key_pattern = r'[A-Z][A-Z0-9]+-\d+'
        
        # If it's a URL, extract from it
        if input_text.startswith('http'):
            parsed_url = urlparse(input_text)
            path = parsed_url.path
            # Look for ticket key in URL path
            match = re.search(key_pattern, path)
            if match:
                return match.group()
        else:
            # Direct key input
            match = re.search(key_pattern, input_text.upper())
            if match:
                return match.group()
        
        return None
    
    def get_ticket_details(self, ticket_key: str) -> Dict[str, Any]:
        """Fetch comprehensive ticket details from Jira"""
        try:
            issue = self.jira.issue(ticket_key, expand='attachment,changelog')
            
            # Extract key information
            ticket_data = {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': issue.fields.description or '',
                'issue_type': issue.fields.issuetype.name,
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                'created': str(issue.fields.created),
                'updated': str(issue.fields.updated),
                'project': issue.fields.project.name,
                'project_key': issue.fields.project.key,
                'attachments': [],
                'epic_link': None,
                'parent': None,
                'subtasks': [],
                'components': [comp.name for comp in issue.fields.components] if issue.fields.components else [],
                'labels': issue.fields.labels or [],
                'fix_versions': [v.name for v in issue.fields.fixVersions] if issue.fields.fixVersions else []
            }
            
            # Handle Epic Link (for stories/tasks under epics)
            if hasattr(issue.fields, 'customfield_10014') and issue.fields.customfield_10014:
                ticket_data['epic_link'] = issue.fields.customfield_10014
            
            # Handle Parent (for subtasks)
            if hasattr(issue.fields, 'parent') and issue.fields.parent:
                ticket_data['parent'] = {
                    'key': issue.fields.parent.key,
                    'summary': issue.fields.parent.fields.summary,
                    'issue_type': issue.fields.parent.fields.issuetype.name
                }
            
            # Handle Subtasks
            if hasattr(issue.fields, 'subtasks') and issue.fields.subtasks:
                ticket_data['subtasks'] = [
                    {
                        'key': subtask.key,
                        'summary': subtask.fields.summary,
                        'status': subtask.fields.status.name
                    }
                    for subtask in issue.fields.subtasks
                ]
            
            # Process attachments
            if issue.fields.attachment:
                for attachment in issue.fields.attachment:
                    attachment_info = {
                        'id': attachment.id,
                        'filename': attachment.filename,
                        'size': attachment.size,
                        'created': str(attachment.created),
                        'author': attachment.author.displayName,
                        'content_type': getattr(attachment, 'mimeType', 'unknown'),
                        'download_url': attachment.content
                    }
                    ticket_data['attachments'].append(attachment_info)
            
            return ticket_data
            
        except Exception as e:
            raise Exception(f"Failed to fetch ticket {ticket_key}: {str(e)}")
    
    def find_parent_epic(self, ticket_key: str) -> Optional[Dict[str, Any]]:
        """Find parent Epic for a given ticket"""
        try:
            # First try to get the ticket details to check for epic link
            ticket_details = self.get_ticket_details(ticket_key)
            
            # If ticket has an epic link, fetch that epic
            if ticket_details.get('epic_link'):
                return self.get_ticket_details(ticket_details['epic_link'])
            
            # If no direct epic link, search using JQL
            jql_query = f'project = {ticket_details["project_key"]} AND issuetype = Epic AND issueFunction in linkedIssuesOf("key = {ticket_key}")'
            
            try:
                issues = self.jira.search_issues(jql_query, maxResults=1)
                if issues:
                    return self.get_ticket_details(issues[0].key)
            except:
                # If linkedIssuesOf doesn't work, try alternative approach
                pass
            
            # Alternative: Search for epics in the same project and check if this ticket is mentioned
            epic_search_jql = f'project = {ticket_details["project_key"]} AND issuetype = Epic'
            epics = self.jira.search_issues(epic_search_jql, maxResults=50)
            
            for epic in epics:
                # Check if the ticket is linked to this epic
                epic_details = self.get_ticket_details(epic.key)
                if ticket_key in epic_details.get('description', ''):
                    return epic_details
            
            return None
            
        except Exception as e:
            print(f"Warning: Could not find parent Epic for {ticket_key}: {str(e)}")
            return None
    
    def download_attachment(self, attachment_url: str, filename: str) -> bytes:
        """Download attachment content from Jira"""
        try:
            # Create authentication header
            auth_string = f"{self.username}:{self.api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Accept': 'application/octet-stream'
            }
            
            response = requests.get(attachment_url, headers=headers)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            raise Exception(f"Failed to download attachment {filename}: {str(e)}")
    
    def extract_confluence_links(self, text: str) -> List[str]:
        """Extract Confluence page URLs from text"""
        if not text:
            return []
        
        # Pattern for Confluence URLs
        confluence_patterns = [
            r'https?://[^/]+/wiki/spaces/[^/]+/pages/\d+/[^\s\)]+',
            r'https?://[^/]+/display/[^/]+/[^\s\)]+',
            r'https?://[^/]+\.atlassian\.net/wiki/[^\s\)]+',
        ]
        
        links = []
        for pattern in confluence_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            links.extend(matches)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(links))
    
    def is_epic(self, ticket_data: Dict[str, Any]) -> bool:
        """Check if a ticket is an Epic based on issue type"""
        return ticket_data.get('issue_type', '').lower() == 'epic'
    
    def get_epic_stories(self, epic_key: str) -> List[Dict[str, Any]]:
        """Get all stories/tasks linked to an Epic"""
        try:
            # Search for issues linked to this epic
            jql_query = f'"Epic Link" = {epic_key}'
            
            issues = self.jira.search_issues(jql_query, maxResults=100)
            
            stories = []
            for issue in issues:
                story_data = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'issue_type': issue.fields.issuetype.name,
                    'status': issue.fields.status.name,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
                }
                stories.append(story_data)
            
            return stories
            
        except Exception as e:
            print(f"Warning: Could not fetch stories for Epic {epic_key}: {str(e)}")
            return []
    
    def search_tickets(self, jql_query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for tickets using JQL"""
        try:
            issues = self.jira.search_issues(jql_query, maxResults=max_results)
            
            results = []
            for issue in issues:
                ticket_data = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'issue_type': issue.fields.issuetype.name,
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else 'None'
                }
                results.append(ticket_data)
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to search tickets with JQL '{jql_query}': {str(e)}") 