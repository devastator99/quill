#!/bin/bash

echo "🔄 Restarting Socratic Backend Services..."

# Kill any existing Celery workers
echo "🛑 Stopping existing Celery workers..."
pkill -f "celery.*worker" || true
pkill -f "celery.*flower" || true

# Wait a moment for processes to stop
sleep 2

# Clear Redis (Celery broker) to remove any stuck tasks
echo "🧹 Clearing Redis cache..."
redis-cli FLUSHALL || echo "Redis not available, skipping..."

# Set environment for macOS fork safety
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export CELERY_WORKER_POOL=solo

echo "🚀 Starting Celery worker with macOS-safe settings..."
celery -A celery_worker.celery_app worker --loglevel=info --pool=solo --concurrency=1 &

# Wait a moment for worker to start
sleep 3

echo "🌸 Starting Celery Flower monitoring (optional)..."
celery -A celery_worker.celery_app flower --port=5555 &

echo "✅ Services restarted successfully!"
echo ""
echo "📊 Monitor Celery at: http://localhost:5555"
echo "🔍 Worker logs: Check terminal output above"
echo ""
echo "To stop services:"
echo "  pkill -f 'celery.*worker'"
echo "  pkill -f 'celery.*flower'" 