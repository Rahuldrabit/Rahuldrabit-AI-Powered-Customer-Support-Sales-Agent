# AI-Powered Customer Support & Sales Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.20-orange.svg)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.5-blue.svg)](https://python.langchain.com/)

An intelligent customer support and sales agent that automates responses across **TikTok** and **LinkedIn** messaging platforms using **FastAPI** and **LangGraph**. This project demonstrates a production-ready AI agent implementation with comprehensive testing, documentation, and deployment configurations.

## 🎯 Features

### Core Capabilities
- 🤖 **Multi-Intent Recognition**: Automatically classifies messages as support, sales, general, or urgent
- 💬 **Context-Aware Responses**: Maintains conversation history for coherent interactions
- 🚨 **Smart Escalation**: Detects urgent issues and escalates to human agents
- 📊 **Analytics Dashboard**: Track metrics, response times, sentiment analysis, and conversation insights
- 🔌 **Multi-Platform Support**: TikTok and LinkedIn webhook integrations with mock clients
- ⚡ **Async Processing**: Redis-based caching and Celery task queue for scalability
- 🌐 **Multi-language Support**: Auto-detect language and respond accordingly
- 🧪 **A/B Testing**: Test different prompt variants and measure performance

### LangGraph Agent Workflow
The agent uses a stateful workflow powered by LangGraph:
1. **Message Classification**: Determine intent (support/sales/general/urgent) and sentiment
2. **Context Retrieval**: Format conversation history for LLM context
3. **Escalation Check**: Identify critical issues requiring human intervention
4. **Response Generation**: Create appropriate responses based on intent and tone
5. **Response Validation**: Ensure response quality and appropriateness

## 📁 Project Structure

```
project/
├── app/
│   ├── agent/                  # LangGraph agent implementation
│   │   ├── graph.py            # Workflow definition and state management
│   │   ├── nodes.py            # Agent node implementations
│   │   ├── prompts.py          # System prompts and templates
│   │   └── tools.py            # Utility functions for agent
│   ├── api/                    # FastAPI routes
│   │   ├── dependencies.py     # Dependency injection utilities
│   │   └── routes/
│   │       ├── webhooks.py     # Platform webhook handlers
│   │       ├── messages.py     # Message sending endpoints
│   │       ├── conversations.py # Conversation management (NEW)
│   │       ├── analytics.py    # Analytics endpoints
│   │       ├── admin.py        # Admin endpoints
│   │       └── oauth.py        # OAuth endpoints
│   ├── integrations/           # Platform clients
│   │   ├── tiktok.py           # TikTok API client (mock)
│   │   └── linkedin.py         # LinkedIn API client (mock)
│   ├── models/                 # Database models
│   │   ├── database.py         # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/               # Business logic
│   │   ├── message_processor.py
│   │   ├── conversation.py
│   │   ├── analytics.py
│   │   └── celery_worker.py    # Celery task definitions
│   ├── utils/                  # Utilities
│   │   ├── logger.py           # Logging configuration (loguru)
│   │   └── exceptions.py       # Custom exceptions
│   ├── config.py               # Configuration management
│   └── main.py                 # FastAPI application entry point
├── tests/                      # Tests
│   ├── conftest.py             # Pytest configuration
│   ├── unit/                   # Unit tests
│   │   ├── test_agent_nodes.py
│   │   └── test_agent_tools.py
│   └── integration/            # Integration tests
│       └── test_api_endpoints.py
├── docs/                       # Additional documentation
│   ├── ARCHITECTURE.md         # System architecture details
│   └── QUICKSTART.md           # Quick start guide
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # Application Dockerfile
├── requirements.txt            # Python dependencies
├── seed_database.py            # Database seeding script
├── postman_collection.json     # Postman API testing collection
├── .env.example                # Environment template (create manually)
└── README.md
```

> **Note**: You'll need to create a `.env` file manually (copy from `.env.example` if available, or create based on the Environment Variables section below).

## 🚀 Quick Start

> **💡 For detailed setup instructions**, see [docs/QUICKSTART.md](docs/QUICKSTART.md)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- Redis (via Docker)

### Installation

#### 1. Clone and Setup
```bash
git clone <repository-url>
cd project-directory
```

#### 2. Environment Configuration
Create a `.env` file with your configuration:
```bash
# You'll need to create this file manually
# See "Environment Variables" section below for required values
```

Example `.env`:
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/customer_agent_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# LLM Configuration (optional - defaults to mock)
LLM_PROVIDER=mock
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here

# Agent Configuration
AGENT_MAX_TOKENS=500
AGENT_TEMPERATURE=0.7
AGENT_PROMPT_VARIANT=A
AGENT_DEFAULT_LANGUAGE=en
AGENT_AUTO_DETECT_LANGUAGE=true

# Logging
LOG_LEVEL=INFO
```

#### 3. Docker Setup (Recommended)
```bash
# Start all services (PostgreSQL, Redis, FastAPI app, Celery worker)
docker-compose up -d

