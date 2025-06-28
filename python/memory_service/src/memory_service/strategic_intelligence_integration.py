"""
Strategic Intelligence Integration for Memory Service

This module provides integration between the memory service and JARVIS strategic intelligence
processing capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
import httpx
from dataclasses import dataclass

from .config import config
from .logging_config import get_logger

logger = get_logger("strategic_intelligence_integration")

@dataclass
class StrategicAnalysisResult:
    """Result from strategic intelligence analysis"""
    success: bool
    analysis_id: str
    executive_summary: str
    domain_analyses: Dict[str, Any]
    confidence_assessment: Dict[str, Any]
    strategic_recommendations: List[str]
    implementation_plan: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    intelligence_sources: List[str]
    processing_time: float
    error: Optional[str] = None

class StrategicIntelligenceClient:
    """Client for JARVIS strategic intelligence services"""
    
    def __init__(self):
        self.logger = logger.bind(component="strategic_intelligence_client")
        
        # Use JARVIS configuration
        self.base_url = config.jarvis.URL.rstrip('/')
        self.timeout = max(config.jarvis.TIMEOUT, 60)  # Strategic analysis may take longer
        self.enabled = config.jarvis.ENABLED
        
        # Create HTTP client
        headers = {"Content-Type": "application/json"}
        if config.jarvis.API_KEY:
            headers["Authorization"] = f"Bearer {config.jarvis.API_KEY}"
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers
        )
        
        self.logger.info("Strategic Intelligence Client initialized",
                        url=self.base_url,
                        enabled=self.enabled,
                        timeout=self.timeout)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if strategic intelligence service is available"""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning("Strategic intelligence health check failed", error=str(e))
            return False
    
    async def process_strategic_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[StrategicAnalysisResult]:
        """
        Process a strategic query using JARVIS strategic intelligence
        
        Args:
            query: The strategic business question
            context: Additional context including memories and user information
            
        Returns:
            StrategicAnalysisResult or None if processing fails
        """
        if not self.enabled:
            self.logger.debug("Strategic intelligence processing disabled")
            return None
        
        try:
            start_time = time.time()
            
            # Prepare strategic intelligence request
            request_data = {
                "task": f"""
                STRATEGIC INTELLIGENCE ANALYSIS REQUEST
                
                Query: {query}
                
                Context: {context or "No additional context provided"}
                
                Instructions:
                Apply the Strategic Intelligence Orchestration Framework to provide comprehensive business analysis:
                
                1. QUERY DECOMPOSITION & DOMAIN ANALYSIS
                   - Identify the strategic domains relevant to this query
                   - Apply appropriate domain expert analysis (Financial, Market, Competitive, Regulatory)
                   
                2. INTELLIGENCE SYNTHESIS
                   - Synthesize insights across all relevant domains
                   - Identify strategic patterns and opportunities
                   - Assess risks and mitigation strategies
                   
                3. EXECUTIVE RECOMMENDATIONS
                   - Provide clear, actionable strategic recommendations
                   - Include implementation roadmap and timeline
                   - Assess confidence levels and key assumptions
                   
                4. DECISION FRAMEWORK
                   - Apply confidence scoring methodology
                   - Provide decision recommendations with risk assessment
                   - Suggest next steps and follow-up analysis
                
                Output Format: Structured executive brief with quantified confidence assessment.
                """,
                "context": {
                    "analysis_type": "strategic_intelligence",
                    "request_source": "memory_service",
                    "timestamp": time.time(),
                    **context if context else {}
                },
                "priority": "high"
            }
            
            self.logger.info("Sending strategic intelligence request",
                           query_preview=query[:100],
                           context_keys=list(context.keys()) if context else [])
            
            # Call JARVIS strategic intelligence endpoint
            response = await self.client.post(
                f"{self.base_url}/strategic-intelligence",
                json=request_data,
                timeout=self.timeout
            )
            
            # Handle case where strategic endpoint doesn't exist yet
            if response.status_code == 404:
                self.logger.info("Strategic intelligence endpoint not available, using tasks endpoint")
                # Fallback to standard tasks endpoint
                response = await self.client.post(
                    f"{self.base_url}/tasks",
                    json=request_data,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            result_data = response.json()
            
            processing_time = time.time() - start_time
            
            # Parse the strategic intelligence response
            strategic_result = self._parse_strategic_response(result_data, processing_time)
            
            self.logger.info("Strategic intelligence analysis completed",
                           analysis_id=strategic_result.analysis_id,
                           processing_time=processing_time,
                           success=strategic_result.success,
                           confidence=strategic_result.confidence_assessment.get("overall_confidence", 0))
            
            return strategic_result
            
        except httpx.TimeoutException:
            self.logger.error("Strategic intelligence analysis timed out",
                            timeout=self.timeout)
            return None
        except httpx.HTTPStatusError as e:
            self.logger.error("Strategic intelligence HTTP error",
                            status_code=e.response.status_code,
                            response_text=e.response.text[:500])
            return None
        except Exception as e:
            self.logger.error("Strategic intelligence analysis failed", error=str(e))
            return None
    
    def _parse_strategic_response(
        self, 
        result_data: Dict[str, Any], 
        processing_time: float
    ) -> StrategicAnalysisResult:
        """Parse JARVIS response into strategic analysis result"""
        try:
            success = result_data.get("success", False)
            task_id = result_data.get("task_id", f"strategic_{int(time.time())}")
            
            # Extract analysis content
            final_decision = result_data.get("final_decision", {})
            agent_outputs = result_data.get("agent_outputs", {})
            
            # Parse decision content
            decision_content = ""
            if isinstance(final_decision, dict):
                decision_content = final_decision.get("decision", "")
            elif isinstance(final_decision, str):
                decision_content = final_decision
            
            # Extract structured insights from agent outputs
            domain_analyses = {}
            for agent_type, output in agent_outputs.items():
                if isinstance(output, dict) and "analysis" in str(output):
                    domain_analyses[agent_type] = output
            
            # Extract recommendations from decision content
            recommendations = self._extract_recommendations(decision_content)
            
            # Generate confidence assessment
            confidence_assessment = self._generate_confidence_assessment(
                result_data, domain_analyses, success
            )
            
            # Extract implementation plan
            implementation_plan = self._extract_implementation_plan(decision_content)
            
            # Extract risk assessment
            risk_assessment = self._extract_risk_assessment(decision_content)
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                decision_content, recommendations, confidence_assessment
            )
            
            return StrategicAnalysisResult(
                success=success,
                analysis_id=task_id,
                executive_summary=executive_summary,
                domain_analyses=domain_analyses,
                confidence_assessment=confidence_assessment,
                strategic_recommendations=recommendations,
                implementation_plan=implementation_plan,
                risk_assessment=risk_assessment,
                intelligence_sources=["jarvis_strategic_intelligence"],
                processing_time=processing_time,
                error=result_data.get("error") if not success else None
            )
            
        except Exception as e:
            self.logger.error("Failed to parse strategic response", error=str(e))
            return StrategicAnalysisResult(
                success=False,
                analysis_id=f"error_{int(time.time())}",
                executive_summary=f"Analysis parsing failed: {str(e)}",
                domain_analyses={},
                confidence_assessment={"overall_confidence": 0},
                strategic_recommendations=[],
                implementation_plan={},
                risk_assessment={},
                intelligence_sources=[],
                processing_time=processing_time,
                error=str(e)
            )
    
    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract strategic recommendations from analysis content"""
        recommendations = []
        
        if not content:
            return recommendations
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or
                line.startswith(('•', '-', '*')) or
                'recommend' in line.lower() and len(line) > 20):
                recommendations.append(line)
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _extract_implementation_plan(self, content: str) -> Dict[str, Any]:
        """Extract implementation plan from analysis content"""
        plan = {
            "immediate_actions": [],
            "short_term": [],
            "long_term": [],
            "timeline": "TBD"
        }
        
        if not content:
            return plan
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.strip().lower()
            if 'immediate' in line_lower or 'next steps' in line_lower:
                current_section = "immediate_actions"
            elif 'short term' in line_lower or 'short-term' in line_lower:
                current_section = "short_term"
            elif 'long term' in line_lower or 'long-term' in line_lower:
                current_section = "long_term"
            elif current_section and (line.strip().startswith(('•', '-', '*')) or
                                    line.strip().startswith(('1.', '2.', '3.'))):
                plan[current_section].append(line.strip())
        
        return plan
    
    def _extract_risk_assessment(self, content: str) -> Dict[str, Any]:
        """Extract risk assessment from analysis content"""
        risks = {
            "high_risks": [],
            "medium_risks": [],
            "low_risks": [],
            "mitigation_strategies": []
        }
        
        if not content:
            return risks
        
        lines = content.split('\n')
        
        for line in lines:
            line_lower = line.strip().lower()
            if 'risk' in line_lower or 'threat' in line_lower:
                if 'high' in line_lower:
                    risks["high_risks"].append(line.strip())
                elif 'medium' in line_lower:
                    risks["medium_risks"].append(line.strip())
                elif 'low' in line_lower:
                    risks["low_risks"].append(line.strip())
            elif 'mitigation' in line_lower or 'mitigate' in line_lower:
                risks["mitigation_strategies"].append(line.strip())
        
        return risks
    
    def _generate_confidence_assessment(
        self, 
        result_data: Dict[str, Any], 
        domain_analyses: Dict[str, Any],
        success: bool
    ) -> Dict[str, Any]:
        """Generate confidence assessment for strategic analysis"""
        if not success:
            return {
                "overall_confidence": 0,
                "decision_recommendation": "DO NOT PROCEED",
                "risk_management": "Analysis failed",
                "data_quality": 0,
                "market_certainty": 0,
                "competitive_predictability": 0,
                "financial_reliability": 0,
                "execution_feasibility": 0
            }
        
        # Simple confidence scoring based on available data
        base_confidence = 60.0  # Base confidence for successful analysis
        
        # Boost for multiple domain analyses
        domain_boost = min(20.0, len(domain_analyses) * 5.0)
        
        # Boost for detailed outputs
        output_quality = 0
        if result_data.get("agent_outputs"):
            output_quality = min(15.0, len(result_data["agent_outputs"]) * 3.0)
        
        # Calculate overall confidence
        overall_confidence = base_confidence + domain_boost + output_quality
        overall_confidence = min(95.0, overall_confidence)  # Cap at 95%
        
        # Determine decision recommendation
        if overall_confidence >= 80:
            decision = "PROCEED"
            risk_level = "Standard risk monitoring"
        elif overall_confidence >= 65:
            decision = "PROCEED WITH CAUTION"
            risk_level = "Enhanced risk tracking"
        elif overall_confidence >= 50:
            decision = "CONDITIONAL PROCEED"
            risk_level = "Active risk mitigation"
        else:
            decision = "DEFER"
            risk_level = "Additional analysis required"
        
        return {
            "overall_confidence": overall_confidence,
            "decision_recommendation": decision,
            "risk_management": risk_level,
            "data_quality": min(90.0, base_confidence + output_quality),
            "market_certainty": min(85.0, base_confidence + domain_boost),
            "competitive_predictability": min(80.0, base_confidence + (domain_boost / 2)),
            "financial_reliability": min(85.0, base_confidence + output_quality),
            "execution_feasibility": min(75.0, base_confidence + (output_quality / 2))
        }
    
    def _generate_executive_summary(
        self, 
        decision_content: str, 
        recommendations: List[str],
        confidence_assessment: Dict[str, Any]
    ) -> str:
        """Generate executive summary from analysis results"""
        confidence = confidence_assessment.get("overall_confidence", 0)
        decision = confidence_assessment.get("decision_recommendation", "DEFER")
        
        summary = f"""
# Strategic Intelligence Executive Summary

## Key Decision
**Recommendation**: {decision}
**Confidence Level**: {confidence:.1f}%

## Strategic Analysis Overview
{decision_content[:300] + '...' if len(decision_content) > 300 else decision_content}

## Top Strategic Recommendations
"""
        
        for i, rec in enumerate(recommendations[:3], 1):
            summary += f"\n{i}. {rec}"
        
        summary += f"""

## Risk Assessment
**Risk Management Level**: {confidence_assessment.get("risk_management", "Standard monitoring")}

## Next Steps
- Review detailed analysis and validate key assumptions
- Proceed based on {decision.lower()} recommendation
- Monitor implementation progress and market conditions

*Analysis generated by JARVIS Strategic Intelligence*
"""
        
        return summary.strip()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global client instance
_strategic_client: Optional[StrategicIntelligenceClient] = None

async def get_strategic_client() -> StrategicIntelligenceClient:
    """Get the global strategic intelligence client instance"""
    global _strategic_client
    if _strategic_client is None:
        _strategic_client = StrategicIntelligenceClient()
    return _strategic_client

async def cleanup_strategic_client():
    """Cleanup the global strategic intelligence client"""
    global _strategic_client
    if _strategic_client is not None:
        await _strategic_client.close()
        _strategic_client = None

# Main entry point for strategic query processing
async def process_strategic_query(
    query: str, 
    context: Optional[Dict[str, Any]] = None
) -> Optional[StrategicAnalysisResult]:
    """
    Process a strategic query using JARVIS strategic intelligence
    
    Args:
        query: The strategic business question
        context: Additional context including memories and user information
        
    Returns:
        StrategicAnalysisResult or None if processing fails
    """
    client = await get_strategic_client()
    return await client.process_strategic_query(query, context)