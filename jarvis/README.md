# 🤖 JARVIS - Core Nexus AI Agent System

JARVIS is an autonomous AI agent system built with LangGraph + Gemini AI + Core Nexus Memory Service integration. It provides self-improving capabilities for system optimization and intelligent automation.

## 🏗️ Architecture

- **LangGraph Supervisor Pattern**: Multi-agent orchestration with supervisor, analysis, and planning agents
- **Gemini AI**: Advanced reasoning with thinking capabilities and function calling
- **Core Nexus Memory**: Persistent memory storage with semantic search
- **PostgreSQL**: State checkpointing and persistence (optional)
- **Redis**: Pub/sub messaging and caching (optional)
- **FastAPI**: REST API for external interaction

## 🚀 Quick Start

### Prerequisites

1. **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/)
2. **Core Nexus**: Ensure Core Nexus Memory Service is running
3. **Python 3.11+**: For local development

### Installation

1. **Clone and Setup**
   ```bash
   cd core-nexus/jarvis
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Required: Add your Gemini API key to .env
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Optional: Customize other settings
   CORE_NEXUS_URL=https://core-nexus-memory-service.onrender.com
   JARVIS_DEBUG=false
   ```

4. **Test Installation**
   ```bash
   python -m jarvis.main --mode test
   ```

### Docker Deployment

```bash
# Local development with full stack
docker-compose up -d

# Production deployment
docker build -t jarvis .
docker run -p 8001:8001 --env-file .env jarvis
```

## 🎯 Usage

### Interactive Mode

```bash
python -m jarvis.main --mode interactive
```

Commands in interactive mode:
- `help` - Show available commands
- `status` - Show system status
- `stats` - Show detailed statistics
- `task <description>` - Process a task through JARVIS workflow
- `chat <message>` - Direct chat with JARVIS supervisor
- `search <query>` - Search Core Nexus memories

### API Server

```bash
# Start API server
python -m jarvis.main --mode api

# Or use Docker
docker-compose up jarvis
```

API endpoints:
- `GET /health` - Health check
- `POST /tasks` - Process a task
- `POST /chat` - Chat with JARVIS
- `GET /stats` - System statistics
- `POST /memories` - Store memory
- `POST /memories/search` - Search memories

### Single Task Processing

```bash
python -m jarvis.main --mode task --task "Analyze system performance and suggest optimizations"
```

## 🧠 Agent Capabilities

### Supervisor Agent
- Central decision making and coordination
- High-level strategic planning
- Agent orchestration and workflow management

### Analysis Agent
- System performance monitoring
- Data analysis and pattern recognition
- Health and capacity assessment

### Planning Agent
- Strategic planning and optimization
- Resource allocation and scheduling
- Implementation roadmap development

### Core Features
- **Memory Integration**: Persistent storage and retrieval via Core Nexus
- **Self-Improvement**: Learning from experiences and adapting strategies
- **Thinking Capabilities**: Deep reasoning with Gemini AI
- **State Persistence**: Workflow state management with checkpointing
- **Human-in-the-Loop**: Approval workflows for critical decisions

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Gemini AI API key | Required |
| `CORE_NEXUS_URL` | Core Nexus Memory Service URL | Production URL |
| `DATABASE_URL` | PostgreSQL connection string | Optional |
| `REDIS_URL` | Redis connection string | Optional |
| `JARVIS_MAX_ITERATIONS` | Maximum workflow iterations | 10 |
| `JARVIS_SELF_IMPROVEMENT` | Enable self-improvement | true |
| `JARVIS_DEBUG` | Debug mode | false |

### Advanced Configuration

- **Checkpointing**: Configure PostgreSQL for state persistence
- **Memory Sync**: Adjust sync intervals with Core Nexus
- **Agent Behavior**: Customize agent system prompts
- **Safety Controls**: Configure human approval workflows

## 📊 Monitoring

### Health Endpoints
- `/health` - System health status
- `/stats` - Detailed system statistics
- `/insights` - Recent JARVIS learnings

### Logging
JARVIS uses structured logging with contextual information for debugging and monitoring.

## 🛡️ Safety & Security

- **Human Approval**: Critical decisions require human confirmation (configurable)
- **State Rollback**: Time-travel debugging and course correction
- **Safety Boundaries**: Controlled self-improvement with limits
- **Audit Trail**: Complete decision and action logging

## 🔄 Self-Improvement

JARVIS continuously learns and improves through:
- **Performance Analysis**: Evaluating decision effectiveness
- **Strategy Adaptation**: Meta-learning for workflow optimization
- **Knowledge Synthesis**: Combining learnings into actionable insights
- **Recursive Enhancement**: Safe self-modification with approval gates

## 🐛 Troubleshooting

### Common Issues

1. **Gemini API Connection**
   ```bash
   # Verify API key
   python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('API key valid')"
   ```

2. **Core Nexus Connection**
   ```bash
   # Test Core Nexus health
   curl https://core-nexus-memory-service.onrender.com/health
   ```

3. **Dependencies**
   ```bash
   # Reinstall dependencies
   pip install --upgrade -r requirements.txt
   ```

### Debug Mode

```bash
# Enable debug logging
export JARVIS_DEBUG=true
export JARVIS_LOG_LEVEL=DEBUG
python -m jarvis.main --mode interactive
```

## 🚀 Production Deployment

### Render.com Deployment

1. **Update render.yaml**
   ```yaml
   services:
     - type: web
       name: jarvis-ai-agent
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: python -m jarvis.main --mode api
       envVars:
         - key: GEMINI_API_KEY
           sync: false  # Set in dashboard
   ```

2. **Set Environment Variables**
   - Configure Gemini API key in Render dashboard
   - Set Core Nexus URL and other production settings

3. **Deploy**
   ```bash
   git push origin main
   ```

### Health Checks

- Health endpoint: `/health`
- Startup time: ~60 seconds
- Auto-restart on failure

## 📚 API Reference

### Task Processing

```bash
# Process a task
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyze system performance",
    "context": {"priority": "high"}
  }'
```

### Chat Interface

```bash
# Chat with JARVIS
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current system status?",
    "agent": "supervisor"
  }'
```

### Memory Operations

```bash
# Store memory
curl -X POST http://localhost:8001/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "System optimization completed",
    "importance_score": 0.8,
    "metadata": {"type": "achievement"}
  }'

# Search memories
curl -X POST http://localhost:8001/memories/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "optimization",
    "limit": 5
  }'
```

## 🔮 Future Development

### Phase 2: Advanced Capabilities
- Execution agent for automated actions
- Multi-modal processing (images, documents)
- Advanced self-modification capabilities
- Predictive system optimization

### Phase 3: Enterprise Features
- Horizontal scaling and load balancing
- Advanced monitoring and alerting
- Enterprise security and compliance
- Integration with CI/CD pipelines

## 🤝 Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation for changes
4. Ensure all safety checks remain in place

## 📄 License

See LICENSE file for details.

---

**🚀 Ready to optimize your systems with JARVIS? Start with `python -m jarvis.main --mode test` to verify your setup!**