# Check service status
docker-compose ps

# Check logs
docker-compose logs -f app
```

The API will be available at `http://localhost:8000`

#### 4. Database Setup
```bash
# Run migrations to add new schema fields
docker-compose exec app alembic upgrade head

# Seed test data (optional but recommended)
docker-compose exec app python seed_database.py
```

**New in v1.1.0:** The migration adds:
- Message deduplication support (`platform_message_id`)
- Message direction tracking (`INBOUND`/`OUTBOUND`)
- Message status for async sending (`QUEUED`/`SENT`/`FAILED`)
- Conversation priority (`high`/`normal`/`low`)
- Agent assignment (`assigned_to`)

#### 5. Local Setup (Alternative)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (must be running)
# Then run database migrations
alembic upgrade head

# Seed test data (optional)
python seed_database.py

# Start the application
uvicorn app.main:app --reload
```

## 📚 API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

> **⚠️ API UPDATES (v1.1.0)**: 
> - Conversation endpoints moved from `/messages/conversations` → `/conversations`
> - Message sending now asynchronous (returns `202 Accepted` with `job_id`)
> - Webhook endpoints include deduplication support

#### Core Endpoints
- `GET /` - Root endpoint (API info)
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus metrics

#### Webhooks
- `POST /webhooks/tiktok` - Receive TikTok messages (**with deduplication**)
- `POST /webhooks/linkedin` - Receive LinkedIn messages (**with deduplication**)
- `GET /webhooks/verify` - Webhook verification

**Deduplication**: Webhooks automatically detect and skip duplicate messages using `platform_message_id`.

#### Messages
- `POST /messages/send` - **[ASYNC]** Send message to platform (returns `202 Accepted` with `job_id`)

**Example Response:**
```json
{
  "success": true,
  "message_id": 123,
  "job_id": "7e3a9f6b-1c4d-4e8a-9b5c-2d7f8a6e4c3b"
}
```

#### Conversations (NEW PATH)
- `GET /conversations` - List conversations with filters
- `GET /conversations/{id}` - Get conversation details with message history

**New Query Parameters:**
- `priority` - Filter by priority (`high`, `normal`, `low`)
- `assigned_to` - Filter by assigned agent ID
- `platform` - Filter by platform (`tiktok`, `linkedin`)
- `status` - Filter by status (`active`, `escalated`, `closed`)
- `escalated` - Filter by escalation status (boolean)
- `limit` / `offset` - Pagination

#### Analytics
- `GET /analytics/metrics` - System metrics (avg response time, escalation rate, etc.)
- `GET /analytics/conversations` - Conversation insights by intent
- `GET /analytics/escalations` - Escalation statistics

#### Admin
- `POST /admin/escalate/{conversation_id}` - Manually escalate conversation
- `PUT /admin/override/{message_id}` - Override AI response
- `GET /admin/logs` - View system logs
- `POST /admin/agent/configure` - Update agent configuration
- `GET /admin/agent/status` - Get agent health status
- `POST /admin/agent/train` - Train/update agent (placeholder)

#### Agent (Aliases to Admin endpoints)
- `POST /agent/configure` - Configure agent settings
- `GET /agent/status` - Get agent status
- `POST /agent/train` - Train agent

## 🧪 Testing

### Run All Tests
```bash
# Activate virtual environment first
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # Linux/Mac

# Run all tests with coverage
pytest --cov=app tests/ -v

# Specific test file
pytest tests/integration/test_api_endpoints.py -v

