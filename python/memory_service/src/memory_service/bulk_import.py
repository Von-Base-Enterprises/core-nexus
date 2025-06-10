"""
Bulk Import API for Core Nexus Memory Service
Enterprise-grade bulk memory import with validation, deduplication, and progress tracking
"""

import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, validator

try:
    import aioredis
except ImportError:
    import redis.asyncio as aioredis
from loguru import logger

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


class DeduplicationStrategy(str, Enum):
    """How to handle duplicate memories."""
    SKIP = "skip"  # Skip duplicates
    OVERWRITE = "overwrite"  # Overwrite with new
    MERGE = "merge"  # Merge metadata
    CREATE_VERSION = "create_version"  # Keep both as versions


class ImportOptions(BaseModel):
    """Options for bulk import operation."""
    deduplicate: bool = Field(True, description="Check for duplicates")
    dedup_strategy: DeduplicationStrategy = Field(DeduplicationStrategy.SKIP)
    validate: bool = Field(True, description="Validate data before import")
    batch_size: int = Field(100, ge=10, le=1000, description="Processing batch size")
    metadata_mapping: dict[str, str] | None = Field(None, description="Map CSV columns to metadata fields")
    default_importance: float = Field(0.5, ge=0.0, le=1.0, description="Default importance for memories")
    tags: list[str] | None = Field(None, description="Tags to apply to all imported memories")
    user_id: str | None = Field(None, description="User ID for all memories")
    source: str | None = Field(None, description="Import source identifier")


class BulkImportRequest(BaseModel):
    """Request model for bulk memory import."""
    format: ImportFormat
    data: str | None = Field(None, description="Base64 encoded data or URL")
    options: ImportOptions = Field(default_factory=ImportOptions)

    @validator('data')
    def validate_data(cls, v, values):
        if not v and 'format' in values:
            raise ValueError("Data is required for import")
        return v


class ImportProgress(BaseModel):
    """Progress tracking for import job."""
    import_id: UUID
    status: ImportStatus
    total_records: int
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    duplicate_records: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    estimated_completion: datetime | None = None
    current_batch: int = 0
    total_batches: int = 0


class ImportResult(BaseModel):
    """Result of import operation."""
    import_id: UUID
    status: ImportStatus
    total_records: int
    successful: int
    failed: int
    duplicates: int
    processing_time_seconds: float
    errors: list[dict[str, Any]] = Field(default_factory=list)
    imported_memory_ids: list[UUID] = Field(default_factory=list)


@dataclass
class MemoryRecord:
    """Internal representation of a memory to import."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.5
    content_hash: str | None = None

    def calculate_hash(self) -> str:
        """Calculate hash for deduplication."""
        if not self.content_hash:
            # Hash content for deduplication
            content_normalized = self.content.lower().strip()
            self.content_hash = hashlib.sha256(content_normalized.encode()).hexdigest()
        return self.content_hash


class BulkImportService:
    """Service for handling bulk memory imports."""

    def __init__(self, store: UnifiedVectorStore, redis_url: str = "redis://localhost"):
        self.store = store
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def get_redis(self) -> aioredis.Redis:
        """Get Redis connection for job tracking."""
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url)
        return self._redis

    async def import_memories(
        self,
        request: BulkImportRequest,
        background_tasks: BackgroundTasks
    ) -> dict[str, Any]:
        """Start bulk import job."""
        import_id = uuid4()

        # Initialize progress tracking
        progress = ImportProgress(
            import_id=import_id,
            status=ImportStatus.PENDING,
            total_records=0,  # Will be updated after parsing
            started_at=datetime.utcnow()
        )

        # Store initial progress
        await self._update_progress(progress)

        # Schedule background processing
        background_tasks.add_task(
            self._process_import,
            import_id,
            request
        )

        return {
            "import_id": str(import_id),
            "status": progress.status,
            "message": "Import job started",
            "progress_url": f"/api/v1/memories/import/{import_id}/status"
        }

    async def get_import_status(self, import_id: UUID) -> ImportProgress:
        """Get current status of import job."""
        redis = await self.get_redis()

        key = f"import:{import_id}"
        data = await redis.get(key)

        if not data:
            raise HTTPException(status_code=404, detail="Import job not found")

        return ImportProgress.parse_raw(data)

    async def _process_import(self, import_id: UUID, request: BulkImportRequest):
        """Process import job in background."""
        progress = await self.get_import_status(import_id)

        try:
            # Update status to validating
            progress.status = ImportStatus.VALIDATING
            await self._update_progress(progress)

            # Parse and validate data
            records = await self._parse_import_data(request)
            progress.total_records = len(records)

            # Calculate batches
            batch_size = request.options.batch_size
            progress.total_batches = (len(records) + batch_size - 1) // batch_size

            # Update status to processing
            progress.status = ImportStatus.PROCESSING
            await self._update_progress(progress)

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
                    progress,
                    import_id
                )

                # Update progress
                progress.processed_records = end_idx
                await self._update_progress(progress)

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
            await self._update_progress(progress)

        except Exception as e:
            logger.error(f"Import {import_id} failed: {str(e)}")
            progress.status = ImportStatus.FAILED
            progress.errors.append({
                "error": "Import failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            progress.completed_at = datetime.utcnow()
            await self._update_progress(progress)

    async def _parse_import_data(self, request: BulkImportRequest) -> list[MemoryRecord]:
        """Parse import data based on format."""
        records = []

        # Decode base64 data if provided
        if request.data:
            import base64
            try:
                if request.data.startswith("http"):
                    # Fetch from URL
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(request.data) as response:
                            data = await response.text()
                else:
                    # Decode base64
                    data = base64.b64decode(request.data).decode('utf-8')
            except Exception as e:
                raise ValueError(f"Failed to decode data: {str(e)}")
        else:
            raise ValueError("No data provided")

        # Parse based on format
        if request.format == ImportFormat.CSV:
            records = await self._parse_csv(data, request.options)
        elif request.format == ImportFormat.JSON:
            records = await self._parse_json(data, request.options)
        elif request.format == ImportFormat.JSONL:
            records = await self._parse_jsonl(data, request.options)

        return records

    async def _parse_csv(self, data: str, options: ImportOptions) -> list[MemoryRecord]:
        """Parse CSV data."""
        records = []

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
            # Auto-detect metadata columns (all except content and importance_score)
            metadata_columns = [col for col in df.columns if col not in ['content', 'importance_score']]

        # Convert to records
        for _, row in df.iterrows():
            metadata = {}

            # Extract metadata
            for col in metadata_columns:
                if col in row and pd.notna(row[col]):
                    mapped_name = options.metadata_mapping.get(col, col) if options.metadata_mapping else col
                    metadata[mapped_name] = row[col]

            # Add default metadata
            if options.tags:
                metadata['tags'] = options.tags
            if options.user_id:
                metadata['user_id'] = options.user_id
            if options.source:
                metadata['import_source'] = options.source

            # Create record
            record = MemoryRecord(
                content=str(row['content']),
                metadata=metadata,
                importance_score=float(row.get('importance_score', options.default_importance))
            )
            record.calculate_hash()
            records.append(record)

        return records

    async def _parse_json(self, data: str, options: ImportOptions) -> list[MemoryRecord]:
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

            for item in memories:
                if 'content' not in item:
                    raise ValueError("Each memory must have 'content' field")

                metadata = item.get('metadata', {})

                # Add default metadata
                if options.tags:
                    metadata['tags'] = options.tags
                if options.user_id:
                    metadata['user_id'] = options.user_id
                if options.source:
                    metadata['import_source'] = options.source

                record = MemoryRecord(
                    content=item['content'],
                    metadata=metadata,
                    importance_score=item.get('importance_score', options.default_importance)
                )
                record.calculate_hash()
                records.append(record)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

        return records

    async def _parse_jsonl(self, data: str, options: ImportOptions) -> list[MemoryRecord]:
        """Parse JSONL (newline-delimited JSON) data."""
        records = []

        for line_num, line in enumerate(data.strip().split('\n'), 1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)

                if 'content' not in item:
                    raise ValueError(f"Line {line_num}: Missing 'content' field")

                metadata = item.get('metadata', {})

                # Add default metadata
                if options.tags:
                    metadata['tags'] = options.tags
                if options.user_id:
                    metadata['user_id'] = options.user_id
                if options.source:
                    metadata['import_source'] = options.source

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
        batch: list[MemoryRecord],
        options: ImportOptions,
        progress: ImportProgress,
        import_id: UUID
    ):
        """Process a batch of records."""
        # Check for duplicates if enabled
        if options.deduplicate:
            existing_hashes = await self._get_existing_hashes([r.content_hash for r in batch])
        else:
            existing_hashes = set()

        for record in batch:
            try:
                # Check duplicate
                if record.content_hash in existing_hashes:
                    progress.duplicate_records += 1

                    if options.dedup_strategy == DeduplicationStrategy.SKIP:
                        continue
                    elif options.dedup_strategy == DeduplicationStrategy.OVERWRITE:
                        # TODO: Implement overwrite logic
                        pass
                    elif options.dedup_strategy == DeduplicationStrategy.MERGE:
                        # TODO: Implement merge logic
                        pass

                # Store memory
                memory_id = await self.store.store(
                    content=record.content,
                    metadata=record.metadata,
                    importance_score=record.importance_score
                )

                progress.successful_records += 1

                # Track imported IDs (limited to prevent memory issues)
                if len(progress.imported_memory_ids) < 1000:
                    progress.imported_memory_ids.append(memory_id)

            except Exception as e:
                progress.failed_records += 1
                progress.errors.append({
                    "record": record.content[:100] + "...",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Limit error tracking
                if len(progress.errors) > 100:
                    progress.errors = progress.errors[-100:]

    async def _get_existing_hashes(self, hashes: list[str]) -> set:
        """Check which content hashes already exist."""
        # TODO: Implement efficient hash checking
        # For now, return empty set
        return set()

    async def _update_progress(self, progress: ImportProgress):
        """Update progress in Redis."""
        redis = await self.get_redis()

        key = f"import:{progress.import_id}"
        # Store for 24 hours
        await redis.setex(key, 86400, progress.json())

        # Publish progress update for real-time monitoring
        await redis.publish(f"import:{progress.import_id}:progress", progress.json())


# Needed imports
from datetime import timedelta
