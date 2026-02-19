# Architecture Deep Dive

## System Overview

The Enterprise UI Automation Platform is built on a **4-layer architecture** that ensures deterministic execution while leveraging AI for intelligent planning and recovery.

```
┌──────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│                                                          │
│  ┌────────────────┐           ┌──────────────────┐     │
│  │   Streamlit    │◄─────────►│   FastAPI        │     │
│  │   Dashboard    │   REST    │   Backend        │     │
│  └────────────────┘           └──────────────────┘     │
└──────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTP/WebSocket
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  LANGGRAPH ORCHESTRATOR                  │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Initialize │─►│   Plan      │─►│  Execute    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                           │              │              │
│                           │              ▼              │
│                           │         ┌─────────────┐    │
│                           └────────►│  Validate   │    │
│                                     └─────────────┘    │
│                                           │             │
│                                ┌──────────┴────────┐   │
│                                ▼                   ▼   │
│                         ┌──────────┐        ┌─────────┐│
│                         │ Recover  │        │ Cleanup ││
│                         └──────────┘        └─────────┘│
└──────────────────────────────────────────────────────────┘
                           ▲
                           │
    ┌──────────────────────┴────────────────────────┐
    │                                                │
┌───▼─────────────────┐              ┌──────────────▼──────┐
│  AI AGENTS LAYER    │              │  CORE ENGINE        │
│  (Advisory Only)    │              │  (Deterministic)    │
│                     │              │                     │
│  • Planner Agent    │              │  • Browser Manager  │
│  • Recovery Agent   │              │  • DOM Extractor    │
│  • Semantic Helper  │              │  • Element Filter   │
│                     │              │  • Element Ranker   │
│                     │              │  • Validator        │
│                     │              │  • Action Executor  │
└─────────────────────┘              └─────────────────────┘
          │                                    │
          │                                    │
          ▼                                    ▼
┌─────────────────────┐              ┌─────────────────────┐
│  MEMORY LAYER       │              │  STATE ENGINE       │
│                     │              │                     │
│  • Pattern Registry │              │  • State Graph      │
│  • Mem0 Adapter     │              │  • Transition Log   │
│  • Success Patterns │              │  • State Manager    │
└─────────────────────┘              └─────────────────────┘
```

## Layer 1: Deterministic Execution Core

### Browser Manager
- Manages Playwright browser lifecycle
- Handles page sessions
- Screenshot capability
- Timeout management

### DOM Extractor
- Converts raw DOM to structured `DOMElement` objects
- Extracts clickables, inputs, all interactive elements
- Captures metadata: text, role, attributes, bounding box
- Region-aware extraction

### Element Filter
- Applies hard constraints to reduce search space
- Filters by action type (click, type, select)
- Visibility filtering
- Region/container filtering
- Size filtering (removes decorative elements)
- Position filtering

### Element Ranker
**Multi-Factor Scoring Algorithm:**

```python
score = (
    0.35 * exact_match +
    0.20 * semantic_similarity +
    0.15 * aria_label_match +
    0.10 * role_match +
    0.10 * container_context +
    0.05 * visibility +
    0.05 * position_bias +
    0.05 * historical_success
)
```

**Threshold:** 0.65 (configurable)

### Outcome Validator
- Captures page state before/after actions
- Validates state transitions
- Checks URL changes
- Checks title changes
- Checks DOM structure changes
- Checks visible text changes
- Prevents random clicking

### Action Executor
- **ONLY** layer that can interact with DOM
- Executes: click, type, navigate, wait
- Multi-candidate retry with validation
- State recording
- Comprehensive error handling

## Layer 2: State & Transition Engine

### State Model
```python
PageState:
  - url: str
  - title: str
  - dom_hash: str
  - visible_text_hash: str
```

### State Graph
- Tracks all UI states as nodes
- Records transitions as edges
- Builds valid transition patterns
- Enables replay and debugging
- Prevents state drift

### State Manager
- High-level state orchestration
- Combines state graph with current page tracking
- Records execution trace
- Provides state history

## Layer 3: AI Assistance Layer

### Planner Agent (OpenAI GPT-4o-mini)
**Role:** Convert natural language to structured plans

**Input:**
```
Navigate to https://example.com
Click Login
Type test@test.com in Email
```

**Output:**
```json
{
  "steps": [
    {"action": "NAVIGATE", "target": "https://example.com"},
    {"action": "CLICK", "target": "Login"},
    {"action": "TYPE", "target": "Email", "value": "test@test.com"}
  ]
}
```

**Also provides:**
- Synonym expansion
- Target text refinement
- Semantic helpers

### Recovery Agent (OpenAI GPT-4o-mini)
**Role:** Suggest recovery strategies on failure

**Input:** Failed action context
**Output:** Recovery strategies
```json
{
  "strategies": [
    {
      "type": "ALTERNATIVE_TARGET",
      "description": "Try 'Sign In' instead of 'Login'",
      "alternative_target": "Sign In"
    }
  ]
}
```

