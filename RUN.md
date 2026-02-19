# Run Scripts for Enterprise UI Automation Platform

## Windows (PowerShell)

# Activate virtual environment
& "C:\Users\gparavasthu\Workspace\Truvelocity\code_export\agentic-sdlc-platform\venv\Scripts\Activate.ps1"

# Install dependencies
python -m pip install -r requirements.txt
python -m playwright install chromium

# Run setup
python setup.py

# Start API server
python -m app.main

# In another terminal, start Streamlit UI
streamlit run ui/streamlit_app.py

## Docker

# Build and run with Docker Compose
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
