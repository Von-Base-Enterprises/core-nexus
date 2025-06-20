#!/bin/bash
# 
# Core Nexus Secure Backup Setup Script
# Sets up environment variables and tests the backup system
#

set -e

echo "🔐 Core Nexus Secure Backup Setup"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "secure_backup_system.py" ]; then
    echo "❌ Error: Please run this script from the core-nexus root directory"
    exit 1
fi

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry is not installed. Please install poetry first."
    exit 1
fi

# Create backups directory if it doesn't exist
echo "📁 Creating backup directory..."
mkdir -p backups

# Check environment variables
if [ -z "$PGVECTOR_PASSWORD" ]; then
    echo "⚠️  Warning: PGVECTOR_PASSWORD environment variable not set"
    echo "   You'll need to set this before running backups:"
    echo "   export PGVECTOR_PASSWORD=\"your_password_here\""
    echo ""
    
    # Offer to set it temporarily for testing
    read -p "Would you like to enter the password now for testing? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -s -p "Enter PostgreSQL password: " temp_password
        echo ""
        export PGVECTOR_PASSWORD="$temp_password"
    else
        echo "❌ Cannot proceed without password. Exiting."
        exit 1
    fi
fi

echo "🏥 Testing database connection..."
if poetry run python secure_backup_system.py health; then
    echo "✅ Database connection successful!"
else
    echo "❌ Database connection failed!"
    exit 1
fi

echo ""
echo "🧪 Running test backup..."
if poetry run python backup_scheduler.py manual; then
    echo "✅ Test backup completed successfully!"
else
    echo "❌ Test backup failed!"
    exit 1
fi

echo ""
echo "📋 Listing current backups..."
poetry run python secure_backup_system.py list

echo ""
echo "✅ Backup system setup complete!"
echo ""
echo "🎯 Available Commands:"
echo "   Health check:        poetry run python secure_backup_system.py health"
echo "   Manual backup:       poetry run python backup_scheduler.py manual"
echo "   List backups:        poetry run python secure_backup_system.py list"
echo "   Verify backup:       poetry run python secure_backup_system.py verify <name>"
echo "   Start scheduler:     poetry run python backup_scheduler.py start"
echo ""
echo "📝 Don't forget to:"
echo "   1. Set PGVECTOR_PASSWORD in your environment"
echo "   2. Consider running the scheduler as a daemon for automated backups"
echo "   3. Periodically verify backup integrity"
echo ""
echo "🚀 Your Core Nexus database is now safely backed up!"