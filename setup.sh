#!/bin/bash
# Setup script for AI Hedge Fund India

set -e  # Exit on error

echo "🚀 AI Hedge Fund India - Setup Script"
echo "======================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.11+ required, but found $python_version"
    exit 1
fi
echo "✅ Python $python_version found"
echo ""

# Check if TA-Lib is installed
echo "📋 Checking TA-Lib installation..."
if python3 -c "import talib" 2>/dev/null; then
    echo "✅ TA-Lib is already installed"
else
    echo "⚠️  TA-Lib not found. Please install it:"
    echo "   macOS: brew install ta-lib"
    echo "   Ubuntu: sudo apt-get install ta-lib"
    echo "   Windows: Download from https://github.com/mrjbq7/ta-lib"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists"
    read -p "Recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✅ Virtual environment recreated"
    fi
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Error installing dependencies"
    exit 1
fi
echo ""

# Create .env file
echo "⚙️  Setting up environment configuration..."
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists"
else
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - GEMINI_API_KEY (for LLM narratives)"
    echo "   - Optional: OPENAI_API_KEY, ANTHROPIC_API_KEY"
    echo ""
fi
echo ""

# Create logs directory
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Run a quick test
echo "🧪 Running quick installation test..."
if python3 -c "import pandas, numpy, fastapi, yfinance; print('All core imports successful')" 2>/dev/null; then
    echo "✅ Installation test passed"
else
    echo "❌ Installation test failed"
    exit 1
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "3. Start the API server:"
echo "   python -m uvicorn api.main:app --reload --port 8010"
echo ""
echo "4. Visit API docs:"
echo "   http://localhost:8010/docs"
echo ""
echo "Happy trading! 📈"
