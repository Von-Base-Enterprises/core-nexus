"""
Simplified Bulk Import API for Core Nexus Memory Service
MVP version using in-memory progress tracking instead of Redis
"""

import asyncio
import csv
import io
import json
import base64
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import hashlib
from dataclasses import dataclass, field

from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
import pandas as pd
from loguru import logger

from .models import MemoryResponse
from .unified_store import UnifiedVectorStore


class ImportFormat(str, Enum):
    """Supported import formats."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"


class ImportStatus(str, Enum):
    """Import job status."""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some records failed


class ImportOptions(BaseModel):
    """Options for bulk import operation."""
    deduplicate: bool = Field(True, description="Check for duplicates")
    validate: bool = Field(True, description="Validate data before import")
    batch_size: int = Field(100, ge=10, le=1000, description="Processing batch size")
    metadata_mapping: Optional[Dict[str, str]] = Field(None, description="Map CSV columns to metadata fields")
    default_importance: float = Field(0.5, ge=0.0, le=1.0, description="Default importance for memories")
    tags: Optional[List[str]] = Field(None, description="Tags to apply to all imported memories")
    user_id: Optional[str] = Field(None, description="User ID for all memories")
    source: Optional[str] = Field(None, description="Import source identifier")


class BulkImportRequest(BaseModel):
    """Request model for bulk memory import."""
    format: ImportFormat
    data: str = Field(..., description="Base64 encoded data")
    options: ImportOptions = Field(default_factory=ImportOptions)


class ImportProgress(BaseModel):
    """Progress tracking for import job."""
    import_id: str
    status: ImportStatus
    total_records: int
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    duplicate_records: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    current_batch: int = 0
    total_batches: int = 0
    processing_time_seconds: Optional[float] = None


@dataclass
class MemoryRecord:
    """Internal representation of a memory to import."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.5
    content_hash: Optional[str] = None
    
    def calculate_hash(self) -> str:
        """Calculate hash for deduplication."""
        if not self.content_hash:
            content_normalized = self.content.lower().strip()
            self.content_hash = hashlib.sha256(content_normalized.encode()).hexdigest()
        return self.content_hash


