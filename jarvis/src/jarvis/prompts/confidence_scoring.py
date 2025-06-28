"""
Confidence Scoring Framework

This module contains the confidence scoring and decision framework for strategic intelligence.
"""

CONFIDENCE_SCORING_FRAMEWORK = """
# Confidence Scoring & Decision Framework

## Strategic Decision Confidence Assessment System

### Core Philosophy
Every strategic recommendation must include quantitative confidence scoring based on data quality, market conditions, competitive factors, and execution feasibility. Confidence scoring provides executives with transparent assessment of recommendation reliability and supports risk-adjusted decision making.

## Confidence Scoring Methodology

### Overall Confidence Calculation Formula

**Base Confidence Score = (Data Quality × 0.25) + (Market Certainty × 0.25) + (Competitive Predictability × 0.20) + (Financial Reliability × 0.20) + (Execution Feasibility × 0.10)**

Each component scored 0-100, resulting in overall confidence percentage.

### Component 1: Data Quality Assessment (25% Weight)

#### Data Quality Scoring Framework

**90-100% (Exceptional Data Quality)**:
- Multiple Tier 1 sources with consistent findings
- Current data (within 30 days) for critical metrics
- Comprehensive market coverage with minimal gaps
- Quantitative data with disclosed methodologies
- Cross-validated findings across independent sources

**70-89% (High Data Quality)**:
- Mix of Tier 1 and Tier 2 sources with general alignment
- Recent data (within 90 days) for most critical metrics
- Good market coverage with minor information gaps
- Combination of quantitative and qualitative insights
- Some validation across multiple sources

**50-69% (Moderate Data Quality)**:
- Primarily Tier 2 and Tier 3 sources
- Data currency varies (30-180 days for critical metrics)
- Moderate information gaps in key areas
- Mix of data types with some methodology concerns
- Limited cross-source validation

**30-49% (Low Data Quality)**:
- Primarily Tier 3 sources with limited authority
- Outdated data (180+ days) for critical metrics
- Significant information gaps affecting analysis
- Primarily qualitative or anecdotal information
- Minimal source validation or corroboration

**0-29% (Poor Data Quality)**:
- Unreliable or unverifiable sources
- Critically outdated or incomplete data
- Major information gaps preventing proper analysis
- Contradictory findings without resolution
- Single-source dependencies for critical insights

### Component 2: Market Certainty Assessment (25% Weight)

#### Market Certainty Scoring Framework

**90-100% (High Market Certainty)**:
- Stable market conditions with predictable trends
- Clear regulatory environment with minimal change probability
- Established customer behavior patterns
- Mature market with well-understood dynamics
- Low probability of disruptive market changes

**70-89% (Moderate-High Market Certainty)**:
- Generally stable market with some volatility
- Regulatory environment mostly stable with minor changes expected
- Customer behavior mostly predictable with some evolution
- Market dynamics well-understood with manageable uncertainty
- Low-moderate probability of significant market shifts

**50-69% (Moderate Market Certainty)**:
- Market volatility with mixed trend signals
- Regulatory changes possible but not imminent
- Customer behavior evolving with new patterns emerging
- Market dynamics changing but still analyzable
- Moderate probability of market disruption

**30-49% (Low Market Certainty)**:
- High market volatility with unclear trends
- Significant regulatory changes likely or pending
- Customer behavior shifting rapidly
- Market dynamics in flux with emerging uncertainties
- High probability of market disruption

**0-29% (Very Low Market Certainty)**:
- Extreme market volatility or crisis conditions
- Major regulatory overhaul imminent or ongoing
- Customer behavior highly unpredictable
- Market dynamics fundamentally changing
- Market disruption already occurring or inevitable

### Component 3: Competitive Predictability Assessment (20% Weight)

#### Competitive Predictability Scoring Framework

**90-100% (High Competitive Predictability)**:
- Well-established competitive landscape with known players
- Competitors follow predictable strategic patterns
- Competitive responses historically consistent and rational
- High barriers to entry limiting new competitors
- Competitive intelligence comprehensive and current

**70-89% (Moderate-High Competitive Predictability)**:
- Mostly stable competitive environment
- Competitors generally predictable with some variability
- Competitive responses mostly rational with occasional surprises
- Moderate barriers to entry with limited new entrant threat
- Good competitive intelligence with minor gaps

**50-69% (Moderate Competitive Predictability)**:
- Competitive landscape evolving with some uncertainty
- Competitor behavior somewhat unpredictable
- Mixed competitive response patterns
- Moderate new entrant threat
- Adequate competitive intelligence with notable gaps

**30-49% (Low Competitive Predictability)**:
- Rapidly changing competitive environment
- Competitor strategies difficult to predict
- Irrational or aggressive competitive responses common
- High threat of new entrants or substitutes
- Limited competitive intelligence

**0-29% (Very Low Competitive Predictability)**:
- Chaotic competitive environment
- Competitor behavior highly unpredictable
- Intense competitive warfare with irrational moves
- Significant disruption from new entrants
- Poor competitive intelligence

### Component 4: Financial Reliability Assessment (20% Weight)

#### Financial Reliability Scoring Framework

**90-100% (High Financial Reliability)**:
- Financial projections based on solid benchmarks and comparables
- Conservative assumptions with sensitivity analysis
- Multiple scenario modeling with probability weighting
- Detailed cost structure analysis with vendor validation
- Historical performance data supporting projections

**70-89% (Moderate-High Financial Reliability)**:
- Financial projections based on reasonable industry benchmarks
- Balanced assumptions with some sensitivity testing
- Base case and alternative scenario analysis
- Good cost structure understanding
- Some historical validation of assumptions

**50-69% (Moderate Financial Reliability)**:
- Financial projections based on limited benchmarks
- Mixed conservative/aggressive assumptions
- Single scenario with limited sensitivity analysis
- Basic cost structure analysis
- Limited historical validation

**30-49% (Low Financial Reliability)**:
- Financial projections based on weak benchmarks
- Optimistic assumptions with minimal testing
- Single optimistic scenario
- Incomplete cost structure analysis
- No historical validation

**0-29% (Very Low Financial Reliability)**:
- Financial projections based on speculation
- Highly optimistic or unrealistic assumptions
- No scenario analysis or sensitivity testing
- Poor understanding of cost structures
- Contradicts historical performance patterns

### Component 5: Execution Feasibility Assessment (10% Weight)

#### Execution Feasibility Scoring Framework

**90-100% (High Execution Feasibility)**:
- Clear execution roadmap with detailed milestones
- Required capabilities and resources available or readily accessible
- Proven track record in similar initiatives
- Strong organizational support and commitment
- Minimal execution complexity and dependencies

**70-89% (Moderate-High Execution Feasibility)**:
- Generally clear execution plan with most details defined
- Most required capabilities available with some development needed
- Some relevant experience with similar initiatives
- Good organizational support
- Manageable execution complexity

**50-69% (Moderate Execution Feasibility)**:
- Basic execution framework with some details undefined
- Mixed capability availability requiring significant development
- Limited relevant experience
- Moderate organizational support
- Moderate execution complexity with some dependencies

**30-49% (Low Execution Feasibility)**:
- Unclear execution plan with major gaps
- Significant capability gaps requiring extensive development
- Little relevant experience
- Limited organizational support
- High execution complexity

**0-29% (Very Low Execution Feasibility)**:
- No clear execution plan
- Critical capability gaps with no development path
- No relevant experience
- Poor organizational support
- Extreme execution complexity

## Decision Framework Integration

### Confidence-Based Decision Matrix

| Overall Confidence | Decision Recommendation | Risk Management |
|-------------------|------------------------|-----------------|
| **85-100%** | **PROCEED** - High confidence recommendation | Standard risk monitoring |
| **70-84%** | **PROCEED WITH CAUTION** - Good confidence with monitoring | Enhanced risk tracking |
| **55-69%** | **CONDITIONAL PROCEED** - Additional validation recommended | Active risk mitigation |
| **40-54%** | **DEFER** - Insufficient confidence for immediate action | Address confidence gaps |
| **0-39%** | **DO NOT PROCEED** - Too high risk/uncertainty | Fundamental reassessment needed |

## Confidence Communication Protocol

### Executive Summary Format

```
## CONFIDENCE ASSESSMENT

**Overall Confidence**: [XX%] - [High/Medium/Low]

**Decision Recommendation**: [PROCEED/PROCEED WITH CAUTION/CONDITIONAL/DEFER/DO NOT PROCEED]

**Key Confidence Drivers**:
- [Highest confidence factor]: [XX%] - [Why high confidence]
- [Lowest confidence factor]: [XX%] - [Why low confidence and improvement path]

**Critical Assumptions**:
- [Assumption 1]: [Impact if incorrect]
- [Assumption 2]: [Impact if incorrect]

**Sensitivity Factors**:
- [Variable 1]: [XX%] change = $[X.X]M impact
- [Variable 2]: [XX%] change = [X]% probability change

**Confidence Improvement Actions**:
- [Action 1]: [How this would improve confidence]
- [Action 2]: [Timeline and expected confidence improvement]
```
"""

def get_confidence_framework() -> str:
    """Get the confidence scoring framework prompt"""
    return CONFIDENCE_SCORING_FRAMEWORK

def calculate_confidence_score(data_quality: float, market_certainty: float, 
                              competitive_predictability: float, financial_reliability: float,
                              execution_feasibility: float) -> dict:
    """Calculate overall confidence score using the framework weights"""
    overall_confidence = (
        data_quality * 0.25 +
        market_certainty * 0.25 +
        competitive_predictability * 0.20 +
        financial_reliability * 0.20 +
        execution_feasibility * 0.10
    )
    
    # Determine decision recommendation
    if overall_confidence >= 85:
        decision = "PROCEED"
        risk_level = "Standard risk monitoring"
    elif overall_confidence >= 70:
        decision = "PROCEED WITH CAUTION"
        risk_level = "Enhanced risk tracking"
    elif overall_confidence >= 55:
        decision = "CONDITIONAL PROCEED"
        risk_level = "Active risk mitigation"
    elif overall_confidence >= 40:
        decision = "DEFER"
        risk_level = "Address confidence gaps"
    else:
        decision = "DO NOT PROCEED"
        risk_level = "Fundamental reassessment needed"
    
    return {
        "overall_confidence": overall_confidence,
        "decision_recommendation": decision,
        "risk_management": risk_level,
        "component_scores": {
            "data_quality": data_quality,
            "market_certainty": market_certainty,
            "competitive_predictability": competitive_predictability,
            "financial_reliability": financial_reliability,
            "execution_feasibility": execution_feasibility
        }
    }