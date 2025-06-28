"""
Strategic Intelligence Processor for JARVIS

This module integrates the strategic intelligence framework with JARVIS LangGraph architecture
to provide advanced reasoning and strategic analysis capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone
import structlog

from .prompts import (
    strategic_intelligence,
    get_strategic_prompt,
    analyze_strategic_query,
    build_analysis_workflow,
    generate_executive_report,
    calculate_confidence_score
)
from .gemini_integration import GeminiAgent, create_strategic_intelligence_agent
from .core_nexus_bridge import get_bridge
from .config import get_config

logger = structlog.get_logger(__name__)
config = get_config()

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

class StrategicIntelligenceProcessor:
    """
    Advanced strategic intelligence processor that integrates with JARVIS workflow
    """
    
    def __init__(self):
        self.logger = logger.bind(component="strategic_intelligence")
        
        # Initialize strategic intelligence agents
        self.strategic_agent = create_strategic_intelligence_agent()
        self.domain_agents = {}
        
        # Initialize domain expert agents
        for domain in ["financial", "market", "competitive", "regulatory"]:
            self.domain_agents[domain] = create_strategic_intelligence_agent(f"{domain}_expert")
        
        # Web search integration (will be configured based on available tools)
        self.web_search_enabled = hasattr(config, 'web_search_enabled') and config.web_search_enabled
        
        # Performance tracking
        self.analysis_cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        self.logger.info("Strategic Intelligence Processor initialized",
                        domain_agents=list(self.domain_agents.keys()),
                        web_search_enabled=self.web_search_enabled)
    
    async def process_strategic_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None,
        priority_domains: Optional[List[str]] = None,
        enable_web_search: bool = True
    ) -> StrategicAnalysisResult:
        """
        Process a strategic business query with comprehensive analysis
        
        Args:
            query: The strategic business question
            context: Additional context from memory service or user
            priority_domains: Optional list of domains to focus on
            enable_web_search: Whether to enable real-time web search
            
        Returns:
            StrategicAnalysisResult with comprehensive analysis
        """
        start_time = time.time()
        analysis_id = f"strategic_{int(time.time())}"
        
        try:
            self.logger.info("Processing strategic query",
                           query=query[:100],
                           analysis_id=analysis_id,
                           priority_domains=priority_domains)
            
            # Phase 1: Query Analysis & Decomposition
            query_analysis = analyze_strategic_query(query, priority_domains)
            workflow = build_analysis_workflow(query, priority_domains)
            
            self.logger.info("Query analysis completed",
                           detected_domains=query_analysis["detected_domains"],
                           workflow_steps=len(workflow["workflow_steps"]))
            
            # Phase 2: Strategic Orchestration
            orchestrator_result = await self._run_strategic_orchestrator(
                query, context, query_analysis
            )
            
            # Phase 3: Domain Expert Analysis
            domain_analyses = await self._run_domain_analyses(
                query, context, query_analysis["detected_domains"], enable_web_search
            )
            
            # Phase 4: Web Search Intelligence (if enabled)
            intelligence_sources = []
            if enable_web_search and self.web_search_enabled:
                web_intelligence = await self._gather_web_intelligence(
                    query, query_analysis["detected_domains"]
                )
                intelligence_sources = web_intelligence.get("sources", [])
            
            # Phase 5: Synthesis & Confidence Assessment
            synthesis_result = await self._synthesize_analyses(
                query, orchestrator_result, domain_analyses, context
            )
            
            # Phase 6: Confidence Scoring
            confidence_assessment = self._calculate_confidence_assessment(
                domain_analyses, intelligence_sources, synthesis_result
            )
            
            # Phase 7: Executive Report Generation
            executive_summary = self._generate_executive_summary(
                query, synthesis_result, confidence_assessment, domain_analyses
            )
            
            # Store strategic insights in memory
            await self._store_strategic_insights(
                analysis_id, query, synthesis_result, confidence_assessment
            )
            
            processing_time = time.time() - start_time
            
            result = StrategicAnalysisResult(
                success=True,
                analysis_id=analysis_id,
                executive_summary=executive_summary,
                domain_analyses=domain_analyses,
                confidence_assessment=confidence_assessment,
                strategic_recommendations=synthesis_result.get("recommendations", []),
                implementation_plan=synthesis_result.get("implementation_plan", {}),
                risk_assessment=synthesis_result.get("risk_assessment", {}),
                intelligence_sources=intelligence_sources,
                processing_time=processing_time
            )
            
            self.logger.info("Strategic analysis completed",
                           analysis_id=analysis_id,
                           processing_time=processing_time,
                           confidence=confidence_assessment.get("overall_confidence", 0),
                           recommendations_count=len(result.strategic_recommendations))
            
            return result
            
        except Exception as e:
            self.logger.error("Strategic analysis failed",
                            analysis_id=analysis_id,
                            query=query[:100],
                            error=str(e))
            
            return StrategicAnalysisResult(
                success=False,
                analysis_id=analysis_id,
                executive_summary=f"Strategic analysis failed: {str(e)}",
                domain_analyses={},
                confidence_assessment={"overall_confidence": 0},
                strategic_recommendations=[],
                implementation_plan={},
                risk_assessment={},
                intelligence_sources=[],
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _run_strategic_orchestrator(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        query_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run the master strategic orchestrator"""
        try:
            # Get master orchestrator prompt
            orchestrator_prompt = get_strategic_prompt("master_orchestrator")
            
            # Prepare context for orchestrator
            orchestration_context = f"""
            Strategic Query: {query}
            
            Query Analysis:
            - Detected Domains: {query_analysis["detected_domains"]}
            - Required Analysis: {query_analysis["required_prompts"]}
            - Web Search Needed: {query_analysis["web_search_needed"]}
            
            Additional Context:
            {context or "No additional context provided"}
            
            Instructions: Apply the Strategic Intelligence Orchestration Framework to decompose this query and prepare for multi-domain analysis.
            """
            
            # Use strategic agent with orchestrator prompt
            result = await self.strategic_agent.process_with_memory_context(
                f"{orchestrator_prompt}\n\n{orchestration_context}",
                f"strategic_orchestration_{query[:50]}"
            )
            
            return {
                "orchestration_decision": result.final_response,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning_steps,
                "decomposition": query_analysis
            }
            
        except Exception as e:
            self.logger.error("Strategic orchestrator failed", error=str(e))
            return {
                "orchestration_decision": f"Orchestration failed: {str(e)}",
                "confidence": 0.1,
                "reasoning": [],
                "decomposition": query_analysis
            }
    
    async def _run_domain_analyses(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        domains: List[str],
        enable_web_search: bool
    ) -> Dict[str, Any]:
        """Run domain expert analyses in parallel"""
        domain_results = {}
        
        # Create analysis tasks for each domain
        tasks = []
        for domain in domains:
            if domain in self.domain_agents:
                task = self._run_single_domain_analysis(
                    domain, query, context, enable_web_search
                )
                tasks.append((domain, task))
        
        # Execute domain analyses in parallel
        if tasks:
            domain_tasks = [task for _, task in tasks]
            domain_names = [domain for domain, _ in tasks]
            
            results = await asyncio.gather(*domain_tasks, return_exceptions=True)
            
            for domain, result in zip(domain_names, results):
                if isinstance(result, Exception):
                    self.logger.error(f"{domain} analysis failed", error=str(result))
                    domain_results[domain] = {
                        "error": str(result),
                        "confidence": 0.1,
                        "analysis": f"{domain} analysis failed"
                    }
                else:
                    domain_results[domain] = result
        
        return domain_results
    
    async def _run_single_domain_analysis(
        self, 
        domain: str, 
        query: str, 
        context: Optional[Dict[str, Any]],
        enable_web_search: bool
    ) -> Dict[str, Any]:
        """Run analysis for a single domain expert"""
        try:
            # Get domain expert prompt
            domain_prompt = get_strategic_prompt(f"{domain}_expert")
            
            # Prepare domain-specific context
            domain_context = f"""
            Strategic Query: {query}
            
            Domain Focus: {domain.title()} Analysis
            
            Additional Context:
            {context or "No additional context provided"}
            
            Web Search Available: {enable_web_search}
            
            Instructions: Apply your {domain} expertise to analyze this strategic question. Provide specific insights, metrics, and recommendations within your domain.
            """
            
            # Get domain agent
            agent = self.domain_agents[domain]
            
            # Process with domain expertise
            result = await agent.process_with_memory_context(
                f"{domain_prompt}\n\n{domain_context}",
                f"{domain}_analysis_{query[:50]}"
            )
            
            return {
                "domain": domain,
                "analysis": result.final_response,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning_steps,
                "key_insights": result.reasoning_steps[-3:] if len(result.reasoning_steps) > 3 else result.reasoning_steps
            }
            
        except Exception as e:
            self.logger.error(f"{domain} domain analysis failed", error=str(e))
            return {
                "domain": domain,
                "analysis": f"Analysis failed: {str(e)}",
                "confidence": 0.1,
                "reasoning": [],
                "key_insights": [],
                "error": str(e)
            }
    
    async def _gather_web_intelligence(
        self, 
        query: str, 
        domains: List[str]
    ) -> Dict[str, Any]:
        """Gather real-time web intelligence (placeholder for future implementation)"""
        # TODO: Integrate with actual web search capabilities
        # For now, return placeholder data
        
        return {
            "sources": [
                "market_intelligence_web_search",
                "competitive_analysis_web_search", 
                "financial_data_web_search",
                "regulatory_information_web_search"
            ],
            "intelligence": {
                "market_data": "Real-time market intelligence would be gathered here",
                "competitive_intel": "Current competitive landscape analysis",
                "financial_metrics": "Latest financial benchmarks and data",
                "regulatory_updates": "Recent regulatory changes and implications"
            },
            "search_strategy": f"Web search strategy for domains: {domains}"
        }
    
    async def _synthesize_analyses(
        self, 
        query: str, 
        orchestrator_result: Dict[str, Any], 
        domain_analyses: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synthesize all domain analyses into unified strategic insights"""
        try:
            # Prepare synthesis context
            synthesis_context = f"""
            Original Query: {query}
            
            Orchestrator Decision: {orchestrator_result.get("orchestration_decision", "")}
            
            Domain Analysis Results:
            """
            
            for domain, analysis in domain_analyses.items():
                if "error" not in analysis:
                    synthesis_context += f"\n{domain.title()} Analysis:\n{analysis.get('analysis', '')[:500]}...\n"
            
            synthesis_context += f"""
            
            Additional Context: {context or "None"}
            
            Instructions: Synthesize all domain analyses into unified strategic recommendations. Identify cross-domain patterns, strategic options, and implementation priorities.
            """
            
            # Use strategic agent for synthesis
            result = await self.strategic_agent.process_with_memory_context(
                synthesis_context,
                f"strategic_synthesis_{query[:50]}"
            )
            
            # Extract structured recommendations
            recommendations = self._extract_recommendations(result.final_response)
            implementation_plan = self._extract_implementation_plan(result.final_response)
            risk_assessment = self._extract_risk_assessment(result.final_response)
            
            return {
                "synthesis": result.final_response,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning_steps,
                "recommendations": recommendations,
                "implementation_plan": implementation_plan,
                "risk_assessment": risk_assessment
            }
            
        except Exception as e:
            self.logger.error("Synthesis failed", error=str(e))
            return {
                "synthesis": f"Synthesis failed: {str(e)}",
                "confidence": 0.1,
                "reasoning": [],
                "recommendations": [],
                "implementation_plan": {},
                "risk_assessment": {}
            }
    
    def _calculate_confidence_assessment(
        self, 
        domain_analyses: Dict[str, Any], 
        intelligence_sources: List[str],
        synthesis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive confidence assessment"""
        try:
            # Data quality based on domain analysis success
            successful_domains = [d for d in domain_analyses.values() if "error" not in d]
            data_quality = min(80.0, (len(successful_domains) / max(1, len(domain_analyses))) * 100)
            
            # Market certainty based on analysis confidence
            analysis_confidences = [
                d.get("confidence", 0) * 100 
                for d in domain_analyses.values() 
                if "error" not in d
            ]
            market_certainty = sum(analysis_confidences) / max(1, len(analysis_confidences)) if analysis_confidences else 50.0
            
            # Competitive predictability based on competitive analysis presence
            has_competitive = "competitive" in domain_analyses and "error" not in domain_analyses["competitive"]
            competitive_predictability = 80.0 if has_competitive else 60.0
            
            # Financial reliability based on financial analysis presence
            has_financial = "financial" in domain_analyses and "error" not in domain_analyses["financial"]
            financial_reliability = 85.0 if has_financial else 65.0
            
            # Execution feasibility based on synthesis quality
            synthesis_confidence = synthesis_result.get("confidence", 0.5) * 100
            execution_feasibility = min(90.0, synthesis_confidence)
            
            # Calculate overall confidence using framework
            confidence_scores = calculate_confidence_score(
                data_quality,
                market_certainty,
                competitive_predictability,
                financial_reliability,
                execution_feasibility
            )
            
            return {
                **confidence_scores,
                "intelligence_sources_count": len(intelligence_sources),
                "successful_domain_analyses": len(successful_domains),
                "total_domain_analyses": len(domain_analyses)
            }
            
        except Exception as e:
            self.logger.error("Confidence assessment failed", error=str(e))
            return {
                "overall_confidence": 50.0,
                "decision_recommendation": "DEFER",
                "risk_management": "Additional analysis required",
                "component_scores": {
                    "data_quality": 50.0,
                    "market_certainty": 50.0,
                    "competitive_predictability": 50.0,
                    "financial_reliability": 50.0,
                    "execution_feasibility": 50.0
                }
            }
    
    def _generate_executive_summary(
        self, 
        query: str, 
        synthesis_result: Dict[str, Any], 
        confidence_assessment: Dict[str, Any],
        domain_analyses: Dict[str, Any]
    ) -> str:
        """Generate executive summary using report templates"""
        try:
            # Prepare report data
            report_data = {
                "original_query": query,
                "analysis_scope": ", ".join(domain_analyses.keys()),
                "confidence_score": f"{confidence_assessment.get('overall_confidence', 0):.1f}",
                "decision_timeline": "Based on analysis complexity",
                "primary_recommendation": synthesis_result.get("synthesis", "")[:200] + "...",
                "supporting_rationale": "Multi-domain strategic analysis",
                "success_probability": f"{confidence_assessment.get('overall_confidence', 0):.1f}",
                "confidence_factors": "data quality, market analysis, domain expertise",
                "immediate_actions": "Review analysis and validate assumptions",
                "strategic_actions": "Implement recommended strategic initiatives",
                "longterm_actions": "Monitor and adapt strategy based on results",
                "report_timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_duration": "Real-time analysis completed"
            }
            
            # Generate executive report
            executive_summary = generate_executive_report(
                "executive_summary", 
                **report_data
            )
            
            return executive_summary
            
        except Exception as e:
            self.logger.error("Executive summary generation failed", error=str(e))
            return f"""
# Strategic Analysis Summary

**Query**: {query}

**Status**: Analysis completed with limitations due to processing error: {str(e)}

**Recommendation**: Review individual domain analyses for insights.

**Confidence**: Medium - Additional validation recommended

**Next Steps**: 
1. Validate key assumptions
2. Gather additional data where needed
3. Proceed with caution based on available analysis
"""
    
    def _extract_recommendations(self, synthesis_text: str) -> List[str]:
        """Extract strategic recommendations from synthesis text"""
        # Simple extraction - look for numbered lists or bullet points
        lines = synthesis_text.split('\n')
        recommendations = []
        
        for line in lines:
            line = line.strip()
            if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                line.startswith(('•', '-', '*')) or
                'recommend' in line.lower()):
                recommendations.append(line)
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _extract_implementation_plan(self, synthesis_text: str) -> Dict[str, Any]:
        """Extract implementation plan from synthesis text"""
        # Simple extraction - look for implementation-related content
        plan = {
            "immediate_actions": [],
            "short_term": [],
            "long_term": [],
            "resources_required": []
        }
        
        lines = synthesis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip().lower()
            if 'immediate' in line or 'urgent' in line:
                current_section = "immediate_actions"
            elif 'short' in line and 'term' in line:
                current_section = "short_term"
            elif 'long' in line and 'term' in line:
                current_section = "long_term"
            elif 'resource' in line or 'requirement' in line:
                current_section = "resources_required"
            elif current_section and (line.startswith(('•', '-', '*')) or 
                                    line.startswith(('1.', '2.', '3.'))):
                plan[current_section].append(line)
        
        return plan
    
    def _extract_risk_assessment(self, synthesis_text: str) -> Dict[str, Any]:
        """Extract risk assessment from synthesis text"""
        risk_assessment = {
            "high_risks": [],
            "medium_risks": [],
            "low_risks": [],
            "mitigation_strategies": []
        }
        
        lines = synthesis_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'risk' in line.lower() or 'threat' in line.lower():
                if 'high' in line.lower():
                    risk_assessment["high_risks"].append(line)
                elif 'medium' in line.lower():
                    risk_assessment["medium_risks"].append(line)
                elif 'low' in line.lower():
                    risk_assessment["low_risks"].append(line)
                elif 'mitigation' in line.lower() or 'manage' in line.lower():
                    risk_assessment["mitigation_strategies"].append(line)
        
        return risk_assessment
    
    async def _store_strategic_insights(
        self, 
        analysis_id: str, 
        query: str, 
        synthesis_result: Dict[str, Any],
        confidence_assessment: Dict[str, Any]
    ):
        """Store strategic insights in memory for future reference"""
        try:
            bridge = await get_bridge()
            
            # Store synthesis insights
            await bridge.store_jarvis_insight(
                f"Strategic Analysis: {synthesis_result.get('synthesis', '')}",
                confidence_assessment.get("overall_confidence", 0) / 100,
                "strategic_intelligence",
                {
                    "analysis_id": analysis_id,
                    "original_query": query,
                    "confidence_assessment": confidence_assessment,
                    "recommendations": synthesis_result.get("recommendations", [])
                }
            )
            
            self.logger.info("Strategic insights stored in memory",
                           analysis_id=analysis_id,
                           confidence=confidence_assessment.get("overall_confidence", 0))
            
        except Exception as e:
            self.logger.error("Failed to store strategic insights", 
                            analysis_id=analysis_id, 
                            error=str(e))
    
    async def get_analysis_summary(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis summary by ID"""
        try:
            bridge = await get_bridge()
            # This would retrieve stored analysis - placeholder for now
            return {
                "analysis_id": analysis_id,
                "status": "completed",
                "summary": "Strategic analysis completed successfully"
            }
        except Exception as e:
            self.logger.error("Failed to retrieve analysis summary", 
                            analysis_id=analysis_id, 
                            error=str(e))
            return None

# Global processor instance
_strategic_processor: Optional[StrategicIntelligenceProcessor] = None

async def get_strategic_processor() -> StrategicIntelligenceProcessor:
    """Get the global strategic intelligence processor instance"""
    global _strategic_processor
    if _strategic_processor is None:
        _strategic_processor = StrategicIntelligenceProcessor()
    return _strategic_processor

# Integration function for JARVIS workflow
async def process_strategic_intelligence_request(
    query: str, 
    context: Optional[Dict[str, Any]] = None
) -> StrategicAnalysisResult:
    """
    Main entry point for strategic intelligence processing from JARVIS workflow
    
    Args:
        query: Strategic business question
        context: Additional context from memory service or workflow
        
    Returns:
        StrategicAnalysisResult with comprehensive analysis
    """
    processor = await get_strategic_processor()
    return await processor.process_strategic_query(query, context)