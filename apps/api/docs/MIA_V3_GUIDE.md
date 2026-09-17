# MIA v3.0 - Gemini 3 Deep Think & Agent Lightning Integration

## Overview
SamudraSense's Marine Intelligence Assistant (MIA) has been upgraded to v3.0 with:
- **Gemini 3 Pro Preview**: Advanced reasoning with Deep Think mode
- **Gemini 3 Flash Preview**: High-speed mode for real-time tracking
- **Agent Lightning RLAF**: Reinforcement Learning from Agent Feedback
- **Enhanced Reasoning Traces**: Transparent decision-making process

## Model Selection

### Primary: gemini-3-pro-preview
**Use for:**
- Complex analytical queries ("Why are vessels avoiding this MPA?")
- Cross-referencing AIS data with pollution coordinates
- Behavioral pattern analysis
- Compliance risk assessments

**Features:**
- Deep Think reasoning mode enabled by default
- Explicit thought traces for transparency
- Superior "Why" question handling
- Multi-step logical deduction

### Speed Mode: gemini-3-flash-preview
**Use for:**
- Real-time vessel tracking
- High-volume alert generation
- Quick status checks
- Dashboard queries

**Features:**
- 3-5x faster response time
- Lower latency for live data
- Optimized for simple queries
- Reduced token costs

## Configuration

### 1. Environment Setup
Add to `.env`:
```bash
# Gemini 3 API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Agent Lightning (Optional)
AGENT_LIGHTNING_URL=http://localhost:8000
AGENT_LIGHTNING_ENABLED=false
```

### 2. Usage in Code

#### Standard Mode (Deep Think)
```python
from app.services.chatbot import mia

# Automatically uses gemini-3-pro-preview with Deep Think
response = await mia.process_message(
    message="Why is vessel MMSI 123456789 showing dark activity patterns?",
    conversation_history=[]
)

print(response["response"])           # Final answer
print(response["reasoning_trace"])    # Gemini 3 thought process
print(response["reward_score"])       # Agent Lightning score
print(response["data_confidence"])    # 0-100% confidence
```

#### Speed Mode (Real-time)
```python
from app.services.chatbot import mia_speed

# Uses gemini-3-flash-preview (no Deep Think)
response = await mia_speed.process_message(
    message="Show vessels near 40.7N, 74.0W",
    conversation_history=[]
)
```

#### Custom Configuration
```python
from app.services.chatbot import MarineIntelligenceAssistant

# Custom instance with specific settings
custom_mia = MarineIntelligenceAssistant(
    use_deep_think=True,   # Enable reasoning trace
    speed_mode=False       # Use Pro model
)
```

### 3. Agent Lightning Integration (Optional)

#### Enable Agent Lightning
```python
from app.services.agent_lightning import initialize_lightning

# Initialize Lightning client
lightning = initialize_lightning(
    server_url="http://localhost:8000",
    enable=True
)

# Process queries (automatically logged to Lightning)
response = await mia.process_message("Show pollution events")

# Get session statistics
stats = lightning.get_session_statistics()
print(f"Average reward: {stats['average_reward']}")
```

#### Using the Decorator
```python
from app.services.agent_lightning import AgentLightningDecorator

lightning = initialize_lightning()
decorator = AgentLightningDecorator(lightning)

@decorator.trace_rollout
async def my_custom_function(message: str):
    return await mia.process_message(message)
```

## System Prompt Highlights

The new MIA v3.0 system prompt includes:

### Reasoning Directive
Before every response, MIA generates an internal `<thought>` block:
1. **Identify States**: Current vessel/pollution/MPA status
2. **Tool Selection**: Which API maximizes data reward
3. **Trace Validation**: Does retrieved data answer the query
4. **Cross-Reference**: Any contradictions or gaps
5. **Confidence Assessment**: Reliability score calculation

### Operational Tasks
- **Vessel Behavioral Intelligence**: Dark activity, loitering, anomalies
- **Pollution Correlation**: Link spills to transit lanes
- **MPA Compliance**: Probability of violation scoring

