#!/bin/bash
# Core Nexus Memory Service - Production Deployment Script
# Automated deployment with health checks and validation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="core-nexus-memory"
SERVICE_PORT="8000"
MAX_WAIT_TIME=300  # 5 minutes
HEALTH_CHECK_URL="http://localhost:${SERVICE_PORT}/health"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service health
wait_for_health() {
    print_status "Waiting for service to become healthy..."
    local count=0
    local max_attempts=$((MAX_WAIT_TIME / 10))
    
    while [ $count -lt $max_attempts ]; do
        if curl -s -f "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
            print_success "Service is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep 10
        count=$((count + 1))
    done
    
    print_error "Service failed to become healthy within ${MAX_WAIT_TIME} seconds"
    return 1
}

# Function to validate deployment
validate_deployment() {
    print_status "Validating deployment..."
    
    # Check service health
    if ! curl -s -f "$HEALTH_CHECK_URL" >/dev/null; then
        print_error "Health check failed"
        return 1
    fi
    
    # Check dashboard metrics
    if ! curl -s -f "http://localhost:${SERVICE_PORT}/dashboard/metrics" >/dev/null; then
        print_warning "Dashboard metrics endpoint not responding"
    fi
    
    # Check ADM performance
    if ! curl -s -f "http://localhost:${SERVICE_PORT}/adm/performance" >/dev/null; then
        print_warning "ADM performance endpoint not responding"
    fi
    
    # Test memory storage
    local test_response=$(curl -s -X POST "http://localhost:${SERVICE_PORT}/memories" \
        -H "Content-Type: application/json" \
        -d '{"content":"Deployment test memory","metadata":{"test":true},"user_id":"deployment_test"}' \
        2>/dev/null)
    
    if echo "$test_response" | grep -q '"id"'; then
        print_success "Memory storage test passed"
    else
        print_warning "Memory storage test failed"
    fi
    
    print_success "Deployment validation completed"
}

# Function to show deployment summary
show_summary() {
    print_success "🎉 Core Nexus Memory Service Deployment Complete!"
    echo ""
    echo "📊 Service Endpoints:"
    echo "   Health Check:    $HEALTH_CHECK_URL"
    echo "   API Docs:        http://localhost:${SERVICE_PORT}/docs"
    echo "   Dashboard:       http://localhost:${SERVICE_PORT}/dashboard/metrics"
    echo "   Analytics:       http://localhost:${SERVICE_PORT}/analytics/usage"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs:       docker-compose logs -f memory-service"
    echo "   Stop service:    docker-compose down"
    echo "   Restart:         docker-compose restart memory-service"
    echo "   Update:          docker-compose pull && docker-compose up -d"
    echo ""
    echo "📚 Documentation:"
    echo "   Deployment Guide: $(pwd)/DEPLOYMENT_GUIDE.md"
    echo "   API Docs:        http://localhost:${SERVICE_PORT}/docs"
    echo ""
}

# Main deployment function
main() {
    echo ""
    echo "🧠 Core Nexus Memory Service Deployment"
    echo "========================================"
    echo ""
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker and try again."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    
    if ! command_exists curl; then
        print_error "curl is not installed. Please install curl and try again."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        if [ -f .env.example ]; then
            print_status "Copying .env.example to .env"
            cp .env.example .env
            print_warning "Please edit .env file with your configuration before proceeding"
            echo "Press Enter to continue after editing .env file..."
            read
        else
            print_error ".env.example file not found. Please create a .env file with your configuration."
            exit 1
        fi
    fi
    
    # Stop existing services
    print_status "Stopping any existing services..."
    docker-compose down >/dev/null 2>&1 || true
    
    # Pull latest images
    print_status "Pulling Docker images..."
    if ! docker-compose pull; then
        print_warning "Failed to pull some images, continuing with local builds..."
    fi
    
    # Build and start services
    print_status "Building and starting services..."
    if ! docker-compose up -d --build; then
        print_error "Failed to start services"
        print_status "Checking logs for errors..."
        docker-compose logs --tail=50
        exit 1
    fi
    
    # Wait for services to be healthy
    if ! wait_for_health; then
        print_error "Deployment failed - service not healthy"
        print_status "Checking logs for errors..."
        docker-compose logs --tail=50 memory-service
        exit 1
    fi
    
    # Validate deployment
    if ! validate_deployment; then
        print_warning "Deployment validation had issues, but service is running"
    fi
    
    # Show summary
    show_summary
}

# Handle script arguments
case "${1:-}" in
    "health")
        curl -s "$HEALTH_CHECK_URL" | python -m json.tool 2>/dev/null || echo "Health check failed"
        ;;
    "logs")
        docker-compose logs -f memory-service
        ;;
    "stop")
        print_status "Stopping Core Nexus Memory Service..."
        docker-compose down
        print_success "Service stopped"
        ;;
    "restart")
        print_status "Restarting Core Nexus Memory Service..."
        docker-compose restart memory-service
        print_success "Service restarted"
        ;;
    "update")
        print_status "Updating Core Nexus Memory Service..."
        docker-compose pull
        docker-compose up -d
        wait_for_health
        print_success "Service updated"
        ;;
    "clean")
        print_status "Cleaning up Docker resources..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
        ;;
    "help"|"-h"|"--help")
        echo "Core Nexus Memory Service Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (no args)  Deploy the service"
        echo "  health     Check service health"
        echo "  logs       Show service logs"
        echo "  stop       Stop the service"
        echo "  restart    Restart the service"
        echo "  update     Update and restart the service"
        echo "  clean      Clean up Docker resources"
        echo "  help       Show this help message"
        echo ""
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac