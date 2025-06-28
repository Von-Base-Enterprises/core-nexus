"""
Enhanced Query Processor for Memory Service

This module provides advanced query processing capabilities that integrate strategic intelligence
with the existing memory service query functionality.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import re

from .models import QueryRequest, QueryResponse, MemoryResponse
from .jarvis_client import get_jarvis_client, JarvisAnalysisResult
from .config import config
from .logging_config import get_logger
from .circuit_breaker import (
    call_with_strategic_circuit,
    call_with_reasoning_circuit,
    call_with_jarvis_circuit,
    get_system_health
)

logger = get_logger("enhanced_query_processor")

@dataclass
class EnhancedQueryResult:
    """Enhanced query result with strategic intelligence"""
    base_response: QueryResponse
    strategic_analysis: Optional[Dict[str, Any]] = None
    reasoning_analysis: Optional[Dict[str, Any]] = None
    query_classification: str = "standard"
    processing_metadata: Dict[str, Any] = None
    confidence_assessment: Optional[Dict[str, Any]] = None

class QueryClassifier:
    """Classifies queries to determine appropriate processing strategy"""
    
    # Strategic intelligence indicators
    STRATEGIC_PATTERNS = [
        # Market analysis patterns
        r'\b(market\s+analysis|market\s+research|competitive\s+landscape)\b',
        r'\b(market\s+size|market\s+opportunity|target\s+market)\b',
        r'\b(industry\s+trends|market\s+trends|growth\s+potential)\b',
        
        # Investment and financial patterns
        r'\b(investment\s+analysis|roi\s+analysis|financial\s+modeling)\b',
        r'\b(cost\s+benefit|budget\s+analysis|financial\s+projections)\b',
        r'\b(revenue\s+forecast|profit\s+analysis|valuation)\b',
        
        # Strategic planning patterns
        r'\b(strategic\s+plan|business\s+strategy|strategic\s+direction)\b',
        r'\b(market\s+entry|expansion\s+strategy|growth\s+strategy)\b',
        r'\b(strategic\s+options|strategic\s+recommendations)\b',
        
        # Competitive analysis patterns
        r'\b(competitive\s+analysis|competitor\s+research|competitive\s+advantage)\b',
        r'\b(market\s+positioning|differentiation\s+strategy)\b',
        r'\b(swot\s+analysis|competitive\s+threats)\b',
        
        # Risk assessment patterns
        r'\b(risk\s+assessment|risk\s+analysis|regulatory\s+compliance)\b',
        r'\b(threat\s+analysis|vulnerability\s+assessment)\b',
        r'\b(regulatory\s+impact|compliance\s+requirements)\b',
        
        # Executive decision patterns
        r'\b(should\s+we|what\s+if|decision\s+analysis)\b',
        r'\b(recommend|suggestion|advice|guidance)\b',
        r'\b(best\s+approach|optimal\s+strategy|next\s+steps)\b'
    ]
    
    # High-value query indicators (require enhanced processing)
    HIGH_VALUE_PATTERNS = [
        r'\b(analyze|assessment|evaluation|review)\b',
        r'\b(strategy|strategic|planning|forecast)\b',
        r'\b(market|competitive|financial|investment)\b',
        r'\b(opportunity|risk|threat|advantage)\b',
        r'\b(recommendation|decision|approach|solution)\b'
    ]
    
    # Simple query patterns (standard processing sufficient)
    SIMPLE_PATTERNS = [
        r'^\s*(what\s+is|who\s+is|when\s+did|where\s+is|how\s+to)\s+\w+\s*\??$',
        r'^\s*\w+\s+definition\s*\??$',
        r'^\s*(status|update|info|information)\s+\w+\s*$'
    ]
    
    @classmethod
    def classify_query(cls, query: str) -> Dict[str, Any]:
        """
        Classify a query to determine processing strategy
        
        Returns:
            Dict with classification results and metadata
        """
        if not query or not query.strip():
            return {
                "classification": "empty",
                "strategic_intelligence_needed": False,
                "enhanced_reasoning_needed": False,
                "confidence": 1.0,
                "rationale": "Empty query"
            }
        
        query_lower = query.lower()
        
        # Check for strategic patterns
        strategic_matches = []
        for pattern in cls.STRATEGIC_PATTERNS:
            if re.search(pattern, query_lower):
                strategic_matches.append(pattern)
        
        # Check for high-value patterns
        high_value_matches = []
        for pattern in cls.HIGH_VALUE_PATTERNS:
            if re.search(pattern, query_lower):
                high_value_matches.append(pattern)
        
        # Check for simple patterns
        simple_matches = []
        for pattern in cls.SIMPLE_PATTERNS:
            if re.search(pattern, query_lower):
                simple_matches.append(pattern)
        
        # Determine classification
        if strategic_matches:
            classification = "strategic"
            strategic_intelligence_needed = True
            enhanced_reasoning_needed = True
            confidence = 0.9
            rationale = f"Strategic patterns detected: {len(strategic_matches)} matches"
        elif high_value_matches and not simple_matches:
            classification = "analytical"
            strategic_intelligence_needed = False
            enhanced_reasoning_needed = True
            confidence = 0.8
            rationale = f"High-value analytical query: {len(high_value_matches)} matches"
        elif simple_matches:
            classification = "simple"
            strategic_intelligence_needed = False
            enhanced_reasoning_needed = False
            confidence = 0.9
            rationale = f"Simple query pattern: {len(simple_matches)} matches"
        else:
            # Default to enhanced reasoning for unclassified queries
            classification = "standard"
            strategic_intelligence_needed = False
            enhanced_reasoning_needed = True
            confidence = 0.6
            rationale = "Standard query - applying enhanced reasoning"
        
        return {
            "classification": classification,
            "strategic_intelligence_needed": strategic_intelligence_needed,
            "enhanced_reasoning_needed": enhanced_reasoning_needed,
            "confidence": confidence,
            "rationale": rationale,
            "pattern_matches": {
                "strategic": len(strategic_matches),
                "high_value": len(high_value_matches),
                "simple": len(simple_matches)
            }
        }

class EnhancedQueryProcessor:
    """Enhanced query processor with strategic intelligence integration"""
    
    def __init__(self):
        self.logger = logger.bind(component="enhanced_query_processor")
        self.classifier = QueryClassifier()
        
        # Performance tracking
        self.processing_stats = {
            "total_queries": 0,
            "strategic_queries": 0,
            "enhanced_reasoning_queries": 0,
            "standard_queries": 0,
            "avg_processing_time": 0.0
        }
        
        self.logger.info("Enhanced Query Processor initialized")
    
    async def process_query(
        self, 
        request: QueryRequest, 
        base_response: QueryResponse
    ) -> EnhancedQueryResult:
        """
        Process a query with appropriate enhancement strategy
        
        Args:
            request: The original query request
            base_response: The base vector search response
            
        Returns:
            EnhancedQueryResult with appropriate enhancements
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing enhanced query: query_preview={request.query[:100] if request.query else 'empty'}, include_reasoning={request.include_reasoning}, memory_count={len(base_response.memories)}")
            
            # Update stats
            self.processing_stats["total_queries"] += 1
            
            # Classify the query
            classification = self.classifier.classify_query(request.query)
            
            self.logger.info(f"Query classified: classification={classification['classification']}, strategic_needed={classification['strategic_intelligence_needed']}, enhanced_reasoning={classification['enhanced_reasoning_needed']}, confidence={classification['confidence']}")
            
            # Initialize result
            result = EnhancedQueryResult(
                base_response=base_response,
                query_classification=classification["classification"],
                processing_metadata={
                    "classification": classification,
                    "processing_strategy": "determined",
                    "start_time": start_time
                }
            )
            
            # Apply appropriate processing strategy
            if not request.include_reasoning:
                # No reasoning requested - return base response only
                result.processing_metadata["strategy_applied"] = "base_only"
                self.processing_stats["standard_queries"] += 1
                
            elif classification["strategic_intelligence_needed"]:
                # Strategic intelligence processing
                result = await self._apply_strategic_intelligence(request, result)
                self.processing_stats["strategic_queries"] += 1
                
            elif classification["enhanced_reasoning_needed"]:
                # Enhanced reasoning processing
                result = await self._apply_enhanced_reasoning(request, result)
                self.processing_stats["enhanced_reasoning_queries"] += 1
                
            else:
                # Standard reasoning processing
                result = await self._apply_standard_reasoning(request, result)
                self.processing_stats["standard_queries"] += 1
            
            # Add processing metadata
            processing_time = time.time() - start_time
            result.processing_metadata.update({
                "processing_time_seconds": processing_time,
                "strategy_applied": result.processing_metadata.get("strategy_applied", "unknown"),
                "enhancement_success": result.strategic_analysis is not None or result.reasoning_analysis is not None
            })
            
            # Update average processing time
            self._update_processing_stats(processing_time)
            
            self.logger.info(f"Enhanced query processing completed: classification={classification['classification']}, processing_time={processing_time}, has_strategic_analysis={result.strategic_analysis is not None}, has_reasoning_analysis={result.reasoning_analysis is not None}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced query processing failed: query={request.query[:100] if request.query else 'empty'}, error={str(e)}")
            
            # Return base response with error metadata
            processing_time = time.time() - start_time
            return EnhancedQueryResult(
                base_response=base_response,
                query_classification="error",
                processing_metadata={
                    "processing_time_seconds": processing_time,
                    "strategy_applied": "error_fallback",
                    "error": str(e),
                    "enhancement_success": False
                }
            )
    
    async def _apply_strategic_intelligence(
        self, 
        request: QueryRequest, 
        result: EnhancedQueryResult
    ) -> EnhancedQueryResult:
        """Apply strategic intelligence processing"""
        try:
            self.logger.info("Applying strategic intelligence processing")
            
            # Import here to avoid circular dependencies
            from .strategic_intelligence_integration import process_strategic_query
            
            # Prepare strategic analysis context
            context = {
                "original_query": request.query,
                "retrieved_memories": [
                    {
                        "content": memory.content,
                        "importance_score": memory.importance_score,
                        "similarity_score": memory.similarity_score,
                        "metadata": memory.metadata
                    }
                    for memory in result.base_response.memories
                ],
                "total_memories_found": result.base_response.total_found,
                "user_context": {
                    "user_id": request.user_id,
                    "conversation_id": request.conversation_id
                }
            }
            
            # Process with strategic intelligence using circuit breaker protection
            strategic_result = await call_with_strategic_circuit(
                process_strategic_query, 
                request.query, 
                context
            )
            
            if strategic_result and strategic_result.success:
                result.strategic_analysis = {
                    "analysis_id": strategic_result.analysis_id,
                    "executive_summary": strategic_result.executive_summary,
                    "strategic_recommendations": strategic_result.strategic_recommendations,
                    "confidence_assessment": strategic_result.confidence_assessment,
                    "implementation_plan": strategic_result.implementation_plan,
                    "risk_assessment": strategic_result.risk_assessment,
                    "domain_analyses": strategic_result.domain_analyses,
                    "processing_time": strategic_result.processing_time,
                    "intelligence_sources": strategic_result.intelligence_sources
                }
                
                result.confidence_assessment = strategic_result.confidence_assessment
                result.processing_metadata["strategy_applied"] = "strategic_intelligence"
                
                self.logger.info(f"Strategic intelligence processing completed: analysis_id={strategic_result.analysis_id}, confidence={strategic_result.confidence_assessment.get('overall_confidence', 0)}, recommendations_count={len(strategic_result.strategic_recommendations)}")
            else:
                # Fallback to enhanced reasoning
                self.logger.warning("Strategic intelligence processing failed, falling back to enhanced reasoning")
                result = await self._apply_enhanced_reasoning(request, result)
                result.processing_metadata["fallback_applied"] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Strategic intelligence processing failed: error={str(e)}")
            # Fallback to enhanced reasoning
            result = await self._apply_enhanced_reasoning(request, result)
            result.processing_metadata["strategy_applied"] = "strategic_fallback_to_enhanced"
            result.processing_metadata["strategic_error"] = str(e)
            return result
    
    async def _apply_enhanced_reasoning(
        self, 
        request: QueryRequest, 
        result: EnhancedQueryResult
    ) -> EnhancedQueryResult:
        """Apply enhanced reasoning processing"""
        try:
            self.logger.info("Applying enhanced reasoning processing")
            
            # Get JARVIS client for enhanced reasoning
            jarvis_client = await get_jarvis_client()
            
            # Check JARVIS health
            if not await jarvis_client.health_check():
                self.logger.warning("JARVIS service unavailable for enhanced reasoning")
                result = await self._apply_standard_reasoning(request, result)
                result.processing_metadata["strategy_applied"] = "enhanced_fallback_to_standard"
                return result
            
            # Enhanced reasoning with additional context
            enhanced_context = {
                "analysis_type": "enhanced_reasoning",
                "query_classification": result.query_classification,
                "total_found": result.base_response.total_found,
                "providers_used": result.base_response.providers_used,
                "user_id": request.user_id,
                "conversation_id": request.conversation_id,
                "enhancement_instructions": """
                Provide enhanced analytical reasoning that goes beyond simple summarization:
                1. Identify key patterns and insights from the retrieved information
                2. Make logical connections between different pieces of information
                3. Provide actionable recommendations based on the analysis
                4. Assess the confidence level of your insights
                5. Suggest follow-up questions or areas for deeper investigation
                """
            }
            
            # Process with enhanced reasoning using circuit breaker protection
            analysis_result = await call_with_reasoning_circuit(
                jarvis_client.analyze_query_results,
                request.query,
                result.base_response.memories,
                enhanced_context
            )
            
            if analysis_result and analysis_result.success:
                result.reasoning_analysis = analysis_result.get_structured_analysis()
                result.reasoning_analysis["enhancement_type"] = "enhanced_reasoning"
                result.processing_metadata["strategy_applied"] = "enhanced_reasoning"
                
                self.logger.info(f"Enhanced reasoning processing completed: task_id={analysis_result.task_id}, duration={analysis_result.duration}")
            else:
                # Fallback to standard reasoning
                result = await self._apply_standard_reasoning(request, result)
                result.processing_metadata["strategy_applied"] = "enhanced_fallback_to_standard"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced reasoning processing failed: error={str(e)}")
            # Fallback to standard reasoning
            result = await self._apply_standard_reasoning(request, result)
            result.processing_metadata["strategy_applied"] = "enhanced_fallback_to_standard"
            result.processing_metadata["enhanced_error"] = str(e)
            return result
    
    async def _apply_standard_reasoning(
        self, 
        request: QueryRequest, 
        result: EnhancedQueryResult
    ) -> EnhancedQueryResult:
        """Apply standard reasoning processing"""
        try:
            self.logger.info("Applying standard reasoning processing")
            
            # Get JARVIS client for standard reasoning
            jarvis_client = await get_jarvis_client()
            
            # Check JARVIS health
            if not await jarvis_client.health_check():
                self.logger.warning("JARVIS service unavailable for standard reasoning")
                result.reasoning_analysis = {
                    "success": False,
                    "error": "JARVIS service unavailable"
                }
                result.processing_metadata["strategy_applied"] = "standard_reasoning_failed"
                return result
            
            # Standard reasoning context
            standard_context = {
                "total_found": result.base_response.total_found,
                "providers_used": result.base_response.providers_used,
                "user_id": request.user_id,
                "conversation_id": request.conversation_id
            }
            
            # Process with standard reasoning using circuit breaker protection
            analysis_result = await call_with_jarvis_circuit(
                jarvis_client.analyze_query_results,
                request.query,
                result.base_response.memories,
                standard_context
            )
            
            if analysis_result and analysis_result.success:
                result.reasoning_analysis = analysis_result.get_structured_analysis()
                result.reasoning_analysis["enhancement_type"] = "standard_reasoning"
                result.processing_metadata["strategy_applied"] = "standard_reasoning"
                
                self.logger.info(f"Standard reasoning processing completed: task_id={analysis_result.task_id}, duration={analysis_result.duration}")
            else:
                result.reasoning_analysis = {
                    "success": False,
                    "error": analysis_result.error if analysis_result else "No analysis result"
                }
                result.processing_metadata["strategy_applied"] = "standard_reasoning_failed"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Standard reasoning processing failed: error={str(e)}")
            result.reasoning_analysis = {
                "success": False,
                "error": f"Analysis error: {str(e)}"
            }
            result.processing_metadata["strategy_applied"] = "standard_reasoning_failed"
            result.processing_metadata["standard_error"] = str(e)
            return result
    
    def _update_processing_stats(self, processing_time: float):
        """Update processing statistics"""
        # Simple moving average for processing time
        current_avg = self.processing_stats["avg_processing_time"]
        total_queries = self.processing_stats["total_queries"]
        
        if total_queries == 1:
            self.processing_stats["avg_processing_time"] = processing_time
        else:
            # Weighted average with more weight on recent queries
            weight = min(0.1, 1.0 / total_queries)
            self.processing_stats["avg_processing_time"] = (
                current_avg * (1 - weight) + processing_time * weight
            )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        total = self.processing_stats["total_queries"]
        if total == 0:
            return self.processing_stats.copy()
        
        stats = self.processing_stats.copy()
        stats.update({
            "strategic_percentage": (stats["strategic_queries"] / total) * 100,
            "enhanced_reasoning_percentage": (stats["enhanced_reasoning_queries"] / total) * 100,
            "standard_percentage": (stats["standard_queries"] / total) * 100
        })
        
        return stats
    
    async def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health including circuit breaker status"""
        try:
            # Get circuit breaker health
            circuit_health = await get_system_health()
            
            # Combine with processing stats
            health_status = {
                "enhanced_query_processor": {
                    "processing_stats": self.get_processing_stats(),
                    "status": "HEALTHY" if self.processing_stats["total_queries"] > 0 else "INACTIVE"
                },
                "circuit_breakers": circuit_health,
                "overall_system_health": circuit_health.get("overall_status", "UNKNOWN"),
                "timestamp": time.time()
            }
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Failed to get system health status: error={str(e)}")
            return {
                "enhanced_query_processor": {"status": "ERROR", "error": str(e)},
                "circuit_breakers": {"status": "UNKNOWN"},
                "overall_system_health": "ERROR",
                "timestamp": time.time()
            }

# Global processor instance
_enhanced_processor: Optional[EnhancedQueryProcessor] = None

async def get_enhanced_processor() -> EnhancedQueryProcessor:
    """Get the global enhanced query processor instance"""
    global _enhanced_processor
    if _enhanced_processor is None:
        _enhanced_processor = EnhancedQueryProcessor()
    return _enhanced_processor

# Main entry point for API integration
async def process_enhanced_query(
    request: QueryRequest, 
    base_response: QueryResponse
) -> EnhancedQueryResult:
    """
    Main entry point for enhanced query processing
    
    Args:
        request: The original query request
        base_response: The base vector search response
        
    Returns:
        EnhancedQueryResult with appropriate enhancements
    """
    processor = await get_enhanced_processor()
    return await processor.process_query(request, base_response)

async def get_enhanced_query_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status for enhanced query processing
    
    Returns:
        Dict containing processor stats and circuit breaker health
    """
    processor = await get_enhanced_processor()
    return await processor.get_system_health_status()