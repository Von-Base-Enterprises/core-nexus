#!/usr/bin/env python3
"""
JARVIS Automated Health Monitoring System
Proactive monitoring with alerts for performance anomalies
"""

import asyncio
import httpx
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import smtplib
from email.mime.text import MimeText

class JarvisHealthMonitor:
    """Automated health monitoring with smart alerting"""
    
    def __init__(self, 
                 jarvis_url: str = None,
                 core_nexus_url: str = None,
                 check_interval: int = None):  # 5 minutes
        
        self.jarvis_url = jarvis_url or os.getenv("JARVIS_URL", "https://jarvis-ai-agent-aa4m.onrender.com")
        self.core_nexus_url = core_nexus_url or os.getenv("CORE_NEXUS_URL", "https://core-nexus-memory-service.onrender.com")
        self.check_interval = check_interval or int(os.getenv("CHECK_INTERVAL", "300"))
        
        # Performance thresholds (based on optimization targets)
        self.thresholds = {
            "max_iterations_simple": 2,
            "max_iterations_complex": 5,
            "max_duration_simple": 5.0,    # seconds
            "max_duration_complex": 20.0,  # seconds
            "max_response_time": 30.0,     # seconds
            "min_success_rate": 95.0       # percentage
        }
        
        # Health tracking
        self.health_history = []
        self.performance_history = []
        self.alert_cooldown = {}  # Prevent spam
        
        # Alert configuration
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL")  # Slack/Discord webhook
        self.alert_email = os.getenv("ALERT_EMAIL")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        
        # Setup logging
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('jarvis_health_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def check_jarvis_health(self) -> Dict[str, Any]:
        """Check JARVIS service health"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                start_time = time.time()
                response = await client.get(f"{self.jarvis_url}/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "data": health_data,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_core_nexus_health(self) -> Dict[str, Any]:
        """Check Core Nexus service health"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                start_time = time.time()
                response = await client.get(f"{self.core_nexus_url}/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "data": health_data,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_performance_simple(self) -> Dict[str, Any]:
        """Test performance with a simple task"""
        test_task = "Quick health status check"
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.jarvis_url}/tasks",
                    json={"task": test_task, "priority": "medium"}
                )
                wall_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": data["success"],
                        "iterations": data["iterations"],
                        "duration": data["duration"],
                        "wall_time": wall_time,
                        "task_type": "simple",
                        "meets_iteration_threshold": data["iterations"] <= self.thresholds["max_iterations_simple"],
                        "meets_duration_threshold": data["duration"] <= self.thresholds["max_duration_simple"],
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "task_type": "simple",
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_type": "simple",
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_health_trends(self) -> Dict[str, Any]:
        """Analyze health trends for anomaly detection and regression"""
        if len(self.health_history) < 3:
            return {"status": "insufficient_data"}
        
        # Get recent health checks (last hour)
        recent_checks = [
            h for h in self.health_history 
            if datetime.fromisoformat(h["timestamp"]) > datetime.now() - timedelta(hours=1)
        ]
        
        if not recent_checks:
            return {"status": "no_recent_data"}
        
        # Calculate trends
        jarvis_healthy = sum(1 for h in recent_checks if h["jarvis"]["status"] == "healthy")
        core_nexus_healthy = sum(1 for h in recent_checks if h["core_nexus"]["status"] == "healthy")
        
        jarvis_uptime = (jarvis_healthy / len(recent_checks)) * 100
        core_nexus_uptime = (core_nexus_healthy / len(recent_checks)) * 100
        
        # Performance analysis with regression detection
        successful_tests = [p for p in self.performance_history if p.get("success")]
        if successful_tests:
            avg_iterations = sum(p["iterations"] for p in successful_tests) / len(successful_tests)
            avg_duration = sum(p["duration"] for p in successful_tests) / len(successful_tests)
            
            performance_score = 100
            if avg_iterations > self.thresholds["max_iterations_simple"]:
                performance_score -= 20
            if avg_duration > self.thresholds["max_duration_simple"]:
                performance_score -= 20
                
            # Regression detection - compare recent vs historical performance
            regression_alerts = self._detect_performance_regression(successful_tests)
        else:
            performance_score = 0
            avg_iterations = 0
            avg_duration = 0
            regression_alerts = []
        
        return {
            "status": "analyzed",
            "jarvis_uptime_pct": jarvis_uptime,
            "core_nexus_uptime_pct": core_nexus_uptime,
            "performance_score": performance_score,
            "avg_iterations": avg_iterations,
            "avg_duration": avg_duration,
            "checks_analyzed": len(recent_checks),
            "performance_tests": len(successful_tests),
            "regression_alerts": regression_alerts
        }
    
    def _detect_performance_regression(self, performance_data: List[Dict]) -> List[Dict[str, Any]]:
        """Detect performance regression by comparing recent vs historical trends"""
        if len(performance_data) < 10:  # Need sufficient data
            return []
            
        # Split into recent (last 25%) and historical (first 75%) 
        split_point = int(len(performance_data) * 0.75)
        historical = performance_data[:split_point]
        recent = performance_data[split_point:]
        
        if not historical or not recent:
            return []
            
        # Calculate averages
        hist_avg_iterations = sum(p["iterations"] for p in historical) / len(historical)
        hist_avg_duration = sum(p["duration"] for p in historical) / len(historical)
        
        recent_avg_iterations = sum(p["iterations"] for p in recent) / len(recent)
        recent_avg_duration = sum(p["duration"] for p in recent) / len(recent)
        
        regression_alerts = []
        
        # Check for iteration regression (>20% increase)
        iteration_increase_pct = ((recent_avg_iterations - hist_avg_iterations) / hist_avg_iterations) * 100
        if iteration_increase_pct > 20:
            regression_alerts.append({
                "type": "iteration_regression",
                "historical_avg": hist_avg_iterations,
                "recent_avg": recent_avg_iterations,
                "increase_pct": iteration_increase_pct,
                "severity": "high" if iteration_increase_pct > 50 else "medium"
            })
        
        # Check for duration regression (>30% increase)
        duration_increase_pct = ((recent_avg_duration - hist_avg_duration) / hist_avg_duration) * 100
        if duration_increase_pct > 30:
            regression_alerts.append({
                "type": "duration_regression", 
                "historical_avg": hist_avg_duration,
                "recent_avg": recent_avg_duration,
                "increase_pct": duration_increase_pct,
                "severity": "high" if duration_increase_pct > 60 else "medium"
            })
        
        return regression_alerts
    
    def should_alert(self, alert_type: str, cooldown_minutes: int = 30) -> bool:
        """Check if we should send an alert (prevents spam)"""
        now = datetime.now()
        last_alert = self.alert_cooldown.get(alert_type)
        
        if last_alert is None:
            self.alert_cooldown[alert_type] = now
            return True
        
        if now - last_alert > timedelta(minutes=cooldown_minutes):
            self.alert_cooldown[alert_type] = now
            return True
        
        return False
    
    def generate_alert(self, alert_type: str, details: Dict[str, Any]) -> str:
        """Generate alert message"""
        alerts = {
            "service_down": f"🚨 JARVIS SERVICE DOWN\nTimestamp: {datetime.now()}\nDetails: {details}",
            "performance_degraded": f"⚠️ JARVIS PERFORMANCE DEGRADED\nTimestamp: {datetime.now()}\nDetails: {details}",
            "high_iterations": f"📈 HIGH ITERATION COUNT DETECTED\nTimestamp: {datetime.now()}\nDetails: {details}",
            "slow_response": f"🐌 SLOW RESPONSE TIME DETECTED\nTimestamp: {datetime.now()}\nDetails: {details}",
            "core_nexus_down": f"🚨 CORE NEXUS SERVICE DOWN\nTimestamp: {datetime.now()}\nDetails: {details}"
        }
        
        return alerts.get(alert_type, f"UNKNOWN ALERT: {alert_type}\n{details}")
    
    async def send_webhook_alert(self, message: str) -> bool:
        """Send alert via webhook (Slack/Discord)"""
        if not self.webhook_url:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                payload = {
                    "text": message,
                    "username": "JARVIS Monitor",
                    "icon_emoji": ":robot_face:"
                }
                
                response = await client.post(self.webhook_url, json=payload)
                if response.status_code == 200:
                    self.logger.info("✅ Webhook alert sent successfully")
                    return True
                else:
                    self.logger.error(f"❌ Webhook alert failed: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Webhook alert error: {e}")
            return False
    
    def send_email_alert(self, message: str) -> bool:
        """Send alert via email"""
        if not all([self.alert_email, self.smtp_user, self.smtp_password]):
            return False
            
        try:
            msg = MimeText(message)
            msg['Subject'] = 'JARVIS System Alert'
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            self.logger.info("✅ Email alert sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Email alert error: {e}")
            return False
    
    async def send_alert(self, alert_type: str, details: Dict[str, Any]) -> bool:
        """Send alert via all configured channels"""
        message = self.generate_alert(alert_type, details)
        
        # Try webhook first (faster)
        webhook_sent = await self.send_webhook_alert(message)
        
        # Try email as backup
        email_sent = self.send_email_alert(message)
        
        if not webhook_sent and not email_sent:
            self.logger.warning("⚠️ No alert channels configured or all failed")
        
        return webhook_sent or email_sent
    
    async def run_health_check_cycle(self) -> Dict[str, Any]:
        """Run a complete health check cycle"""
        self.logger.info("Starting health check cycle...")
        
        # Check services
        jarvis_health = await self.check_jarvis_health()
        core_nexus_health = await self.check_core_nexus_health()
        
        # Test performance
        performance_test = await self.test_performance_simple()
        
        # Combine results
        health_check = {
            "timestamp": datetime.now().isoformat(),
            "jarvis": jarvis_health,
            "core_nexus": core_nexus_health,
            "performance": performance_test
        }
        
        # Store history
        self.health_history.append(health_check)
        if performance_test.get("success"):
            self.performance_history.append(performance_test)
        
        # Keep last 100 checks
        self.health_history = self.health_history[-100:]
        self.performance_history = self.performance_history[-50:]
        
        # Analyze and alert
        trends = self.analyze_health_trends()
        alerts = []
        
        # Check for alerts
        if jarvis_health["status"] != "healthy" and self.should_alert("service_down"):
            alert_sent = await self.send_alert("service_down", jarvis_health)
            alert_msg = self.generate_alert("service_down", jarvis_health)
            alerts.append(alert_msg)
            self.logger.error(f"{'📱 Alert sent' if alert_sent else '⚠️ Alert failed'}: {alert_msg}")
        
        if core_nexus_health["status"] != "healthy" and self.should_alert("core_nexus_down"):
            alert_sent = await self.send_alert("core_nexus_down", core_nexus_health)
            alert_msg = self.generate_alert("core_nexus_down", core_nexus_health)
            alerts.append(alert_msg)
            self.logger.error(f"{'📱 Alert sent' if alert_sent else '⚠️ Alert failed'}: {alert_msg}")
        
        if performance_test.get("success"):
            # Check iteration threshold
            if (performance_test["iterations"] > self.thresholds["max_iterations_simple"] and 
                self.should_alert("high_iterations")):
                details = {
                    "iterations": performance_test["iterations"],
                    "threshold": self.thresholds["max_iterations_simple"],
                    "task": "simple"
                }
                alert_sent = await self.send_alert("high_iterations", details)
                alert_msg = self.generate_alert("high_iterations", details)
                alerts.append(alert_msg)
                self.logger.warning(f"{'📱 Alert sent' if alert_sent else '⚠️ Alert failed'}: {alert_msg}")
            
            # Check duration threshold
            if (performance_test["duration"] > self.thresholds["max_duration_simple"] and 
                self.should_alert("slow_response")):
                details = {
                    "duration": performance_test["duration"],
                    "threshold": self.thresholds["max_duration_simple"],
                    "task": "simple"
                }
                alert_sent = await self.send_alert("slow_response", details)
                alert_msg = self.generate_alert("slow_response", details)
                alerts.append(alert_msg)
                self.logger.warning(f"{'📱 Alert sent' if alert_sent else '⚠️ Alert failed'}: {alert_msg}")
        
        # Check for performance regression alerts
        if trends.get("status") == "analyzed" and trends.get("regression_alerts"):
            for regression in trends["regression_alerts"]:
                if self.should_alert(f"regression_{regression['type']}", cooldown_minutes=60):  # Longer cooldown for regressions
                    alert_sent = await self.send_alert("performance_degraded", regression)
                    alert_msg = f"📉 PERFORMANCE REGRESSION DETECTED\n" \
                               f"Type: {regression['type']}\n" \
                               f"Historical Avg: {regression['historical_avg']:.2f}\n" \
                               f"Recent Avg: {regression['recent_avg']:.2f}\n" \
                               f"Increase: {regression['increase_pct']:.1f}%\n" \
                               f"Severity: {regression['severity']}\n" \
                               f"Timestamp: {datetime.now()}"
                    alerts.append(alert_msg)
                    self.logger.error(f"{'📱 Regression alert sent' if alert_sent else '⚠️ Regression alert failed'}: {alert_msg}")
        
        # Log status
        status = "✅ HEALTHY" if (jarvis_health["status"] == "healthy" and 
                                  core_nexus_health["status"] == "healthy") else "❌ UNHEALTHY"
        
        perf_info = ""
        if performance_test.get("success"):
            perf_info = f" | Performance: {performance_test['iterations']} iterations, {performance_test['duration']:.1f}s"
        
        self.logger.info(f"{status}{perf_info}")
        
        health_check["trends"] = trends
        health_check["alerts"] = alerts
        
        return health_check
    
    async def run_continuous_monitoring(self):
        """Run continuous health monitoring"""
        self.logger.info(f"🚨 JARVIS Health Monitor Started")
        self.logger.info(f"📊 Check interval: {self.check_interval} seconds")
        self.logger.info(f"🎯 Thresholds: {self.thresholds}")
        
        while True:
            try:
                await self.run_health_check_cycle()
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.logger.info("Health monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Health check cycle failed: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

async def main():
    """Main monitoring function"""
    monitor = JarvisHealthMonitor()
    await monitor.run_continuous_monitoring()

if __name__ == "__main__":
    asyncio.run(main())