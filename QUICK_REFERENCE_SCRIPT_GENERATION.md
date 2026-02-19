# 🚀 Quick Reference: Script Generation Feature

## 🎯 What It Does
Converts your natural language tests into **executable Playwright scripts** in JavaScript or TypeScript.

---

## ⚡ Quick Start (3 Steps)

### 1. Select Language
**UI Sidebar:**
```
Script Language: [TypeScript ▼]
```
Choose: `TypeScript` or `JavaScript`

### 2. Run Test
```
Navigate to https://example.com
Click Login
Type test@test.com in Email
Click Submit
```
Click: `▶️ Execute`

### 3. Download Script
After execution completes:
- Scroll to "📝 Generated Playwright Script"
- Click `📥 Download .ts` (or `.js`)
- Save file

**Done!** You now have a runnable Playwright test.

---

## 📋 Supported Actions

| Natural Language | Generated Code |
|-----------------|----------------|
| `Navigate to URL` | `await page.goto('URL'); await page.waitForLoadState('networkidle');` |
| `Click Button` | `await page.getByText('Button').click({ timeout: 5000 });` (with 4 fallback strategies) |
| `Type text in Field` | `await page.getByLabel(/Field/i).fill('text');` (with 3 fallback strategies) |
| `Wait for Element` | `await page.waitForTimeout(2000);` |
| `Verify Text` | `await expect(page.getByText(/Text/i)).toBeVisible();` |
| `Select Option` | `await page.getByLabel(/Field/i).selectOption('value');` |

---

## 🎨 UI Features

### Language Selector
**Location:** Sidebar  
**Options:** TypeScript (default), JavaScript  
**Changes:** Updates generated script language

### Script Display
**Location:** Results section (after execution)  
**Shows:**
- ✅ Syntax-highlighted code
- ✅ Language indicator (TS/JS)
- ✅ File name (test.ts or test.js)
- ✅ Download button
- ✅ Run instructions (expandable)

---

## 💻 Running Generated Scripts

### First Time Setup
```bash
# Install dependencies
npm init -y
npm install -D @playwright/test
npx playwright install
```

### Run Test
```bash
# Basic run
npx playwright test test.ts

# With browser visible
npx playwright test test.ts --headed

# Debug mode
npx playwright test test.ts --ui

# Specific browser
npx playwright test test.ts --project=chromium
```

### View Results
```bash
npx playwright show-report
```

---

## 🔄 Workflow Options

### Option 1: Quick Test
```
Write in UI → Execute → Done
(Use platform for one-off tests)
```

### Option 2: Export & Customize
```
Write in UI → Execute → Download → Customize → Run independently
(Get starting point, then customize)
```

### Option 3: CI/CD Pipeline
```
Create in UI → Download → Add to repo → Run in GitHub Actions
(Integrate with existing pipeline)
```

### Option 4: Learn Playwright
```
Write action → See generated code → Learn selector strategies
(Educational tool)
```

---

## 📊 Generated Code Features

### ✅ Robust Selectors
```typescript
// Multiple fallback strategies
try {
  await page.getByText('Login', { exact: true }).click();
} catch {
  await page.getByRole('button', { name: /Login/i }).click();
}
```

### ✅ Proper Waits
```typescript
await page.goto(url);
await page.waitForLoadState('networkidle');
```

### ✅ Error Handling
```typescript
try {
  // Primary approach
} catch (e1) {
  try {
    // Fallback 1
  } catch (e2) {
    // Fallback 2
  }
}
```

### ✅ Type Safety (TypeScript)
```typescript
async ({ page }: Page) => {
  // Full type safety
}
```

### ✅ Comments
```typescript
// Step 1: NAVIGATE
// Click element: 'Login'
```

---

## 🎯 Use Cases

| Scenario | How It Helps |
|----------|--------------|
| **CI/CD Integration** | Download script → Add to pipeline |
| **Learning Playwright** | See how NL translates to code |
| **Quick Prototyping** | Test in UI, export to code |
| **Code Review** | Generated code can be reviewed |
| **Version Control** | Scripts can be committed to Git |
| **Team Collaboration** | Share executable test files |
| **No Lock-in** | Own the code, run anywhere |

---

## 📁 File Structure

### What You Download
```
test.ts (or test.js)
├── Imports
├── Test definition
├── Test configuration
├── Step 1 code
├── Step 2 code
├── ...
└── Step N code
```

### Complete Project (Optional)
```
project/
├── tests/
│   └── test.ts          ← Downloaded script
├── package.json         ← npm dependencies
├── playwright.config.ts ← Test configuration
└── node_modules/        ← After npm install
```

---

## 🔧 Customization Examples

### Add Page Object Pattern
```typescript
// Generated code
await page.getByText('Login').click();

// Customize with page object
class LoginPage {
  async clickLogin() {
    await page.getByText('Login').click();
  }
}
```

### Add Better Selectors
```typescript
// Generated (text-based)
await page.getByText('Submit').click();

// Customize (data attribute)
await page.locator('[data-testid="submit-btn"]').click();
```

### Add Custom Assertions
```typescript
// Generated
await expect(page.getByText('Success')).toBeVisible();

// Customize
await expect(page.locator('.success-msg')).toHaveText('Success!');
await expect(page).toHaveURL(/.*dashboard/);
```

---

## 💡 Pro Tips

### Tip 1: Start Simple
Write minimal test → Execute → Get script → Build from there

### Tip 2: Use as Template
Generated code = starting point, not final version

### Tip 3: Combine Approaches
- Quick changes: Use UI
- Complex logic: Edit generated script

### Tip 4: Build Library
Generate multiple tests → Build test suite

### Tip 5: Learn Patterns
Study generated code to learn Playwright best practices

---

## 📞 Quick Help

### Generated script won't run?
```bash
# Make sure Playwright is installed
npx playwright install

# Check dependencies
npm install -D @playwright/test
```

### Need to change language?
- Sidebar → Script Language → Select JS or TS
- Re-execute test
- New script generated in chosen language

### Script needs customization?
1. Download script
2. Open in VS Code
3. Edit selectors/logic as needed
4. Run: `npx playwright test`

### Want config files?
```bash
# Run the demo
python examples/script_generation_demo.py

# Generates:
# - demo_test.ts
# - demo_test.js
# - demo_package.json
# - demo_playwright.config.ts
```

---

## 📚 Full Documentation

- **Complete Guide:** [docs/SCRIPT_GENERATION.md](../docs/SCRIPT_GENERATION.md)
- **Visual Guide:** [docs/SCRIPT_GENERATION_VISUAL_GUIDE.md](../docs/SCRIPT_GENERATION_VISUAL_GUIDE.md)
- **Feature Update:** [FEATURE_UPDATE_SCRIPT_GENERATION.md](../FEATURE_UPDATE_SCRIPT_GENERATION.md)
- **Main README:** [README.md](../README.md)

---

## 🎉 Summary

**In 3 steps:**
1. Select language (TS/JS)
2. Execute test
3. Download script

**You get:**
✅ Production-ready code  
✅ Robust selectors  
✅ Error handling  
✅ Ready to customize  
✅ CI/CD ready  

**No lock-in. Own your code. Run anywhere.** 🚀