class BulkImportService:
    """Simplified bulk import service with in-memory progress tracking."""
    
    def __init__(self, store: UnifiedVectorStore):
        self.store = store
        # In-memory storage for job progress (MVP solution)
        self._jobs: Dict[str, ImportProgress] = {}
        # Clean up old jobs periodically
        self._last_cleanup = datetime.utcnow()
        
    async def import_memories(
        self,
        request: BulkImportRequest,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """Start bulk import job."""
        import_id = str(uuid4())
        
        # Initialize progress tracking
        progress = ImportProgress(
            import_id=import_id,
            status=ImportStatus.PENDING,
            total_records=0,
            started_at=datetime.utcnow()
        )
        
        # Store progress in memory
        self._jobs[import_id] = progress
        self._cleanup_old_jobs()
        
        # Schedule background processing
        background_tasks.add_task(
            self._process_import,
            import_id,
            request
        )
        
        return {
            "import_id": import_id,
            "status": progress.status.value,
            "message": "Import job started",
            "progress_url": f"/api/v1/memories/import/{import_id}/status"
        }
        
    async def get_import_status(self, import_id: str) -> ImportProgress:
        """Get current status of import job."""
        if import_id not in self._jobs:
            raise HTTPException(status_code=404, detail="Import job not found")
            
        return self._jobs[import_id]
        
    def _cleanup_old_jobs(self):
        """Remove jobs older than 24 hours."""
        now = datetime.utcnow()
        if (now - self._last_cleanup).total_seconds() < 3600:  # Clean every hour
            return
            
        cutoff = now - timedelta(hours=24)
        old_jobs = [
            job_id for job_id, progress in self._jobs.items()
            if progress.started_at < cutoff
        ]
        
        for job_id in old_jobs:
            del self._jobs[job_id]
            
        self._last_cleanup = now
        logger.info(f"Cleaned up {len(old_jobs)} old import jobs")
        
    async def _process_import(self, import_id: str, request: BulkImportRequest):
        """Process import job in background."""
        progress = self._jobs[import_id]
        
        try:
            # Update status to validating
            progress.status = ImportStatus.VALIDATING
            
            # Parse and validate data
            records = await self._parse_import_data(request)
            progress.total_records = len(records)
            
            if progress.total_records == 0:
                raise ValueError("No valid records found in import data")
            
            # Calculate batches
            batch_size = request.options.batch_size
            progress.total_batches = (len(records) + batch_size - 1) // batch_size
            
            # Update status to processing
            progress.status = ImportStatus.PROCESSING
            
            # Process in batches
            for batch_num in range(progress.total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(records))
                batch = records[start_idx:end_idx]
                
                progress.current_batch = batch_num + 1
                
                # Process batch
                await self._process_batch(
                    batch,
                    request.options,
                    progress
                )
                
                # Update progress
                progress.processed_records = end_idx
                
                # Estimate completion time
                if progress.processed_records > 0:
                    elapsed = (datetime.utcnow() - progress.started_at).total_seconds()
                    rate = progress.processed_records / elapsed
                    remaining = progress.total_records - progress.processed_records
                    eta_seconds = remaining / rate if rate > 0 else 0
                    progress.estimated_completion = datetime.utcnow() + timedelta(seconds=eta_seconds)
                
            # Mark as completed
            progress.status = ImportStatus.COMPLETED
            if progress.failed_records > 0:
                progress.status = ImportStatus.PARTIAL
                
            progress.completed_at = datetime.utcnow()
            progress.processing_time_seconds = (
                progress.completed_at - progress.started_at
            ).total_seconds()
            
            logger.info(f"Import {import_id} completed: {progress.successful_records}/{progress.total_records} successful")
            
        except Exception as e:
            logger.error(f"Import {import_id} failed: {str(e)}")
            progress.status = ImportStatus.FAILED
            progress.errors.append({
                "error": "Import failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            progress.completed_at = datetime.utcnow()
            if progress.completed_at and progress.started_at:
                progress.processing_time_seconds = (
                    progress.completed_at - progress.started_at
                ).total_seconds()
            
    async def _parse_import_data(self, request: BulkImportRequest) -> List[MemoryRecord]:
        """Parse import data based on format."""
        records = []
        
        # Decode base64 data
        try:
            data = base64.b64decode(request.data).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decode base64 data: {str(e)}")
            
        # Parse based on format
        if request.format == ImportFormat.CSV:
            records = await self._parse_csv(data, request.options)
        elif request.format == ImportFormat.JSON:
            records = await self._parse_json(data, request.options)
        elif request.format == ImportFormat.JSONL:
            records = await self._parse_jsonl(data, request.options)
            
        return records
        
    async def _parse_csv(self, data: str, options: ImportOptions) -> List[MemoryRecord]:
        """Parse CSV data."""
        records = []
        
        try:
            # Use pandas for robust CSV parsing
            df = pd.read_csv(io.StringIO(data))
            
            # Validate required columns
            if 'content' not in df.columns:
                raise ValueError("CSV must have 'content' column")
                
            # Apply metadata mapping
            metadata_columns = []
            if options.metadata_mapping:
                metadata_columns = list(options.metadata_mapping.keys())
            else:
                # Auto-detect metadata columns
                metadata_columns = [
                    col for col in df.columns 
                    if col not in ['content', 'importance_score']
                ]
                
            # Convert to records
            for _, row in df.iterrows():
                if pd.isna(row['content']) or str(row['content']).strip() == '':
                    continue
                    
                metadata = {}
                
                # Extract metadata
                for col in metadata_columns:
                    if col in row and pd.notna(row[col]):
                        mapped_name = (
                            options.metadata_mapping.get(col, col) 
                            if options.metadata_mapping else col
                        )
                        metadata[mapped_name] = str(row[col])
                        
                # Add default metadata
                if options.tags:
                    metadata['tags'] = options.tags
                if options.user_id:
                    metadata['user_id'] = options.user_id
                if options.source:
                    metadata['import_source'] = options.source
                metadata['import_timestamp'] = datetime.utcnow().isoformat()
                    
                # Create record
                record = MemoryRecord(
                    content=str(row['content']),
                    metadata=metadata,
                    importance_score=float(row.get('importance_score', options.default_importance))
                )
                record.calculate_hash()
                records.append(record)
                
        except Exception as e:
            raise ValueError(f"CSV parsing error: {str(e)}")
            
        return records
        
    async def _parse_json(self, data: str, options: ImportOptions) -> List[MemoryRecord]:
        """Parse JSON data."""
        records = []
        
        try:
            json_data = json.loads(data)
            
            # Handle both array and object with memories array
            if isinstance(json_data, list):
                memories = json_data
            elif isinstance(json_data, dict) and 'memories' in json_data:
                memories = json_data['memories']
            else:
                raise ValueError("JSON must be array or object with 'memories' array")
                
            for idx, item in enumerate(memories):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {idx} is not an object")
                    
                if 'content' not in item or not item['content']:
                    continue
                    
                metadata = item.get('metadata', {})
                
                # Add default metadata
                if options.tags:
                    metadata['tags'] = options.tags
                if options.user_id:
                    metadata['user_id'] = options.user_id
                if options.source:
                    metadata['import_source'] = options.source
                metadata['import_timestamp'] = datetime.utcnow().isoformat()
                    
                record = MemoryRecord(
                    content=item['content'],
                    metadata=metadata,
                    importance_score=item.get('importance_score', options.default_importance)
                )
                record.calculate_hash()
                records.append(record)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"JSON parsing error: {str(e)}")
            
        return records
        
    async def _parse_jsonl(self, data: str, options: ImportOptions) -> List[MemoryRecord]:
        """Parse JSONL (newline-delimited JSON) data."""
        records = []
        
        for line_num, line in enumerate(data.strip().split('\n'), 1):
            if not line.strip():
                continue
                
            try:
                item = json.loads(line)
                
                if 'content' not in item or not item['content']:
                    continue
                    
                metadata = item.get('metadata', {})
                
                # Add default metadata
                if options.tags:
                    metadata['tags'] = options.tags
                if options.user_id:
                    metadata['user_id'] = options.user_id
                if options.source:
                    metadata['import_source'] = options.source
                metadata['import_timestamp'] = datetime.utcnow().isoformat()
                    
                record = MemoryRecord(
                    content=item['content'],
                    metadata=metadata,
                    importance_score=item.get('importance_score', options.default_importance)
                )
                record.calculate_hash()
                records.append(record)
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {line_num}: Invalid JSON - {str(e)}")
                
        return records
        
    async def _process_batch(
        self,
        batch: List[MemoryRecord],
        options: ImportOptions,
        progress: ImportProgress
    ):
        """Process a batch of records."""
        # For MVP, skip deduplication check
        # In production, would query existing hashes
        
        # Process records concurrently
        tasks = []
        for record in batch:
            tasks.append(self._store_single_memory(record, options, progress))
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _store_single_memory(
        self,
        record: MemoryRecord,
        options: ImportOptions,
        progress: ImportProgress
    ):
        """Store a single memory record."""
        try:
            # Check if duplicate (simplified for MVP)
            if options.deduplicate:
                # In production, would check against existing memories
                # For now, just track it
                pass
                
            # Store memory
            from .models import MemoryRequest
            memory_request = MemoryRequest(
                content=record.content,
                metadata=record.metadata,
                importance_score=record.importance_score
            )
            
            memory_response = await self.store.store_memory(memory_request)
            progress.successful_records += 1
            
        except Exception as e:
            progress.failed_records += 1
            error_msg = str(e)
            
            # Track error (limit details for large imports)
            if len(progress.errors) < 100:
                progress.errors.append({
                    "content_preview": record.content[:100] + "..." if len(record.content) > 100 else record.content,
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            logger.error(f"Failed to store memory: {error_msg}")