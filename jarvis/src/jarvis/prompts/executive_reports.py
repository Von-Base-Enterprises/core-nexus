"""
Executive Report Templates

This module contains templates for generating executive-ready strategic reports and briefings.
"""

EXECUTIVE_SUMMARY_TEMPLATE = """
# Executive Strategic Intelligence Brief

## Strategic Question Analysis
**Query**: {original_query}
**Analysis Scope**: {analysis_scope}
**Intelligence Confidence**: {confidence_score}% 
**Decision Timeline**: {decision_timeline}

---

## Executive Summary

### Strategic Recommendation
**PRIMARY RECOMMENDATION**: {primary_recommendation}

**Supporting Rationale**:
{supporting_rationale}

**Success Probability**: {success_probability}% based on {confidence_factors}

### Critical Action Items
1. **Immediate (0-30 days)**: {immediate_actions}
2. **Strategic (1-6 months)**: {strategic_actions}  
3. **Long-term (6+ months)**: {longterm_actions}

---

## Strategic Intelligence Analysis

### Market Intelligence Summary
- **Market Size**: {market_size}
- **Growth Rate**: {growth_rate} CAGR (2025-2030)
- **Key Segments**: {key_segments}
- **Market Dynamics**: {market_dynamics}

**Strategic Implications**: {market_implications}

### Competitive Landscape Assessment
- **Market Leaders**: {market_leaders}
- **Competitive Intensity**: {competitive_intensity}
- **Differentiation Opportunities**: {differentiation_opportunities}
- **Competitive Threats**: {competitive_threats}

**Strategic Implications**: {competitive_implications}

### Financial Analysis Overview
- **Investment Required**: {investment_required}
- **Expected Returns**: {expected_returns}
- **ROI Projection**: {roi_projection}
- **Payback Period**: {payback_period}
- **Risk-Adjusted NPV**: {risk_adjusted_npv}

**Strategic Implications**: {financial_implications}

### Regulatory & Risk Assessment
- **Regulatory Environment**: {regulatory_environment}
- **Compliance Requirements**: {compliance_requirements}
- **Key Risk Factors**: {key_risks}
- **Risk Mitigation Strategy**: {risk_mitigation}

**Strategic Implications**: {regulatory_implications}

---

## Decision Framework & Options Analysis

### Strategic Options Matrix

| Option | Success Probability | ROI Potential | Risk Level | Strategic Fit | Implementation Complexity |
|--------|-------------------|---------------|------------|---------------|-------------------------|
{options_matrix}

### Recommended Decision Path
**Selected Option**: {selected_option}

**Decision Rationale**:
{decision_rationale}

**Key Success Factors**:
{success_factors}

**Critical Dependencies**:
{critical_dependencies}

---

## Risk Assessment & Mitigation

### High-Risk Factors (Immediate Attention Required)
{high_risk_factors}

### Medium-Risk Factors (Active Monitoring)
{medium_risk_factors}

### Risk Mitigation Strategy
{risk_mitigation_strategy}

---

## Implementation Roadmap

### Phase 1: Foundation (0-3 months)
**Objectives**: {phase1_objectives}
**Key Milestones**: {phase1_milestones}
**Resource Requirements**: {phase1_resources}
**Success Metrics**: {phase1_metrics}

### Phase 2: Execution (3-12 months)
**Objectives**: {phase2_objectives}
**Key Milestones**: {phase2_milestones}
**Resource Requirements**: {phase2_resources}
**Success Metrics**: {phase2_metrics}

### Phase 3: Optimization (12+ months)
**Objectives**: {phase3_objectives}
**Key Milestones**: {phase3_milestones}
**Resource Requirements**: {phase3_resources}
**Success Metrics**: {phase3_metrics}

---

## Intelligence Confidence Assessment

### Data Quality Analysis
- **Tier 1 Sources**: {tier1_sources}% of intelligence
- **Tier 2 Sources**: {tier2_sources}% of intelligence
- **Tier 3 Sources**: {tier3_sources}% of intelligence
- **Overall Data Quality Score**: {data_quality_score}/100

### Market Certainty Analysis
- **Market Stability**: {market_stability}/100
- **Regulatory Predictability**: {regulatory_predictability}/100
- **Competitive Predictability**: {competitive_predictability}/100
- **Overall Market Certainty**: {market_certainty}/100

### Financial Reliability Analysis
- **Projection Methodology**: {projection_methodology}/100
- **Historical Validation**: {historical_validation}/100
- **Sensitivity Analysis**: {sensitivity_analysis}/100
- **Overall Financial Reliability**: {financial_reliability}/100

### Execution Feasibility Analysis
- **Resource Availability**: {resource_availability}/100
- **Capability Readiness**: {capability_readiness}/100
- **Organizational Support**: {organizational_support}/100
- **Overall Execution Feasibility**: {execution_feasibility}/100

---

## Strategic Monitoring Framework

### Key Performance Indicators (KPIs)
{strategic_kpis}

### Early Warning Indicators
{early_warning_indicators}

### Monitoring Schedule
- **Weekly Reviews**: {weekly_monitoring}
- **Monthly Assessments**: {monthly_monitoring}
- **Quarterly Strategic Reviews**: {quarterly_monitoring}

---

## Appendix: Supporting Analysis

### Market Intelligence Deep Dive
{market_deep_dive}

### Competitive Intelligence Deep Dive
{competitive_deep_dive}

### Financial Model Assumptions
{financial_assumptions}

### Regulatory Analysis Details
{regulatory_details}

---

**Report Generated**: {report_timestamp}
**Analysis Duration**: {analysis_duration}
**Intelligence Sources**: {source_count} sources validated
**Next Review Date**: {next_review_date}
"""

