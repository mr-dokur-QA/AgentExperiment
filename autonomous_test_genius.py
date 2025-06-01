#!/usr/bin/env python3
"""
Autonomous TestGenius - AI-Powered Test Documentation Assistant
Using OpenAI Agents SDK for autonomous workflow management
"""

import asyncio
import sys
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import Config
from agents.test_genius_agent import AutonomousTestGeniusRunner, WorkflowState

class AutonomousTestGenius:
    """Autonomous TestGenius using OpenAI Agents SDK"""
    
    def __init__(self):
        """Initialize autonomous TestGenius"""
        self.console = Console()
        self.runner = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all components with error handling"""
        try:
            # Validate configuration
            Config.validate_config()
            
            # Initialize autonomous runner
            self.runner = AutonomousTestGeniusRunner()
            
            self.console.print("✅ Autonomous TestGenius initialized successfully!", style="green")
            
        except Exception as e:
            self.console.print(f"❌ Initialization failed: {str(e)}", style="red")
            self.console.print("\nPlease check your configuration in the .env file.", style="yellow")
            sys.exit(1)
    
    async def start(self):
        """Start the autonomous TestGenius workflow"""
        self._display_welcome()
        
        while True:
            try:
                # Get ticket input
                ticket_input = await self._get_ticket_input()
                if not ticket_input:
                    continue
                
                # Run autonomous workflow
                workflow_state = await self._run_autonomous_workflow(ticket_input)
                
                # Handle workflow result
                await self._handle_workflow_result(workflow_state)
                
                # Ask if user wants to continue
                if not Confirm.ask("\n🔄 Would you like to work on another ticket?"):
                    break
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 Goodbye! Thanks for using Autonomous TestGenius!", style="cyan")
                break
            except Exception as e:
                self.console.print(f"\n❌ An error occurred: {str(e)}", style="red")
                if Confirm.ask("Would you like to continue?"):
                    continue
                else:
                    break
    
    def _display_welcome(self):
        """Display welcome message"""
        welcome_text = Text()
        welcome_text.append("🤖 Welcome to ", style="cyan")
        welcome_text.append("Autonomous TestGenius", style="bold cyan")
        welcome_text.append("! 🚀\n\n", style="cyan")
        welcome_text.append("I'm your fully autonomous AI-powered Test Documentation Assistant. I can independently:\n\n", style="white")
        welcome_text.append("✨ Analyze Jira tickets and determine document types\n", style="green")
        welcome_text.append("📚 Gather and process all relevant documents\n", style="green")
        welcome_text.append("🎯 Generate comprehensive test documentation\n", style="green")
        welcome_text.append("🔍 Validate and refine content automatically\n", style="green")
        welcome_text.append("💾 Save final documents when quality is sufficient\n\n", style="green")
        welcome_text.append("Just provide a Jira ticket and I'll handle the rest! 😊", style="yellow")
        
        panel = Panel(welcome_text, title="Autonomous TestGenius", border_style="cyan")
        self.console.print(panel)
    
    async def _get_ticket_input(self) -> Optional[str]:
        """Get Jira ticket input from user"""
        self.console.print("\n🎫 Let's get started!", style="bold blue")
        
        ticket_input = Prompt.ask(
            "Please provide the Jira ticket key or URL",
            default=""
        )
        
        if not ticket_input:
            self.console.print("Please provide a valid Jira ticket key or URL.", style="yellow")
            return None
        
        return ticket_input
    
    async def _run_autonomous_workflow(self, ticket_input: str) -> WorkflowState:
        """Run the autonomous workflow with progress tracking"""
        self.console.print(f"\n🚀 Starting autonomous workflow for: {ticket_input}", style="bold green")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            # Start autonomous workflow
            task = progress.add_task("Initializing autonomous workflow...", total=None)
            
            try:
                # Run the autonomous workflow with missing document handling
                workflow_state = await self.runner.run_autonomous_workflow_with_interaction(ticket_input, self.console)
                
                # Update progress based on workflow state
                if workflow_state.current_phase == "completed":
                    progress.update(task, description="✅ Autonomous workflow completed successfully!")
                elif workflow_state.current_phase == "needs_review":
                    progress.update(task, description="⚠️ Workflow completed, but document needs review")
                elif workflow_state.current_phase == "error":
                    progress.update(task, description="❌ Workflow encountered errors")
                else:
                    progress.update(task, description=f"🔄 Workflow in progress: {workflow_state.current_phase}")
                
                # Brief pause to show final status
                await asyncio.sleep(1)
                
                return workflow_state
                
            except Exception as e:
                progress.update(task, description=f"❌ Workflow failed: {str(e)}")
                raise e
    
    async def _handle_workflow_result(self, workflow_state: WorkflowState):
        """Handle the result of the autonomous workflow"""
        # Display workflow summary
        self._display_workflow_summary(workflow_state)
        
        if workflow_state.current_phase == "completed":
            # Workflow completed successfully
            self.console.print(f"\n🎉 Excellent! I've successfully created the **{workflow_state.document_type}** for {workflow_state.ticket_key}!", style="green")
            
            if workflow_state.final_document_path:
                self.console.print(f"📁 Final document saved: {workflow_state.final_document_path}", style="green")
            
            # Display document metrics
            if workflow_state.generated_document:
                self._display_document_metrics(workflow_state.generated_document)
            
            # Offer Jira integration help
            if Confirm.ask(f"\n📎 Would you like help attaching this to Jira ticket {workflow_state.ticket_key}?"):
                self._help_with_jira_attachment(workflow_state)
        
        elif workflow_state.current_phase == "needs_review":
            # Document needs human review
            self.console.print(f"\n👀 I've generated the **{workflow_state.document_type}**, but it could benefit from your review.", style="yellow")
            
            if workflow_state.generated_document:
                # Display the document
                self.console.print(f"\n📄 Here's the generated {workflow_state.document_type}:", style="blue")
                self.console.print(Panel(
                    workflow_state.generated_document.content[:2000] + "..." if len(workflow_state.generated_document.content) > 2000 else workflow_state.generated_document.content,
                    title=f"{workflow_state.document_type} - {workflow_state.ticket_key}",
                    border_style="blue"
                ))
                
                # Get feedback and refine
                await self._handle_feedback_loop(workflow_state)
        
        elif workflow_state.current_phase == "error":
            # Handle errors
            self.console.print(f"\n❌ The autonomous workflow encountered some issues:", style="red")
            for error in workflow_state.errors:
                self.console.print(f"   • {error}", style="red")
            
            # Offer manual intervention
            if Confirm.ask("Would you like to try a manual approach?"):
                self.console.print("💡 Consider using the original test_genius_chatbot.py for manual workflow.", style="blue")
    
    async def _handle_feedback_loop(self, workflow_state: WorkflowState):
        """Handle the feedback and refinement loop"""
        while True:
            feedback = Prompt.ask(
                "\n💭 Please provide feedback for improvement (or press Enter if it looks good)",
                default=""
            )
            
            if not feedback:
                # User is satisfied, save the document
                self.console.print("✅ Great! Saving the final document...", style="green")
                
                # Force save the document
                try:
                    final_path = await self.runner._save_final_document()
                    workflow_state.final_document_path = final_path
                    workflow_state.current_phase = "completed"
                    self.console.print(f"📁 Document saved: {final_path}", style="green")
                except Exception as e:
                    self.console.print(f"❌ Error saving document: {str(e)}", style="red")
                break
            
            # Refine with feedback
            self.console.print(f"\n🔄 Processing your feedback autonomously...", style="blue")
            
            try:
                refined_state = await self.runner.refine_with_feedback(feedback)
                
                if refined_state.current_phase == "completed":
                    self.console.print("✅ Document refined and automatically saved!", style="green")
                    workflow_state.update(refined_state)
                    break
                else:
                    # Show refined document
                    if refined_state.generated_document:
                        self.console.print(f"\n📄 Here's the refined {workflow_state.document_type}:", style="blue")
                        self.console.print(Panel(
                            refined_state.generated_document.content[:2000] + "..." if len(refined_state.generated_document.content) > 2000 else refined_state.generated_document.content,
                            title=f"Refined {workflow_state.document_type}",
                            border_style="green"
                        ))
                        workflow_state.generated_document = refined_state.generated_document
                
            except Exception as e:
                self.console.print(f"❌ Error refining document: {str(e)}", style="red")
                break
    
    def _display_workflow_summary(self, workflow_state: WorkflowState):
        """Display a summary of the workflow execution"""
        table = Table(title="🔍 Autonomous Workflow Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        # Add completed phases
        for phase in workflow_state.completed_phases:
            table.add_row(phase.replace("_", " ").title(), "✅ Completed", "Successfully processed")
        
        # Add current phase
        if workflow_state.current_phase not in ["completed", "error"]:
            table.add_row(
                workflow_state.current_phase.replace("_", " ").title(),
                "🔄 In Progress",
                "Currently processing"
            )
        
        # Add final status
        if workflow_state.current_phase == "completed":
            table.add_row("Finalization", "✅ Completed", f"Document saved successfully")
        elif workflow_state.current_phase == "error":
            table.add_row("Error Handling", "❌ Failed", f"{len(workflow_state.errors)} error(s) occurred")
        
        self.console.print(table)
        
        # Display key information
        if workflow_state.ticket_key:
            self.console.print(f"\n📋 Ticket: {workflow_state.ticket_key}", style="cyan")
        if workflow_state.document_type:
            self.console.print(f"📝 Document Type: {workflow_state.document_type}", style="cyan")
    
    def _display_document_metrics(self, document):
        """Display metrics for the generated document"""
        metrics_table = Table(title="📊 Document Quality Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")
        
        metrics_table.add_row("Word Count", str(document.word_count))
        metrics_table.add_row("Section Count", str(document.section_count))
        metrics_table.add_row("Validation Score", f"{document.validation_score:.2f}")
        
        quality_rating = "Excellent" if document.validation_score >= 0.9 else "Good" if document.validation_score >= 0.7 else "Needs Improvement"
        metrics_table.add_row("Quality Rating", quality_rating)
        
        if document.issues:
            metrics_table.add_row("Issues Found", str(len(document.issues)))
        if document.suggestions:
            metrics_table.add_row("Suggestions", str(len(document.suggestions)))
        
        self.console.print(metrics_table)
    
    def _help_with_jira_attachment(self, workflow_state: WorkflowState):
        """Help user with Jira attachment process"""
        self.console.print(f"\n📋 To attach this document to Jira ticket {workflow_state.ticket_key}:", style="blue")
        self.console.print(f"   1. Open: {Config.JIRA_SERVER}/browse/{workflow_state.ticket_key}", style="white")
        self.console.print(f"   2. Click 'Attach' or the paperclip icon", style="white")
        self.console.print(f"   3. Upload: {workflow_state.final_document_path}", style="white")
        self.console.print(f"   4. Add a comment describing the test documentation", style="white")
        
        if Confirm.ask("\nWould you like me to open the Jira ticket in your browser?"):
            import webbrowser
            webbrowser.open(f"{Config.JIRA_SERVER}/browse/{workflow_state.ticket_key}")

async def main():
    """Main entry point for autonomous TestGenius"""
    try:
        chatbot = AutonomousTestGenius()
        await chatbot.start()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using Autonomous TestGenius!")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the autonomous workflow
    asyncio.run(main()) 