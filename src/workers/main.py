"""
Background Worker Entry Point.
Source: Design Document Section 6.1 - Deployment Architecture
Verified: 2025-12-18

Processes background tasks like claim adjudication, notifications, etc.
"""

import asyncio
import signal
import sys
from datetime import datetime

# Graceful shutdown flag
shutdown_event = asyncio.Event()


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print(f"\nReceived signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()


async def process_claims_queue():
    """Process pending claims from the queue."""
    print(f"[{datetime.utcnow().isoformat()}] Claims processor started")

    while not shutdown_event.is_set():
        try:
            # Simulate processing claims
            # In production, this would pull from Redis/RabbitMQ queue
            await asyncio.sleep(5)
            print(f"[{datetime.utcnow().isoformat()}] Checking for pending claims...")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error processing claims: {e}")
            await asyncio.sleep(1)


async def process_notifications_queue():
    """Process pending notifications from the queue."""
    print(f"[{datetime.utcnow().isoformat()}] Notification processor started")

    while not shutdown_event.is_set():
        try:
            # Simulate processing notifications
            await asyncio.sleep(10)
            print(f"[{datetime.utcnow().isoformat()}] Checking for pending notifications...")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error processing notifications: {e}")
            await asyncio.sleep(1)


async def health_check_reporter():
    """Report worker health status."""
    print(f"[{datetime.utcnow().isoformat()}] Health reporter started")

    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(30)
            print(f"[{datetime.utcnow().isoformat()}] Worker health: OK")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Health check error: {e}")
            await asyncio.sleep(5)


async def main():
    """Main worker entry point."""
    print("=" * 60)
    print("Claims Processing System - Background Worker")
    print("=" * 60)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create worker tasks
    tasks = [
        asyncio.create_task(process_claims_queue()),
        asyncio.create_task(process_notifications_queue()),
        asyncio.create_task(health_check_reporter()),
    ]

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Cancel all tasks
    print("\nShutting down workers...")
    for task in tasks:
        task.cancel()

    # Wait for tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)

    print("Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker interrupted")
        sys.exit(0)
