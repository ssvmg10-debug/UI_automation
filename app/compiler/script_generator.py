"""
Script Generator - Converts execution plans to Playwright JavaScript/TypeScript code.
Accepts Instruction or ExecutionStep (action as string).
"""
from typing import List, Literal, Any
from app.compiler.instruction_model import Instruction, ActionType


class ScriptGenerator:
    """Generates Playwright scripts in JavaScript or TypeScript"""
    
    def __init__(self, language: Literal["javascript", "typescript"] = "typescript"):
        self.language = language
        self.use_types = language == "typescript"
    
    def _normalize_instruction(self, step: Any) -> Instruction:
        """Convert ExecutionStep (action=str) or dict to Instruction (action=ActionType). Never use .get on non-dict."""
        if isinstance(step, Instruction) and hasattr(step.action, "value"):
            return step
        if isinstance(step, dict):
            action = step.get("action")
            target = step.get("target", "") or ""
            value = step.get("value")
        else:
            action = getattr(step, "action", None)
            target = getattr(step, "target", "") or ""
            value = getattr(step, "value", None)
        if isinstance(action, str):
            try:
                action = ActionType[action.upper()]
            except (KeyError, ValueError):
                try:
                    action = ActionType(action.lower())
                except (KeyError, ValueError):
                    action = ActionType.CLICK if action.lower() in ("click", "press") else ActionType.ASSERT
        return Instruction(action=action, target=target, value=value)
    
    def generate_script(
        self, 
        instructions: List[Any], 
        test_name: str = "automatedTest"
    ) -> str:
        """
        Generate a complete Playwright test script.
        
        Args:
            instructions: List of Instruction, ExecutionStep, or dict
            test_name: Name for the test function
            
        Returns:
            Complete Playwright script as string
        """
        normalized = [self._normalize_instruction(s) for s in instructions]
        imports = self._generate_imports()
        test_function = self._generate_test_function(normalized, test_name)
        
        return f"{imports}\n\n{test_function}\n"
    
    def _generate_imports(self) -> str:
        """Generate import statements"""
        if self.use_types:
            return """import { test, expect, Page, Browser, BrowserContext } from '@playwright/test';"""
        else:
            return """const { test, expect } = require('@playwright/test');"""
    
    def _generate_test_function(
        self, 
        instructions: List[Instruction], 
        test_name: str
    ) -> str:
        """Generate the test function"""
        type_annotation = ": Page" if self.use_types else ""
        
        lines = [
            f"test('{test_name}', async ({{ page }}{type_annotation}) => {{",
        ]
        
        # Add test timeout
        lines.append("  test.setTimeout(60000); // 60 second timeout")
        lines.append("")
        
        # Convert each instruction
        for i, instruction in enumerate(instructions, 1):
            # Add comment for step
            lines.append(f"  // Step {i}: {instruction.action.value}")
            
            # Generate code for this instruction
            code_lines = self._generate_instruction_code(instruction)
            lines.extend(f"  {line}" for line in code_lines)
            lines.append("")
        
        lines.append("});")
        
        return "\n".join(lines)
    
    def _generate_instruction_code(self, instruction: Instruction) -> List[str]:
        """Generate code for a single instruction"""
        action = instruction.action
        
        if action == ActionType.NAVIGATE:
            return [
                f"await page.goto('{instruction.target}');",
                "await page.waitForLoadState('networkidle');"
            ]
        
        elif action == ActionType.CLICK:
            return self._generate_click_code(instruction)
        
        elif action == ActionType.TYPE:
            return self._generate_type_code(instruction)
        
        elif action == ActionType.WAIT:
            wait_time = int(instruction.value or 2) * 1000
            return [f"await page.waitForTimeout({wait_time});"]
        
        elif action == ActionType.ASSERT:
            return self._generate_verify_code(instruction)
        
        elif action == ActionType.SELECT:
            return self._generate_select_code(instruction)
        
        else:
            return [f"// Unknown action: {action.value}"]
    
    def _generate_click_code(self, instruction: Instruction) -> List[str]:
        """Generate click action code"""
        target = instruction.target
        lines = []
        
        # Try multiple selectors in order of specificity
        if target:
            # Clean target text
            target_text = target.replace("'", "\\'")
            
            lines.append(f"// Click element: '{target_text}'")
            lines.append("try {")
            
            # Strategy 1: Text exact match
            lines.append(f"  await page.getByText('{target_text}', {{ exact: true }}).click({{ timeout: 5000 }});")
            
            lines.append("} catch (e1) {")
            lines.append("  try {")
            
            # Strategy 2: Text partial match
            lines.append(f"    await page.getByText('{target_text}').first().click({{ timeout: 5000 }});")
            
            lines.append("  } catch (e2) {")
            lines.append("    try {")
            
            # Strategy 3: Role-based
            lines.append(f"      await page.getByRole('button', {{ name: /{target_text}/i }}).click({{ timeout: 5000 }});")
            
            lines.append("    } catch (e3) {")
            
            # Strategy 4: Label
            lines.append(f"      await page.getByLabel(/{target_text}/i).click({{ timeout: 5000 }});")
            
            lines.append("    }")
            lines.append("  }")
            lines.append("}")
        else:
            lines.append("// Click action without target specified")
            lines.append("// TODO: Add specific selector")
        
        return lines
    
    def _generate_type_code(self, instruction: Instruction) -> List[str]:
        """Generate type action code"""
        target = instruction.target
        value = instruction.value or ""
        lines = []
        
        if target and value:
            target_text = target.replace("'", "\\'")
            value_text = value.replace("'", "\\'")
            
            lines.append(f"// Type into: '{target_text}'")
            lines.append("try {")
            
            # Strategy 1: Label
            lines.append(f"  await page.getByLabel(/{target_text}/i).fill('{value_text}');")
            
            lines.append("} catch (e1) {")
            lines.append("  try {")
            
            # Strategy 2: Placeholder
            lines.append(f"    await page.getByPlaceholder(/{target_text}/i).fill('{value_text}');")
            
            lines.append("  } catch (e2) {")
            
            # Strategy 3: Role
            lines.append(f"    await page.getByRole('textbox', {{ name: /{target_text}/i }}).fill('{value_text}');")
            
            lines.append("  }")
            lines.append("}")
        else:
            lines.append("// Type action incomplete")
            lines.append(f"// Target: {target}, Value: {value}")
        
        return lines
    
    def _generate_verify_code(self, instruction: Instruction) -> List[str]:
        """Generate verification code"""
        target = instruction.target
        expected = getattr(instruction, "expected_outcome", None) or getattr(instruction, "expected", None) or instruction.value
        
        lines = []
        
        if target and expected:
            target_text = target.replace("'", "\\'")
            expected_text = expected.replace("'", "\\'")
            
            lines.append(f"// Verify: '{target_text}' contains '{expected_text}'")
            
            # Check if page contains the expected text
            lines.append("try {")
            lines.append(f"  await expect(page.getByText(/{expected_text}/i)).toBeVisible({{ timeout: 5000 }});")
            lines.append("} catch (e) {")
            lines.append(f"  // Fallback: check if text exists anywhere on page")
            lines.append(f"  await expect(page.locator('body')).toContainText(/{expected_text}/i);")
            lines.append("}")
        elif target:
            target_text = target.replace("'", "\\'")
            lines.append(f"// Verify element exists: '{target_text}'")
            lines.append(f"await expect(page.getByText(/{target_text}/i)).toBeVisible();")
        else:
            lines.append("// Verify action without target")
        
        return lines
    
    def _generate_select_code(self, instruction: Instruction) -> List[str]:
        """Generate select/dropdown action code"""
        target = instruction.target
        value = instruction.value
        
        lines = []
        
        if target and value:
            target_text = target.replace("'", "\\'")
            value_text = value.replace("'", "\\'")
            
            lines.append(f"// Select from dropdown: '{target_text}'")
            lines.append("try {")
            lines.append(f"  await page.getByLabel(/{target_text}/i).selectOption('{value_text}');")
            lines.append("} catch (e) {")
            lines.append(f"  await page.selectOption('select', '{value_text}');")
            lines.append("}")
        else:
            lines.append("// Select action incomplete")
        
        return lines
    
    def generate_package_json(self) -> str:
        """Generate package.json for the test project"""
        if self.use_types:
            return """{
  "name": "ui-automation-tests",
  "version": "1.0.0",
  "description": "Auto-generated Playwright tests",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}"""
        else:
            return """{
  "name": "ui-automation-tests",
  "version": "1.0.0",
  "description": "Auto-generated Playwright tests",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}"""
    
    def generate_playwright_config(self) -> str:
        """Generate playwright.config file"""
        if self.use_types:
            return """import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});"""
        else:
            return """const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});"""
    
    def get_file_extension(self) -> str:
        """Get the appropriate file extension"""
        return ".ts" if self.use_types else ".js"
    
    def get_config_file_name(self) -> str:
        """Get the config file name"""
        return "playwright.config.ts" if self.use_types else "playwright.config.js"
