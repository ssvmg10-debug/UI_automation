# 🔧 Troubleshooting Guide

## Common Issues & Solutions

### 🚨 Installation Issues

#### Problem: `pip install` fails
**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solution:**
```powershell
# Ensure Python 3.9+ is installed
python --version

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
python -m pip install -r requirements.txt
```

---

#### Problem: Playwright installation fails
**Symptoms:**
```
ERROR: Playwright browsers not installed
```

**Solution:**
```powershell
# Install Playwright browsers
python -m playwright install chromium

# If permission issues
python -m playwright install chromium --with-deps
```

---

### 🔌 Connection Issues

#### Problem: API won't start
**Symptoms:**
```
ERROR: Address already in use (port 8000)
```

**Solution 1: Change port**
```env
# In .env file
API_PORT=8001
```

**Solution 2: Kill existing process**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

---

#### Problem: UI can't connect to API
**Symptoms:**
- UI shows "API Unreachable"
- Connection refused errors

**Solution:**
```powershell
# 1. Verify API is running
curl http://localhost:8000/health

# 2. Check API logs
# Look in Terminal 1 for errors

# 3. Verify environment
# Make sure .env exists with OPENAI_API_KEY

# 4. Check firewall
# Ensure localhost connections allowed
```

---

### 🤖 Execution Issues

#### Problem: Tests fail with "No elements found"
**Symptoms:**
```
ERROR: No clickable elements found matching filters
```

**Solutions:**

**1. Check if page loaded**
```
# Add wait before action
Navigate to URL
Wait for 3 seconds
Click Element
```

**2. Verify element text**
```
# Use exact text from page
# Wrong: Click "login"
# Right:  Click "Log In"
```

**3. Lower threshold**
```env
# In .env
SCORE_THRESHOLD=0.50
```

**4. Try with visible browser**
```python
# In UI sidebar
Headless Mode: [unchecked]
```

---

#### Problem: Tests fail with "No valid transition"
**Symptoms:**
```
ERROR: No valid transition found
```

**Solutions:**

**1. Check if click actually worked**
- Run with `headless=False`
- Verify element is clickable

**2. Increase wait time**
```env
# In .env
RETRY_DELAY=2.0
```

**3. Add explicit wait**
```
Click Button
Wait for Next Page
```

---

#### Problem: "OpenAI API error"
**Symptoms:**
```
ERROR: Invalid API key
ERROR: Rate limit exceeded
```

**Solutions:**

**1. Verify API key**
```env
# Check .env file
OPENAI_API_KEY=sk-...
# Must start with "sk-"
```

**2. Check API limits**
- Go to OpenAI dashboard
- Verify billing is active
- Check rate limits

**3. Use alternative model**
```python
# In planner_agent.py
self.model = "gpt-3.5-turbo"
```

---

### 🎨 UI Issues

#### Problem: Streamlit won't start
**Symptoms:**
```
ERROR: ModuleNotFoundError: No module named 'streamlit'
```

**Solution:**
```powershell
# Reinstall streamlit
pip install streamlit

# Or reinstall all
pip install -r requirements.txt
```

---

#### Problem: UI shows blank page
**Symptoms:**
- Page loads but shows nothing
- Console errors

**Solution:**
```powershell
# Clear Streamlit cache
streamlit cache clear

# Restart Streamlit
# Press Ctrl+C, then restart
streamlit run ui/streamlit_app.py
```

---

### 🐛 Browser Issues

#### Problem: Browser crashes
**Symptoms:**
```
ERROR: Browser closed unexpectedly
ERROR: Target closed
```

**Solutions:**

**1. Increase timeout**
```env
# In .env
BROWSER_TIMEOUT=60000
```

**2. Disable headless temporarily**
```env
HEADLESS=false
```

**3. Update Playwright**
```powershell
pip install --upgrade playwright
python -m playwright install chromium
```

---

#### Problem: Screenshots not saving
**Symptoms:**
- No screenshots in directory
- Permission errors

**Solution:**
```powershell
# Create screenshots directory
mkdir screenshots

# Check permissions
icacls screenshots
```

---

### 📝 Logging Issues

