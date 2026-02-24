"""
Streamlit UI for Enterprise UI Automation Platform.
"""
import os
import streamlit as st
import requests
import requests.exceptions
import json
from datetime import datetime
import pandas as pd

# Load .env so API_HOST, API_PORT, API_BASE_URL are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Page config
st.set_page_config(
    page_title="Enterprise UI Automation",
    page_icon="🤖",
    layout="wide"
)

# API endpoint - from env or API_HOST:API_PORT (matches backend config)
# Use localhost when backend binds to 0.0.0.0 so the UI (client) can reach it
_api_host = os.environ.get("API_HOST", "localhost").strip()
if _api_host == "0.0.0.0":
    _api_host = "localhost"
API_BASE_URL = os.environ.get("API_BASE_URL") or (
    f"http://{_api_host}:{os.environ.get('API_PORT', '8002')}"
)

# Execution timeout (seconds) - keep high so long enterprise tests complete and UI gets response/script
EXECUTE_TIMEOUT = int(os.environ.get("EXECUTE_TIMEOUT", "7200"))  # 2h default; set EXECUTE_TIMEOUT in .env to override

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
    force_run = st.checkbox(
        "Force re-run (bypass cache)",
        value=False,
        help="If the same test was run recently, result is reused. Check to run again and skip cache."
    )
    
    st.divider()
    
    st.header("📊 System Status")
    
    # Health check
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5).json()
        st.success("✓ System Healthy")
        summary = health.get("timestamp") or health.get("metrics") or {}

        # Previous summary (for deltas)
        prev_summary = st.session_state.get("prev_metrics_summary_sidebar")

        # Total executions (with delta vs previous)
        total_exec = summary.get("total_executions", 0)
        prev_total_exec = prev_summary.get("total_executions", 0) if prev_summary else None
        total_delta = None
        if prev_total_exec is not None and total_exec != prev_total_exec:
            total_delta = total_exec - prev_total_exec
        st.metric("Total Executions", total_exec, delta=total_delta)

        # Success rate (with delta vs previous)
        if total_exec > 0:
            curr_sr = float(summary.get("success_rate", 0) or 0.0)
            prev_sr = float(prev_summary.get("success_rate", 0) or 0.0) if prev_summary else None
            sr_delta = None
            if prev_sr is not None:
                sr_delta = f"{curr_sr - prev_sr:+.1f} pts"
            st.metric("Success Rate", f"{curr_sr:.1f}%", delta=sr_delta)

        # Persist for next render so we can show "previous" metrics
        st.session_state["prev_metrics_summary_sidebar"] = summary
    except (requests.exceptions.RequestException, KeyError):
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
                            "use_v3": use_v3,
                            "force_run": force_run,
                        },
                        timeout=EXECUTE_TIMEOUT
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
                        st.success(f"✅ Test Passed! 100% success ({steps_ok}/{steps_total} steps) - Headed mode execution completed.")
                    elif result["success"] and steps_total == 0:
                        st.info("No steps to run.")
                    else:
                        err_msg = result.get("error") or "One or more steps failed."
                        st.error(f"❌ Test Failed: {err_msg}")
                        st.caption(f"Steps completed: {steps_ok}/{steps_total}")
                    
                    # ---------- Test script (JavaScript or TypeScript per user selection) ----------
                    st.divider()
                    st.subheader("📝 Test script used for execution")
                    script_lang = result.get("script_language") or script_language or "typescript"
                    file_ext = result.get("file_extension") or (".ts" if script_lang == "typescript" else ".js")
                    test_file = f"test{file_ext}"
                    # Show executed-only script when we have it (partial run); always show script section
                    has_partial = steps_total > 0 and result.get("generated_script_executed")

                    if has_partial:
                        # Partial run (e.g. 6/24): show script for executed steps first, then full plan
                        st.caption(f"Language: **{script_lang.upper()}** (from your selection in the sidebar)")
                        st.markdown(f"**Script for steps that executed successfully ({steps_ok} steps)**")
                        st.download_button(
                            label=f"📥 Download executed-only {file_ext}",
                            data=result["generated_script_executed"],
                            file_name=f"test_executed_only{file_ext}",
                            mime="text/plain",
                            key="download_script_executed",
                        )
                        st.code(result["generated_script_executed"], language=script_lang)
                        with st.expander(f"📄 Full planned script ({steps_total} steps)"):
                            st.code(result.get("generated_script") or "", language=script_lang)
                            st.download_button(
                                label=f"📥 Download full script",
                                data=result.get("generated_script") or "",
                                file_name=test_file,
                                mime="text/plain",
                                key="download_script_full",
                            )
                        with st.expander("ℹ️ How to run this script"):
                            st.markdown(f"""
1. **Install Playwright** (if needed):
```bash
npm init -y
npm install -D @playwright/test
npx playwright install
```

2. **Executed-only script** (reproduces the {steps_ok} steps that ran): save as `test_executed_only{file_ext}` and run:
```bash
npx playwright test test_executed_only{file_ext}
```
3. **Full script** (all {steps_total} steps): save as `{test_file}` to run or edit from step {steps_ok + 1}.
Headed: add `--headed` · Debug: `--ui`
                            """)
                    elif result.get("generated_script"):
                        st.caption(f"Language: **{script_lang.upper()}** (from your selection in the sidebar)")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**File:** `{test_file}`")
                        with col2:
                            st.download_button(
                                label=f"📥 Download {file_ext}",
                                data=result["generated_script"],
                                file_name=test_file,
                                mime="text/plain",
                                key="download_script",
                            )
                        st.code(result["generated_script"], language=script_lang)
                        with st.expander("ℹ️ How to run this script"):
                            st.markdown(f"""
1. **Install Playwright** (if needed):
```bash
npm init -y
npm install -D @playwright/test
npx playwright install
```

2. **Save** as `{test_file}` and run:
```bash
npx playwright test {test_file}
```
Headed: `npx playwright test {test_file} --headed` · Debug: `--ui`
                            """)
                    else:
                        st.info("No script was generated for this run (e.g. no steps could be planned). Try again or check backend logs.")
                    
                except requests.exceptions.Timeout:
                    st.error(f"⏱️ Execution timed out (>{EXECUTE_TIMEOUT // 60} minutes). Increase EXECUTE_TIMEOUT in streamlit_app.py if needed.")
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

        # Previous summary (for deltas)
        prev_summary = st.session_state.get("prev_metrics_summary_tab")
        
        # Display summary
        col1, col2, col3, col4 = st.columns(4)

        total_exec = summary.get("total_executions", 0)
        prev_total_exec = prev_summary.get("total_executions", 0) if prev_summary else None
        total_delta = None
        if prev_total_exec is not None and total_exec != prev_total_exec:
            total_delta = total_exec - prev_total_exec

        successful = summary.get("successful", 0)
        prev_successful = prev_summary.get("successful", 0) if prev_summary else None
        successful_delta = None
        if prev_successful is not None and successful != prev_successful:
            successful_delta = successful - prev_successful

        failed = summary.get("failed", 0)
        prev_failed = prev_summary.get("failed", 0) if prev_summary else None
        failed_delta = None
        if prev_failed is not None and failed != prev_failed:
            failed_delta = failed - prev_failed

        curr_sr = float(summary.get("success_rate", 0) or 0.0)
        prev_sr = float(prev_summary.get("success_rate", 0) or 0.0) if prev_summary else None
        sr_delta = None
        if prev_sr is not None:
            sr_delta = f"{curr_sr - prev_sr:+.1f} pts"
        
        with col1:
            st.metric("Total Executions", total_exec, delta=total_delta)
        
        with col2:
            st.metric("Successful", successful, delta=successful_delta)
        
        with col3:
            st.metric("Failed", failed, delta=failed_delta)
        
        with col4:
            st.metric("Success Rate", f"{curr_sr:.1f}%", delta=sr_delta)
        
        col1, col2 = st.columns(2)

        avg_dur = float(summary.get("average_duration", 0.0) or 0.0)
        prev_avg_dur = float(prev_summary.get("average_duration", 0.0) or 0.0) if prev_summary else None
        avg_dur_delta = None
        if prev_avg_dur is not None:
            avg_dur_delta = f"{avg_dur - prev_avg_dur:+.2f}s"

        total_dur = float(summary.get("total_duration", 0.0) or 0.0)
        prev_total_dur = float(prev_summary.get("total_duration", 0.0) or 0.0) if prev_summary else None
        total_dur_delta = None
        if prev_total_dur is not None:
            total_dur_delta = f"{total_dur - prev_total_dur:+.2f}s"
        
        with col1:
            st.metric("Average Duration", f"{avg_dur:.2f}s", delta=avg_dur_delta)
        
        with col2:
            st.metric("Total Duration", f"{total_dur:.2f}s", delta=total_dur_delta)

        # Persist for next render so we can show "previous" metrics
        st.session_state["prev_metrics_summary_tab"] = summary
        
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