### Reward Alignment (Agent Lightning)
- **Accuracy (+1.0)**: Grounded in tool data only
- **Explainability (+0.5)**: Citing sources
- **Hallucination (-1.0)**: Fabricating data
- **Completeness (+0.3)**: Providing follow-up questions

## Response Format

MIA v3.0 responses now include:

```json
{
  "response": "Full markdown-formatted answer",
  "reasoning_trace": "Internal thought process from Gemini 3",
  "tool_calls": [
    {
      "name": "query_vessel_intel",
      "arguments": {"mmsi": "123456789"},
      "result": {...}
    }
  ],
  "data_confidence": 95,
  "sources": ["AIS Database", "Copernicus Sentinel-2"],
  "reward_score": 1.5,
  "model_used": "gemini-3-pro-preview"
}
```

## Tool Enhancements

### New Parameters
- **behavioral_flag**: Filter by `dark_activity`, `loitering`, `speed_anomaly`
- **indicator**: Added `microplastics` to pollution types
- **metric_type**: Added `risk_assessment` for MPA compliance

### Example Tool Calls
```python
# Vessel dark activity analysis
await mia.process_message(
    "Show vessels with dark activity in the Mediterranean last week"
)

# Pollution correlation
await mia.process_message(
    "Find oil spills near busy shipping lanes in the Gulf of Mexico"
)

# MPA risk assessment
await mia.process_message(
    "What's the violation probability for commercial vessels near Galápagos Marine Reserve?"
)
```

## Performance Benchmarks

| Model | Query Type | Avg Response Time | Token Cost | Use Case |
|-------|-----------|-------------------|------------|----------|
| gemini-3-pro-preview | Complex analytical | 4-8s | Higher | Deep investigations |
| gemini-3-flash-preview | Simple queries | 0.5-2s | Lower | Real-time dashboards |

## Migration from v2.x

### Breaking Changes
1. Import path changed: `from google import genai` (new SDK)
2. Response includes `reasoning_trace` field
3. Tool definitions use JSON-RPC format (not protobuf)

### Backward Compatibility
Old chatbot endpoints remain functional. No frontend changes required.

### Gradual Rollout
```python
# Use v3.0 for specific features
if user_query_needs_deep_analysis:
    response = await mia.process_message(query)  # v3.0
else:
    response = await legacy_chatbot.process(query)  # v2.x
```

## Troubleshooting

### Issue: "Model not found" error
**Solution**: Ensure using the latest Google Generative AI SDK:
```bash
pip install --upgrade google-genai==0.3.0
```

### Issue: No reasoning trace in response
**Solution**: Verify Deep Think is enabled:
```python
mia = MarineIntelligenceAssistant(use_deep_think=True)
```

### Issue: High latency
**Solution**: Switch to speed mode for real-time queries:
```python
from app.services.chatbot import mia_speed
response = await mia_speed.process_message(query)
```

## Best Practices

1. **Use Pro for "Why" questions**: Deep Think excels at causation analysis
2. **Use Flash for dashboards**: Speed mode for frequent polling
3. **Enable Lightning for training**: Track reward scores to improve performance
4. **Monitor confidence scores**: Alert if confidence drops below 70%
5. **Cite sources always**: Helps users trust the analysis

## Example Queries (Optimized for Gemini 3)

### Complex Reasoning (Pro)
```
"Why are fishing vessels loitering near the EEZ boundary 
despite the MPA restrictions? Cross-reference with historical 
violation patterns."
```

### Real-time Tracking (Flash)
```
"Show all tankers within 50km of 34.5N, 120.2W moving faster than 15 knots"
```

### Pollution Investigation (Pro)
```
"Find oil spill events in Q1 2026, correlate with nearby vessel 
traffic, and identify potential sources"
```

## Additional Resources

- [Gemini API documentation](https://ai.google.dev/gemini-api/docs)
- Issues: https://github.com/Aditya-Patil27/marine_gurad/issues
