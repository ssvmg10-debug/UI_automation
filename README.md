# 🤖 Enterprise UI Automation Platform

**Production-grade, deterministic UI automation with AI assistance**

A revolutionary UI automation platform that inverts the traditional approach: **execution is deterministic, AI assists but never controls**.

## 🎯 Core Philosophy

### Traditional Approach (WRONG)
```
AI → Selects Element → Clicks DOM → Hope it works ❌
```

### Our Approach (CORRECT)
```
Deterministic Engine → Validates State → AI Assists Planning ✅
```

## 🏗 Architecture

### 4-Layer Design

```
┌─────────────────────────────────────────────────┐
│  Layer 4: Memory & Learning                     │
│  - Pattern Registry                             │
│  - Semantic Memory (Optional Mem0)              │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: AI Assistance (Advisory Only)         │
│  - Planner Agent (NL → Structured)              │
│  - Recovery Agent (Suggests fixes)              │
│  - LangGraph Orchestrator                       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: State & Transition Engine             │
│  - State Graph                                  │
│  - Transition Validator                         │
│  - State Manager                                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 1: Deterministic Execution Core          │
│  - Browser Manager                              │
│  - DOM Extractor                                │
│  - Element Filter (Hard constraints)            │
│  - Element Ranker (Multi-factor scoring)        │
│  - Outcome Validator (State transitions)        │
│  - Action Executor (ONLY layer that clicks)     │
└─────────────────────────────────────────────────┘
```

## ✨ Key Features

✅ **Deterministic Execution** - No random clicking, no element guessing  
✅ **State Validation** - Every action validated with state transitions  
✅ **AI Assistance** - Plans and suggests, never executes directly  
✅ **Multi-Factor Scoring** - Enterprise-grade element ranking (8 factors)  
✅ **Pattern Learning** - Remembers successful interactions  
✅ **Intelligent Recovery** - Smart failure diagnosis and recovery  
✅ **Real-time Metrics** - Complete observability and telemetry  
✅ **Natural Language** - Write tests in plain English  
✅ **Script Generation** - Export tests as JavaScript/TypeScript Playwright code  

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. **Clone and navigate to directory**
   ```bash
   cd "c:\Users\gparavasthu\Workspace\Gen AI QE\UI_automation"
   ```

2. **Activate virtual environment**
   ```powershell
   & "C:\Users\gparavasthu\Workspace\Truvelocity\code_export\agentic-sdlc-platform\venv\Scripts\Activate.ps1"
   ```

3. **Run setup**
   ```bash
   python setup.py
   ```

4. **Configure environment**
   - Copy `.env.example` to `.env`
   - Add your `OPENAI_API_KEY`

5. **Start the platform**

   **Terminal 1 - API Server:**
   ```bash
   python -m app.main
   ```

   **Terminal 2 - UI:**
   ```bash
   streamlit run ui/streamlit_app.py
   ```

6. **Access UI**
   - Open browser: http://localhost:8501

## 📝 Writing Test Cases

### Natural Language Format

```
Navigate to https://www.lg.com/in
Click Air Solutions
Click Split AC
Click the first product
Click Buy Now
```

### Supported Actions

| Action | Syntax | Example |
|--------|--------|---------|
| Navigate | `Go to URL` | `Go to https://example.com` |
| Click | `Click ELEMENT` | `Click Login button` |
| Type | `Type TEXT in FIELD` | `Type test@test.com in Email` |
| Wait | `Wait for ELEMENT` | `Wait for Dashboard` |

## 🔧 How It Works

### 1. Planning Phase (AI)
```
Natural Language → Planner Agent → Structured Steps
```

### 2. Execution Phase (Deterministic)
```
For each step:
  1. Extract DOM → Structured Elements
  2. Filter by action type
  3. Rank by multi-factor score
  4. Try top candidates
  5. Validate state transition
  6. If valid → Success
     If invalid → Next candidate
```

### 3. Recovery Phase (AI Assists)
```
On failure:
  1. Recovery Agent analyzes context
  2. Suggests alternative targets
  3. Deterministic engine retries
```

## 📊 Element Ranking (Production-Grade)

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Exact Match | 35% | Text matches exactly |
| Semantic Similarity | 20% | Text similarity score |
| Aria Label | 15% | Accessibility label match |
| Role Match | 10% | Correct HTML role |
| Container Context | 10% | In expected region |
| Visibility | 5% | Element visible |
| Position Bias | 5% | Prefer upper page elements |

**Threshold:** 0.65 (configurable)

## 🎨 UI Dashboard

The Streamlit dashboard provides:

- **Test Execution** - Run tests with real-time feedback
- **Script Language Selection** - Choose JavaScript or TypeScript output
- **Generated Scripts** - Download executable Playwright test code
- **Metrics Dashboard** - Success rates, duration, trends
- **Execution History** - Detailed step-by-step results
- **Configuration** - Headless mode, recovery attempts

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📦 Project Structure

