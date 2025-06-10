#!/usr/bin/env python3
"""
Keep-alive worker for Core Nexus Memory Service on Render.com

Prevents cold starts by pinging the health endpoint every 5 minutes.
Render's free tier has a 15-minute idle timeout, so this keeps the service warm.
"""

import asyncio
import logging
import os
import time
from datetime import datetime

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = os.getenv("API_URL", "https://core-nexus-memory-service.onrender.com")
PING_INTERVAL = int(os.getenv("PING_SEC", "300"))  # 5 minutes
TIMEOUT = int(os.getenv("PING_TIMEOUT", "10"))
RETRY_COUNT = int(os.getenv("PING_RETRIES", "3"))


async def ping_health_endpoint(client: httpx.AsyncClient) -> tuple[int, float, str]:
    """Ping the health endpoint and return status code, response time, and details."""
    t0 = time.perf_counter()

    try:
        response = await client.get(f"{API_URL}/health", timeout=TIMEOUT)
        dt = (time.perf_counter() - t0) * 1000

        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            providers = len(data.get('providers', {}))
            return response.status_code, dt, f"status={status}, providers={providers}"
        else:
            return response.status_code, dt, f"HTTP {response.status_code}"

    except httpx.TimeoutException:
        dt = (time.perf_counter() - t0) * 1000
        return 0, dt, "TIMEOUT"
    except httpx.ConnectError:
        dt = (time.perf_counter() - t0) * 1000
        return 0, dt, "CONNECTION_ERROR"
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        return 0, dt, f"ERROR: {str(e)[:100]}"


async def keep_alive_loop():
    """Main keep-alive loop."""
    logger.info("🔥 Core Nexus Keep-Alive Worker Starting")
    logger.info(f"📍 Target: {API_URL}")
    logger.info(f"⏰ Ping interval: {PING_INTERVAL}s ({PING_INTERVAL/60:.1f} minutes)")
    logger.info(f"🔄 Timeout: {TIMEOUT}s, Retries: {RETRY_COUNT}")

    ping_count = 0
    success_count = 0

    async with httpx.AsyncClient() as client:
        while True:
            ping_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Try pinging with retries
            for attempt in range(1, RETRY_COUNT + 1):
                status_code, response_time, details = await ping_health_endpoint(client)

                if status_code == 200:
                    success_count += 1
                    success_rate = (success_count / ping_count) * 100
                    logger.info(
                        f"✅ [{ping_count:4d}] {timestamp} → 200 OK "
                        f"({response_time:5.1f}ms) | {details} | "
                        f"Success: {success_rate:.1f}%"
                    )
                    break
                elif attempt < RETRY_COUNT:
                    logger.warning(
                        f"⚠️ [{ping_count:4d}] {timestamp} → {details} "
                        f"({response_time:5.1f}ms) | Retry {attempt}/{RETRY_COUNT-1}"
                    )
                    await asyncio.sleep(5)  # Wait 5s between retries
                else:
                    success_rate = (success_count / ping_count) * 100
                    logger.error(
                        f"❌ [{ping_count:4d}] {timestamp} → {details} "
                        f"({response_time:5.1f}ms) | Failed after {RETRY_COUNT} attempts | "
                        f"Success: {success_rate:.1f}%"
                    )

            # Log summary every 12 pings (1 hour)
            if ping_count % 12 == 0:
                success_rate = (success_count / ping_count) * 100
                uptime_hours = (ping_count * PING_INTERVAL) / 3600
                logger.info(
                    f"📊 SUMMARY: {ping_count} pings over {uptime_hours:.1f}h, "
                    f"success rate: {success_rate:.1f}% ({success_count}/{ping_count})"
                )

            # Wait for next ping
            await asyncio.sleep(PING_INTERVAL)


async def main():
    """Main entry point."""
    try:
        await keep_alive_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Keep-alive worker stopped by user")
    except Exception as e:
        logger.error(f"💥 Keep-alive worker crashed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
