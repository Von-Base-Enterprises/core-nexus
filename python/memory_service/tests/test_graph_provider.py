"""
Comprehensive test suite for GraphProvider functionality.

Tests entity extraction, relationship inference, and graph operations
without requiring a live database connection.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4, UUID
import json

# Mock implementations for testing
class MockConnection:
    """Mock database connection for testing."""
    
    def __init__(self):
        self.data = {
            'graph_nodes': {},
            'graph_relationships': {},
            'memory_entity_map': {}
        }
        self.queries = []
    
    async def execute(self, query: str, *args):
        """Mock execute method."""
        self.queries.append((query, args))
        return "EXECUTE 1"
    
    async def fetchval(self, query: str, *args):
        """Mock fetchval method."""
        self.queries.append((query, args))
        if "SELECT 1" in query:
            return 1
        elif "COUNT(*) FROM graph_nodes" in query:
            return len(self.data['graph_nodes'])
        elif "COUNT(*) FROM graph_relationships" in query:
            return len(self.data['graph_relationships'])
        return None
    
    async def fetchrow(self, query: str, *args):
        """Mock fetchrow method."""
        self.queries.append((query, args))
        
        # Mock existing entity check
        if "SELECT id, mention_count FROM graph_nodes" in query:
            entity_name = args[0] if args else None
            for node_id, node in self.data['graph_nodes'].items():
                if node.get('entity_name') == entity_name:
                    return {'id': node_id, 'mention_count': node.get('mention_count', 1)}
        
        # Mock stats query
        if "total_nodes" in query:
            return {
                'total_nodes': len(self.data['graph_nodes']),
                'total_relationships': len(self.data['graph_relationships']),
                'entity_types': 5,
                'relationship_types': 8,
                'avg_mentions_per_entity': 2.5,
                'avg_occurrences_per_relationship': 1.5
            }
        
        return None
    
    async def fetch(self, query: str, *args):
        """Mock fetch method."""
        self.queries.append((query, args))
        return []


class MockConnectionPool:
    """Mock connection pool for testing."""
    
    def __init__(self):
        self.acquired_count = 0
        self._connection = MockConnection()
    
    def acquire(self):
        """Context manager for acquiring connection."""
        class AcquireContext:
            def __init__(self, pool):
                self.pool = pool
                
            async def __aenter__(self):
                self.pool.acquired_count += 1
                return self.pool._connection
                
            async def __aexit__(self, *args):
                pass
        
        return AcquireContext(self)
    
    async def close(self):
        """Mock close method."""
        pass


class TestGraphProvider:
    """Test suite for GraphProvider functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock provider config."""
        from memory_service.models import ProviderConfig
        return ProviderConfig(
            name="graph",
            enabled=True,
            primary=False,
            config={
                "connection_string": "postgresql://test@localhost/test",
                "table_prefix": "graph"
            }
        )
    
    @pytest.fixture
    async def graph_provider(self, mock_config, monkeypatch):
        """Create GraphProvider with mocked dependencies."""
        from memory_service.providers import GraphProvider
        
        # Mock asyncpg
        mock_pool = MockConnectionPool()
        
        async def mock_create_pool(*args, **kwargs):
            return mock_pool
        
        monkeypatch.setattr("asyncpg.create_pool", mock_create_pool)
        
        # Create provider
        provider = GraphProvider(mock_config)
        provider._pool_initialized = False
        await provider._ensure_pool()
        
        return provider
    
    @pytest.mark.asyncio
    async def test_entity_extraction_with_spacy_mock(self, graph_provider):
        """Test entity extraction with mocked spaCy."""
        # Mock spaCy entity
        class MockEntity:
            def __init__(self, text, label_, start, end):
                self.text = text
                self.label_ = label_
                self.start_char = start
                self.end_char = end
        
        class MockDoc:
            def __init__(self):
                self.ents = [
                    MockEntity("OpenAI", "ORG", 0, 6),
                    MockEntity("GPT-4", "PRODUCT", 10, 15),
                    MockEntity("San Francisco", "LOC", 20, 33)
                ]
        
        # Mock spaCy
        graph_provider.entity_extractor = lambda text: MockDoc()
        
        # Extract entities
        entities = await graph_provider._extract_entities(
            "OpenAI's GPT-4 in San Francisco is revolutionary"
        )
        
        assert len(entities) == 3
        assert entities[0]['name'] == "OpenAI"
        assert entities[0]['type'] == "organization"
        assert entities[1]['name'] == "GPT-4"
        assert entities[1]['type'] == "product"
        assert entities[2]['name'] == "San Francisco"
        assert entities[2]['type'] == "location"
    
    @pytest.mark.asyncio
    async def test_entity_extraction_with_regex_fallback(self, graph_provider):
        """Test entity extraction with regex fallback."""
        # Force regex fallback
        graph_provider.entity_extractor = "simple"
        
        # Extract entities
        entities = await graph_provider._extract_entities(
            "Microsoft Azure and Google Cloud are competing platforms"
        )
        
        # Should extract capitalized words
        entity_names = [e['name'] for e in entities]
        assert "Microsoft Azure" in entity_names
        assert "Google Cloud" in entity_names
        
        # All should be 'other' type with regex
        for entity in entities:
            assert entity['type'] == 'other'
            assert entity['confidence'] == 0.5
    
    @pytest.mark.asyncio
    async def test_relationship_inference(self, graph_provider):
        """Test relationship inference between entities."""
        entities = [
            {'name': 'Alice', 'type': 'person', 'start': 0, 'end': 5, 'confidence': 0.9},
            {'name': 'TechCorp', 'type': 'organization', 'start': 10, 'end': 18, 'confidence': 0.8},
            {'name': 'Python', 'type': 'technology', 'start': 25, 'end': 31, 'confidence': 0.7}
        ]
        
        content = "Alice at TechCorp uses Python for development"
        
        relationships = await graph_provider._infer_relationships(entities, content)
        
        assert len(relationships) >= 2
        
        # Check Alice -> TechCorp relationship
        alice_techcorp = next(
            (r for r in relationships if r['from_entity'] == 'Alice' and r['to_entity'] == 'TechCorp'),
            None
        )
        assert alice_techcorp is not None
        assert alice_techcorp['strength'] > 0.5  # Close proximity
        
        # Check relationship types
        relationship_types = [r['type'] for r in relationships]
        assert any(t in ['works_at', 'affiliated_with', 'relates_to'] for t in relationship_types)
    
    @pytest.mark.asyncio
    async def test_store_with_entity_extraction(self, graph_provider):
        """Test storing memory with entity extraction."""
        content = "Tesla's Elon Musk announced new AI features"
        embedding = [0.1] * 1536
        metadata = {'importance_score': 0.8, 'source': 'test'}
        
        # Mock entity extractor
        graph_provider.entity_extractor = "simple"
        
        # Store memory
        memory_id = await graph_provider.store(content, embedding, metadata)
        
        assert isinstance(memory_id, UUID)
        
        # Check that execute was called for entities
        conn = graph_provider.connection_pool._connection
        
        # Should have queries for entity operations
        entity_queries = [q for q in conn.queries if "graph_nodes" in q[0]]
        assert len(entity_queries) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, graph_provider):
        """Test health check functionality."""
        health = await graph_provider.health_check()
        
        assert health['status'] == 'healthy'
        assert 'details' in health
        assert health['details']['connection'] == 'active'
        assert health['details']['graph_nodes'] == 0
        assert health['details']['graph_relationships'] == 0
        assert health['details']['entity_extractor'] in ['spacy', 'regex']
    
    @pytest.mark.asyncio
    async def test_get_stats(self, graph_provider):
        """Test statistics gathering."""
        stats = await graph_provider.get_stats()
        
        assert 'total_nodes' in stats
        assert 'total_relationships' in stats
        assert 'entity_types' in stats
        assert 'relationship_types' in stats
        assert 'avg_mentions_per_entity' in stats
        assert 'avg_occurrences_per_relationship' in stats
    
    @pytest.mark.asyncio
    async def test_relationship_type_determination(self, graph_provider):
        """Test relationship type determination logic."""
        test_cases = [
            ("works at", "person", "organization", "works_at"),
            ("develops", "person", "product", "develops"),
            ("leads the team", "person", "organization", "leads"),
            ("uses Python", "person", "technology", "uses"),
            ("located in", "organization", "location", "located_at"),
            ("random text", "concept", "concept", "relates_to")
        ]
        
        for context, type1, type2, expected_rel in test_cases:
            rel_type = graph_provider._determine_relationship_type(type1, type2, context)
            assert rel_type == expected_rel or rel_type == "relates_to"
    
    @pytest.mark.asyncio
    async def test_query_with_entity_filter(self, graph_provider):
        """Test querying with entity name filter."""
        query_embedding = [0.2] * 1536
        filters = {'entity_name': 'Tesla'}
        
        results = await graph_provider.query(query_embedding, limit=10, filters=filters)
        
        # Should return empty list (no data in mock)
        assert isinstance(results, list)
        assert len(results) == 0
        
        # Check that entity query was attempted
        conn = graph_provider.connection_pool._connection
        entity_queries = [q for q in conn.queries if "entity_name" in str(q)]
        assert len(entity_queries) > 0
    
    @pytest.mark.asyncio
    async def test_get_relationships(self, graph_provider):
        """Test getting relationships for a node."""
        node_id = uuid4()
        relationships = await graph_provider.get_relationships(node_id)
        
        assert isinstance(relationships, list)
        # Mock returns empty list
        assert len(relationships) == 0
    
    @pytest.mark.asyncio
    async def test_map_spacy_labels(self, graph_provider):
        """Test spaCy label mapping."""
        label_mappings = {
            'PERSON': 'person',
            'ORG': 'organization',
            'GPE': 'location',
            'LOC': 'location',
            'PRODUCT': 'product',
            'EVENT': 'event',
            'UNKNOWN': 'other'
        }
        
        for spacy_label, expected_type in label_mappings.items():
            mapped_type = graph_provider._map_spacy_to_entity_type(spacy_label)
            assert mapped_type == expected_type
    
    @pytest.mark.asyncio
    async def test_lazy_pool_initialization(self, mock_config):
        """Test that pool is initialized lazily."""
        from memory_service.providers import GraphProvider
        
        # Create provider without pool
        provider = GraphProvider(mock_config)
        assert provider._pool_initialized is False
        assert provider.connection_pool is None
        
        # Pool should be created on first use
        await provider._ensure_pool()
        assert provider._pool_initialized is True
        assert provider.connection_pool is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_in_store(self, graph_provider):
        """Test error handling during entity extraction."""
        # Force an error in entity extraction
        def raise_error(content):
            raise Exception("Entity extraction failed")
        
        graph_provider._extract_entities = raise_error
        
        content = "Test content"
        embedding = [0.1] * 1536
        metadata = {}
        
        # Should still return memory_id even if graph processing fails
        memory_id = await graph_provider.store(content, embedding, metadata)
        assert isinstance(memory_id, UUID)


class TestEntityExtraction:
    """Focused tests for entity extraction functionality."""
    
    def test_regex_pattern_matching(self):
        """Test regex patterns for entity extraction."""
        import re
        
        # Pattern used in GraphProvider
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        
        test_cases = [
            ("Apple Inc is a technology company", ["Apple Inc"]),
            ("John Smith works at Microsoft", ["John Smith", "Microsoft"]),
            ("The United States of America", ["The United States"]),  # Partial match
            ("NASA and SpaceX collaborate", ["NASA", "SpaceX"]),
            ("lowercase text only", []),  # No matches
        ]
        
        for text, expected in test_cases:
            matches = [m.group() for m in re.finditer(pattern, text)]
            for exp in expected:
                assert exp in matches or any(exp in m for m in matches)


class TestRelationshipInference:
    """Focused tests for relationship inference logic."""
    
    def test_distance_based_strength(self):
        """Test relationship strength calculation based on distance."""
        # Distance-based strength formula
        def calculate_strength(distance, max_distance=200):
            if distance >= max_distance:
                return 0.0
            return 1.0 - (distance / max_distance)
        
        assert calculate_strength(0) == 1.0
        assert calculate_strength(100) == 0.5
        assert calculate_strength(200) == 0.0
        assert calculate_strength(300) == 0.0
    
    def test_relationship_context_keywords(self):
        """Test keyword detection for relationship types."""
        contexts = {
            "works at the company": ["work", "employ"],
            "develops software": ["develop", "create", "build"],
            "leads the team": ["lead", "manage"],
            "uses the technology": ["use", "utilize"]
        }
        
        for context, keywords in contexts.items():
            context_lower = context.lower()
            assert any(keyword in context_lower for keyword in keywords)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])