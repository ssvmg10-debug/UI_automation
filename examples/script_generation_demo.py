"""
Example: Script Generation Feature
Demonstrates how the platform generates executable Playwright scripts
"""
import asyncio
from app.compiler.script_generator import ScriptGenerator
from app.compiler.instruction_model import Instruction, ActionType


async def demo_script_generation():
    """Demonstrate script generation in both JavaScript and TypeScript"""
    
    # Example test case
    instructions = [
        Instruction(
            action=ActionType.NAVIGATE,
            target="https://www.lg.com/in"
        ),
        Instruction(
            action=ActionType.CLICK,
            target="Air Solutions"
        ),
        Instruction(
            action=ActionType.CLICK,
            target="Split AC"
        ),
        Instruction(
            action=ActionType.WAIT,
            value="2"
        ),
        Instruction(
            action=ActionType.CLICK,
            target="Buy Now"
        ),
        Instruction(
            action=ActionType.VERIFY,
            target="Cart",
            expected="Added to cart"
        )
    ]
    
    print("=" * 80)
    print("SCRIPT GENERATION DEMO")
    print("=" * 80)
    
    # Generate TypeScript version
    print("\n📘 Generating TypeScript Script...")
    print("-" * 80)
    
    ts_generator = ScriptGenerator(language="typescript")
    ts_script = ts_generator.generate_script(instructions, "lg_ecommerce_test")
    
    print(ts_script)
    
    # Save TypeScript version
    with open("demo_test.ts", "w") as f:
        f.write(ts_script)
    print("\n✅ Saved as: demo_test.ts")
    
    print("\n" + "=" * 80)
    
    # Generate JavaScript version
    print("\n📗 Generating JavaScript Script...")
    print("-" * 80)
    
    js_generator = ScriptGenerator(language="javascript")
    js_script = js_generator.generate_script(instructions, "lg_ecommerce_test")
    
    print(js_script)
    
    # Save JavaScript version
    with open("demo_test.js", "w") as f:
        f.write(js_script)
    print("\n✅ Saved as: demo_test.js")
    
    print("\n" + "=" * 80)
    
    # Generate supporting files
    print("\n📦 Generating Supporting Files...")
    print("-" * 80)
    
    # package.json
    package_json = ts_generator.generate_package_json()
    with open("demo_package.json", "w") as f:
        f.write(package_json)
    print("✅ Generated: demo_package.json")
    
    # playwright.config.ts
    config = ts_generator.generate_playwright_config()
    with open("demo_playwright.config.ts", "w") as f:
        f.write(config)
    print("✅ Generated: demo_playwright.config.ts")
    
    print("\n" + "=" * 80)
    print("\n🎉 Script Generation Complete!")
    print("\nTo run the generated tests:")
    print("1. npm install")
    print("2. npx playwright install")
    print("3. npx playwright test demo_test.ts")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_script_generation())
