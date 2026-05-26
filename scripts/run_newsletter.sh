#!/bin/bash

# Quantum Intelligence Newsletter Generator - Execution Script
# This script activates the virtual environment and runs the newsletter generator

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Quantum Intelligence Newsletter Generator ===${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of scripts/)
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Navigate to project directory
cd "$PROJECT_DIR" || exit

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: python3.13 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env from .env.example and add your API keys"
    exit 1
fi

# Check if main Python file exists
if [ ! -f "quantum_intelligence.py" ]; then
    echo -e "${RED}Error: quantum_intelligence.py not found!${NC}"
    echo "Are you in the correct directory?"
    exit 1
fi

# Run the newsletter generator
echo -e "${GREEN}Starting newsletter generation...${NC}"
echo ""
python quantum_intelligence.py

# Check if execution was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Newsletter generated successfully!${NC}"
    echo ""
    echo "Output files:"
    [ -f "quantum_newsletter_output.md" ] && echo "  - quantum_newsletter_output.md"
    [ -f "quantum_newsletter.log" ] && echo "  - quantum_newsletter.log"
    [ -f "newsletter_stats.json" ] && echo "  - newsletter_stats.json"
    [ -f "sent_articles.txt" ] && echo "  - sent_articles.txt (updated)"
else
    echo ""
    echo -e "${RED}✗ Newsletter generation failed!${NC}"
    echo "Check quantum_newsletter.log for details"
    exit 1
fi

echo ""
echo -e "${YELLOW}Deactivating virtual environment...${NC}"
deactivate
