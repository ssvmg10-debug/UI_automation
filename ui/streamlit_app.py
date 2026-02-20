"""
Streamlit UI for Enterprise UI Automation Platform.
"""
import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# Page config
st.set_page_config(
    page_title="Enterprise UI Automation",
    page_icon="🤖",
    layout="wide"
)

# API endpoint
API_BASE_URL = "http://localhost:8001"

# Title and description
st.title("🤖 Enterprise UI Automation Platform")
st.markdown("""
**Production-grade deterministic UI automation with AI assistance**

This platform uses a 4-layer architecture:
1. **Deterministic Execution Core** - Stable, predictable automation
2. **State & Transition Engine** - Validates every action
3. **AI Assistance Layer** - Plans and suggests, never executes
4. **Memory & Learning** - Remembers successful patterns
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Browser always runs in headed mode (visible) - no headless option
    max_recovery = st.slider("Max Recovery Attempts", 0, 5, 2)
    use_v3 = st.checkbox("Use SAM-V3 Engine", value=True, help="SAM-V3: Vision+DOM+Semantic fusion, self-healing. Recommended for LG/e-commerce flows.")
    
    script_language = st.selectbox(
        "Script Language",
        options=["typescript", "javascript"],
        index=0,
        help="Choose the language for the generated Playwright script"
    )
    
    st.divider()
    
    st.header("📊 System Status")
    
    # Health check
    try:
        health = requests.get(f"{API_BASE_URL}/health").json()
        st.success("✓ System Healthy")
        st.metric("Total Executions", health["timestamp"]["total_executions"])
        if health["timestamp"]["total_executions"] > 0:
            st.metric("Success Rate", f"{health['timestamp']['success_rate']:.1f}%")
    except:
        st.error("✗ API Unreachable")
    
    st.caption("Backend logs: logs\\backend.log, logs\\uvicorn.log")

# Main tabs
tab1, tab2, tab3 = st.tabs(["🚀 Execute Test", "📈 Metrics", "📚 Documentation"])

# Tab 1: Execute Test
with tab1:
    st.header("Execute Test Case")
    
    instruction = st.text_area(
        "Test Case (Natural Language)",
        value="",
        height=200,
        placeholder="Enter test steps in natural language...\nExample:\nGo to https://example.com\nClick Login button\nType test@test.com in Email field"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        execute_btn = st.button("▶️ Execute", type="primary", use_container_width=True)
    
    # Execute
    if execute_btn:
        if not instruction.strip():
            st.error("Please enter test instructions")
        else:
            with st.spinner("🤖 Executing automation..."):
                try:
                    # Call API
                    response = requests.post(
                        f"{API_BASE_URL}/execute",
                        json={
                            "instruction": instruction,
                            "headless": False,
                            "max_recovery_attempts": max_recovery,
                            "script_language": script_language,
                            "use_v3": use_v3
                        },
                        timeout=300  # 5 minutes
                    )
                    
                    result = response.json()
                    steps_ok = result["steps_executed"]
                    steps_total = result["total_steps"]
                    success_pct = (steps_ok / steps_total * 100) if steps_total else 0
                    
                    # ---------- Execution Report (headed mode, success %, script) ----------
                    st.subheader("📋 Execution Report")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Browser mode", "Headed (visible)")
                    with col2:
                        st.metric("Steps", f"{steps_ok} / {steps_total}")
                    with col3:
                        st.metric("Success rate", f"{success_pct:.0f}%")
                    
                    # Display result banner
                    if result["success"] and steps_total > 0 and steps_ok == steps_total:
                        st.success(f"✅ Test Passed! 100% success ({steps_ok}/{steps_total} steps) – Headed mode execution completed.")
                    elif result["success"] and steps_total == 0:
                        st.info("No steps to run.")
                    else:
                        err_msg = result.get("error") or "One or more steps failed."
                        st.error(f"❌ Test Failed: {err_msg}")
                        st.caption(f"Steps completed: {steps_ok}/{steps_total}")
                    
                    # Test script used for this run (report)
                    if result.get("generated_script"):
                        st.divider()
                        st.subheader("📝 Test script used for UI automation (download or copy)")
                        
                        script_lang = result.get("script_language", "typescript")
                        file_ext = result.get("file_extension", ".ts")
                        test_file = f"test{file_ext}"
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Language:** `{script_lang.upper()}`")
                            st.markdown(f"**File:** `{test_file}`")
                        with col2:
                            st.download_button(
                                label=f"📥 Download {file_ext}",
                                data=result["generated_script"],
                                file_name=test_file,
                                mime="text/plain",
                                width="stretch"
                            )
                        
                        # Display script in code block
                        st.code(result["generated_script"], language=script_lang)
                        
                        # Instructions
                        with st.expander("ℹ️ How to run this script"):
                            st.markdown(f"""
To run the generated Playwright script:

1. **Install Playwright** (if not already installed):
```bash
npm init -y
npm install -D @playwright/test
npx playwright install
```

2. **Save the script** as `{test_file}` in your project directory

3. **Run the test**:
```bash
npx playwright test {test_file}
```

4. **Run with UI Mode** (for debugging):
```bash
npx playwright test {test_file} --ui
```

5. **Run in headed mode**:
```bash
npx playwright test {test_file} --headed
```
                            """)
                    
                    # Show execution details
                    st.divider()
                    # Show execution details
                    st.subheader("Execution Details")
                    
                    # Steps executed
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Steps Executed", result["steps_executed"])
                    col2.metric("Total Steps", result["total_steps"])
                    sr = (result["steps_executed"] / result["total_steps"] * 100) if result["total_steps"] else 0
                    col3.metric("Success Rate", f"{sr:.1f}%")
                    
                    # Step results
                    if result["results"]:
                        st.subheader("Step-by-Step Results")
                        
                        for i, step_result in enumerate(result["results"], 1):
                            with st.expander(f"Step {i} - {'✓ SUCCESS' if step_result['success'] else '✗ FAILED'}"):
                                st.json(step_result)
                    
                except requests.exceptions.Timeout:
                    st.error("⏱️ Execution timed out (>5 minutes)")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Cannot connect to API. Is the backend running?")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# Tab 2: Metrics
with tab2:
    st.header("📊 Execution Metrics")
    
    # Refresh button
    if st.button("🔄 Refresh Metrics"):
        st.rerun()
    
    try:
        # Get summary
        summary = requests.get(f"{API_BASE_URL}/metrics/summary").json()
        
        # Display summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Executions", summary["total_executions"])
        
        with col2:
            st.metric("Successful", summary["successful"])
        
        with col3:
            st.metric("Failed", summary["failed"])
        
        with col4:
            st.metric("Success Rate", f"{summary['success_rate']:.1f}%")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Average Duration", f"{summary['average_duration']:.2f}s")
        
        with col2:
            st.metric("Total Duration", f"{summary['total_duration']:.2f}s")
        
        # Recent executions
        st.subheader("Recent Executions")
        
        recent = requests.get(f"{API_BASE_URL}/metrics/recent?limit=20").json()
        
        if recent["executions"]:
            # Convert to DataFrame
            df_data = []
            for exec in recent["executions"]:
                df_data.append({
                    "Test Name": exec["test_name"],
                    "Status": "✓ SUCCESS" if exec["success"] else "✗ FAILED",
                    "Steps": f"{exec['steps_executed']}/{exec['steps_total']}",
                    "Duration (s)": f"{exec['duration_seconds']:.2f}",
                    "Time": exec["start_time"]
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("No executions yet")
        
        # Clear metrics
        if st.button("🗑️ Clear Metrics", type="secondary"):
            requests.post(f"{API_BASE_URL}/metrics/clear")
            st.success("Metrics cleared")
            st.rerun()
            
    except Exception as e:
        st.error(f"Failed to load metrics: {e}")

# Tab 3: Documentation
with tab3:
    st.header("📚 Documentation")
    
    st.markdown("""
    ## Architecture Overview
    
    ### Layer 1: Deterministic Execution Core
    - **Browser Manager**: Handles Playwright browser lifecycle
    - **DOM Extractor**: Converts raw DOM to structured elements
    - **Element Filter**: Applies hard constraints to reduce search space
    - **Element Ranker**: Multi-factor scoring for element matching
    - **Outcome Validator**: Ensures meaningful state transitions
    - **Action Executor**: Performs validated actions
    
    ### Layer 2: State & Transition Engine
    - **State Graph**: Tracks UI states as a graph
    - **Transition Detector**: Validates state changes
    - **State Manager**: Manages execution state
    
    ### Layer 3: AI Assistance Layer
    - **Planner Agent**: Converts natural language to structured plans
    - **Recovery Agent**: Suggests recovery strategies on failure
    - **LangGraph Orchestrator**: Coordinates execution flow
    
    ### Layer 4: Memory & Learning
    - **Pattern Registry**: Stores successful interaction patterns
    - **Semantic Memory**: Optional Mem0 integration
    
    ## Writing Test Cases
    
    Test cases are written in natural language. Supported actions:
    
    - **Navigate**: `Go to URL` or `Navigate to URL`
    - **Click**: `Click ELEMENT` or `Click on ELEMENT`
    - **Type**: `Type TEXT in FIELD` or `Enter TEXT in FIELD`
    - **Wait**: `Wait for ELEMENT`
    
    ### Example
    ```
    Navigate to https://example.com
    Click Login button
    Type user@example.com in Email
    Type password123 in Password
    Click Submit
    Wait for Dashboard
    ```
    
    ## Key Features
    
    ✅ **Deterministic Execution** - No random clicking
    ✅ **State Validation** - Every action validated
    ✅ **AI Assistance** - Plans and suggests, never executes
    ✅ **Pattern Learning** - Remembers what works
    ✅ **Recovery Strategies** - Intelligent failure recovery
    ✅ **Real-time Metrics** - Complete observability
    
    ## API Endpoints
    
    - `POST /execute` - Execute test case
    - `GET /metrics/summary` - Get metrics summary
    - `GET /metrics/recent` - Get recent executions
    - `WS /ws/execute` - WebSocket for real-time updates
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
    Enterprise UI Automation Platform v1.0.0 | Built with Playwright, LangGraph, and FastAPI
</div>
""", unsafe_allow_html=True)
