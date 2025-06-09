"""
Input validators for the memory service.

Provides security and data validation for API inputs.
"""

import re
from typing import Optional
from fastapi import HTTPException


def validate_entity_name(entity_name: str) -> str:
    """
    Validate and sanitize entity names to prevent injection attacks.
    
    Args:
        entity_name: Raw entity name from user input
        
    Returns:
        Sanitized entity name
        
    Raises:
        HTTPException: If entity name is invalid
    """
    if not entity_name:
        raise HTTPException(status_code=400, detail="Entity name cannot be empty")
    
    # Remove leading/trailing whitespace
    entity_name = entity_name.strip()
    
    # Check length
    if len(entity_name) > 255:
        raise HTTPException(status_code=400, detail="Entity name too long (max 255 characters)")
    
    if len(entity_name) < 1:
        raise HTTPException(status_code=400, detail="Entity name too short (min 1 character)")
    
    # Check for SQL injection patterns
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b)",
        r"(--|;|\/\*|\*\/|xp_|sp_)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)"
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, entity_name, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Invalid characters in entity name")
    
    # Allow alphanumeric, spaces, and common punctuation
    if not re.match(r"^[a-zA-Z0-9\s\-_.,&'()]+$", entity_name):
        raise HTTPException(status_code=400, detail="Entity name contains invalid characters")
    
    return entity_name


def validate_relationship_type(rel_type: str) -> str:
    """
    Validate relationship type against allowed values.
    
    Args:
        rel_type: Relationship type string
        
    Returns:
        Validated relationship type
        
    Raises:
        HTTPException: If relationship type is invalid
    """
    allowed_types = [
        "relates_to", "mentions", "caused_by", "part_of",
        "works_with", "located_in", "created_by", "used_by",
        "similar_to", "precedes", "follows", "works_at",
        "develops", "leads", "uses", "affiliated_with",
        "invests_in", "competes_with", "owns"
    ]
    
    if rel_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid relationship type. Allowed types: {', '.join(allowed_types)}"
        )
    
    return rel_type


def validate_confidence_score(score: float, field_name: str = "confidence") -> float:
    """
    Validate confidence scores are within valid range.
    
    Args:
        score: Confidence score
        field_name: Name of field for error messages
        
    Returns:
        Validated score
        
    Raises:
        HTTPException: If score is invalid
    """
    if not isinstance(score, (int, float)):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a number")
    
    if score < 0.0 or score > 1.0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between 0.0 and 1.0")
    
    return float(score)


def validate_graph_depth(depth: int) -> int:
    """
    Validate graph traversal depth to prevent DoS.
    
    Args:
        depth: Requested traversal depth
        
    Returns:
        Validated depth
        
    Raises:
        HTTPException: If depth is invalid
    """
    if not isinstance(depth, int):
        raise HTTPException(status_code=400, detail="Depth must be an integer")
    
    if depth < 1:
        raise HTTPException(status_code=400, detail="Depth must be at least 1")
    
    if depth > 5:
        raise HTTPException(status_code=400, detail="Depth cannot exceed 5 (performance limit)")
    
    return depth