#!/bin/bash
#
# setup_project.sh
#
# This script creates the complete directory structure and placeholder files
# for the Oracle Monitor project. Run it from your project's root directory.

echo "🚀 Starting project setup for Oracle Monitor..."

# --- Create src directory and sub-packages ---
echo "Creating source directories: src/services and src/utils..."
mkdir -p src/services
mkdir -p src/utils

# Create __init__.py files to make directories Python packages
echo "Creating __init__.py files..."
touch src/__init__.py
touch src/services/__init__.py
touch src/utils/__init__.py

# Create placeholder .py files based on the project structure
echo "Creating placeholder Python files..."
touch src/services/ai_analyzer.py
touch src/services/email_service.py
touch src/services/file_monitor.py
touch src/services/health_checker.py
touch src/utils/security.py
touch src/utils/metrics.py

# --- Create config directory ---
echo "Creating configuration directory and files..."
mkdir -p config
touch config/config.yaml
touch config/logging.yaml

# --- Create tests directory ---
echo "Creating tests directory structure..."
mkdir -p tests/fixtures
touch tests/__init__.py
touch tests/test_oracle_monitor.py

# --- Create deployment directory ---
echo "Creating deployment directory and files..."
mkdir -p deployment
touch deployment/Dockerfile
touch deployment/docker-compose.yml
touch deployment/oracle-monitor.service
touch deployment/requirements.txt

# --- Create scripts directory ---
echo "Creating scripts directory and files..."
mkdir -p scripts
touch scripts/install.sh
touch scripts/health_check.py

# --- Create root files ---
echo "Creating README.md..."
touch README.md

echo "✅ Project structure created successfully!"
echo "➡️ Next steps:"
echo "   1. Populate the new files with your code."
echo "   2. Make sure config/config.yaml is configured."
echo "   3. Run the application from the project root: python3 -m src.oracle_monitor"