INVESTMENT_DECISION_TEMPLATE = """
# Investment Decision Brief

## Investment Overview
**Investment Opportunity**: {investment_name}
**Requested Investment**: ${investment_amount:,.0f}
**Investment Type**: {investment_type}
**Decision Required By**: {decision_deadline}

---

## Investment Recommendation

### Executive Summary
**RECOMMENDATION**: {investment_recommendation}
**CONFIDENCE LEVEL**: {confidence_level}%
**EXPECTED ROI**: {expected_roi}%
**PAYBACK PERIOD**: {payback_period} years

### Key Investment Metrics
- **Net Present Value (NPV)**: ${npv:,.0f}
- **Internal Rate of Return (IRR)**: {irr}%
- **Return on Investment (ROI)**: {roi}%
- **Risk-Adjusted Return**: {risk_adjusted_return}%

---

## Market Analysis

### Market Opportunity
- **Total Addressable Market (TAM)**: ${tam:,.0f}
- **Serviceable Addressable Market (SAM)**: ${sam:,.0f}
- **Serviceable Obtainable Market (SOM)**: ${som:,.0f}
- **Market Growth Rate**: {market_growth}% CAGR

### Competitive Position
{competitive_position}

---

## Financial Projections

### Revenue Forecast (5-Year)
{revenue_forecast}

### Profitability Analysis
{profitability_analysis}

### Cash Flow Projections
{cashflow_projections}

---

## Risk Analysis

### Investment Risks
{investment_risks}

### Risk Mitigation
{risk_mitigation}

---

## Investment Decision Matrix

| Criteria | Weight | Score (1-10) | Weighted Score |
|----------|---------|--------------|----------------|
{decision_matrix}

**Total Score**: {total_score}/100

---

## Recommendation & Next Steps
{recommendation_details}
"""

MARKET_ENTRY_TEMPLATE = """
# Market Entry Strategy Brief

## Market Entry Overview
**Target Market**: {target_market}
**Entry Strategy**: {entry_strategy}
**Investment Required**: ${investment_required:,.0f}
**Timeline**: {entry_timeline}

---

## Market Entry Recommendation

### Strategic Recommendation
**PRIMARY STRATEGY**: {primary_strategy}
**ENTRY TIMING**: {entry_timing}
**SUCCESS PROBABILITY**: {success_probability}%

---

## Market Analysis

### Market Size & Growth
{market_analysis}

### Customer Segments
{customer_segments}

### Market Dynamics
{market_dynamics}

---

## Competitive Landscape

### Key Competitors
{key_competitors}

### Competitive Advantages
{competitive_advantages}

### Market Positioning
{market_positioning}

---

## Entry Strategy Options

### Option 1: {strategy_option_1}
{strategy_1_details}

### Option 2: {strategy_option_2}
{strategy_2_details}

### Option 3: {strategy_option_3}
{strategy_3_details}

---

## Implementation Plan
{implementation_plan}

---

## Success Metrics
{success_metrics}
"""

