# 📝 Script Generation Feature

## Overview

The UI Automation Platform now generates **executable Playwright scripts** in both **JavaScript** and **TypeScript** from your natural language test cases!

## ✨ Features

### 1. **Language Selection**
- Choose between JavaScript or TypeScript
- Get production-ready Playwright test code
- Includes proper error handling and retry logic

### 2. **Smart Locator Strategies**
The generated scripts use multiple fallback strategies:
```typescript
// Strategy 1: Exact text match
await page.getByText('Login', { exact: true }).click();

// Strategy 2: Partial match
await page.getByText('Login').first().click();

// Strategy 3: Role-based
await page.getByRole('button', { name: /Login/i }).click();

// Strategy 4: Label-based
await page.getByLabel(/Login/i).click();
```

### 3. **Comprehensive Actions**
Supports all automation actions:
- ✅ Navigation with load state waiting
- ✅ Click with multiple selector strategies
- ✅ Type with intelligent field detection
- ✅ Verification with assertions
- ✅ Explicit waits
- ✅ Dropdown selection

### 4. **Ready to Run**
Generated scripts include:
- ✅ Proper imports
- ✅ Test structure
- ✅ Timeout configuration
- ✅ Error handling
- ✅ Comments explaining each step

## 🚀 Usage

### Via UI (Streamlit)

1. **Open the UI**: http://localhost:8501

2. **Select Script Language**:
   - In the sidebar, choose "JavaScript" or "TypeScript"

3. **Enter Test Case**:
   ```
   Navigate to https://example.com
   Click Login
   Type user@test.com in Email
   Type password123 in Password
   Click Submit
   Verify Dashboard
   ```

4. **Execute Test**:
   - Click "▶️ Execute"
   - Platform runs the test AND generates the script

5. **View Generated Script**:
   - Script appears below execution results
   - Syntax highlighted
   - Download button provided

6. **Download and Run**:
   - Click "📥 Download .ts" (or .js)
   - Save to your project
   - Run with Playwright

### Via API

```python
import requests

response = requests.post(
    "http://localhost:8000/execute",
    json={
        "instruction": """
        Navigate to https://example.com
        Click Login
        Type user@test.com in Email
        Click Submit
        """,
        "headless": True,
        "script_language": "typescript"  # or "javascript"
    }
)

result = response.json()

# Get generated script
script = result["generated_script"]
language = result["script_language"]
extension = result["file_extension"]

# Save to file
with open(f"test{extension}", "w") as f:
    f.write(script)
```

## 📊 Example Output

### TypeScript Example
```typescript
import { test, expect, Page } from '@playwright/test';

test('example_login_test', async ({ page }: Page) => {
  test.setTimeout(60000); // 60 second timeout

  // Step 1: NAVIGATE
  await page.goto('https://example.com');
  await page.waitForLoadState('networkidle');

  // Step 2: CLICK
  // Click element: 'Login'
  try {
    await page.getByText('Login', { exact: true }).click({ timeout: 5000 });
  } catch (e1) {
    try {
      await page.getByText('Login').first().click({ timeout: 5000 });
    } catch (e2) {
      try {
        await page.getByRole('button', { name: /Login/i }).click({ timeout: 5000 });
      } catch (e3) {
        await page.getByLabel(/Login/i).click({ timeout: 5000 });
      }
    }
  }

  // Step 3: TYPE
  // Type into: 'Email'
  try {
    await page.getByLabel(/Email/i).fill('user@test.com');
  } catch (e1) {
    try {
      await page.getByPlaceholder(/Email/i).fill('user@test.com');
    } catch (e2) {
      await page.getByRole('textbox', { name: /Email/i }).fill('user@test.com');
    }
  }

  // Step 4: CLICK
  await page.getByText('Submit', { exact: true }).click({ timeout: 5000 });

  // Step 5: VERIFY
  // Verify: 'Dashboard' contains 'Dashboard'
  try {
    await expect(page.getByText(/Dashboard/i)).toBeVisible({ timeout: 5000 });
  } catch (e) {
    await expect(page.locator('body')).toContainText(/Dashboard/i);
  }
});
```