### LangGraph Orchestrator
Coordinates the full execution flow:

```
Initialize → Plan → Execute → Validate
                              │
                   ┌──────────┴─────────┐
                   │                    │
                Success              Failure
                   │                    │
                Next Step           Recover?
                                       │
                                    Retry
```

## Layer 4: Memory & Learning

### Pattern Registry
Stores successful interaction patterns:

```python
{
  "site": "lg.com",
  "intent": "checkout_as_guest",
  "canonical_label": "Continue as Guest",
  "alternative_labels": ["Guest Checkout", "Skip Login"],
  "success_count": 15,
  "transition_signature": "url_contains_checkout"
}
```

**NOT stored:** Raw selectors, XPaths, CSS selectors

### Mem0 Adapter (Optional)
- Semantic memory storage
- Vector-based similarity search
- Long-term pattern learning

## Execution Flow Example

### Test Case
```
Navigate to https://www.lg.com/in
Click Air Solutions
```

### Detailed Flow

**1. Planning (AI)**
```
Planner Agent processes:
"Navigate to https://www.lg.com/in
Click Air Solutions"

Generates:
[
  {"action": "NAVIGATE", "target": "https://www.lg.com/in"},
  {"action": "CLICK", "target": "Air Solutions"}
]
```

**2. Step 1 - Navigate (Deterministic)**
```
1. Capture state before: (url: "about:blank")
2. Execute: page.goto("https://www.lg.com/in")
3. Capture state after: (url: "https://www.lg.com/in")
4. Validate: URL changed ✓
5. Record transition
```

**3. Step 2 - Click (Deterministic)**
```
1. Capture state before
2. DOM Extraction:
   - Total elements found: 243
   - Clickable elements: 127
   
3. Filtering:
   - By visibility: 89 elements
   - By action type (CLICK): 89 elements
   - By size: 86 elements
   
4. Ranking (top 3):
   - "Air Solutions" (score: 0.95) ✓
   - "Air Conditioning" (score: 0.72)
   - "Air Care" (score: 0.68)
   
5. Try candidate 1:
   - Click "Air Solutions"
   - Wait 0.5s
   - Capture state after
   - Validate transition: URL changed ✓
   - SUCCESS!
   
6. Record success in pattern registry
```

## Key Design Decisions

### Why Deterministic First?
1. **Stability**: 75-80% success rate without AI
2. **Predictability**: Know exactly what will happen
3. **Debuggability**: Clear execution trace
4. **Performance**: No AI latency on each action

### Why Multi-Factor Scoring?
1. **Robustness**: No single point of failure
2. **Flexibility**: Handles various UI patterns
3. **Accuracy**: Reduces false positives
4. **Tunability**: Weights can be adjusted

### Why State Validation?
1. **Correctness**: Ensures action had intended effect
2. **Safety**: Prevents cascading failures
3. **Confidence**: Know when something actually worked
4. **Recovery**: Clear signal for when to retry

### Why AI Advisory Only?
1. **Control**: Execution never dependent on AI
2. **Cost**: No API calls for every action
3. **Speed**: Deterministic execution is faster
4. **Reliability**: No AI hallucinations in execution

## Performance Characteristics

### Execution Speed
- **DOM Extraction**: ~100-200ms
- **Filtering**: ~10ms
- **Ranking**: ~20ms
- **Action + Validation**: ~500-1000ms
- **Total per step**: ~1-2 seconds

### AI Latency
- **Planning**: ~2-5 seconds (once per test)
- **Recovery**: ~2-3 seconds (only on failure)

### Success Rates
- **Deterministic engine alone**: 75-80%
- **With AI recovery**: 85-95%
- **With pattern memory**: 90-95+%

## Scalability

### Current Architecture
- Single browser instance
- Sequential execution
- Suitable for: 10-100 tests/hour

### Future Scaling Options
1. **Parallel Execution**: Multiple browser instances
2. **Distributed**: Queue-based job distribution
3. **Cloud**: Kubernetes deployment
4. **Multi-browser**: Chrome, Firefox, Safari

## Security Considerations

1. **Credentials**: Never log sensitive data
2. **Screenshots**: Configurable, stored securely
3. **API Keys**: Environment variables only
4. **Memory**: Semantic patterns only, no raw selectors

## Monitoring & Observability

### Logging Levels
- **DEBUG**: Full execution trace
- **INFO**: Step-level progress
- **WARNING**: Recoverable issues
- **ERROR**: Failures

### Metrics Tracked
- Execution count
- Success rate
- Duration statistics
- Failure patterns
- Element scoring distribution

### Telemetry
- State transition history
- Element ranking details
- Recovery strategy effectiveness
- Pattern learning statistics

---

**This architecture ensures reliable, maintainable, and scalable UI automation.**
