import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for TestGenius chatbot"""
    
    # Azure OpenAI Configuration
    AZURE_TOKEN_URL = os.getenv("AZURE_TOKEN_URL")
    AZURE_OPENAI_URL = os.getenv("AZURE_OPENAI_URL")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
    
    # Jira Configuration
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    
    # Confluence Configuration
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", os.getenv("JIRA_URL"))
    CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME", os.getenv("JIRA_USERNAME"))
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", os.getenv("JIRA_API_TOKEN"))
    
    # Backward compatibility properties
    @property
    def AZURE_OPENAI_ENDPOINT(self):
        """Backward compatibility for AZURE_OPENAI_ENDPOINT"""
        return self.AZURE_OPENAI_URL
    
    @property
    def JIRA_SERVER(self):
        """Backward compatibility for JIRA_SERVER"""
        return self.JIRA_URL
    
    @property
    def CONFLUENCE_SERVER(self):
        """Backward compatibility for CONFLUENCE_SERVER"""
        return self.CONFLUENCE_URL
    
    # Application Settings
    DOCUMENTS_FOLDER = os.getenv("DOCUMENTS_FOLDER", "documents")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        required_fields = [
            "AZURE_OPENAI_URL",
            "AZURE_OPENAI_API_KEY", 
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "JIRA_URL",
            "JIRA_USERNAME",
            "JIRA_API_TOKEN"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        return True
    
    @classmethod
    def ensure_documents_folder(cls):
        """Ensure the documents folder exists"""
        Path(cls.DOCUMENTS_FOLDER).mkdir(exist_ok=True)
        return cls.DOCUMENTS_FOLDER 