### JavaScript Example
```javascript
const { test, expect } = require('@playwright/test');

test('example_login_test', async ({ page }) => {
  test.setTimeout(60000); // 60 second timeout

  // Step 1: NAVIGATE
  await page.goto('https://example.com');
  await page.waitForLoadState('networkidle');

  // Step 2: CLICK
  try {
    await page.getByText('Login', { exact: true }).click({ timeout: 5000 });
  } catch (e1) {
    await page.getByText('Login').first().click({ timeout: 5000 });
  }

  // ... rest of the test
});
```

## 🎯 Benefits

### 1. **Export Your Tests**
- Run automation through the platform
- Get the equivalent Playwright code
- Integrate into CI/CD pipelines

### 2. **Learn Playwright**
- See how natural language translates to code
- Understand selector strategies
- Learn best practices

### 3. **Customize Further**
- Generated code is a starting point
- Modify selectors as needed
- Add custom logic
- Integrate with existing test suites

### 4. **Version Control**
- Store scripts in Git
- Review changes
- Collaborate with team

### 5. **CI/CD Integration**
- Run in GitHub Actions
- Integrate with Jenkins
- Deploy to any CI platform

## 🛠️ Running Generated Scripts

### Prerequisites
```bash
npm init -y
npm install -D @playwright/test
npx playwright install
```

### Run Tests
```bash
# Run all tests
npx playwright test

# Run specific test
npx playwright test test.ts

# Run with UI mode (debugging)
npx playwright test --ui

# Run headed (see browser)
npx playwright test --headed

# Run and keep browser open on failure
npx playwright test --headed --debug
```

### View Report
```bash
npx playwright show-report
```

## 📁 Generated File Structure

When you download a script, you'll also want these files:

### package.json
```json
{
  "name": "ui-automation-tests",
  "version": "1.0.0",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}
```

### playwright.config.ts
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

## 🎓 Try the Demo

Run the script generation demo:

```powershell
python examples/script_generation_demo.py
```

This will:
1. Generate a TypeScript test
2. Generate a JavaScript test
3. Generate package.json
4. Generate playwright.config
5. Save all files with demo_ prefix

## 🔄 Workflow

```
Natural Language → AI Planning → Deterministic Execution → Script Generation
     ↓                  ↓                   ↓                      ↓
  "Click Login"    Parse Intent      Execute Action        Generate Code
```

## 💡 Best Practices

### 1. **Use Generated Scripts as Starting Points**
```typescript
// Generated script provides structure
await page.getByText('Login').click();

// Customize with specific selectors
await page.locator('[data-testid="login-btn"]').click();
```

### 2. **Combine with Page Objects**
```typescript
class LoginPage {
  async login(page: Page, email: string, password: string) {
    // Use generated code in page objects
    await page.getByLabel(/Email/i).fill(email);
    await page.getByLabel(/Password/i).fill(password);
    await page.getByRole('button', { name: /Login/i }).click();
  }
}
```

### 3. **Add Custom Validations**
```typescript
// Generated verification
await expect(page.getByText(/Dashboard/i)).toBeVisible();

// Add more specific checks
await expect(page.locator('.user-name')).toHaveText('John Doe');
await expect(page).toHaveURL(/.*dashboard/);
```

## 🎉 Summary

The Script Generation feature bridges the gap between:
- **No-code automation** (UI execution)
- **Full-code testing** (Playwright scripts)

You get the best of both worlds:
- ✅ Quick test creation via natural language
- ✅ Professional-grade test code output
- ✅ Flexibility to customize
- ✅ CI/CD integration ready

**Start automating, get the code, own your tests!** 🚀
