# Getting Started Guide

## 🎯 Your First Test in 5 Minutes

### Step 1: Setup Environment

```powershell
# Navigate to project
cd "c:\Users\gparavasthu\Workspace\Gen AI QE\UI_automation"

# Activate virtual environment
& "C:\Users\gparavasthu\Workspace\Truvelocity\code_export\agentic-sdlc-platform\venv\Scripts\Activate.ps1"

# Run setup
python setup.py
```

### Step 2: Configure API Key

1. Copy `.env.example` to `.env`
2. Open `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

### Step 3: Start the Platform

**Terminal 1 - API Server:**
```powershell
python -m app.main
```

Wait for: `INFO: Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - UI Dashboard:**
```powershell
streamlit run ui/streamlit_app.py
```

### Step 4: Run Your First Test

1. Open browser: http://localhost:8501
2. Select "LG E-commerce" example
3. Click "▶️ Execute"
4. Watch it work! 🎉

## 📚 Next Steps

### Write Custom Tests

```
Navigate to YOUR_URL
Click BUTTON_NAME
Type YOUR_TEXT in FIELD_NAME
```

### Try Different Examples

1. **Simple Login**
   ```
   Go to https://example.com
   Click Login
   Type test@test.com in Email
   Type password in Password
   Click Submit
   ```

2. **E-commerce**
   ```
   Navigate to https://example.com
   Click Products
   Click First Product
   Click Add to Cart
   Click Checkout
   ```

## 🔍 Understanding Results

### Success Indicators
- ✅ All steps completed
- State transitions validated
- No errors in execution

### Failure Analysis
- Review step-by-step results
- Check recovery suggestions
- Examine element scoring

## ⚙️ Configuration Options

### In UI Sidebar:
- **Headless Mode**: Run browser invisibly
- **Max Recovery Attempts**: How many times to retry failed steps

### In `.env` file:
- `SCORE_THRESHOLD`: Minimum element match score (0.0-1.0)
- `MAX_RETRIES`: Maximum retry attempts per action
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING)

## 🐛 Troubleshooting

### API won't start
- Check if port 8000 is available
- Verify virtual environment is activated
- Check `.env` file exists with API key

### UI won't connect
- Ensure API is running first
- Check browser console for errors
- Verify API_BASE_URL in UI code

### Tests failing
1. Check logs in `logs/automation.log`
2. Try with `headless=False` to see browser
3. Review element scoring in results
4. Adjust `SCORE_THRESHOLD` if needed

## 📊 Monitoring Execution

### Real-time Logs
Watch Terminal 1 for detailed execution logs

### Metrics Dashboard
UI → Metrics tab shows:
- Success rates
- Execution times
- Recent runs

### Debug Mode
Set `LOG_LEVEL=DEBUG` in `.env` for detailed output

## 🚀 Production Tips

1. **Start with headless=False** to debug
2. **Use specific element text** in test cases
3. **Check metrics** after each run
4. **Save successful patterns** by running repeatedly
5. **Review recovery suggestions** on failures

## 🎓 Best Practices

### Writing Test Cases
✅ Use specific, unique text for elements  
✅ Include wait steps for dynamic content  
✅ Keep steps simple and atomic  
✅ Test incrementally  

❌ Don't use vague element descriptions  
❌ Don't skip validation steps  
❌ Don't chain too many actions without waits  

## 🤝 Getting Help

- Check logs: `logs/automation.log`
- Review README.md for architecture
- Examine example test cases in `examples/`
- Check metrics for patterns

---

**You're ready to build reliable UI automation! 🎉**
