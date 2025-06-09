"""
Memory Export API for Core Nexus
Quick deployment version with minimal dependencies
"""

import csv
import json
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
from uuid import UUID

from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .models import MemoryResponse, QueryRequest
from .unified_store import UnifiedVectorStore


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"  # Future implementation


class ExportFilters(BaseModel):
    """Filters for memory export."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    importance_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    importance_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    user_id: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=100000)


class ExportRequest(BaseModel):
    """Request model for memory export."""
    format: ExportFormat = ExportFormat.JSON
    filters: Optional[ExportFilters] = None
    include_embeddings: bool = Field(False, description="Include raw embeddings")
    include_metadata: bool = Field(True, description="Include metadata")
    gdpr_compliant: bool = Field(False, description="GDPR compliance format")


class MemoryExportService:
    """Service for exporting memories."""
    
    def __init__(self, store: UnifiedVectorStore):
        self.store = store
        
    async def export_memories(self, request: ExportRequest) -> StreamingResponse:
        """Export memories in requested format."""
        # Fetch memories based on filters
        memories = await self._fetch_memories(request.filters)
        
        if request.format == ExportFormat.JSON:
            return self._export_json(memories, request)
        elif request.format == ExportFormat.CSV:
            return self._export_csv(memories, request)
        elif request.format == ExportFormat.PDF:
            raise HTTPException(status_code=501, detail="PDF export coming soon")
        else:
            raise HTTPException(status_code=400, detail="Invalid export format")
            
    async def _fetch_memories(self, filters: Optional[ExportFilters]) -> List[MemoryResponse]:
        """Fetch memories based on filters."""
        # For MVP, use simple query approach
        # In production, would use direct database queries for efficiency
        
        # Start with all memories query
        query_request = QueryRequest(
            query="",  # Empty query to get all
            limit=filters.limit if filters and filters.limit else 10000,
            min_similarity=0.0  # Get all memories
        )
        
        # Query memories
        results = await self.store.query_memories(query_request)
        memories = results.memories
        
        # Apply filters
        if filters:
            filtered_memories = []
            
            for memory in memories:
                # Date filter
                if filters.date_from or filters.date_to:
                    try:
                        memory_date = datetime.fromisoformat(memory.created_at.replace('Z', '+00:00'))
                        if filters.date_from and memory_date < filters.date_from:
                            continue
                        if filters.date_to and memory_date > filters.date_to:
                            continue
                    except:
                        pass  # Skip if date parsing fails
                
                # Importance filter
                if filters.importance_min and memory.importance_score < filters.importance_min:
                    continue
                if filters.importance_max and memory.importance_score > filters.importance_max:
                    continue
                    
                # Tags filter
                if filters.tags:
                    memory_tags = memory.metadata.get('tags', [])
                    if isinstance(memory_tags, str):
                        memory_tags = [memory_tags]
                    if not any(tag in memory_tags for tag in filters.tags):
                        continue
                        
                # User filter
                if filters.user_id and memory.metadata.get('user_id') != filters.user_id:
                    continue
                    
                filtered_memories.append(memory)
                
            memories = filtered_memories
            
        return memories
        
    def _export_json(self, memories: List[MemoryResponse], request: ExportRequest) -> StreamingResponse:
        """Export memories as JSON."""
        
        def generate():
            yield '{"export_info":{'
            yield f'"export_date":"{datetime.utcnow().isoformat()}Z",'
            yield f'"total_memories":{len(memories)},'
            yield f'"format":"json",'
            yield f'"gdpr_compliant":{str(request.gdpr_compliant).lower()}'
            yield '},"memories":['
            
            for i, memory in enumerate(memories):
                if i > 0:
                    yield ','
                    
                memory_dict = {
                    "id": str(memory.id),
                    "content": memory.content,
                    "importance_score": memory.importance_score,
                    "created_at": memory.created_at
                }
                
                if request.include_metadata and memory.metadata:
                    memory_dict["metadata"] = memory.metadata
                    
                if request.include_embeddings and hasattr(memory, 'embedding') and memory.embedding:
                    memory_dict["embedding"] = memory.embedding
                    
                yield json.dumps(memory_dict)
                
            yield ']}'
            
        filename = f"core_nexus_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    def _export_csv(self, memories: List[MemoryResponse], request: ExportRequest) -> StreamingResponse:
        """Export memories as CSV."""
        
        output = io.StringIO()
        
        # Determine columns
        fieldnames = ['id', 'content', 'importance_score', 'created_at']
        
        # Add metadata columns if requested
        metadata_keys = set()
        if request.include_metadata:
            for memory in memories:
                if memory.metadata:
                    metadata_keys.update(memory.metadata.keys())
            fieldnames.extend(sorted(metadata_keys))
            
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for memory in memories:
            row = {
                'id': str(memory.id),
                'content': memory.content,
                'importance_score': memory.importance_score,
                'created_at': memory.created_at
            }
            
            # Add metadata fields
            if request.include_metadata and memory.metadata:
                for key in metadata_keys:
                    value = memory.metadata.get(key, '')
                    # Convert lists to comma-separated strings
                    if isinstance(value, list):
                        value = ','.join(str(v) for v in value)
                    row[key] = value
                    
            writer.writerow(row)
            
        output.seek(0)
        filename = f"core_nexus_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    async def create_gdpr_package(self, user_id: str) -> StreamingResponse:
        """Create GDPR-compliant data export package."""
        # Filter memories for specific user
        filters = ExportFilters(user_id=user_id)
        memories = await self._fetch_memories(filters)
        
        # Create comprehensive data package
        gdpr_data = {
            "data_export": {
                "export_date": datetime.utcnow().isoformat() + "Z",
                "user_id": user_id,
                "data_categories": {
                    "memories": {
                        "count": len(memories),
                        "description": "All stored memory records",
                        "data": []
                    }
                },
                "metadata": {
                    "export_reason": "GDPR Data Subject Request",
                    "includes_all_data": True,
                    "format_version": "1.0"
                }
            }
        }
        
        # Add memories with full details
        for memory in memories:
            memory_record = {
                "id": str(memory.id),
                "content": memory.content,
                "metadata": memory.metadata,
                "importance_score": memory.importance_score,
                "created_at": memory.created_at,
                "data_sources": ["user_input", "api_storage"]
            }
            gdpr_data["data_export"]["data_categories"]["memories"]["data"].append(memory_record)
            
        # Convert to JSON
        json_str = json.dumps(gdpr_data, indent=2)
        filename = f"gdpr_data_export_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )