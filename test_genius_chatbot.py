import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

from config import Config
from utils.jira_client import JiraClient
from utils.document_processor import DocumentProcessor
from utils.azure_openai_client import AzureOpenAIClient

class TestGeniusChatbot:
    """TestGenius - AI-powered Test Documentation Assistant"""
    
    def __init__(self):
        """Initialize TestGenius chatbot"""
        self.console = Console()
        self.jira_client = None
        self.doc_processor = None
        self.ai_client = None
        
        # Session state
        self.current_ticket = None
        self.current_epic = None
        self.document_type = None
        self.processed_documents = []
        self.final_content_path = None
        self.generated_document = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all components with error handling"""
        try:
            # Validate configuration
            Config.validate_config()
            
            # Initialize clients
            self.jira_client = JiraClient()
            self.doc_processor = DocumentProcessor()
            self.ai_client = AzureOpenAIClient()
            
            self.console.print("✅ TestGenius initialized successfully!", style="green")
            
        except Exception as e:
            self.console.print(f"❌ Initialization failed: {str(e)}", style="red")
            self.console.print("\nPlease check your configuration in the .env file.", style="yellow")
            sys.exit(1)
    
    def start(self):
        """Start the TestGenius chatbot"""
        self._display_welcome()
        
        while True:
            try:
                # Phase 1: Initiation & Goal Clarification
                if not self.current_ticket:
                    self._phase_1_initiation()
                
                # Phase 2: Information Gathering & Processing
                self._phase_2_information_gathering()
                
                # Phase 3: Context Understanding & Consolidation
                self._phase_3_consolidation()
                
                # Phase 4: Test Document Drafting
                self._phase_4_document_generation()
                
                # Phase 5: Review & Refinement (HITL)
                self._phase_5_review_refinement()
                
                # Phase 6: Finalization & Next Steps
                self._phase_6_finalization()
                
                # Ask if user wants to start over
                if not Confirm.ask("\n🔄 Would you like to work on another ticket?"):
                    break
                
                # Reset for new session
                self._reset_session()
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 Goodbye! Thanks for using TestGenius!", style="cyan")
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
        welcome_text.append("TestGenius", style="bold cyan")
        welcome_text.append("! 🚀\n\n", style="cyan")
        welcome_text.append("I'm your AI-powered Test Documentation Assistant. I can help you create comprehensive Test Plans and Test Cases by leveraging information from Jira tickets, PRDs, HLDs, LLDs, and Confluence pages.\n\n", style="white")
        welcome_text.append("Let's get started! 😊", style="green")
        
        panel = Panel(welcome_text, title="TestGenius", border_style="cyan")
        self.console.print(panel)
    
    def _phase_1_initiation(self):
        """Phase 1: Initiation & Goal Clarification"""
        self.console.print("\n📋 Phase 1: Let's get started!", style="bold blue")
        
        # Get Jira ticket input
        while not self.current_ticket:
            ticket_input = Prompt.ask(
                "\n🎫 Please provide the Jira ticket key or URL",
                default=""
            )
            
            if not ticket_input:
                self.console.print("Please provide a valid Jira ticket key or URL.", style="yellow")
                continue
            
            # Extract ticket key
            ticket_key = self.jira_client.extract_ticket_key(ticket_input)
            if not ticket_key:
                self.console.print("❌ Could not extract a valid ticket key from your input. Please try again.", style="red")
                continue
            
            # Fetch ticket details
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Fetching details for {ticket_key}...", total=None)
                
                try:
                    self.current_ticket = self.jira_client.get_ticket_details(ticket_key)
                    progress.update(task, description=f"✅ Successfully fetched {ticket_key}")
                    time.sleep(0.5)  # Brief pause to show success
                except Exception as e:
                    progress.update(task, description=f"❌ Failed to fetch {ticket_key}")
                    self.console.print(f"Error: {str(e)}", style="red")
                    continue
        
        # Display ticket information
        self._display_ticket_info(self.current_ticket)
        
        # Determine document type based on issue type
        is_epic = self.jira_client.is_epic(self.current_ticket)
        
        if is_epic:
            self.document_type = "Test Plan"
            self.console.print(f"\n📝 I can see that {self.current_ticket['key']} is an Epic. I'll create a comprehensive **Test Plan** for this Epic.", style="green")
        else:
            self.document_type = "Test Cases"
            self.console.print(f"\n📝 I see that {self.current_ticket['key']} is a {self.current_ticket['issue_type']}. I'll create detailed **Test Cases** for this ticket.", style="green")
            
            # For non-Epic tickets, try to find parent Epic
            self.console.print(f"\n🔍 To create the most thorough test cases, I'll also fetch details of its parent Epic...", style="blue")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Searching for parent Epic...", total=None)
                
                try:
                    self.current_epic = self.jira_client.find_parent_epic(self.current_ticket['key'])
                    if self.current_epic:
                        progress.update(task, description=f"✅ Found parent Epic: {self.current_epic['key']}")
                        self.console.print(f"\n🎉 Great news! I've found and saved information from the parent Epic **{self.current_epic['key']}**. Now we have a really good foundation!", style="green")
                    else:
                        progress.update(task, description="⚠️ No parent Epic found")
                        self.console.print(f"\n⚠️ I couldn't find a parent Epic for {self.current_ticket['key']}. We can still proceed with the information from this ticket.", style="yellow")
                        
                        if Confirm.ask("Do you know the Epic key and want to provide it?"):
                            epic_key = Prompt.ask("Please enter the Epic key")
                            if epic_key:
                                try:
                                    self.current_epic = self.jira_client.get_ticket_details(epic_key)
                                    self.console.print(f"✅ Successfully fetched Epic {epic_key}!", style="green")
                                except Exception as e:
                                    self.console.print(f"❌ Could not fetch Epic {epic_key}: {str(e)}", style="red")
                except Exception as e:
                    progress.update(task, description="❌ Error searching for Epic")
                    self.console.print(f"Warning: {str(e)}", style="yellow")
        
        # Confirm document type
        confirmed = Confirm.ask(f"\n✅ I'll be creating **{self.document_type}** for {self.current_ticket['key']}. Does that sound right?")
        if not confirmed:
            if Confirm.ask("Would you like Test Cases instead?"):
                self.document_type = "Test Cases"
            else:
                self.document_type = "Test Plan"
        
        self.console.print(f"\n🎯 Perfect! I'll create **{self.document_type}** for you.", style="green")
    
    def _phase_2_information_gathering(self):
        """Phase 2: Information Gathering & Initial Processing"""
        self.console.print("\n📚 Phase 2: Gathering and processing information...", style="bold blue")
        
        # Save Jira content
        self._save_jira_content()
        
        # Process PRD attachments
        self._process_prd_attachments()
        
        # Process HLD/LLD attachments and Confluence links
        self._process_design_documents()
    
    def _save_jira_content(self):
        """Save Jira ticket content to documents folder"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            # Save primary ticket
            task1 = progress.add_task(f"Saving {self.current_ticket['key']} content...", total=None)
            
            try:
                filepath = self.doc_processor.save_jira_content(self.current_ticket)
                self.processed_documents.append(filepath)
                progress.update(task1, description=f"✅ Saved {self.current_ticket['key']} content")
            except Exception as e:
                progress.update(task1, description=f"❌ Failed to save {self.current_ticket['key']}")
                self.console.print(f"Error: {str(e)}", style="red")
            
            # Save Epic content if available
            if self.current_epic:
                task2 = progress.add_task(f"Saving Epic {self.current_epic['key']} content...", total=None)
                
                try:
                    filepath = self.doc_processor.save_jira_content(self.current_epic)
                    self.processed_documents.append(filepath)
                    progress.update(task2, description=f"✅ Saved Epic {self.current_epic['key']} content")
                except Exception as e:
                    progress.update(task2, description=f"❌ Failed to save Epic {self.current_epic['key']}")
                    self.console.print(f"Error: {str(e)}", style="red")
    
    def _process_prd_attachments(self):
        """Process PRD attachments from Jira tickets"""
        self.console.print("\n🔍 Looking for PRD attachments...", style="blue")
        
        # Check primary ticket for PRDs
        prd_attachments = self.doc_processor.identify_prd_attachments(self.current_ticket)
        
        # Check Epic for PRDs if available
        if self.current_epic:
            epic_prds = self.doc_processor.identify_prd_attachments(self.current_epic)
            prd_attachments.extend(epic_prds)
        
        if prd_attachments:
            self.console.print(f"📄 Found {len(prd_attachments)} PRD attachment(s). Processing all of them...", style="green")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                for i, attachment in enumerate(prd_attachments, 1):
                    task = progress.add_task(f"Processing PRD {i}: {attachment['filename']}...", total=None)
                    
                    try:
                        # Determine source ticket
                        source_ticket = self.current_ticket['key']
                        if self.current_epic and attachment in self.doc_processor.identify_prd_attachments(self.current_epic):
                            source_ticket = self.current_epic['key']
                        
                        filepath = self.doc_processor.process_attachment(
                            attachment, self.jira_client, "prd", source_ticket, i
                        )
                        
                        if filepath:
                            self.processed_documents.append(filepath)
                            progress.update(task, description=f"✅ Processed PRD {i}: {attachment['filename']}")
                        else:
                            progress.update(task, description=f"⚠️ Could not extract content from PRD {i}")
                            
                    except Exception as e:
                        progress.update(task, description=f"❌ Failed to process PRD {i}")
                        self.console.print(f"Error processing {attachment['filename']}: {str(e)}", style="red")
        else:
            self.console.print("⚠️ No PRD attachments found in the Jira ticket(s).", style="yellow")
            
            if Confirm.ask("Would you like to provide PRD content manually?"):
                self._handle_manual_prd_input()
    
    def _process_design_documents(self):
        """Process HLD/LLD attachments and Confluence links"""
        self.console.print("\n🔍 Looking for HLD/LLD documents and Confluence links...", style="blue")
        
        # Process HLD/LLD attachments
        design_attachments = self.doc_processor.identify_hld_lld_attachments(self.current_ticket)
        if self.current_epic:
            epic_designs = self.doc_processor.identify_hld_lld_attachments(self.current_epic)
            design_attachments.extend(epic_designs)
        
        if design_attachments:
            self.console.print(f"📐 Found {len(design_attachments)} HLD/LLD attachment(s). Processing...", style="green")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                for i, attachment in enumerate(design_attachments, 1):
                    task = progress.add_task(f"Processing design doc {i}: {attachment['filename']}...", total=None)
                    
                    try:
                        # Determine source ticket and document type
                        source_ticket = self.current_ticket['key']
                        if self.current_epic and attachment in self.doc_processor.identify_hld_lld_attachments(self.current_epic):
                            source_ticket = self.current_epic['key']
                        
                        doc_type = "hld" if "hld" in attachment['filename'].lower() or "high" in attachment['filename'].lower() else "lld"
                        
                        filepath = self.doc_processor.process_attachment(
                            attachment, self.jira_client, doc_type, source_ticket, i
                        )
                        
                        if filepath:
                            self.processed_documents.append(filepath)
                            progress.update(task, description=f"✅ Processed {doc_type.upper()} {i}: {attachment['filename']}")
                        else:
                            progress.update(task, description=f"⚠️ Could not extract content from design doc {i}")
                            
                    except Exception as e:
                        progress.update(task, description=f"❌ Failed to process design doc {i}")
                        self.console.print(f"Error: {str(e)}", style="red")
        
        # Process Confluence links
        self._process_confluence_links()
    
    def _process_confluence_links(self):
        """Process Confluence links found in ticket descriptions"""
        confluence_links = []
        
        # Extract from primary ticket
        if self.current_ticket.get('description'):
            links = self.jira_client.extract_confluence_links(self.current_ticket['description'])
            confluence_links.extend([(link, self.current_ticket['key']) for link in links])
        
        # Extract from Epic if available
        if self.current_epic and self.current_epic.get('description'):
            links = self.jira_client.extract_confluence_links(self.current_epic['description'])
            confluence_links.extend([(link, self.current_epic['key']) for link in links])
        
        if confluence_links:
            self.console.print(f"🔗 Found {len(confluence_links)} Confluence link(s). Processing...", style="green")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                for i, (link, source_ticket) in enumerate(confluence_links, 1):
                    task = progress.add_task(f"Fetching Confluence page {i}...", total=None)
                    
                    try:
                        filepath = self.doc_processor.fetch_confluence_page(link, source_ticket, i)
                        
                        if filepath:
                            self.processed_documents.append(filepath)
                            progress.update(task, description=f"✅ Fetched Confluence page {i}")
                        else:
                            progress.update(task, description=f"⚠️ Could not fetch Confluence page {i}")
                            
                    except Exception as e:
                        progress.update(task, description=f"❌ Failed to fetch Confluence page {i}")
                        self.console.print(f"Error: {str(e)}", style="red")
        else:
            self.console.print("ℹ️ No Confluence links found in ticket descriptions.", style="blue")
            
            if Confirm.ask("Would you like to provide Confluence page URLs manually?"):
                self._handle_manual_confluence_input()
    
    def _handle_manual_prd_input(self):
        """Handle manual PRD content input"""
        self.console.print("\n📝 Please provide PRD content:", style="blue")
        
        prd_content = ""
        self.console.print("Enter your PRD content (press Ctrl+D when finished):")
        
        try:
            while True:
                line = input()
                prd_content += line + "\n"
        except EOFError:
            pass
        
        if prd_content.strip():
            # Save manual PRD content
            filename = f"prd-manual-content.md"
            filepath = self.doc_processor.save_markdown_file(
                f"# Manual PRD Content\n\n{prd_content}", 
                filename
            )
            self.processed_documents.append(filepath)
            self.console.print("✅ Manual PRD content saved!", style="green")
    
    def _handle_manual_confluence_input(self):
        """Handle manual Confluence URL input"""
        while True:
            url = Prompt.ask("Enter Confluence page URL (or press Enter to skip)")
            if not url:
                break
            
            try:
                filepath = self.doc_processor.fetch_confluence_page(
                    url, self.current_ticket['key'], len(self.processed_documents) + 1
                )
                if filepath:
                    self.processed_documents.append(filepath)
                    self.console.print("✅ Confluence page processed!", style="green")
                else:
                    self.console.print("⚠️ Could not process Confluence page.", style="yellow")
            except Exception as e:
                self.console.print(f"❌ Error: {str(e)}", style="red")
    
    def _phase_3_consolidation(self):
        """Phase 3: Context Understanding & Consolidation"""
        self.console.print("\n🧠 Phase 3: Processing and synthesizing all information...", style="bold blue")
        
        if not self.processed_documents:
            self.console.print("⚠️ No documents were processed. Cannot proceed with generation.", style="yellow")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Consolidating all documents...", total=None)
            
            try:
                self.final_content_path = self.doc_processor.consolidate_documents(self.processed_documents)
                progress.update(task, description="✅ Successfully consolidated all information")
                
                # Display summary
                self.console.print(f"\n📊 Information Summary:", style="green")
                self.console.print(f"   • Jira ticket(s): {self.current_ticket['key']}", style="white")
                if self.current_epic:
                    self.console.print(f"   • Epic: {self.current_epic['key']}", style="white")
                self.console.print(f"   • Total documents processed: {len(self.processed_documents)}", style="white")
                self.console.print(f"   • Consolidated content saved to: {self.final_content_path}", style="white")
                
            except Exception as e:
                progress.update(task, description="❌ Failed to consolidate documents")
                self.console.print(f"Error: {str(e)}", style="red")
                return
    
    def _phase_4_document_generation(self):
        """Phase 4: Test Document Drafting"""
        self.console.print(f"\n✨ Phase 4: Generating {self.document_type}...", style="bold blue")
        
        if not self.final_content_path:
            self.console.print("❌ No consolidated content available for generation.", style="red")
            return
        
        self.console.print(f"🎯 I'm now drafting the **{self.document_type}** for {self.current_ticket['key']}. I'll use our standard detailed format, drawing from all the documents we've gathered. This is where the magic happens! ✨", style="green")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Generating {self.document_type}...", total=None)
            
            try:
                if self.document_type == "Test Plan":
                    self.generated_document = self.ai_client.generate_test_plan(
                        self.final_content_path, 
                        self.current_ticket['key']
                    )
                else:
                    self.generated_document = self.ai_client.generate_test_cases(
                        self.final_content_path, 
                        self.current_ticket['key']
                    )
                
                progress.update(task, description=f"✅ Successfully generated {self.document_type}")
                
                # Save generated document
                filename = f"generated-{self.document_type.lower().replace(' ', '-')}-{self.current_ticket['key']}.md"
                self.doc_processor.save_markdown_file(self.generated_document, filename)
                
                self.console.print(f"\n🎉 I've completed generating the **{self.document_type}** document! It's been saved locally.", style="green")
                
            except Exception as e:
                progress.update(task, description=f"❌ Failed to generate {self.document_type}")
                self.console.print(f"Error: {str(e)}", style="red")
                return
    
    def _phase_5_review_refinement(self):
        """Phase 5: Review & Refinement (HITL)"""
        self.console.print(f"\n👀 Phase 5: Review and refinement", style="bold blue")
        
        if not self.generated_document:
            self.console.print("❌ No document available for review.", style="red")
            return
        
        while True:
            # Display the document
            self.console.print(f"\n📄 Here's your {self.document_type}:", style="green")
            self.console.print(Panel(self.generated_document, title=f"{self.document_type} - {self.current_ticket['key']}", border_style="green"))
            
            # Ask for feedback
            self.console.print(f"\n💭 What do you think? Please let me know if any adjustments are needed or if anything needs clarification.", style="blue")
            
            feedback = Prompt.ask(
                "Your feedback (or press Enter if it looks good)",
                default=""
            )
            
            if not feedback:
                self.console.print("✅ Great! The document looks good to you.", style="green")
                break
            
            # Process feedback
            self.console.print(f"\n🔄 Processing your feedback...", style="blue")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Updating document based on feedback...", total=None)
                
                try:
                    updated_document = self.ai_client.get_user_feedback_response(feedback, self.generated_document)
                    self.generated_document = updated_document
                    progress.update(task, description="✅ Document updated successfully")
                    
                    # Save updated document
                    filename = f"generated-{self.document_type.lower().replace(' ', '-')}-{self.current_ticket['key']}-updated.md"
                    self.doc_processor.save_markdown_file(self.generated_document, filename)
                    
                except Exception as e:
                    progress.update(task, description="❌ Failed to update document")
                    self.console.print(f"Error: {str(e)}", style="red")
                    break
    
    def _phase_6_finalization(self):
        """Phase 6: Finalization & Next Steps"""
        self.console.print(f"\n🎯 Phase 6: Finalization", style="bold blue")
        
        if not self.generated_document:
            self.console.print("❌ No document to finalize.", style="red")
            return
        
        self.console.print(f"🎉 Excellent! The **{self.document_type}** for {self.current_ticket['key']} is now finalized!", style="green")
        
        # Validate the generated content
        validation = self.ai_client.validate_generated_content(self.generated_document, self.document_type.replace(" ", "_").lower())
        
        if validation["issues"]:
            self.console.print("⚠️ Validation Issues Found:", style="yellow")
            for issue in validation["issues"]:
                self.console.print(f"   • {issue}", style="yellow")
        
        if validation["suggestions"]:
            self.console.print("💡 Suggestions:", style="blue")
            for suggestion in validation["suggestions"]:
                self.console.print(f"   • {suggestion}", style="blue")
        
        # Save final document
        final_filename = f"FINAL-{self.document_type.lower().replace(' ', '-')}-{self.current_ticket['key']}.md"
        final_path = self.doc_processor.save_markdown_file(self.generated_document, final_filename)
        
        self.console.print(f"\n📁 Final document saved as: {final_filename}", style="green")
        
        # Offer to help with Jira attachment
        if Confirm.ask(f"\n📎 Would you like me to help you prepare this content for attachment to Jira ticket {self.current_ticket['key']}?"):
            self._help_with_jira_attachment(final_path)
    
    def _help_with_jira_attachment(self, file_path: str):
        """Help user with Jira attachment process"""
        self.console.print(f"\n📋 To attach this document to Jira ticket {self.current_ticket['key']}:", style="blue")
        self.console.print(f"   1. Open the Jira ticket: {self.jira_client.server}/browse/{self.current_ticket['key']}", style="white")
        self.console.print(f"   2. Click on 'Attach' or the paperclip icon", style="white")
        self.console.print(f"   3. Upload the file: {file_path}", style="white")
        self.console.print(f"   4. Add a comment describing the test documentation", style="white")
        
        if Confirm.ask("\nWould you like me to open the Jira ticket in your browser?"):
            import webbrowser
            webbrowser.open(f"{self.jira_client.server}/browse/{self.current_ticket['key']}")
    
    def _display_ticket_info(self, ticket_data: Dict[str, Any]):
        """Display ticket information in a formatted panel"""
        info_text = Text()
        info_text.append(f"Key: ", style="bold")
        info_text.append(f"{ticket_data['key']}\n", style="cyan")
        info_text.append(f"Summary: ", style="bold")
        info_text.append(f"{ticket_data['summary']}\n", style="white")
        info_text.append(f"Type: ", style="bold")
        info_text.append(f"{ticket_data['issue_type']}\n", style="green")
        info_text.append(f"Status: ", style="bold")
        info_text.append(f"{ticket_data['status']}\n", style="yellow")
        info_text.append(f"Priority: ", style="bold")
        info_text.append(f"{ticket_data['priority']}", style="red")
        
        panel = Panel(info_text, title="📋 Ticket Information", border_style="blue")
        self.console.print(panel)
    
    def _reset_session(self):
        """Reset session for new ticket"""
        self.current_ticket = None
        self.current_epic = None
        self.document_type = None
        self.processed_documents = []
        self.final_content_path = None
        self.generated_document = None
        self.ai_client.reset_conversation()
        
        # Clean up documents folder for new session
        try:
            import shutil
            if os.path.exists(Config.DOCUMENTS_FOLDER):
                shutil.rmtree(Config.DOCUMENTS_FOLDER)
            Config.ensure_documents_folder()
        except Exception as e:
            self.console.print(f"Warning: Could not clean up documents folder: {str(e)}", style="yellow")

def main():
    """Main entry point"""
    try:
        chatbot = TestGeniusChatbot()
        chatbot.start()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using TestGenius!")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 