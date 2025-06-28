"""
Strategic Intelligence Prompts Package

This package contains the complete strategic intelligence framework for JARVIS, including:
- Master Strategic Orchestrator
- Domain Expert Prompts (Financial, Market, Competitive, Regulatory)
- Web Search Intelligence Framework
- Executive Report Templates
- Confidence Scoring Framework

Usage:
    from jarvis.prompts import get_strategic_prompt, generate_executive_report
    
    # Get master orchestrator prompt
    master_prompt = get_strategic_prompt("master_orchestrator")
    
    # Get domain expert prompt
    financial_prompt = get_strategic_prompt("financial_expert")
    
    # Generate executive report
    report = generate_executive_report("executive_summary", **report_data)
"""

from .master_strategic_orchestrator import get_master_prompt, MASTER_STRATEGIC_ORCHESTRATOR
from .domain_experts import (
    get_domain_expert_prompt, 
    get_all_domain_prompts,
    FINANCIAL_EXPERT_PROMPT,
    MARKET_INTELLIGENCE_EXPERT_PROMPT,
    COMPETITIVE_STRATEGY_EXPERT_PROMPT,
    REGULATORY_RISK_EXPERT_PROMPT
)
from .web_search_intelligence import (
    get_web_search_framework,
    get_search_templates,
    build_search_query,
    WEB_SEARCH_INTELLIGENCE_FRAMEWORK,
    SEARCH_TEMPLATES
)
from .executive_reports import (
    get_report_template,
    generate_executive_report,
    get_available_templates,
    get_report_section,
    build_custom_report,
    REPORT_TEMPLATES,
    REPORT_SECTIONS
)
from .confidence_scoring import (
    get_confidence_framework,
    calculate_confidence_score,
    CONFIDENCE_SCORING_FRAMEWORK
)

# Version info
__version__ = "1.0.0"
__author__ = "Core Nexus Strategic Intelligence Team"
__description__ = "Strategic Intelligence Framework for JARVIS AI Agent"

# Main prompt registry for easy access
STRATEGIC_PROMPTS = {
    # Core orchestration
    "master_orchestrator": MASTER_STRATEGIC_ORCHESTRATOR,
    
    # Domain experts
    "financial_expert": FINANCIAL_EXPERT_PROMPT,
    "market_expert": MARKET_INTELLIGENCE_EXPERT_PROMPT,
    "competitive_expert": COMPETITIVE_STRATEGY_EXPERT_PROMPT,
    "regulatory_expert": REGULATORY_RISK_EXPERT_PROMPT,
    "risk_expert": REGULATORY_RISK_EXPERT_PROMPT,  # Alias for regulatory
    
    # Intelligence frameworks
    "web_search_framework": WEB_SEARCH_INTELLIGENCE_FRAMEWORK,
    "confidence_scoring": CONFIDENCE_SCORING_FRAMEWORK,
}

def get_strategic_prompt(prompt_type: str) -> str:
    """
    Get a strategic intelligence prompt by type
    
    Args:
        prompt_type: Type of prompt to retrieve. Options:
            - "master_orchestrator": Main strategic orchestration prompt
            - "financial_expert": Financial analysis expert prompt
            - "market_expert": Market intelligence expert prompt  
            - "competitive_expert": Competitive strategy expert prompt
            - "regulatory_expert"/"risk_expert": Regulatory and risk expert prompt
            - "web_search_framework": Web search intelligence framework
            - "confidence_scoring": Confidence scoring framework
    
    Returns:
        str: The requested prompt text
    """
    return STRATEGIC_PROMPTS.get(prompt_type, "")

def get_all_strategic_prompts() -> dict:
    """Get all available strategic prompts"""
    return STRATEGIC_PROMPTS.copy()

def get_available_prompt_types() -> list:
    """Get list of available prompt types"""
    return list(STRATEGIC_PROMPTS.keys())

# Strategic Intelligence Orchestrator Class
class StrategicIntelligenceOrchestrator:
    """
    Main orchestrator class for strategic intelligence operations
    """
    
    def __init__(self):
        self.prompts = STRATEGIC_PROMPTS.copy()
        self.templates = REPORT_TEMPLATES.copy()
        self.search_templates = SEARCH_TEMPLATES.copy()
    
    def get_prompt(self, prompt_type: str) -> str:
        """Get a specific prompt"""
        return self.prompts.get(prompt_type, "")
    
    def get_domain_expert(self, domain: str) -> str:
        """Get domain expert prompt"""
        return get_domain_expert_prompt(domain)
    
    def get_search_queries(self, intelligence_type: str, **kwargs) -> list:
        """Get search query templates for specific intelligence type"""
        templates = get_search_templates(intelligence_type)
        return [build_search_query(template, **kwargs) for template in templates]
    
    def generate_report(self, report_type: str = "executive_summary", **kwargs) -> str:
        """Generate executive report"""
        return generate_executive_report(report_type, **kwargs)
    
    def calculate_confidence(self, data_quality: float, market_certainty: float,
                           competitive_predictability: float, financial_reliability: float,
                           execution_feasibility: float) -> dict:
        """Calculate confidence score"""
        return calculate_confidence_score(
            data_quality, market_certainty, competitive_predictability,
            financial_reliability, execution_feasibility
        )
    
    def get_framework_info(self) -> dict:
        """Get information about the strategic intelligence framework"""
        return {
            "version": __version__,
            "description": __description__,
            "available_prompts": list(self.prompts.keys()),
            "available_templates": list(self.templates.keys()),
            "search_intelligence_types": list(self.search_templates.keys()),
            "capabilities": [
                "Strategic Query Decomposition",
                "Multi-Domain Expert Orchestration", 
                "Real-Time Intelligence Gathering",
                "Cross-Domain Synthesis",
                "Executive Report Generation",
                "Confidence Scoring",
                "Risk Assessment",
                "Implementation Planning"
            ]
        }

