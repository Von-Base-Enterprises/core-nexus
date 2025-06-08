#!/usr/bin/env python3
"""
Keep-Alive Service for Core Nexus Memory Service
Prevents cold starts and monitors health
Agent 2 Implementation
"""

import asyncio
import aiohttp
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoreNexusKeepAlive:
    def __init__(self, base_url="https://core-nexus-memory-service.onrender.com"):
        self.base_url = base_url
        self.stats = {
            "heartbeats_sent": 0,
            "failures": 0,
            "last_success": None,
            "uptime_percentage": 100.0
        }
    
    async def heartbeat(self):
        """Send heartbeat to keep service warm."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        self.stats["heartbeats_sent"] += 1
                        self.stats["last_success"] = datetime.now()
                        data = await response.json()
                        logger.info(f"❤️  Heartbeat #{self.stats['heartbeats_sent']} - Service: {data.get('status', 'unknown')}")
                        return True
                    else:
                        raise Exception(f"Status {response.status}")
        except Exception as e:
            self.stats["failures"] += 1
            logger.warning(f"💔 Heartbeat failed: {e}")
            return False
    
    async def keep_warm(self):
        """Main loop to keep service warm."""
        logger.info("🔥 Starting Core Nexus Keep-Alive Service...")
        
        while True:
            success = await self.heartbeat()
            
            # Calculate uptime
            total = self.stats["heartbeats_sent"] + self.stats["failures"]
            if total > 0:
                self.stats["uptime_percentage"] = (self.stats["heartbeats_sent"] / total) * 100
            
            # Log stats every 10 heartbeats
            if total % 10 == 0:
                logger.info(f"📊 Stats: {self.stats}")
            
            # Wait 5 minutes before next heartbeat
            await asyncio.sleep(300)
    
    async def aggressive_warmup(self):
        """Aggressive warmup for cold service."""
        logger.info("🔥🔥🔥 AGGRESSIVE WARMUP MODE!")
        
        for i in range(5):
            await self.heartbeat()
            await asyncio.sleep(10)  # Every 10 seconds for first minute
        
        logger.info("✅ Warmup complete, switching to normal mode")

async def main():
    keeper = CoreNexusKeepAlive()
    
    # First do aggressive warmup
    await keeper.aggressive_warmup()
    
    # Then maintain warmth
    await keeper.keep_warm()

if __name__ == "__main__":
    asyncio.run(main())