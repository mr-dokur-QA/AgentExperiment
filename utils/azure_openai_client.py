import os
from openai import AzureOpenAI
from typing import Dict, List, Optional, Any
from config import Config
from prompt import CHAT_META_PROMPT

class AzureOpenAIClient:
    """Azure OpenAI client for TestGenius chatbot"""
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        self.client = AzureOpenAI(
            api_key=Config.AZURE_OPENAI_API_KEY,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT_NAME
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        
        # Initialize conversation history
        self.conversation_history = [
            {"role": "system", "content": CHAT_META_PROMPT}
        ]
    
    def chat_completion(self, user_message: str, context: Optional[str] = None) -> str:
        """Get chat completion from Azure OpenAI"""
        try:
            # Prepare the message
            if context:
                enhanced_message = f"{user_message}\n\nContext:\n{context}"
            else:
                enhanced_message = user_message
            
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user", 
                "content": enhanced_message
            })
            
            # Get completion
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=self.conversation_history,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extract assistant response
            assistant_message = response.choices[0].message.content
            
            # Add assistant response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            return f"Error getting response from Azure OpenAI: {str(e)}"
    
    def generate_test_plan(self, consolidated_content: str, ticket_key: str) -> str:
        """Generate test plan using consolidated content"""
        try:
            # Read the consolidated content
            with open(consolidated_content, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Prepare the prompt for test plan generation
            test_plan_prompt = f"""
Based on the consolidated content below, generate a comprehensive Test Plan for Epic {ticket_key}. 
Follow the Test Plan template and guidelines specified in the CHAT_META_PROMPT.

Use ONLY the information provided in the consolidated content. Do not invent or assume details not present in the source documents.

Consolidated Content:
{content}

Generate a detailed Test Plan following the exact format specified in section A of the document generation guidelines.
"""
            
            # Generate test plan
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": CHAT_META_PROMPT},
                    {"role": "user", "content": test_plan_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating test plan: {str(e)}"
    
    def generate_test_cases(self, consolidated_content: str, ticket_key: str) -> str:
        """Generate test cases using consolidated content"""
        try:
            # Read the consolidated content
            with open(consolidated_content, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Prepare the prompt for test cases generation
            test_cases_prompt = f"""
Based on the consolidated content below, generate comprehensive Test Cases for ticket {ticket_key}. 
Follow the Test Cases template and guidelines specified in the CHAT_META_PROMPT.

Use ONLY the information provided in the consolidated content. Do not invent or assume details not present in the source documents.

Generate between 8 and 12 distinct test cases covering positive, negative, edge cases, and boundary analysis as appropriate.

Consolidated Content:
{content}

Generate detailed Test Cases following the exact format specified in section B of the document generation guidelines.
"""
            
            # Generate test cases
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": CHAT_META_PROMPT},
                    {"role": "user", "content": test_cases_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating test cases: {str(e)}"
    
    def get_user_feedback_response(self, user_feedback: str, current_document: str) -> str:
        """Process user feedback and generate updated document"""
        try:
            feedback_prompt = f"""
The user has provided feedback on the generated test document. Please review their feedback and update the document accordingly.

Current Document:
{current_document}

User Feedback:
{user_feedback}

Please provide the updated document incorporating the user's feedback. Maintain the same format and structure while addressing their specific requests.
"""
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": CHAT_META_PROMPT},
                    {"role": "user", "content": feedback_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error processing feedback: {str(e)}"
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = [
            {"role": "system", "content": CHAT_META_PROMPT}
        ]
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation"""
        if len(self.conversation_history) <= 1:
            return "No conversation history available."
        
        # Extract user and assistant messages (skip system message)
        messages = self.conversation_history[1:]
        
        summary = "Conversation Summary:\n\n"
        for i, message in enumerate(messages, 1):
            role = "User" if message["role"] == "user" else "TestGenius"
            content = message["content"][:200] + "..." if len(message["content"]) > 200 else message["content"]
            summary += f"{i}. {role}: {content}\n\n"
        
        return summary
    
    def validate_generated_content(self, content: str, document_type: str) -> Dict[str, Any]:
        """Validate generated test documentation content"""
        validation_result = {
            "is_valid": True,
            "issues": [],
            "suggestions": []
        }
        
        # Basic validation checks
        if not content or len(content.strip()) < 100:
            validation_result["is_valid"] = False
            validation_result["issues"].append("Content is too short or empty")
        
        # Check for required sections based on document type
        if document_type.lower() == "test_plan":
            required_sections = [
                "Introduction", "Scope of Testing", "Test Objectives", 
                "Testing Approach", "Test Schedule", "Test Environment"
            ]
        else:  # test_cases
            required_sections = [
                "Test Case ID", "Test Case Title", "Description", 
                "Preconditions", "Test Steps", "Expected Result"
            ]
        
        missing_sections = []
        for section in required_sections:
            if section.lower() not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            validation_result["suggestions"].append(
                f"Consider adding these sections: {', '.join(missing_sections)}"
            )
        
        # Check for placeholder content
        placeholders = ["TBD", "TODO", "[PLACEHOLDER]", "Information not found"]
        placeholder_count = sum(content.lower().count(placeholder.lower()) for placeholder in placeholders)
        
        if placeholder_count > 5:
            validation_result["suggestions"].append(
                "Document contains many placeholders. Consider providing more specific information."
            )
        
        return validation_result 