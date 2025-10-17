#!/bin/bash
# FIRE Project Setup Script

echo "🔥 FIRE Video Processing Project Setup"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check VLC
if ! command -v vlc &> /dev/null; then
    echo "⚠️  VLC not found. Installing..."
    sudo apt update
    sudo apt install -y vlc
else
    echo "✅ VLC found: $(vlc --version | head -1)"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the environment:"
echo "   source activate_env.sh"
echo ""
echo "Or manually:"
echo "   source venv/bin/activate"