COMPETITIVE_ANALYSIS_TEMPLATE = """
# Competitive Intelligence Brief

## Competitive Landscape Overview
**Industry**: {industry}
**Market Focus**: {market_focus}
**Analysis Scope**: {analysis_scope}
**Competitive Intensity**: {competitive_intensity}

---

## Key Findings

### Market Leaders
{market_leaders}

### Emerging Competitors
{emerging_competitors}

### Competitive Dynamics
{competitive_dynamics}

---

## Competitive Positioning Map
{positioning_map}

---

## Strategic Implications
{strategic_implications}

---

## Recommended Actions
{recommended_actions}
"""

# Template registry for easy access
REPORT_TEMPLATES = {
    "executive_summary": EXECUTIVE_SUMMARY_TEMPLATE,
    "investment_decision": INVESTMENT_DECISION_TEMPLATE,
    "market_entry": MARKET_ENTRY_TEMPLATE,
    "competitive_analysis": COMPETITIVE_ANALYSIS_TEMPLATE
}

def get_report_template(template_type: str) -> str:
    """Get a specific report template"""
    return REPORT_TEMPLATES.get(template_type, EXECUTIVE_SUMMARY_TEMPLATE)

def generate_executive_report(template_type: str = "executive_summary", **kwargs) -> str:
    """Generate an executive report using the specified template"""
    template = get_report_template(template_type)
    
    # Fill in missing values with placeholders
    import datetime
    default_values = {
        "report_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "analysis_duration": "Unknown",
        "source_count": "Multiple",
        "next_review_date": "TBD"
    }
    
    # Merge provided kwargs with defaults
    template_vars = {**default_values, **kwargs}
    
    try:
        return template.format(**template_vars)
    except KeyError as e:
        # Return template with missing variable indicated
        return f"Missing template variable: {e}\n\n{template}"

def get_available_templates() -> list:
    """Get list of available report templates"""
    return list(REPORT_TEMPLATES.keys())

# Standard report sections for building custom reports
REPORT_SECTIONS = {
    "executive_summary": """
## Executive Summary
**Strategic Recommendation**: {recommendation}
**Confidence Level**: {confidence}%
**Key Success Factors**: {success_factors}
**Critical Risks**: {critical_risks}
""",
    
    "market_analysis": """
## Market Analysis
**Market Size**: {market_size}
**Growth Rate**: {growth_rate}
**Key Trends**: {key_trends}
**Market Dynamics**: {market_dynamics}
""",
    
    "competitive_analysis": """
## Competitive Analysis
**Market Leaders**: {market_leaders}
**Competitive Intensity**: {competitive_intensity}
**Differentiation Opportunities**: {differentiation_opportunities}
**Competitive Threats**: {competitive_threats}
""",
    
    "financial_analysis": """
## Financial Analysis
**Investment Required**: {investment_required}
**Expected Returns**: {expected_returns}
**ROI**: {roi}%
**Payback Period**: {payback_period}
**Risk-Adjusted NPV**: {risk_adjusted_npv}
""",
    
    "risk_assessment": """
## Risk Assessment
**High-Risk Factors**: {high_risks}
**Medium-Risk Factors**: {medium_risks}
**Risk Mitigation Strategy**: {risk_mitigation}
**Contingency Plans**: {contingency_plans}
""",
    
    "implementation_plan": """
## Implementation Plan
**Phase 1 (0-3 months)**: {phase1}
**Phase 2 (3-12 months)**: {phase2}
**Phase 3 (12+ months)**: {phase3}
**Resource Requirements**: {resource_requirements}
**Success Metrics**: {success_metrics}
"""
}

def get_report_section(section_name: str) -> str:
    """Get a specific report section template"""
    return REPORT_SECTIONS.get(section_name, "")

def build_custom_report(sections: list, **kwargs) -> str:
    """Build a custom report from specified sections"""
    report_parts = []
    
    for section in sections:
        if section in REPORT_SECTIONS:
            try:
                section_content = REPORT_SECTIONS[section].format(**kwargs)
                report_parts.append(section_content)
            except KeyError:
                report_parts.append(f"## {section.title().replace('_', ' ')}\n[Missing data for {section}]\n")
    
    return "\n".join(report_parts)