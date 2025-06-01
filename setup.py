#!/usr/bin/env python3
"""
TestGenius Setup Script
Helps users install dependencies and configure the environment
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("=" * 60)
    print("🤖 TestGenius Setup - AI-Powered Test Documentation")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    print()

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("   Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    print()

def setup_environment():
    """Set up environment configuration"""
    print("⚙️ Setting up environment configuration...")
    
    env_file = Path(".env")
    example_file = Path("config.env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if not example_file.exists():
        print("❌ config.env.example not found")
        return
    
    # Copy example to .env
    with open(example_file, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print("✅ Created .env file from template")
    print("📝 Please edit .env file with your actual configuration")
    print()

def create_documents_folder():
    """Create documents folder if it doesn't exist"""
    print("📁 Setting up documents folder...")
    
    docs_folder = Path("documents")
    if not docs_folder.exists():
        docs_folder.mkdir()
        print("✅ Created documents folder")
    else:
        print("✅ Documents folder already exists")
    
    print()

def print_configuration_guide():
    """Print configuration guide"""
    print("📋 Configuration Guide:")
    print("-" * 30)
    print()
    
    print("1. Azure OpenAI Setup:")
    print("   • Create an Azure OpenAI resource")
    print("   • Deploy a GPT-4 model")
    print("   • Get your endpoint, API key, and deployment name")
    print()
    
    print("2. Jira API Setup:")
    print("   • Go to Jira → Profile → Personal Access Tokens")
    print("   • Create a new token with appropriate permissions")
    print("   • Use your email and the token for authentication")
    print()
    
    print("3. Confluence Setup (Optional):")
    print("   • Uses same credentials as Jira by default")
    print("   • Can be configured separately if needed")
    print()
    
    print("4. Edit .env file with your configuration:")
    print("   • AZURE_OPENAI_ENDPOINT")
    print("   • AZURE_OPENAI_API_KEY")
    print("   • AZURE_OPENAI_DEPLOYMENT_NAME")
    print("   • JIRA_SERVER")
    print("   • JIRA_USERNAME")
    print("   • JIRA_API_TOKEN")
    print()

def print_usage_guide():
    """Print usage guide"""
    print("🚀 Usage Guide:")
    print("-" * 20)
    print()
    
    print("Autonomous Mode (Recommended):")
    print("   python autonomous_test_genius.py")
    print("   • Fully autonomous workflow")
    print("   • Minimal human intervention")
    print("   • Agent-based processing")
    print()
    
    print("Interactive Mode:")
    print("   python test_genius_chatbot.py")
    print("   • Step-by-step guided workflow")
    print("   • Manual control over each phase")
    print("   • Detailed progress tracking")
    print()

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Setup environment
    setup_environment()
    
    # Create documents folder
    create_documents_folder()
    
    # Print guides
    print_configuration_guide()
    print_usage_guide()
    
    print("=" * 60)
    print("🎉 Setup completed successfully!")
    print("📝 Next steps:")
    print("   1. Edit .env file with your configuration")
    print("   2. Run: python autonomous_test_genius.py")
    print("=" * 60)

if __name__ == "__main__":
    main() 