"""
Self-Evolution Learning Engine for Core Nexus

This module implements continuous learning and self-improvement capabilities
for the strategic intelligence system.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import json
import hashlib

from .config import config
from .logging_config import get_logger
from .models import MemoryRequest, MemoryResponse

logger = get_logger("self_evolution_engine")

@dataclass
class LearningInsight:
    """Represents a learning insight for system evolution"""
    insight_id: str
    category: str  # strategic_pattern, query_optimization, domain_expertise, etc.
    content: str
    confidence_score: float
    evidence: Dict[str, Any]
    suggested_improvements: List[str]
    impact_assessment: str
    created_at: datetime
    applied: bool = False
    validation_score: Optional[float] = None

@dataclass
class EvolutionMetrics:
    """Metrics tracking system evolution progress"""
    total_insights_generated: int
    insights_applied: int
    strategic_query_improvement: float
    confidence_score_trend: float
    processing_time_improvement: float
    user_satisfaction_proxy: float
    last_evolution_cycle: datetime

class SelfEvolutionEngine:
    """
    Core engine for continuous learning and system evolution
    
    Analyzes patterns in strategic intelligence processing to identify
    opportunities for improvement and automatically evolves the system.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Learning configuration
        self.learning_enabled = getattr(config.features, 'self_evolution_enabled', True)
        self.insight_threshold = 0.7  # Minimum confidence for actionable insights
        self.evolution_cycle_hours = 24  # Run evolution analysis every 24 hours
        
        # Learning state
        self.insights_cache: List[LearningInsight] = []
        self.evolution_history: List[Dict[str, Any]] = []
        self.last_evolution_run: Optional[datetime] = None
        
        # Pattern tracking
        self.query_patterns: Dict[str, Any] = {}
        self.strategic_outcomes: List[Dict[str, Any]] = []
        self.confidence_trends: List[Tuple[datetime, float]] = []
        self.performance_metrics: List[Dict[str, Any]] = []
        
        self.logger.info(f"Self-Evolution Engine initialized: learning_enabled={self.learning_enabled}, insight_threshold={self.insight_threshold}, evolution_cycle_hours={self.evolution_cycle_hours}")
    
    async def record_strategic_analysis(
        self, 
        query: str,
        classification: Dict[str, Any],
        strategic_result: Optional[Dict[str, Any]],
        processing_metadata: Dict[str, Any]
    ):
        """Record strategic analysis results for learning"""
        if not self.learning_enabled:
            return
        
        try:
            # Create analysis record
            analysis_record = {
                "timestamp": datetime.now(timezone.utc),
                "query": query,
                "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
                "classification": classification,
                "strategic_result": strategic_result,
                "processing_metadata": processing_metadata,
                "confidence_score": strategic_result.get("confidence_assessment", {}).get("overall_confidence", 0) if strategic_result else 0,
                "processing_time": processing_metadata.get("processing_time_seconds", 0),
                "success": strategic_result is not None and strategic_result.get("success", False)
            }
            
            # Store for pattern analysis
            self.strategic_outcomes.append(analysis_record)
            
            # Track confidence trends
            confidence = analysis_record["confidence_score"]
            self.confidence_trends.append((analysis_record["timestamp"], confidence))
            
            # Track query patterns
            query_category = classification.get("classification", "unknown")
            if query_category not in self.query_patterns:
                self.query_patterns[query_category] = {
                    "count": 0,
                    "total_confidence": 0,
                    "total_processing_time": 0,
                    "success_rate": 0,
                    "common_patterns": []
                }
            
            pattern = self.query_patterns[query_category]
            pattern["count"] += 1
            pattern["total_confidence"] += confidence
            pattern["total_processing_time"] += analysis_record["processing_time"]
            if analysis_record["success"]:
                pattern["success_rate"] = (pattern["success_rate"] * (pattern["count"] - 1) + 1) / pattern["count"]
            else:
                pattern["success_rate"] = (pattern["success_rate"] * (pattern["count"] - 1)) / pattern["count"]
            
            # Limit data retention for performance
            if len(self.strategic_outcomes) > 1000:
                self.strategic_outcomes = self.strategic_outcomes[-800:]  # Keep last 800 records
            
            if len(self.confidence_trends) > 500:
                self.confidence_trends = self.confidence_trends[-400:]  # Keep last 400 records
            
            self.logger.debug("Strategic analysis recorded for learning",
                            query_category=query_category,
                            confidence=confidence,
                            success=analysis_record["success"])
            
        except Exception as e:
            self.logger.error("Failed to record strategic analysis", error=str(e))
    
    async def run_evolution_cycle(self) -> List[LearningInsight]:
        """Run a complete evolution cycle to generate learning insights"""
        if not self.learning_enabled:
            return []
        
        try:
            cycle_start = time.time()
            self.logger.info(f"Starting self-evolution cycle: outcomes_to_analyze={len(self.strategic_outcomes)}, query_patterns={len(self.query_patterns)}")
            
            insights = []
            
            # 1. Analyze strategic patterns
            pattern_insights = await self._analyze_strategic_patterns()
            insights.extend(pattern_insights)
            
            # 2. Analyze confidence trends
            confidence_insights = await self._analyze_confidence_trends()
            insights.extend(confidence_insights)
            
            # 3. Analyze performance trends
            performance_insights = await self._analyze_performance_trends()
            insights.extend(performance_insights)
            
            # 4. Analyze domain effectiveness
            domain_insights = await self._analyze_domain_effectiveness()
            insights.extend(domain_insights)
            
            # 5. Analyze query classification accuracy
            classification_insights = await self._analyze_classification_accuracy()
            insights.extend(classification_insights)
            
            # Filter high-quality insights
            actionable_insights = [
                insight for insight in insights 
                if insight.confidence_score >= self.insight_threshold
            ]
            
            # Store insights
            self.insights_cache.extend(actionable_insights)
            
            # Record evolution cycle
            cycle_time = time.time() - cycle_start
            evolution_record = {
                "timestamp": datetime.now(timezone.utc),
                "cycle_duration": cycle_time,
                "total_insights": len(insights),
                "actionable_insights": len(actionable_insights),
                "insights_by_category": self._categorize_insights(actionable_insights),
                "data_analyzed": {
                    "strategic_outcomes": len(self.strategic_outcomes),
                    "query_patterns": len(self.query_patterns),
                    "confidence_trends": len(self.confidence_trends)
                }
            }
            
            self.evolution_history.append(evolution_record)
            self.last_evolution_run = datetime.now(timezone.utc)
            
            # Store evolution insights in memory
            await self._store_evolution_insights(actionable_insights)
            
            self.logger.info(f"Self-evolution cycle completed: cycle_duration={cycle_time}, total_insights={len(insights)}, actionable_insights={len(actionable_insights)}")
            
            return actionable_insights
            
        except Exception as e:
            self.logger.error("Evolution cycle failed", error=str(e))
            return []
    
    async def _analyze_strategic_patterns(self) -> List[LearningInsight]:
        """Analyze patterns in strategic query handling"""
        insights = []
        
        try:
            if len(self.strategic_outcomes) < 10:  # Need minimum data
                return insights
            
            # Analyze recent outcomes (last 50)
            recent_outcomes = self.strategic_outcomes[-50:]
            
            # Pattern 1: Query categories with low success rates
            category_performance = {}
            for outcome in recent_outcomes:
                category = outcome["classification"].get("classification", "unknown")
                if category not in category_performance:
                    category_performance[category] = {"success": 0, "total": 0, "avg_confidence": 0}
                
                perf = category_performance[category]
                perf["total"] += 1
                if outcome["success"]:
                    perf["success"] += 1
                perf["avg_confidence"] += outcome["confidence_score"]
            
            # Calculate success rates
            for category, perf in category_performance.items():
                success_rate = perf["success"] / perf["total"]
                avg_confidence = perf["avg_confidence"] / perf["total"]
                
                if success_rate < 0.7 and perf["total"] >= 5:  # Low success rate with sufficient data
                    insight = LearningInsight(
                        insight_id=f"pattern_lowsuccess_{category}_{int(time.time())}",
                        category="strategic_pattern",
                        content=f"Query category '{category}' shows low success rate ({success_rate:.2f}) with average confidence {avg_confidence:.1f}%",
                        confidence_score=0.8,
                        evidence={
                            "category": category,
                            "success_rate": success_rate,
                            "avg_confidence": avg_confidence,
                            "sample_size": perf["total"]
                        },
                        suggested_improvements=[
                            f"Enhance {category} query processing with additional domain experts",
                            f"Improve prompt engineering for {category} queries",
                            f"Add specialized validation for {category} strategic analysis"
                        ],
                        impact_assessment=f"Could improve {category} query success rate by 15-25%",
                        created_at=datetime.now(timezone.utc)
                    )
                    insights.append(insight)
            
            # Pattern 2: Processing time anomalies
            processing_times = [outcome["processing_time"] for outcome in recent_outcomes]
            avg_processing_time = sum(processing_times) / len(processing_times)
            
            slow_queries = [
                outcome for outcome in recent_outcomes 
                if outcome["processing_time"] > avg_processing_time * 2
            ]
            
            if len(slow_queries) > len(recent_outcomes) * 0.1:  # More than 10% are slow
                insight = LearningInsight(
                    insight_id=f"pattern_slowqueries_{int(time.time())}",
                    category="performance_optimization",
                    content=f"Detected {len(slow_queries)} slow queries ({len(slow_queries)/len(recent_outcomes)*100:.1f}%) exceeding 2x average processing time ({avg_processing_time:.2f}s)",
                    confidence_score=0.85,
                    evidence={
                        "slow_query_count": len(slow_queries),
                        "percentage": len(slow_queries)/len(recent_outcomes)*100,
                        "avg_processing_time": avg_processing_time,
                        "slow_query_samples": [
                            {
                                "query": outcome["query"][:50] + "...",
                                "processing_time": outcome["processing_time"],
                                "classification": outcome["classification"]["classification"]
                            }
                            for outcome in slow_queries[:3]
                        ]
                    },
                    suggested_improvements=[
                        "Implement query complexity pre-analysis to route complex queries differently",
                        "Add query caching for similar strategic patterns",
                        "Optimize domain expert parallel processing",
                        "Implement progressive analysis with early termination for simple strategic queries"
                    ],
                    impact_assessment="Could reduce average processing time by 20-30%",
                    created_at=datetime.now(timezone.utc)
                )
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error("Failed to analyze strategic patterns", error=str(e))
            return []
    
    async def _analyze_confidence_trends(self) -> List[LearningInsight]:
        """Analyze trends in confidence scoring"""
        insights = []
        
        try:
            if len(self.confidence_trends) < 20:
                return insights
            
            # Analyze confidence trend over time
            recent_trends = self.confidence_trends[-30:]  # Last 30 measurements
            older_trends = self.confidence_trends[-60:-30] if len(self.confidence_trends) >= 60 else []
            
            if older_trends:
                recent_avg = sum(conf for _, conf in recent_trends) / len(recent_trends)
                older_avg = sum(conf for _, conf in older_trends) / len(older_trends)
                
                confidence_change = recent_avg - older_avg
                
                if confidence_change < -5:  # Significant confidence drop
                    insight = LearningInsight(
                        insight_id=f"confidence_declining_{int(time.time())}",
                        category="confidence_optimization",
                        content=f"Confidence scores declining: {confidence_change:.1f}% drop from {older_avg:.1f}% to {recent_avg:.1f}%",
                        confidence_score=0.9,
                        evidence={
                            "recent_avg_confidence": recent_avg,
                            "older_avg_confidence": older_avg,
                            "confidence_change": confidence_change,
                            "sample_size": len(recent_trends)
                        },
                        suggested_improvements=[
                            "Review recent changes to strategic intelligence prompts",
                            "Analyze failing query patterns for prompt optimization",
                            "Enhance confidence scoring algorithm with additional factors",
                            "Implement confidence calibration based on outcome validation"
                        ],
                        impact_assessment="Could restore confidence scores to previous levels",
                        created_at=datetime.now(timezone.utc)
                    )
                    insights.append(insight)
                
                elif confidence_change > 5:  # Significant improvement
                    insight = LearningInsight(
                        insight_id=f"confidence_improving_{int(time.time())}",
                        category="success_pattern",
                        content=f"Confidence scores improving: {confidence_change:.1f}% increase from {older_avg:.1f}% to {recent_avg:.1f}%",
                        confidence_score=0.8,
                        evidence={
                            "recent_avg_confidence": recent_avg,
                            "older_avg_confidence": older_avg,
                            "confidence_change": confidence_change,
                            "sample_size": len(recent_trends)
                        },
                        suggested_improvements=[
                            "Identify and replicate successful patterns that led to improvement",
                            "Apply successful techniques to other query categories",
                            "Document best practices for strategic analysis"
                        ],
                        impact_assessment="Continue positive trend and apply learnings broadly",
                        created_at=datetime.now(timezone.utc)
                    )
                    insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error("Failed to analyze confidence trends", error=str(e))
            return []
    
    async def _analyze_performance_trends(self) -> List[LearningInsight]:
        """Analyze performance trends and optimization opportunities"""
        insights = []
        
        try:
            if len(self.strategic_outcomes) < 15:
                return insights
            
            # Analyze processing time trends
            recent_outcomes = self.strategic_outcomes[-20:]
            processing_times = [outcome["processing_time"] for outcome in recent_outcomes]
            
            avg_time = sum(processing_times) / len(processing_times)
            max_time = max(processing_times)
            min_time = min(processing_times)
            
            # Check for high variance in processing times
            variance = sum((t - avg_time) ** 2 for t in processing_times) / len(processing_times)
            std_dev = variance ** 0.5
            
            if std_dev > avg_time * 0.5:  # High variance indicates inconsistent performance
                insight = LearningInsight(
                    insight_id=f"performance_variance_{int(time.time())}",
                    category="performance_optimization",
                    content=f"High processing time variance detected: {std_dev:.2f}s std dev with {avg_time:.2f}s average (range: {min_time:.1f}s - {max_time:.1f}s)",
                    confidence_score=0.75,
                    evidence={
                        "avg_processing_time": avg_time,
                        "std_deviation": std_dev,
                        "min_time": min_time,
                        "max_time": max_time,
                        "variance_ratio": std_dev / avg_time
                    },
                    suggested_improvements=[
                        "Implement more consistent query routing logic",
                        "Add processing time prediction based on query complexity",
                        "Optimize domain expert parallel processing coordination",
                        "Add timeout controls for individual domain analyses"
                    ],
                    impact_assessment="Could reduce processing time variance by 40-60%",
                    created_at=datetime.now(timezone.utc)
                )
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error("Failed to analyze performance trends", error=str(e))
            return []
    
    async def _analyze_domain_effectiveness(self) -> List[LearningInsight]:
        """Analyze effectiveness of different domain experts"""
        insights = []
        
        try:
            # Analyze domain expert performance from strategic results
            domain_performance = {}
            
            for outcome in self.strategic_outcomes[-30:]:  # Last 30 strategic analyses
                if not outcome.get("strategic_result"):
                    continue
                
                domain_analyses = outcome["strategic_result"].get("domain_analyses", {})
                
                for domain, analysis in domain_analyses.items():
                    if domain not in domain_performance:
                        domain_performance[domain] = {
                            "total_analyses": 0,
                            "avg_confidence": 0,
                            "successful_analyses": 0
                        }
                    
                    perf = domain_performance[domain]
                    perf["total_analyses"] += 1
                    
                    domain_confidence = analysis.get("confidence", 0) if isinstance(analysis, dict) else 0
                    perf["avg_confidence"] += domain_confidence
                    
                    if domain_confidence > 0.6:  # Consider successful if confidence > 60%
                        perf["successful_analyses"] += 1
            
            # Calculate performance metrics
            for domain, perf in domain_performance.items():
                if perf["total_analyses"] >= 5:  # Need sufficient data
                    avg_confidence = perf["avg_confidence"] / perf["total_analyses"]
                    success_rate = perf["successful_analyses"] / perf["total_analyses"]
                    
                    if success_rate < 0.6:  # Low success rate
                        insight = LearningInsight(
                            insight_id=f"domain_lowperformance_{domain}_{int(time.time())}",
                            category="domain_optimization",
                            content=f"Domain expert '{domain}' showing low performance: {success_rate:.2f} success rate, {avg_confidence:.1f}% average confidence",
                            confidence_score=0.8,
                            evidence={
                                "domain": domain,
                                "success_rate": success_rate,
                                "avg_confidence": avg_confidence,
                                "total_analyses": perf["total_analyses"]
                            },
                            suggested_improvements=[
                                f"Enhance {domain} expert prompts with more specific guidance",
                                f"Add additional validation for {domain} analysis results",
                                f"Improve {domain} domain knowledge base",
                                f"Consider adding specialized sub-experts for {domain}"
                            ],
                            impact_assessment=f"Could improve {domain} analysis effectiveness by 20-30%",
                            created_at=datetime.now(timezone.utc)
                        )
                        insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error("Failed to analyze domain effectiveness", error=str(e))
            return []
    
    async def _analyze_classification_accuracy(self) -> List[LearningInsight]:
        """Analyze query classification accuracy and optimization opportunities"""
        insights = []
        
        try:
            # Analyze classification vs actual processing results
            classification_outcomes = {}
            
            for outcome in self.strategic_outcomes[-40:]:  # Last 40 outcomes
                classification = outcome["classification"]["classification"]
                strategic_needed = outcome["classification"]["strategic_intelligence_needed"]
                success = outcome["success"]
                confidence = outcome["confidence_score"]
                
                if classification not in classification_outcomes:
                    classification_outcomes[classification] = {
                        "total": 0,
                        "strategic_requests": 0,
                        "high_confidence_results": 0,
                        "successful_results": 0
                    }
                
                outcomes = classification_outcomes[classification]
                outcomes["total"] += 1
                
                if strategic_needed:
                    outcomes["strategic_requests"] += 1
                
                if confidence > 75:
                    outcomes["high_confidence_results"] += 1
                
                if success:
                    outcomes["successful_results"] += 1
            
            # Analyze classification effectiveness
            for classification, outcomes in classification_outcomes.items():
                if outcomes["total"] >= 5:  # Need sufficient data
                    strategic_rate = outcomes["strategic_requests"] / outcomes["total"]
                    confidence_rate = outcomes["high_confidence_results"] / outcomes["total"]
                    success_rate = outcomes["successful_results"] / outcomes["total"]
                    
                    # Check for misclassification patterns
                    if classification == "simple" and strategic_rate > 0.3:  # Simple queries getting strategic processing
                        insight = LearningInsight(
                            insight_id=f"classification_overprocessing_{int(time.time())}",
                            category="classification_optimization",
                            content=f"'Simple' queries getting strategic processing {strategic_rate:.1%} of the time - potential overprocessing",
                            confidence_score=0.7,
                            evidence={
                                "classification": classification,
                                "strategic_processing_rate": strategic_rate,
                                "sample_size": outcomes["total"]
                            },
                            suggested_improvements=[
                                "Refine simple query patterns to better identify truly simple queries",
                                "Add query complexity scoring to prevent overprocessing",
                                "Implement fast-path processing for clearly simple queries"
                            ],
                            impact_assessment="Could reduce unnecessary processing by 15-25%",
                            created_at=datetime.now(timezone.utc)
                        )
                        insights.append(insight)
                    
                    elif classification == "strategic" and confidence_rate < 0.5:  # Strategic queries with low confidence
                        insight = LearningInsight(
                            insight_id=f"classification_lowconfidence_{int(time.time())}",
                            category="strategic_optimization",
                            content=f"Strategic queries showing low confidence results {confidence_rate:.1%} of the time",
                            confidence_score=0.8,
                            evidence={
                                "classification": classification,
                                "high_confidence_rate": confidence_rate,
                                "sample_size": outcomes["total"]
                            },
                            suggested_improvements=[
                                "Enhance strategic analysis prompts for better reliability",
                                "Add additional domain experts for strategic queries",
                                "Improve strategic intelligence synthesis methodology",
                                "Add strategic query validation framework"
                            ],
                            impact_assessment="Could improve strategic analysis confidence by 20-30%",
                            created_at=datetime.now(timezone.utc)
                        )
                        insights.append(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error("Failed to analyze classification accuracy", error=str(e))
            return []
    
    def _categorize_insights(self, insights: List[LearningInsight]) -> Dict[str, int]:
        """Categorize insights by type for reporting"""
        categories = {}
        for insight in insights:
            category = insight.category
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    async def _store_evolution_insights(self, insights: List[LearningInsight]):
        """Store evolution insights in Core Nexus memory for persistence"""
        try:
            from .unified_store import get_unified_store
            
            store = await get_unified_store()
            
            for insight in insights:
                # Create memory entry for the insight
                memory_content = f"""
SELF-EVOLUTION INSIGHT: {insight.category.upper()}

{insight.content}

CONFIDENCE: {insight.confidence_score:.1%}
IMPACT: {insight.impact_assessment}

SUGGESTED IMPROVEMENTS:
{chr(10).join(f"- {improvement}" for improvement in insight.suggested_improvements)}

EVIDENCE:
{json.dumps(insight.evidence, indent=2)}

Generated: {insight.created_at.isoformat()}
"""
                
                memory_request = MemoryRequest(
                    content=memory_content,
                    importance_score=insight.confidence_score,
                    metadata={
                        "type": "self_evolution_insight",
                        "category": insight.category,
                        "insight_id": insight.insight_id,
                        "confidence_score": insight.confidence_score,
                        "impact_assessment": insight.impact_assessment,
                        "automated_learning": True,
                        "system_evolution": True
                    }
                )
                
                await store.store_memory(memory_request)
                
                self.logger.debug("Stored evolution insight in memory",
                                insight_id=insight.insight_id,
                                category=insight.category)
        
        except Exception as e:
            self.logger.error("Failed to store evolution insights", error=str(e))
    
    async def should_run_evolution_cycle(self) -> bool:
        """Check if it's time to run an evolution cycle"""
        if not self.learning_enabled:
            return False
        
        if self.last_evolution_run is None:
            return len(self.strategic_outcomes) >= 20  # Initial threshold
        
        time_since_last = datetime.now(timezone.utc) - self.last_evolution_run
        return time_since_last.total_seconds() >= (self.evolution_cycle_hours * 3600)
    
    def get_evolution_metrics(self) -> EvolutionMetrics:
        """Get current evolution metrics"""
        total_insights = len(self.insights_cache)
        applied_insights = len([i for i in self.insights_cache if i.applied])
        
        # Calculate confidence trend
        if len(self.confidence_trends) >= 2:
            recent_confidence = sum(conf for _, conf in self.confidence_trends[-10:]) / min(10, len(self.confidence_trends))
            older_confidence = sum(conf for _, conf in self.confidence_trends[-20:-10]) / min(10, len(self.confidence_trends) - 10)
            confidence_trend = recent_confidence - older_confidence if len(self.confidence_trends) >= 20 else 0
        else:
            confidence_trend = 0
        
        # Calculate processing time improvement
        if len(self.strategic_outcomes) >= 20:
            recent_times = [o["processing_time"] for o in self.strategic_outcomes[-10:]]
            older_times = [o["processing_time"] for o in self.strategic_outcomes[-20:-10]]
            recent_avg = sum(recent_times) / len(recent_times)
            older_avg = sum(older_times) / len(older_times)
            time_improvement = (older_avg - recent_avg) / older_avg * 100 if older_avg > 0 else 0
        else:
            time_improvement = 0
        
        # Proxy for user satisfaction (high confidence + success rate)
        if self.strategic_outcomes:
            recent_outcomes = self.strategic_outcomes[-20:]
            satisfaction = sum(
                o["confidence_score"] / 100 * (1 if o["success"] else 0.5)
                for o in recent_outcomes
            ) / len(recent_outcomes)
        else:
            satisfaction = 0
        
        return EvolutionMetrics(
            total_insights_generated=total_insights,
            insights_applied=applied_insights,
            strategic_query_improvement=0,  # Would need baseline measurement
            confidence_score_trend=confidence_trend,
            processing_time_improvement=time_improvement,
            user_satisfaction_proxy=satisfaction,
            last_evolution_cycle=self.last_evolution_run or datetime.now(timezone.utc)
        )
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """Get summary of current insights"""
        if not self.insights_cache:
            return {"message": "No insights generated yet"}
        
        by_category = {}
        for insight in self.insights_cache:
            category = insight.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append({
                "insight_id": insight.insight_id,
                "content": insight.content[:100] + "...",
                "confidence": insight.confidence_score,
                "applied": insight.applied
            })
        
        return {
            "total_insights": len(self.insights_cache),
            "applied_insights": len([i for i in self.insights_cache if i.applied]),
            "insights_by_category": by_category,
            "last_evolution_run": self.last_evolution_run.isoformat() if self.last_evolution_run else None
        }

# Global evolution engine instance
_evolution_engine: Optional[SelfEvolutionEngine] = None

async def get_evolution_engine() -> SelfEvolutionEngine:
    """Get the global self-evolution engine instance"""
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = SelfEvolutionEngine()
    return _evolution_engine

# Main entry points for integration
async def record_strategic_analysis_for_learning(
    query: str,
    classification: Dict[str, Any],
    strategic_result: Optional[Dict[str, Any]],
    processing_metadata: Dict[str, Any]
):
    """Record strategic analysis for learning (called from enhanced query processor)"""
    engine = await get_evolution_engine()
    await engine.record_strategic_analysis(query, classification, strategic_result, processing_metadata)

async def run_evolution_cycle_if_needed() -> Optional[List[LearningInsight]]:
    """Run evolution cycle if needed (called periodically)"""
    engine = await get_evolution_engine()
    if await engine.should_run_evolution_cycle():
        return await engine.run_evolution_cycle()
    return None

async def get_evolution_status() -> Dict[str, Any]:
    """Get current evolution status and metrics"""
    engine = await get_evolution_engine()
    metrics = engine.get_evolution_metrics()
    insights_summary = engine.get_insights_summary()
    
    return {
        "evolution_enabled": engine.learning_enabled,
        "metrics": asdict(metrics),
        "insights_summary": insights_summary,
        "should_run_cycle": await engine.should_run_evolution_cycle(),
        "data_points": {
            "strategic_outcomes": len(engine.strategic_outcomes),
            "confidence_trends": len(engine.confidence_trends),
            "query_patterns": len(engine.query_patterns)
        }
    }