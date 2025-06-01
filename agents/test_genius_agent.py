from typing import Dict, List, Optional, Any, Union
from agents import Agent, Runner, AgentHooks
from pydantic import BaseModel
from dataclasses import dataclass

from .jira_agent import create_jira_agent, JiraContext, JiraTicketInfo
from .document_agent import create_document_agent, DocumentContext, DocumentProcessingResult
from .generation_agent import create_generation_agent, GenerationContext, GeneratedDocument

class WorkflowState(BaseModel):
    """Overall workflow state"""
    current_phase: str
    ticket_key: Optional[str] = None
    document_type: Optional[str] = None
    jira_info: Optional[JiraTicketInfo] = None
    processing_result: Optional[DocumentProcessingResult] = None
    generated_document: Optional[GeneratedDocument] = None
    final_document_path: Optional[str] = None
    errors: List[str] = []
    completed_phases: List[str] = []

@dataclass
class TestGeniusContext:
    """Combined context for all TestGenius operations"""
    jira_context: JiraContext
    document_context: DocumentContext
    generation_context: GenerationContext
    workflow_state: WorkflowState
    
    def __init__(self):
        self.jira_context = JiraContext()
        self.document_context = DocumentContext()
        self.generation_context = GenerationContext()
        self.workflow_state = WorkflowState(current_phase="initiation")

class TestGeniusHooks(AgentHooks[TestGeniusContext]):
    """Lifecycle hooks for TestGenius workflow"""
    
    def on_agent_start(self, context: TestGeniusContext, agent: Agent[TestGeniusContext]):
        """Called when agent starts"""
        print(f"🚀 Starting {agent.name} in phase: {context.workflow_state.current_phase}")
    
    def on_agent_end(self, context: TestGeniusContext, agent: Agent[TestGeniusContext], result: Any):
        """Called when agent completes"""
        print(f"✅ Completed {agent.name}")
        
        # Update workflow state based on agent completion
        if agent.name == "JiraAgent":
            context.workflow_state.current_phase = "document_processing"
            context.workflow_state.completed_phases.append("jira_analysis")
        elif agent.name == "DocumentAgent":
            context.workflow_state.current_phase = "generation"
            context.workflow_state.completed_phases.append("document_processing")
        elif agent.name == "GenerationAgent":
            context.workflow_state.current_phase = "review"
            context.workflow_state.completed_phases.append("generation")
    
    def on_tool_call(self, context: TestGeniusContext, agent: Agent[TestGeniusContext], tool_name: str, args: Dict[str, Any]):
        """Called before tool execution"""
        print(f"🔧 {agent.name} calling tool: {tool_name}")
    
    def on_tool_result(self, context: TestGeniusContext, agent: Agent[TestGeniusContext], tool_name: str, result: Any):
        """Called after tool execution"""
        print(f"✅ Tool {tool_name} completed")
    
    def on_error(self, context: TestGeniusContext, agent: Agent[TestGeniusContext], error: Exception):
        """Called when an error occurs"""
        error_msg = f"❌ Error in {agent.name}: {str(error)}"
        print(error_msg)
        context.workflow_state.errors.append(error_msg)

def dynamic_instructions(context: TestGeniusContext, agent: Agent[TestGeniusContext]) -> str:
    """Dynamic instructions based on workflow state"""
    base_instructions = """
    You are TestGenius, an AI-powered Test Documentation Assistant.
    You orchestrate the creation of comprehensive Test Plans and Test Cases.
    """
    
    phase = context.workflow_state.current_phase
    
    if phase == "initiation":
        return base_instructions + """
        Current Phase: INITIATION
        - Get Jira ticket input from user
        - Hand off to JiraAgent to analyze the ticket
        - Determine document type (Test Plan vs Test Cases)
        """
    elif phase == "document_processing":
        return base_instructions + """
        Current Phase: DOCUMENT PROCESSING
        - Hand off to DocumentAgent to process all documents
        - Gather PRDs, HLDs, LLDs, and Confluence pages
        - Consolidate all information
        """
    elif phase == "generation":
        return base_instructions + """
        Current Phase: GENERATION
        - Hand off to GenerationAgent to create test documentation
        - Generate appropriate document type based on ticket analysis
        - Validate generated content
        """
    elif phase == "review":
        return base_instructions + """
        Current Phase: REVIEW & REFINEMENT
        - Present generated document to user
        - Collect feedback and refine if needed
        - Finalize and save the document
        """
    else:
        return base_instructions

def create_test_genius_agent() -> Agent[TestGeniusContext]:
    """Create the main TestGenius orchestrating agent"""
    
    # Create specialized agents
    jira_agent = create_jira_agent()
    document_agent = create_document_agent()
    generation_agent = create_generation_agent()
    
    return Agent[TestGeniusContext](
        name="TestGenius",
        instructions=dynamic_instructions,
        model="gpt-4",
        handoffs=[jira_agent, document_agent, generation_agent],
        hooks=TestGeniusHooks(),
        # Enable autonomous decision making
        model_settings={
            "temperature": 0.1,  # Lower temperature for more consistent decisions
            "tool_choice": "auto"  # Let the agent decide when to use tools
        }
    )

class AutonomousTestGeniusRunner:
    """Autonomous runner for TestGenius workflow"""
    
    def __init__(self):
        self.agent = create_test_genius_agent()
        self.context = TestGeniusContext()
        self.runner = Runner()
    
    async def run_autonomous_workflow_with_interaction(self, ticket_input: str, console) -> WorkflowState:
        """Run the autonomous workflow with user interaction for missing documents"""
        try:
            # Phase 1: Initiation - Analyze Jira ticket
            console.print("🎯 Phase 1: Analyzing Jira ticket...", style="blue")
            jira_result = await self.runner.run(
                agent=self.agent.handoffs[0],  # JiraAgent
                context=self.context.jira_context,
                messages=[{"role": "user", "content": f"Analyze this Jira ticket: {ticket_input}"}]
            )
            
            if jira_result.data:
                self.context.workflow_state.jira_info = jira_result.data
                self.context.workflow_state.ticket_key = jira_result.data.key
                self.context.workflow_state.document_type = "Test Plan" if jira_result.data.issue_type.lower() == "epic" else "Test Cases"
            
            # Phase 2: Document Processing with Missing Document Handling
            console.print("📚 Phase 2: Processing documents...", style="blue")
            
            # First, process existing documents
            doc_result = await self.runner.run(
                agent=self.agent.handoffs[1],  # DocumentAgent
                context=self.context.document_context,
                messages=[{"role": "user", "content": f"Process all available documents for ticket {self.context.workflow_state.ticket_key}"}]
            )
            
            # Check for missing documents
            console.print("🔍 Checking for missing critical documents...", style="blue")
            missing_docs_result = await self.runner.run(
                agent=self.agent.handoffs[1],  # DocumentAgent
                context=self.context.document_context,
                messages=[{"role": "user", "content": f"Check for missing documents in ticket data"}]
            )
            
            # Handle missing documents with user interaction
            if missing_docs_result.data and hasattr(missing_docs_result.data, 'missing_documents') and missing_docs_result.data.missing_documents:
                console.print(f"⚠️ Found {len(missing_docs_result.data.missing_documents)} missing document type(s)", style="yellow")
                
                # Get user input for missing documents
                user_provided_docs = await self._handle_missing_documents(missing_docs_result.data.missing_documents, console)
                
                # If user provided additional documents, reprocess everything
                if user_provided_docs:
                    console.print("🔄 Reprocessing documents with user-provided content...", style="blue")
                    doc_result = await self.runner.run(
                        agent=self.agent.handoffs[1],  # DocumentAgent
                        context=self.context.document_context,
                        messages=[{"role": "user", "content": f"Consolidate all documents including user-provided content for ticket {self.context.workflow_state.ticket_key}"}]
                    )
            
            if doc_result.data:
                self.context.workflow_state.processing_result = doc_result.data
            
            # Phase 3: Generation
            console.print("✨ Phase 3: Generating test documentation...", style="blue")
            gen_result = await self.runner.run(
                agent=self.agent.handoffs[2],  # GenerationAgent
                context=self.context.generation_context,
                messages=[{"role": "user", "content": f"Generate {self.context.workflow_state.document_type} for {self.context.workflow_state.ticket_key}"}]
            )
            
            if gen_result.data:
                self.context.workflow_state.generated_document = gen_result.data
            
            # Phase 4: Finalization (autonomous)
            console.print("🎯 Phase 4: Finalizing document...", style="blue")
            if self.context.workflow_state.generated_document:
                # Auto-save if validation score is high enough
                if self.context.workflow_state.generated_document.validation_score >= 0.8:
                    final_path = await self._save_final_document()
                    self.context.workflow_state.final_document_path = final_path
                    self.context.workflow_state.current_phase = "completed"
                else:
                    self.context.workflow_state.current_phase = "needs_review"
            
            return self.context.workflow_state
            
        except Exception as e:
            self.context.workflow_state.errors.append(str(e))
            self.context.workflow_state.current_phase = "error"
            return self.context.workflow_state
    
    async def _handle_missing_documents(self, missing_requests, console) -> List[str]:
        """Handle missing document requests with user interaction"""
        from rich.prompt import Prompt, Confirm
        from rich.panel import Panel
        
        user_provided_docs = []
        
        for request in missing_requests:
            # Display missing document information
            console.print(f"\n📋 Missing Document: {request.document_type.upper()}", style="yellow bold")
            console.print(Panel(
                request.message,
                title=f"Missing {request.document_type.title()}",
                border_style="yellow"
            ))
            
            # Show options to user
            console.print("\n🔧 Available options:", style="cyan")
            for i, option in enumerate(request.options, 1):
                console.print(f"   {i}. {option}", style="white")
            
            # Get user choice
            choice = Prompt.ask(
                f"\nHow would you like to handle the missing {request.document_type}?",
                choices=[str(i) for i in range(1, len(request.options) + 1)],
                default="3"  # Default to "Skip and continue"
            )
            
            choice_idx = int(choice) - 1
            selected_option = request.options[choice_idx]
            
            # Handle user choice
            if "provide" in selected_option.lower() and "text" in selected_option.lower():
                # User wants to provide content as text
                content = Prompt.ask(f"\nPlease provide the {request.document_type} content")
                if content:
                    success = await self._process_user_content(request.document_type, content, request.ticket_key)
                    if success:
                        console.print(f"✅ {request.document_type.title()} content added successfully!", style="green")
                        user_provided_docs.append(request.document_type)
                    else:
                        console.print(f"❌ Failed to process {request.document_type} content", style="red")
            
            elif "provide" in selected_option.lower() and ("url" in selected_option.lower() or "path" in selected_option.lower()):
                # User wants to provide URL or file path
                url = Prompt.ask(f"\nPlease provide the {request.document_type} URL or file path")
                if url:
                    success = await self._process_user_url(url, request.document_type, request.ticket_key)
                    if success:
                        console.print(f"✅ {request.document_type.title()} from URL added successfully!", style="green")
                        user_provided_docs.append(request.document_type)
                    else:
                        console.print(f"❌ Failed to process {request.document_type} from URL", style="red")
            
            elif "parent epic" in selected_option.lower():
                # Check parent Epic for PRD
                console.print(f"🔍 Checking parent Epic for {request.document_type}...", style="blue")
                success = await self._check_parent_epic_for_documents(request.document_type, request.ticket_key)
                if success:
                    console.print(f"✅ Found {request.document_type} in parent Epic!", style="green")
                    user_provided_docs.append(request.document_type)
                else:
                    console.print(f"⚠️ No {request.document_type} found in parent Epic", style="yellow")
                
            elif "skip" in selected_option.lower():
                # User chooses to skip this document
                console.print(f"⏭️ Skipping {request.document_type} and continuing with available information", style="yellow")
            
            else:
                console.print(f"⏭️ Continuing without {request.document_type}", style="yellow")
        
        return user_provided_docs
    
    async def _process_user_content(self, content_type: str, content: str, ticket_key: str) -> bool:
        """Process user-provided content"""
        try:
            result = await self.runner.run(
                agent=self.agent.handoffs[1],  # DocumentAgent
                context=self.context.document_context,
                messages=[{"role": "user", "content": f"Process user provided {content_type} content: {content} for ticket {ticket_key}"}]
            )
            return result.data is not None
        except Exception as e:
            print(f"Error processing user content: {str(e)}")
            return False
    
    async def _process_user_url(self, url: str, content_type: str, ticket_key: str) -> bool:
        """Process user-provided URL"""
        try:
            result = await self.runner.run(
                agent=self.agent.handoffs[1],  # DocumentAgent
                context=self.context.document_context,
                messages=[{"role": "user", "content": f"Process user provided {content_type} URL: {url} for ticket {ticket_key}"}]
            )
            return result.data is not None
        except Exception as e:
            print(f"Error processing user URL: {str(e)}")
            return False
    
    async def _check_parent_epic_for_documents(self, content_type: str, ticket_key: str) -> bool:
        """Check parent Epic for missing documents"""
        try:
            result = await self.runner.run(
                agent=self.agent.handoffs[0],  # JiraAgent
                context=self.context.jira_context,
                messages=[{"role": "user", "content": f"Find parent Epic for {ticket_key} and check for {content_type} documents"}]
            )
            return result.data is not None
        except Exception as e:
            print(f"Error checking parent Epic: {str(e)}")
            return False

    async def run_autonomous_workflow(self, ticket_input: str) -> WorkflowState:
        """Run the complete autonomous workflow"""
        try:
            # Phase 1: Initiation - Analyze Jira ticket
            print("🎯 Phase 1: Analyzing Jira ticket...")
            jira_result = await self.runner.run(
                agent=self.agent.handoffs[0],  # JiraAgent
                context=self.context.jira_context,
                messages=[{"role": "user", "content": f"Analyze this Jira ticket: {ticket_input}"}]
            )
            
            if jira_result.data:
                self.context.workflow_state.jira_info = jira_result.data
                self.context.workflow_state.ticket_key = jira_result.data.key
                self.context.workflow_state.document_type = "Test Plan" if jira_result.data.issue_type.lower() == "epic" else "Test Cases"
            
            # Phase 2: Document Processing
            print("📚 Phase 2: Processing documents...")
            doc_result = await self.runner.run(
                agent=self.agent.handoffs[1],  # DocumentAgent
                context=self.context.document_context,
                messages=[{"role": "user", "content": f"Process all documents for ticket {self.context.workflow_state.ticket_key}"}]
            )
            
            if doc_result.data:
                self.context.workflow_state.processing_result = doc_result.data
            
            # Phase 3: Generation
            print("✨ Phase 3: Generating test documentation...")
            gen_result = await self.runner.run(
                agent=self.agent.handoffs[2],  # GenerationAgent
                context=self.context.generation_context,
                messages=[{"role": "user", "content": f"Generate {self.context.workflow_state.document_type} for {self.context.workflow_state.ticket_key}"}]
            )
            
            if gen_result.data:
                self.context.workflow_state.generated_document = gen_result.data
            
            # Phase 4: Finalization (autonomous)
            print("🎯 Phase 4: Finalizing document...")
            if self.context.workflow_state.generated_document:
                # Auto-save if validation score is high enough
                if self.context.workflow_state.generated_document.validation_score >= 0.8:
                    final_path = await self._save_final_document()
                    self.context.workflow_state.final_document_path = final_path
                    self.context.workflow_state.current_phase = "completed"
                else:
                    self.context.workflow_state.current_phase = "needs_review"
            
            return self.context.workflow_state
            
        except Exception as e:
            self.context.workflow_state.errors.append(str(e))
            self.context.workflow_state.current_phase = "error"
            return self.context.workflow_state
    
    async def refine_with_feedback(self, feedback: str) -> WorkflowState:
        """Refine document based on user feedback"""
        if not self.context.workflow_state.generated_document:
            raise Exception("No document available for refinement")
        
        try:
            # Use GenerationAgent to refine
            refined_result = await self.runner.run(
                agent=self.agent.handoffs[2],  # GenerationAgent
                context=self.context.generation_context,
                messages=[{"role": "user", "content": f"Refine document with feedback: {feedback}"}]
            )
            
            if refined_result.data:
                self.context.workflow_state.generated_document = refined_result.data
                
                # Auto-save if validation score improved
                if refined_result.data.validation_score >= 0.8:
                    final_path = await self._save_final_document()
                    self.context.workflow_state.final_document_path = final_path
                    self.context.workflow_state.current_phase = "completed"
            
            return self.context.workflow_state
            
        except Exception as e:
            self.context.workflow_state.errors.append(str(e))
            return self.context.workflow_state
    
    async def _save_final_document(self) -> str:
        """Save the final document"""
        if not self.context.workflow_state.ticket_key:
            raise Exception("No ticket key available")
        
        save_result = await self.runner.run(
            agent=self.agent.handoffs[2],  # GenerationAgent
            context=self.context.generation_context,
            messages=[{"role": "user", "content": f"Save final document for {self.context.workflow_state.ticket_key}"}]
        )
        
        return save_result.data if save_result.data else ""
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "current_phase": self.context.workflow_state.current_phase,
            "completed_phases": self.context.workflow_state.completed_phases,
            "ticket_key": self.context.workflow_state.ticket_key,
            "document_type": self.context.workflow_state.document_type,
            "has_errors": len(self.context.workflow_state.errors) > 0,
            "errors": self.context.workflow_state.errors,
            "validation_score": self.context.workflow_state.generated_document.validation_score if self.context.workflow_state.generated_document else None,
            "is_complete": self.context.workflow_state.current_phase == "completed"
        } 