# Global orchestrator instance
strategic_intelligence = StrategicIntelligenceOrchestrator()

# Convenience functions for common operations
def analyze_strategic_query(query: str, domain_focus: list = None) -> dict:
    """
    Analyze a strategic query and determine required expert domains
    
    Args:
        query: The strategic business query
        domain_focus: Optional list of domains to focus on
    
    Returns:
        dict: Analysis results with domain recommendations
    """
    # Simple keyword-based domain detection
    query_lower = query.lower()
    
    domains_detected = []
    
    # Financial keywords
    if any(word in query_lower for word in ['roi', 'investment', 'cost', 'revenue', 'profit', 'financial', 'valuation', 'funding']):
        domains_detected.append('financial')
    
    # Market keywords  
    if any(word in query_lower for word in ['market', 'customer', 'segment', 'demand', 'size', 'growth', 'trend']):
        domains_detected.append('market')
    
    # Competitive keywords
    if any(word in query_lower for word in ['competitor', 'competition', 'positioning', 'advantage', 'differentiation']):
        domains_detected.append('competitive')
    
    # Regulatory/Risk keywords
    if any(word in query_lower for word in ['risk', 'regulatory', 'compliance', 'legal', 'policy', 'regulation']):
        domains_detected.append('regulatory')
    
    # If no specific domains detected, use all
    if not domains_detected:
        domains_detected = ['market', 'competitive', 'financial', 'regulatory']
    
    # Apply domain focus filter if provided
    if domain_focus:
        domains_detected = [d for d in domains_detected if d in domain_focus]
    
    return {
        "query": query,
        "detected_domains": domains_detected,
        "required_prompts": [f"{domain}_expert" for domain in domains_detected],
        "orchestrator_prompt": "master_orchestrator",
        "web_search_needed": True,
        "confidence_scoring_needed": True
    }

def build_analysis_workflow(query: str, domain_focus: list = None) -> dict:
    """
    Build a complete analysis workflow for a strategic query
    
    Args:
        query: The strategic business query
        domain_focus: Optional list of domains to focus on
        
    Returns:
        dict: Complete workflow specification
    """
    analysis = analyze_strategic_query(query, domain_focus)
    
    workflow = {
        "query": query,
        "workflow_steps": [
            {
                "step": 1,
                "name": "Strategic Orchestration",
                "prompt": get_strategic_prompt("master_orchestrator"),
                "description": "Initialize strategic analysis framework"
            },
            {
                "step": 2, 
                "name": "Web Search Intelligence",
                "prompt": get_strategic_prompt("web_search_framework"),
                "description": "Gather real-time intelligence"
            }
        ],
        "domain_analysis": [],
        "synthesis": {
            "step": "final",
            "name": "Strategic Synthesis & Reporting",
            "confidence_framework": get_strategic_prompt("confidence_scoring"),
            "report_template": "executive_summary"
        }
    }
    
    # Add domain expert steps
    step_counter = 3
    for domain in analysis["detected_domains"]:
        workflow["domain_analysis"].append({
            "step": step_counter,
            "name": f"{domain.title()} Expert Analysis",
            "prompt": get_strategic_prompt(f"{domain}_expert"),
            "search_queries": get_search_templates(f"{domain}_intelligence") if f"{domain}_intelligence" in SEARCH_TEMPLATES else [],
            "description": f"Specialized {domain} analysis and recommendations"
        })
        step_counter += 1
    
    return workflow

# Export key functions and classes
__all__ = [
    # Main orchestrator
    'strategic_intelligence',
    'StrategicIntelligenceOrchestrator',
    
    # Prompt functions
    'get_strategic_prompt',
    'get_all_strategic_prompts', 
    'get_available_prompt_types',
    
    # Domain experts
    'get_domain_expert_prompt',
    'get_all_domain_prompts',
    
    # Web search
    'get_web_search_framework',
    'get_search_templates',
    'build_search_query',
    
    # Reports
    'get_report_template',
    'generate_executive_report',
    'get_available_templates',
    'build_custom_report',
    
    # Confidence scoring
    'get_confidence_framework',
    'calculate_confidence_score',
    
    # Analysis workflows
    'analyze_strategic_query',
    'build_analysis_workflow',
    
    # Constants
    'STRATEGIC_PROMPTS',
    'REPORT_TEMPLATES',
    'SEARCH_TEMPLATES'
]