# Unit tests only
pytest tests/unit/ -v
```

### Test Coverage
```bash
pytest --cov=app --cov-report=html tests/
# View coverage report at htmlcov/index.html
```

**Latest Test Suite Includes:**
- ✅ Webhook deduplication tests
- ✅ Async message sending (202 Accepted)
- ✅ New conversation endpoints
- ✅ Priority and assignment filtering
- ✅ Admin and agent management
- ✅ 30+ comprehensive integration tests

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| **Application** |
| `APP_NAME` | Application name | `AI Customer Support Agent` |
| `APP_VERSION` | Application version | `1.0.0` |
| `DEBUG` | Debug mode | `true` |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| **Database** |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/customer_agent_db` |
| **Redis & Celery** |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/0` |
| **LLM Configuration** |
| `LLM_PROVIDER` | LLM provider (`openai`, `anthropic`, `mock`) | `mock` |
| `OPENAI_API_KEY` | OpenAI API key (optional) | `None` |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | `None` |
| **Agent Configuration** |
| `AGENT_MAX_TOKENS` | Max tokens for LLM responses | `500` |
| `AGENT_TEMPERATURE` | LLM temperature | `0.7` |
| `AGENT_TIMEOUT_SECONDS` | Agent processing timeout | `30` |
| `AGENT_PROMPT_VARIANT` | Prompt variant for A/B testing (A/B) | `A` |
| `AGENT_DEFAULT_LANGUAGE` | Default language code | `en` |
| `AGENT_AUTO_DETECT_LANGUAGE` | Auto-detect message language | `true` |
| **Platform Integration** |
| `TIKTOK_CLIENT_KEY` | TikTok client key (optional) | `None` |
| `TIKTOK_CLIENT_SECRET` | TikTok client secret (optional) | `None` |
| `TIKTOK_WEBHOOK_SECRET` | TikTok webhook secret (optional) | `None` |
| `LINKEDIN_CLIENT_ID` | LinkedIn client ID (optional) | `None` |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn client secret (optional) | `None` |
| **Rate Limiting** |
| `TIKTOK_RATE_LIMIT` | TikTok requests per minute | `60` |
| `LINKEDIN_RATE_LIMIT` | LinkedIn requests per minute | `100` |
| **Logging** |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `logs/app.log` |

## 🎨 Agent Behavior Examples

### Scenario 1: Customer Support (TikTok)
**User**: "Hey, I ordered the blue hoodie 3 days ago but haven't received tracking info yet"

**Agent**:
- Classifies as `SUPPORT`
- Detects no urgency
- Responds: "Thank you for reaching out! I understand your concern. Could you please provide your order number so I can look into this for you right away?"

### Scenario 2: Sales Inquiry (LinkedIn)
**User**: "I'm interested in your enterprise plan. What's the pricing for 50 users?"

**Agent**:
- Classifies as `SALES`
- Generates persuasive response
- Captures lead information

### Scenario 3: Urgent Escalation
**User**: "This is ridiculous! I've been charged twice and no one is helping me!"

**Agent**:
- Classifies as `URGENT`
- **Immediately escalates** to human agent
- Flags as high priority
- Sends empathetic escalation message

## 🏗️ Architecture

### System Components

```mermaid
graph TB
    A[TikTok/LinkedIn] -->|Webhook| B[FastAPI]
    B --> C[Message Processor]
    C --> D[LangGraph Agent]
    D --> E[Intent Classifier]
    E --> F[Response Generator]
    F --> G[Escalation Checker]
    G --> H[Response Validator]
    H --> I[Database]
    H --> J[Platform API]
    C --> K[Redis Queue]
    K --> L[Celery Worker]
    I --> M[Analytics Service]
```

### Database Schema

**Users** → **Conversations** → **Messages**

- **Users**: Platform-specific user profiles
- **Conversations**: Conversation threads with status tracking
- **Messages**: Individual messages with sentiment and intent
- **AgentConfig**: Agent configuration and prompts
- **Analytics**: System metrics and insights

## 🔐 Security Notes

- All API endpoints should be secured with authentication in production
- Webhook signatures should be verified (implemented in platform clients)
- Environment variables should be properly secured
- Database connections use connection pooling
- Rate limiting implemented for platform APIs

## 📊 Monitoring & Logging

### Logs Location
- **Console**: Colored output with loguru
- **File**: `logs/app.log` (rotated at 500MB, 10 days retention)

### Log Levels
```bash
# Change log level in .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🚢 Deployment

### Docker Production Build
```bash
docker build -t customer-agent:latest .
docker-compose -f docker-compose.yml up -d
```

### Environment Checklist
- [ ] Set secure database password
- [ ] Configure LLM API keys
- [ ] Set up platform OAuth credentials
- [ ] Configure backup strategy
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure reverse proxy (Nginx)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License


## 🛠️ Development

### Code Quality
```bash
# Type checking
mypy app/

# Run linting (if configured)
# flake8 app/
```

### Database Seeding
The project includes a database seeding script for development and testing:
```bash
# Seed test data
python seed_database.py

# Or via Docker
docker-compose exec app python seed_database.py
```

This creates sample users, conversations, messages, and agent configurations.

### API Testing
Import the Postman collection for easy API testing:
```bash
# File: postman_collection.json
# Import into Postman to test all endpoints
```

### Adding New Features

#### Adding New Intents
1. Update `MessageIntent` enum in `app/models/database.py`
2. Add prompt template in `app/agent/prompts.py`
3. Update classification logic in `app/agent/nodes.py`
4. Add corresponding tests

#### Adding New Agent Nodes
1. Add node function in `app/agent/nodes.py`
2. Update workflow in `app/agent/graph.py`
3. Update `AgentState` TypedDict if needed
4. Add unit tests

## 📞 Support

For questions or issues:
- **API Documentation**: Visit http://localhost:8000/docs for interactive API docs
- **System Logs**: Check `/admin/logs` endpoint or view with `docker-compose logs -f`
- **Agent Status**: Check agent health at `/admin/agent/status` or `/agent/status`
- **Detailed Guides**: 
  - [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide with step-by-step setup
  - [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Comprehensive architecture documentation

## 📖 Additional Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Detailed system architecture, data flow diagrams, database schema, scaling considerations, and deployment architecture
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)**: 5-minute setup guide with testing examples and troubleshooting
- **[postman_collection.json](postman_collection.json)**: Postman collection for API testing

---

**Built with** ❤️ **using FastAPI, LangGraph, and LangChain**
