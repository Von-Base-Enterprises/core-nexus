#!/usr/bin/env python3
"""
Web-based Monitoring Dashboard for Core Nexus PGVector Optimization System

Provides a real-time web interface for monitoring PostgreSQL vector performance.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Core Nexus Performance Dashboard", version="1.0.0")

# Database connection
DB_PATH = "monitoring_dashboard.db"

class WebDashboard:
    """Web dashboard for performance monitoring"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect_websocket(self, websocket: WebSocket):
        """Connect new WebSocket client"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")
    
    def disconnect_websocket(self, websocket: WebSocket):
        """Disconnect WebSocket client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")
    
    async def broadcast_data(self, data: Dict[str, Any]):
        """Broadcast data to all connected WebSocket clients"""
        if not self.active_connections:
            return
            
        message = json.dumps(data, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect_websocket(connection)

# Global dashboard instance
dashboard = WebDashboard()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Core Nexus Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-left: 10px;
        }
        
        .status-healthy { background-color: #4CAF50; }
        .status-warning { background-color: #FF9800; }
        .status-critical { background-color: #F44336; }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
        }
        
        .metric-title {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .metric-unit {
            font-size: 0.8rem;
            color: #888;
        }
        
        .metric-trend {
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }
        
        .trend-up { color: #4CAF50; }
        .trend-down { color: #F44336; }
        .trend-stable { color: #666; }
        
        .chart-container {
            grid-column: span 2;
            height: 300px;
            position: relative;
        }
        
        .alerts-panel {
            grid-column: span 1;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .alert-item {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            border-left: 4px solid;
        }
        
        .alert-critical {
            background-color: #ffebee;
            border-left-color: #F44336;
        }
        
        .alert-warning {
            background-color: #fff3e0;
            border-left-color: #FF9800;
        }
        
        .alert-info {
            background-color: #e3f2fd;
            border-left-color: #2196F3;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .connected {
            background-color: #4CAF50;
            color: white;
        }
        
        .disconnected {
            background-color: #F44336;
            color: white;
        }
        
        @media (max-width: 768px) {
            .chart-container {
                grid-column: span 1;
            }
            
            .dashboard {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Core Nexus Performance Dashboard <span id="status-indicator" class="status-indicator status-healthy"></span></h1>
        <div id="connection-status" class="connection-status connected">Connected</div>
    </div>
    
    <div class="dashboard">
        <!-- Performance Metrics -->
        <div class="metric-card">
            <div class="metric-title">P95 Latency</div>
            <div class="metric-value" id="p95-latency">--</div>
            <div class="metric-unit">milliseconds</div>
            <div class="metric-trend" id="p95-trend">--</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Throughput</div>
            <div class="metric-value" id="throughput">--</div>
            <div class="metric-unit">queries per second</div>
            <div class="metric-trend" id="throughput-trend">--</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Error Rate</div>
            <div class="metric-value" id="error-rate">--</div>
            <div class="metric-unit">percentage</div>
            <div class="metric-trend" id="error-trend">--</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Active Connections</div>
            <div class="metric-value" id="connections">--</div>
            <div class="metric-unit">connections</div>
            <div class="metric-trend" id="connections-trend">--</div>
        </div>
        
        <!-- Performance Chart -->
        <div class="metric-card chart-container">
            <div class="metric-title">Performance History</div>
            <canvas id="performance-chart"></canvas>
        </div>
        
        <!-- Alerts Panel -->
        <div class="metric-card alerts-panel">
            <div class="metric-title">Recent Alerts</div>
            <div id="alerts-container">
                <p style="color: #666; font-style: italic;">No recent alerts</p>
            </div>
        </div>
    </div>
    
    <script>
        // WebSocket connection
        let ws;
        let performanceData = [];
        let performanceChart;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function(event) {
                console.log('WebSocket connected');
                document.getElementById('connection-status').textContent = 'Connected';
                document.getElementById('connection-status').className = 'connection-status connected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket disconnected');
                document.getElementById('connection-status').textContent = 'Disconnected';
                document.getElementById('connection-status').className = 'connection-status disconnected';
                
                // Attempt to reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateDashboard(data) {
            if (data.type === 'performance_update') {
                updatePerformanceMetrics(data.data);
                updatePerformanceChart(data.data);
            } else if (data.type === 'alert') {
                addAlert(data.data);
            }
        }
        
        function updatePerformanceMetrics(data) {
            // Update P95 latency
            document.getElementById('p95-latency').textContent = data.p95_latency_ms?.toFixed(1) || '--';
            updateTrend('p95-trend', data.p95_latency_ms, 25);
            
            // Update throughput
            document.getElementById('throughput').textContent = data.throughput_qps?.toFixed(1) || '--';
            updateTrend('throughput-trend', data.throughput_qps, 100, true);
            
            // Update error rate
            const errorRate = data.error_rate ? (data.error_rate * 100).toFixed(2) : '--';
            document.getElementById('error-rate').textContent = errorRate;
            updateTrend('error-trend', data.error_rate, 0.05);
            
            // Update connections
            document.getElementById('connections').textContent = data.connection_count || '--';
            
            // Update status indicator
            updateStatusIndicator(data);
        }
        
        function updateTrend(elementId, value, threshold, higherIsBetter = false) {
            const element = document.getElementById(elementId);
            if (!value) {
                element.textContent = '--';
                element.className = 'metric-trend trend-stable';
                return;
            }
            
            let className, text;
            if (higherIsBetter) {
                if (value >= threshold) {
                    className = 'trend-up';
                    text = '↗ Above target';
                } else {
                    className = 'trend-down';
                    text = '↘ Below target';
                }
            } else {
                if (value <= threshold) {
                    className = 'trend-up';
                    text = '↗ Within target';
                } else {
                    className = 'trend-down';
                    text = '↘ Above target';
                }
            }
            
            element.textContent = text;
            element.className = `metric-trend ${className}`;
        }
        
        function updateStatusIndicator(data) {
            const indicator = document.getElementById('status-indicator');
            const p95 = data.p95_latency_ms || 0;
            const throughput = data.throughput_qps || 0;
            const errorRate = data.error_rate || 0;
            
            if (p95 > 50 || throughput < 50 || errorRate > 0.1) {
                indicator.className = 'status-indicator status-critical';
            } else if (p95 > 25 || throughput < 100 || errorRate > 0.05) {
                indicator.className = 'status-indicator status-warning';
            } else {
                indicator.className = 'status-indicator status-healthy';
            }
        }
        
        function updatePerformanceChart(data) {
            const now = new Date();
            
            // Add new data point
            performanceData.push({
                time: now,
                p95_latency: data.p95_latency_ms || 0,
                throughput: data.throughput_qps || 0
            });
            
            // Keep only last 50 data points
            if (performanceData.length > 50) {
                performanceData.shift();
            }
            
            // Update chart
            if (performanceChart) {
                performanceChart.data.labels = performanceData.map(d => 
                    d.time.toLocaleTimeString()
                );
                performanceChart.data.datasets[0].data = performanceData.map(d => d.p95_latency);
                performanceChart.data.datasets[1].data = performanceData.map(d => d.throughput);
                performanceChart.update();
            }
        }
        
        function addAlert(alert) {
            const container = document.getElementById('alerts-container');
            
            // Remove "no alerts" message
            if (container.children.length === 1 && container.firstElementChild.tagName === 'P') {
                container.innerHTML = '';
            }
            
            const alertElement = document.createElement('div');
            alertElement.className = `alert-item alert-${alert.severity}`;
            alertElement.innerHTML = `
                <strong>${alert.severity.toUpperCase()}</strong>
                <div>${alert.message}</div>
                <small>${new Date().toLocaleTimeString()}</small>
            `;
            
            container.insertBefore(alertElement, container.firstChild);
            
            // Keep only last 10 alerts
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        
        function initializeChart() {
            const ctx = document.getElementById('performance-chart').getContext('2d');
            
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'P95 Latency (ms)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    }, {
                        label: 'Throughput (QPS)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Latency (ms)'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Throughput (QPS)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            },
                        }
                    },
                    plugins: {
                        legend: {
                            display: true
                        }
                    }
                }
            });
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeChart();
            connectWebSocket();
        });
    </script>
</body>
</html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await dashboard.connect_websocket(websocket)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        dashboard.disconnect_websocket(websocket)

@app.get("/api/performance/current")
async def get_current_performance():
    """Get current performance metrics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM performance_snapshots 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="No performance data found")
        
        # Map to column names
        columns = [
            'id', 'timestamp', 'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
            'avg_latency_ms', 'max_latency_ms', 'throughput_qps', 'concurrent_qps',
            'error_rate', 'connection_count', 'cpu_usage', 'memory_usage_mb'
        ]
        
        return dict(zip(columns, result))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance/history")
async def get_performance_history(hours: int = 24):
    """Get performance history for specified hours"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        since_timestamp = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT timestamp, p95_latency_ms, throughput_qps, error_rate
            FROM performance_snapshots 
            WHERE timestamp > ?
            ORDER BY timestamp
        ''', (since_timestamp,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "p95_latency_ms": row[1],
                "throughput_qps": row[2],
                "error_rate": row[3]
            }
            for row in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/recent")
async def get_recent_alerts(hours: int = 24):
    """Get recent alerts"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        since_timestamp = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT timestamp, alert_type, severity, metric, value, threshold, message
            FROM alerts 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (since_timestamp,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "alert_type": row[1],
                "severity": row[2],
                "metric": row[3],
                "value": row[4],
                "threshold": row[5],
                "message": row[6]
            }
            for row in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Background task to broadcast real-time updates
async def broadcast_performance_updates():
    """Background task to broadcast performance updates to WebSocket clients"""
    while True:
        try:
            # Get latest performance data
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM performance_snapshots 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                columns = [
                    'id', 'timestamp', 'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
                    'avg_latency_ms', 'max_latency_ms', 'throughput_qps', 'concurrent_qps',
                    'error_rate', 'connection_count', 'cpu_usage', 'memory_usage_mb'
                ]
                
                data = dict(zip(columns, result))
                
                await dashboard.broadcast_data({
                    "type": "performance_update",
                    "data": data
                })
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
            await asyncio.sleep(30)  # Wait longer on error

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    asyncio.create_task(broadcast_performance_updates())

if __name__ == "__main__":
    # Run the web dashboard
    uvicorn.run(
        "web_dashboard:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )