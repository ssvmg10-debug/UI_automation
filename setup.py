"""
Setup script for Enterprise UI Automation Platform.
"""
import subprocess
import sys
import os


def setup():
    """Run setup process."""
    print("🚀 Setting up Enterprise UI Automation Platform...")
    print()
    
    # Check Python version
    print("✓ Checking Python version...")
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print()
    
    # Install dependencies
    print("📦 Installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✓ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)
    print()
    
    # Install Playwright browsers
    print("🌐 Installing Playwright browsers...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Playwright browsers installed")
    except subprocess.CalledProcessError as e:
        print("⚠ Warning: Failed to install Playwright browsers")
        print("You can install them manually later with:")
        print("  python -m playwright install chromium")
        print("\nContinuing setup...")
    print()
    
    # Create directories
    print("📁 Creating directories...")
    os.makedirs("logs", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("memory_data", exist_ok=True)
    print("✓ Directories created")
    print()
    
    # Create .env file
    if not os.path.exists(".env"):
        print("📝 Creating .env file...")
        with open(".env.example", "r") as source:
            with open(".env", "w") as target:
                target.write(source.read())
        print("✓ .env file created (please add your API keys)")
        print()
    
    print("✅ Setup complete!")
    print()
    print("Next steps:")
    print("1. Edit .env file and add your OPENAI_API_KEY")
    print("2. Start the API: python -m app.main")
    print("3. Start the UI: streamlit run ui/streamlit_app.py")
    print()


if __name__ == "__main__":
    setup()
