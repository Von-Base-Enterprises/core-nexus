# 🤖 Jarvis AI Assistant - Core Nexus Integration Guide

## Overview

Jarvis is a conversational AI assistant powered by Google ADK (Agent Development Kit) that provides an intelligent interface to the Core Nexus memory system. It combines state-of-the-art language models with Core Nexus's semantic memory capabilities.

## Architecture

```
┌─────────────────────┐
│   User Interface    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Jarvis Agent      │
│  (Google ADK)       │
├─────────────────────┤
│ • Gemini 2.0 Flash  │
│ • Session Management│
│ • Function Calling  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Core Nexus API    │
├─────────────────────┤
│ • Memory Store      │
│ • Vector Search     │
│ • Knowledge Graph   │
└─────────────────────┘
```

## Key Features

### 1. **Conversational Memory Interface**
- Natural language queries to search memories
- Context-aware responses using conversation history
- Automatic memory creation from important conversations

### 2. **Google ADK Integration**
- Leverages Gemini 2.0 Flash for advanced language understanding
- Built-in function calling for seamless Core Nexus integration
- Session management for maintaining conversation context

### 3. **Memory Operations**
- **Search**: Find relevant memories using natural language
- **Create**: Store important information from conversations
- **Context**: Maintain conversation history and continuity

## Installation

1. **Install Google ADK**:
```bash
pip install google-genai
```

2. **Set Environment Variables**:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export PGVECTOR_PASSWORD="your-database-password"
```

3. **Deploy with Core Nexus**:
The Jarvis agent is automatically included when deploying the memory service.

## Usage

### Interactive CLI Mode

```bash
cd python/memory_service
python jarvis_agent.py
```

### API Endpoints

#### Chat with Jarvis
```bash
POST /jarvis/chat
Content-Type: application/json

{
  "message": "What do you know about Project Horizon?",
  "user_id": "user123",
  "conversation_id": "conv456"
}

Response:
{
  "response": "Project Horizon is an AI initiative focused on autonomous agents...",
  "conversation_id": "conv456",
  "session_id": "sess789"
}
```

#### Check Jarvis Status
```bash
GET /jarvis/status

Response:
{
  "status": "online",
  "session_id": "sess789",
  "capabilities": ["memory_search", "memory_creation", "conversation_history", "context_awareness"],
  "model": "gemini-2.0-flash-latest",
  "framework": "google-adk",
  "conversation_history_size": 5
}
```

## Example Conversations

### Basic Memory Search
```
User: What are the latest performance improvements for Core Nexus?
Jarvis: Based on the memories I found, Core Nexus achieved a 78% performance improvement through pgvector optimization and Redis caching, bringing query latency down from 755ms to 165ms.
```

### Creating Memories
```
User: Remember that the Q2 deadline for Project Horizon is June 30, 2025.
Jarvis: I've stored this important deadline information. The Q2 deadline for Project Horizon (June 30, 2025) has been added to the memory system.
```

### Contextual Follow-ups
```
User: Who is leading that project?
Jarvis: Let me search for information about Project Horizon's leadership... According to the memories, the Horizon team consists of 5 engineers and 2 ML researchers, though I don't have specific information about the project lead.
```

## Advanced Features

### 1. **Function Calling**
Jarvis uses three main functions:
- `search_memories(query, limit)` - Search Core Nexus memories
- `create_memory(content, importance, tags)` - Store new memories
- `get_conversation_history(limit)` - Retrieve conversation context

### 2. **Memory Importance Scoring**
- Automatically assigns importance scores (0.0-1.0) to memories
- Higher scores for explicitly requested memories
- Contextual scoring based on conversation flow

### 3. **Entity Recognition**
- Integrates with Core Nexus's entity extraction pipeline
- Automatically identifies people, projects, dates, and concepts
- Builds knowledge graph relationships

## Performance Considerations

1. **Response Time**: Average 200-500ms including memory search
2. **Context Window**: Maintains last 10-20 messages for context
3. **Concurrent Sessions**: Supports multiple simultaneous conversations
4. **Caching**: Leverages Core Nexus's Redis cache for faster responses

## Security

- API key authentication required
- User-scoped memory access
- Conversation isolation by user_id and conversation_id
- No storage of sensitive information in conversation history

## Troubleshooting

### Common Issues

1. **"Jarvis agent not available" error**
   - Ensure `jarvis_agent.py` is in the correct path
   - Check Google ADK installation: `pip show google-genai`

2. **"Failed to initialize Jarvis" error**
   - Verify GEMINI_API_KEY is set correctly
   - Check network connectivity to Google services

3. **Memory search returns no results**
   - Ensure Core Nexus has indexed memories
   - Check database connectivity
   - Verify user permissions

## Future Enhancements

1. **Multi-turn Reasoning**: Complex queries requiring multiple memory searches
2. **Proactive Insights**: Suggest relevant memories based on context
3. **Voice Interface**: Speech-to-text and text-to-speech integration
4. **Custom Personas**: Configurable agent personalities and behaviors
5. **Advanced Analytics**: Track conversation patterns and memory usage

## Development

### Testing Jarvis
```bash
python test_jarvis_agent.py
```

### Adding New Capabilities
1. Add function declaration to `JARVIS_FUNCTIONS`
2. Implement handler in `handle_function_call()`
3. Update system prompt if needed
4. Test with example conversations

## Conclusion

Jarvis brings conversational AI to Core Nexus, making the memory system more accessible and intelligent. By combining Google ADK's advanced language capabilities with Core Nexus's semantic memory storage, users can interact with their knowledge base in a natural, intuitive way.