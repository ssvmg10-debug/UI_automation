# 🎬 Script Generation Feature - Visual Guide

## Before & After Comparison

### ❌ Before (Traditional Approach)
```
1. Write test in natural language
2. Run test through platform
3. Test executes but...
   - No reusable code
   - Can't run outside platform
   - Can't customize
   - Can't version control easily
```

### ✅ After (With Script Generation)
```
1. Write test in natural language
2. Select JavaScript or TypeScript
3. Run test through platform
4. Get executable Playwright script!
   ✅ Reusable code
   ✅ Run anywhere
   ✅ Customize as needed
   ✅ Version control friendly
   ✅ CI/CD ready
```

---

## 📸 UI Walkthrough

### Step 1: Open UI Dashboard
```
http://localhost:8501
```

### Step 2: Configure Script Language

**In Sidebar:**
```
┌─────────────────────────┐
│ ⚙️ Configuration        │
├─────────────────────────┤
│ ☑ Headless Mode         │
│                         │
│ Max Recovery Attempts   │
│ ├───┬───┬───┬───┬──┤   │
│     2                   │
│                         │
│ Script Language         │
│ ┌─────────────────────┐ │
│ │ TypeScript      ▼  │ │  ← SELECT HERE
│ └─────────────────────┘ │
│   - TypeScript          │
│   - JavaScript          │
│                         │
└─────────────────────────┘
```

### Step 3: Enter Test Case

**Main Panel:**
```
┌──────────────────────────────────────────┐
│ Test Case (Natural Language)             │
├──────────────────────────────────────────┤
│                                          │
│ Navigate to https://www.lg.com/in       │
│ Click Air Solutions                      │
│ Click Split AC                           │
│ Wait for 2 seconds                       │
│ Click Buy Now                            │
│                                          │
└──────────────────────────────────────────┘

       [▶️ Execute]
```

### Step 4: Execute & View Results

**After Execution:**
```
✅ Test Passed! (5/5 steps)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Generated Playwright Script

Language: TYPESCRIPT
File: test.ts                     [📥 Download .ts]

┌──────────────────────────────────────────┐
│ import { test, expect, Page } from      │
│   '@playwright/test';                    │
│                                          │
│ test('Navigate_to_https_www_lg_com',    │
│   async ({ page }: Page) => {           │
│   test.setTimeout(60000);                │
│                                          │
│   // Step 1: NAVIGATE                   │
│   await page.goto(                       │
│     'https://www.lg.com/in'              │
│   );                                     │
│   await page.waitForLoadState(           │
│     'networkidle'                        │
│   );                                     │
│                                          │
│   // Step 2: CLICK                       │
│   // Click element: 'Air Solutions'     │
│   try {                                  │
│     await page                           │
│       .getByText('Air Solutions',        │
│         { exact: true })                 │
│       .click({ timeout: 5000 });         │
│   } catch (e1) {                         │
│     ...                                  │
│   }                                      │
│   ...                                    │
│ });                                      │
└──────────────────────────────────────────┘

ℹ️ How to run this script  [Click to expand]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Execution Details

 Steps Executed    Duration    Status
      5             12.3s      Success
```

---

## 🎯 Use Cases

### 1. **Quick Prototyping**
```
1. Draft test in UI (natural language)
2. Execute to verify it works
3. Download script
4. Customize in code editor
```

### 2. **CI/CD Integration**
```
1. Create tests via UI
2. Export as TypeScript
3. Add to test suite
4. Run in GitHub Actions/Jenkins
```

### 3. **Learning Playwright**
```
1. Write what you want to do
2. See how it translates to code
3. Learn selector strategies
4. Understand best practices
```

### 4. **Hybrid Approach**
```
Day 1: Use UI for quick tests
Day 2: Export successful tests
Day 3: Build suite with exported code
Day 4: Mix UI + code tests
```

---

## 💻 Generated Code Quality

### ✅ What You Get

**1. Production-Ready Structure**
```typescript
import { test, expect, Page } from '@playwright/test';

test('test_name', async ({ page }: Page) => {
  test.setTimeout(60000);
  // Your test code
});
```