#### Problem: No logs generated
**Symptoms:**
- `logs/` directory empty
- Can't find execution trace

**Solution:**
```powershell
# Create logs directory
mkdir logs

# Set log level
# In .env
LOG_LEVEL=DEBUG
LOG_FILE=logs/automation.log
```

---

#### Problem: Too many logs
**Symptoms:**
- Log file grows very large
- Performance degradation

**Solution:**
```env
# In .env
LOG_LEVEL=INFO

# Or use WARNING for production
LOG_LEVEL=WARNING
```

---

### 💾 Memory Issues

#### Problem: High memory usage
**Symptoms:**
- System slows down
- Out of memory errors

**Solutions:**

**1. Clear history**
```env
# In .env
MAX_STATE_HISTORY=50
```

**2. Restart between runs**
```python
# Close browser after each test
await browser_manager.close()
```

**3. Use headless mode**
```env
HEADLESS=true
```

---

### 🔍 Debugging Tips

#### Enable Debug Logging
```env
# In .env
LOG_LEVEL=DEBUG
```

#### Run Single Step
```python
# Test one action at a time
Navigate to URL
# Stop here, verify it worked
# Then add next step
```

#### Check Element Scoring
```python
# Look in logs for:
"Element 'X' scored 0.XX"
# If score < threshold, action won't execute
```

#### View State Transitions
```python
# Check logs for:
"Captured state: PageState(url=..., title=...)"
"Transition validation: URL=True, Title=True..."
```

---

## 📊 Performance Optimization

### Slow Execution

**Problem:** Tests take too long

**Solutions:**

1. **Reduce wait times**
```env
RETRY_DELAY=0.5
```

2. **Use headless mode**
```env
HEADLESS=true
```

3. **Skip unnecessary steps**
```
# Don't wait if not needed
# Remove: Wait for Element
```

4. **Increase threshold**
```env
# Accept lower match scores
SCORE_THRESHOLD=0.60
```

---

### High API Costs

**Problem:** Too many OpenAI API calls

**Solutions:**

1. **Cache plans**
- Run same test multiple times
- Plan is only generated once

2. **Reduce recovery attempts**
```env
MAX_RECOVERY_ATTEMPTS=1
```

3. **Use pattern memory**
- System learns and needs AI less over time

---

## 🆘 Getting Help

### Where to Look

1. **Logs**
   ```
   logs/automation.log
   ```

2. **API Logs**
   - Check Terminal 1 (API server)

3. **UI Logs**
   - Check Terminal 2 (Streamlit)

4. **Browser Console**
   - If running non-headless

### What to Check

- [ ] Virtual environment activated?
- [ ] `.env` file exists?
- [ ] `OPENAI_API_KEY` set?
- [ ] Dependencies installed?
- [ ] Playwright browsers installed?
- [ ] API server running?
- [ ] Port 8000/8501 available?

### Diagnostic Commands

```powershell
# Check Python version
python --version

# Check pip packages
pip list

# Check Playwright
python -m playwright --version

# Test API
curl http://localhost:8000/health

# Check ports
netstat -ano | findstr :8000
netstat -ano | findstr :8501
```

---

## 🔄 Reset Everything

If all else fails:

```powershell
# Stop all services
# Press Ctrl+C in both terminals

# Clear caches
streamlit cache clear

# Delete logs
Remove-Item -Recurse logs/*

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Reinstall Playwright
python -m playwright install chromium

# Restart
python setup.py
.\start.ps1
```

---

## 📞 Still Stuck?

1. **Check Documentation**
   - README.md
   - ARCHITECTURE.md
   - GETTING_STARTED.md

2. **Review Examples**
   - examples/test_cases.py
   - examples/quick_start.py

3. **Check Metrics**
   - UI → Metrics tab
   - Look for patterns in failures

4. **Enable Debug Mode**
   ```env
   LOG_LEVEL=DEBUG
   ```

5. **Run Simple Test**
   ```
   Navigate to https://example.com
   ```
   If this fails, it's a setup issue.

---

**Remember: Most issues are configuration or environment related!**

✅ Double-check `.env` file  
✅ Ensure API key is valid  
✅ Verify virtual environment  
✅ Check logs for errors  
✅ Try simple test first