```
enterprise_ui_automation/
├── app/
│   ├── core/               # Deterministic execution engine
│   │   ├── browser.py
│   │   ├── dom_extractor.py
│   │   ├── element_filter.py
│   │   ├── element_ranker.py
│   │   ├── outcome_validator.py
│   │   ├── action_executor.py
│   │   └── state_manager.py
│   │
│   ├── agents/             # AI assistance layer
│   │   ├── planner_agent.py
│   │   ├── recovery_agent.py
│   │   └── orchestrator.py
│   │
│   ├── memory/             # Learning layer
│   │   ├── pattern_registry.py
│   │   └── mem0_adapter.py
│   │
│   ├── compiler/           # NL compiler
│   │   ├── instruction_model.py
│   │   └── nl_compiler.py
│   │
│   ├── telemetry/          # Observability
│   │   ├── logger.py
│   │   └── metrics.py
│   │
│   └── api/                # FastAPI backend
│       └── main.py
│
├── ui/                     # Streamlit frontend
│   └── streamlit_app.py
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔍 Example: LG E-commerce Flow

### Test Case
```
Navigate to https://www.lg.com/in
Click Air Solutions
Click Split AC
Click the first product
Click Buy Now
```

### Execution Flow

1. **Planning**
   - Planner converts to 5 structured steps

2. **Step 1: Navigate**
   - Direct navigation to URL
   - State validation: URL changed ✓

3. **Step 2: Click "Air Solutions"**
   - Extract 127 clickable elements
   - Filter to visible clickables: 89
   - Rank by target "Air Solutions"
   - Top candidate scores 0.92
   - Click and validate state transition ✓

4. **Step 3: Click "Split AC"**
   - Extract elements in "Air Solutions" region
   - Rank and click best match
   - Validate URL or DOM changed ✓

And so on...

## 🛡️ What This Fixes

| Problem | Traditional | Our Solution |
|---------|------------|--------------|
| Random Clicks | AI guesses elements | Deterministic ranking with threshold |
| State Drift | No validation | Every action validated |
| Cache Poisoning | Raw selectors stored | Semantic patterns only |
| Flaky Tests | Hope-based | Multi-candidate retry with validation |
| Over-dependence on AI | AI controls everything | AI assists, deterministic executes |

## ⚙️ Configuration

### Environment Variables

```env
# API Keys
OPENAI_API_KEY=your_key_here

# Execution
HEADLESS=true
MAX_RETRIES=3
SCORE_THRESHOLD=0.65

# State Management
ENABLE_STATE_TRACKING=true
MAX_STATE_HISTORY=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/automation.log
```

## 📈 Metrics & Observability

### Available Metrics

- Total executions
- Success rate
- Average duration
- Step-by-step results
- Failure analysis
- State transition history

### API Endpoints

- `POST /execute` - Execute test case
- `GET /metrics/summary` - Get metrics summary
- `GET /metrics/recent` - Recent executions
- `WS /ws/execute` - WebSocket for real-time updates

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Test Coverage
```bash
pytest --cov=app tests/
```

## � Documentation

- **[README.md](README.md)** - This file, complete overview
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Deep architectural dive
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Quick start guide
- **[SCRIPT_GENERATION.md](docs/SCRIPT_GENERATION.md)** - Script generation feature guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What was built
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Problem solving

## �🔮 Roadmap

### Phase 1 - Foundation (✅ Complete)
- Deterministic execution core
- State graph engine
- Basic AI planning

### Phase 2 - Intelligence (In Progress)
- Enhanced semantic matching
- Advanced recovery strategies
- Pattern learning optimization

### Phase 3 - Scale (Planned)
- Distributed execution
- Multi-browser support
- Advanced analytics

### Phase 4 - Enterprise (Planned)
- SaaS deployment
- Team collaboration
- CI/CD integration

## 🤝 Contributing

This is a production-grade enterprise platform. Contributions should maintain:

1. **Deterministic-first** approach
2. **AI as assistant**, not controller
3. **State validation** on all actions
4. **Clean architecture** separation
5. **Comprehensive logging**

## 📄 License

MIT License - See LICENSE file

## 🙏 Credits

Built with:
- **Playwright** - Browser automation
- **LangGraph** - AI workflow orchestration
- **FastAPI** - High-performance API
- **Streamlit** - Interactive UI
- **OpenAI** - Natural language processing

## 🎓 Philosophy

> "The best automation is invisible. The system should be so reliable that you forget it's there."

This platform achieves that by:
1. Making execution **deterministic**
2. Making validation **mandatory**
3. Making AI **advisory**
4. Making observability **comprehensive**

---

**Built for enterprises who need automation they can trust.**

🚀 **Ready to automate with confidence!**