**2. Robust Selectors**
```typescript
// Multiple fallback strategies
try {
  await page.getByText('Login', { exact: true }).click();
} catch (e1) {
  try {
    await page.getByText('Login').first().click();
  } catch (e2) {
    try {
      await page.getByRole('button', { name: /Login/i }).click();
    } catch (e3) {
      await page.getByLabel(/Login/i).click();
    }
  }
}
```

**3. Proper Waits**
```typescript
await page.goto('https://example.com');
await page.waitForLoadState('networkidle');
```

**4. Type Safety** (TypeScript)
```typescript
async ({ page }: Page) => {
  // Full type safety
}
```

**5. Error Handling**
```typescript
try {
  await page.getByText('Button').click({ timeout: 5000 });
} catch (e) {
  // Graceful fallback
}
```

---

## 📦 Complete Package

When you use the platform, you get:

### File: `test.ts` (or `test.js`)
```typescript
// Your complete test
import { test, expect, Page } from '@playwright/test';
// ... full test code
```

### Instructions to Run
```bash
# 1. Install dependencies
npm init -y
npm install -D @playwright/test
npx playwright install

# 2. Run the test
npx playwright test test.ts

# 3. View results
npx playwright show-report
```

### Optional: Config Files

**package.json** *(can be generated via demo)*
```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
```

**playwright.config.ts** *(can be generated via demo)*
```typescript
export default defineConfig({
  testDir: './tests',
  use: {
    trace: 'on-first-retry',
  },
});
```

---

## 🔄 Complete Workflow Example

### Scenario: E-commerce Product Purchase

**1. Write in UI:**
```
Navigate to https://store.example.com
Click Login
Type user@test.com in Email
Type password123 in Password
Click Sign In button
Wait for Dashboard
Type "laptop" in Search
Click Search button
Click first product
Click Add to Cart
Verify Cart icon
```

**2. Select TypeScript** *(in sidebar)*

**3. Click Execute** *(runs the test)*

**4. Test Executes:**
```
✅ Step 1: Navigate ✓
✅ Step 2: Click Login ✓
✅ Step 3: Type in Email ✓
✅ Step 4: Type in Password ✓
✅ Step 5: Click Sign In ✓
...
```

**5. View Generated Script:**
```typescript
// 150+ lines of production-ready code
import { test, expect, Page } from '@playwright/test';

test('ecommerce_purchase_flow', async ({ page }: Page) => {
  // Complete implementation
});
```

**6. Download & Use:**
```bash
# Click "📥 Download .ts"
# Save as: purchase-flow.spec.ts

# Run it
npx playwright test purchase-flow.spec.ts
```

**7. Customize (Optional):**
```typescript
// Add assertions
await expect(page.locator('.cart-count')).toHaveText('1');

// Add data-driven testing
const products = ['laptop', 'phone', 'tablet'];
for (const product of products) {
  // Test each product
}
```

---

## 🎓 Pro Tips

### Tip 1: Start Simple
```
Write simple test → Execute → Get script → Learn from it
```

### Tip 2: Iterate
```
Test in UI → Download script → Customize → Run independently
```

### Tip 3: Best of Both Worlds
```
- Quick changes: Use UI
- Complex logic: Edit generated script
```

### Tip 4: Build Test Library
```
Day 1: Generate login.spec.ts
Day 2: Generate search.spec.ts
Day 3: Generate checkout.spec.ts
Day 4: Combine into full suite
```

### Tip 5: Learn Patterns
```
Generated code shows best practices:
- Proper selector strategies
- Error handling
- Timeout management
- State management
```

---

## 🚀 Summary

**The Script Generation feature gives you:**

✅ **Speed** - Write tests in natural language  
✅ **Flexibility** - Get executable code  
✅ **Portability** - Run anywhere  
✅ **Learning** - See how it's done  
✅ **Integration** - Add to existing suites  
✅ **Control** - Customize as needed  

**You're no longer locked into the platform - you own the code!** 🎉

---

## 📞 Need Help?

- **Full Guide:** [docs/SCRIPT_GENERATION.md](SCRIPT_GENERATION.md)
- **Examples:** Run `python examples/script_generation_demo.py`
- **Troubleshooting:** [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
