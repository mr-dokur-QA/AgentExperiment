# TestGenius - AI-Powered Test Documentation Assistant 🤖

TestGenius is an intelligent chatbot that autonomously creates comprehensive Test Plans and Test Cases by analyzing Jira tickets and gathering relevant documentation. Built with Azure OpenAI and the OpenAI Agents SDK for autonomous workflow management.

## 🚀 Features

### Core Capabilities
- **Autonomous Workflow Management**: Fully autonomous operation using OpenAI Agents SDK
- **Smart Document Type Detection**: Automatically determines Test Plan (for Epics) vs Test Cases (for Stories/Tasks)
- **Multi-Source Content Processing**: Gathers data from Jira tickets, PRDs, HLDs, LLDs, and Confluence pages
- **AI-Powered Generation**: Creates professional test documentation using Azure OpenAI
- **Interactive Feedback System**: Human-in-the-loop refinement with autonomous processing
- **Quality Validation**: Automatic content validation with scoring and suggestions
- **Rich Console Interface**: Beautiful progress tracking and status updates

### Autonomous Agent Features
- **Specialized Agents**: JiraAgent, DocumentAgent, GenerationAgent with specific tools
- **Agent Handoffs**: Seamless workflow transitions between specialized agents
- **Lifecycle Hooks**: Comprehensive monitoring and error handling
- **Tool Integration**: Function tools for autonomous operations
- **Context Management**: Persistent state across workflow phases

### 6-Phase Autonomous Workflow
1. **Initiation & Goal Clarification**: Ticket analysis and document type determination
2. **Information Gathering**: Automated document collection and processing
3. **Context Understanding & Consolidation**: Content analysis and preparation
4. **Test Document Drafting**: AI-powered generation with validation
5. **Review & Refinement**: Human-in-the-loop feedback processing
6. **Finalization**: Automatic saving and Jira integration assistance

## 📋 Prerequisites

- Python 3.8 or higher
- Azure OpenAI account with deployed model
- Jira account with API access
- Confluence access (optional, for Confluence page processing)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd testgenius
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp config.env.example .env
   # Edit .env with your actual configuration
   ```

4. **Set up your environment**:
   - Azure OpenAI API credentials
   - Jira server and authentication
   - Confluence access (optional)

## 🚀 Usage

### Autonomous Mode (Recommended)

Run the fully autonomous version with agent-based workflow:

```bash
python autonomous_test_genius.py
```

**Features:**
- Fully autonomous operation with minimal human intervention
- Agent handoffs and specialized tools
- Automatic quality validation and decision making
- Rich progress tracking and status updates
- Human-in-the-loop only when needed

### Interactive Mode

Run the original interactive chatbot:

```bash
python test_genius_chatbot.py
```

**Features:**
- Step-by-step guided workflow
- Manual control over each phase
- Detailed progress tracking
- Interactive feedback collection

### Example Workflow

1. **Start the autonomous agent**:
   ```bash
   python autonomous_test_genius.py
   ```

2. **Provide Jira ticket**:
   - Enter ticket key (e.g., `PROJ-123`) or full URL
   - Agent automatically determines document type

3. **Autonomous processing**:
   - JiraAgent analyzes ticket and gathers information
   - DocumentAgent processes all attachments and links
   - GenerationAgent creates test documentation

4. **Quality validation**:
   - Automatic validation with scoring
   - Auto-save if quality score ≥ 0.8
   - Human review if quality needs improvement

5. **Finalization**:
   - Document saved to `documents/` folder
   - Jira attachment assistance provided

## 📁 Project Structure

```
testgenius/
├── agents/                          # Autonomous agent framework
│   ├── __init__.py                 # Agent package initialization
│   ├── jira_agent.py              # Jira specialist agent with tools
│   ├── document_agent.py          # Document processing agent
│   ├── generation_agent.py        # Test generation agent
│   └── test_genius_agent.py       # Main orchestrating agent
├── utils/                          # Utility modules
│   ├── __init__.py
│   ├── jira_client.py             # Jira API integration
│   ├── document_processor.py      # Document processing utilities
│   └── azure_openai_client.py     # Azure OpenAI integration
├── documents/                      # Generated documents storage
├── config.py                      # Configuration management
├── requirements.txt               # Python dependencies
├── config.env.example            # Environment variables template
├── test_genius_chatbot.py         # Original interactive chatbot
├── autonomous_test_genius.py      # New autonomous agent version
└── README.md                      # This file
```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name

# Jira Configuration
JIRA_SERVER=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# Confluence Configuration (Optional)
CONFLUENCE_SERVER=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

# Application Settings
DOCUMENTS_FOLDER=documents
LOG_LEVEL=INFO
```

## 📊 Quality Metrics

The system provides comprehensive quality metrics:

- **Validation Score**: 0.0 to 1.0 based on content analysis
- **Word Count**: Document length metrics
- **Section Count**: Structural completeness
- **Issues Detection**: Automatic identification of problems
- **Suggestions**: AI-powered improvement recommendations
- **Quality Rating**: Excellent (≥0.9), Good (≥0.7), Needs Improvement (<0.7)

## 🔍 Document Types

### Test Plan (for Epic tickets)
- Executive Summary
- Test Objectives
- Scope and Approach
- Test Strategy
- Resource Requirements
- Timeline and Milestones
- Risk Assessment
- Entry/Exit Criteria

### Test Cases (for Story/Task tickets)
- Test Case ID and Title
- Objective and Description
- Preconditions
- Test Steps
- Expected Results
- Test Data Requirements
- Priority and Severity

## 🛡️ Error Handling

The autonomous system includes comprehensive error handling:

- **Graceful Degradation**: Continues workflow even if some components fail
- **Error Reporting**: Clear error messages with suggested actions
- **Fallback Options**: Manual intervention when autonomous processing fails
- **State Recovery**: Maintains workflow state across errors
- **Retry Logic**: Automatic retries for transient failures

## 🔧 Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Issues**:
   - Verify endpoint URL and API key
   - Check deployment name and API version
   - Ensure sufficient quota and rate limits

2. **Jira Authentication Problems**:
   - Verify API token is valid and has necessary permissions
   - Check Jira server URL format
   - Ensure user has access to specified tickets

3. **Document Processing Failures**:
   - Check file permissions in documents folder
   - Verify attachment download permissions
   - Ensure Confluence access if using Confluence links

4. **Agent Framework Issues**:
   - Ensure `openai-agents>=1.0.0` is installed
   - Check Python version compatibility (3.8+)
   - Verify all dependencies are correctly installed

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

## 🚀 Future Enhancements

- **Multi-language Support**: Support for different programming languages and frameworks
- **Custom Templates**: User-defined test document templates
- **Integration Plugins**: Direct Jira attachment and comment posting
- **Batch Processing**: Process multiple tickets simultaneously
- **Advanced Analytics**: Test coverage analysis and metrics
- **Team Collaboration**: Multi-user workflows and shared templates
- **API Integration**: REST API for external tool integration

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the Agents SDK and GPT models
- Microsoft Azure for OpenAI services
- Atlassian for Jira and Confluence APIs
- Rich library for beautiful console interfaces

---

**TestGenius** - Making test documentation creation autonomous, intelligent, and effortless! 🚀 