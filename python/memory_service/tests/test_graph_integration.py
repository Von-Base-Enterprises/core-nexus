"""
Integration tests for Knowledge Graph functionality.

Tests the complete flow from memory storage through entity extraction
to relationship inference, using mock components.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4, UUID
import json


class MockMemory:
    """Mock memory for testing."""
    def __init__(self, content: str, metadata: Dict = None):
        self.id = uuid4()
        self.content = content
        self.metadata = metadata or {}
        self.embedding = [0.1] * 1536
        self.importance_score = metadata.get('importance_score', 0.5) if metadata else 0.5
        self.created_at = datetime.utcnow()


class MockGraphStore:
    """Mock graph store for integration testing."""
    
    def __init__(self):
        self.nodes = {}
        self.relationships = {}
        self.memory_entity_map = {}
        self.extraction_calls = []
        self.inference_calls = []
    
    async def add_node(self, entity_name: str, entity_type: str, properties: Dict = None):
        """Add a node to the graph."""
        node_id = uuid4()
        self.nodes[node_id] = {
            'id': node_id,
            'entity_name': entity_name,
            'entity_type': entity_type,
            'properties': properties or {},
            'mention_count': 1,
            'first_seen': datetime.utcnow(),
            'last_seen': datetime.utcnow()
        }
        return node_id
    
    async def add_relationship(self, from_id: UUID, to_id: UUID, rel_type: str, strength: float):
        """Add a relationship to the graph."""
        rel_id = uuid4()
        self.relationships[rel_id] = {
            'id': rel_id,
            'from_node_id': from_id,
            'to_node_id': to_id,
            'relationship_type': rel_type,
            'strength': strength,
            'confidence': 0.8,
            'occurrence_count': 1
        }
        return rel_id
    
    async def link_memory_to_entity(self, memory_id: UUID, entity_id: UUID):
        """Link a memory to an entity."""
        link_id = uuid4()
        self.memory_entity_map[link_id] = {
            'memory_id': memory_id,
            'entity_id': entity_id
        }
        return link_id
    
    def get_entity_memories(self, entity_name: str) -> List[UUID]:
        """Get all memories linked to an entity."""
        entity_ids = [
            node['id'] for node in self.nodes.values()
            if node['entity_name'] == entity_name
        ]
        
        memory_ids = []
        for link in self.memory_entity_map.values():
            if link['entity_id'] in entity_ids:
                memory_ids.append(link['memory_id'])
        
        return memory_ids


class TestGraphIntegration:
    """Integration tests for the knowledge graph system."""
    
    @pytest.fixture
    def mock_graph_store(self):
        """Create a mock graph store."""
        return MockGraphStore()
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for testing."""
        return [
            MockMemory(
                "OpenAI released GPT-4 with improved reasoning capabilities",
                {'source': 'news', 'importance_score': 0.9}
            ),
            MockMemory(
                "Microsoft invested heavily in OpenAI for AI development",
                {'source': 'news', 'importance_score': 0.8}
            ),
            MockMemory(
                "GPT-4 powers many Microsoft products including Copilot",
                {'source': 'article', 'importance_score': 0.7}
            ),
            MockMemory(
                "Anthropic competes with OpenAI in the AI space",
                {'source': 'analysis', 'importance_score': 0.8}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_entity_extraction_flow(self, mock_graph_store, sample_memories):
        """Test the complete entity extraction flow."""
        # Simulate entity extraction for each memory
        extracted_entities = {
            sample_memories[0].id: [
                ('OpenAI', 'organization'),
                ('GPT-4', 'product'),
            ],
            sample_memories[1].id: [
                ('Microsoft', 'organization'),
                ('OpenAI', 'organization'),
            ],
            sample_memories[2].id: [
                ('GPT-4', 'product'),
                ('Microsoft', 'organization'),
                ('Copilot', 'product'),
            ],
            sample_memories[3].id: [
                ('Anthropic', 'organization'),
                ('OpenAI', 'organization'),
            ]
        }
        
        # Process each memory
        entity_registry = {}  # Track unique entities
        
        for memory in sample_memories:
            entities = extracted_entities.get(memory.id, [])
            
            for entity_name, entity_type in entities:
                # Add or update entity
                if entity_name not in entity_registry:
                    entity_id = await mock_graph_store.add_node(
                        entity_name, entity_type
                    )
                    entity_registry[entity_name] = entity_id
                else:
                    # Update mention count
                    entity_id = entity_registry[entity_name]
                    node = mock_graph_store.nodes[entity_id]
                    node['mention_count'] += 1
                    node['last_seen'] = datetime.utcnow()
                
                # Link memory to entity
                await mock_graph_store.link_memory_to_entity(
                    memory.id, entity_id
                )
        
        # Verify extraction results
        assert len(mock_graph_store.nodes) == 5  # OpenAI, GPT-4, Microsoft, Copilot, Anthropic
        assert mock_graph_store.nodes[entity_registry['OpenAI']]['mention_count'] == 3
        assert mock_graph_store.nodes[entity_registry['Microsoft']]['mention_count'] == 2
        assert mock_graph_store.nodes[entity_registry['GPT-4']]['mention_count'] == 2
    
    @pytest.mark.asyncio
    async def test_relationship_inference_flow(self, mock_graph_store, sample_memories):
        """Test the complete relationship inference flow."""
        # First, create entities
        entities = {
            'OpenAI': await mock_graph_store.add_node('OpenAI', 'organization'),
            'GPT-4': await mock_graph_store.add_node('GPT-4', 'product'),
            'Microsoft': await mock_graph_store.add_node('Microsoft', 'organization'),
            'Anthropic': await mock_graph_store.add_node('Anthropic', 'organization'),
        }
        
        # Infer relationships based on co-occurrence
        relationships = [
            # From memory 1: OpenAI released GPT-4
            (entities['OpenAI'], entities['GPT-4'], 'develops', 0.9),
            
            # From memory 2: Microsoft invested in OpenAI
            (entities['Microsoft'], entities['OpenAI'], 'invests_in', 0.8),
            
            # From memory 3: GPT-4 powers Microsoft products
            (entities['GPT-4'], entities['Microsoft'], 'used_by', 0.7),
            
            # From memory 4: Anthropic competes with OpenAI
            (entities['Anthropic'], entities['OpenAI'], 'competes_with', 0.8),
        ]
        
        for from_id, to_id, rel_type, strength in relationships:
            await mock_graph_store.add_relationship(
                from_id, to_id, rel_type, strength
            )
        
        # Verify relationships
        assert len(mock_graph_store.relationships) == 4
        
        # Check specific relationships
        ms_openai_rels = [
            r for r in mock_graph_store.relationships.values()
            if r['from_node_id'] == entities['Microsoft'] 
            and r['to_node_id'] == entities['OpenAI']
        ]
        assert len(ms_openai_rels) == 1
        assert ms_openai_rels[0]['relationship_type'] == 'invests_in'
    
    @pytest.mark.asyncio
    async def test_entity_memory_correlation(self, mock_graph_store, sample_memories):
        """Test that entities are correctly linked to source memories."""
        # Create entities and link to memories
        openai_id = await mock_graph_store.add_node('OpenAI', 'organization')
        
        # Link OpenAI to memories 0, 1, and 3
        for i in [0, 1, 3]:
            await mock_graph_store.link_memory_to_entity(
                sample_memories[i].id, openai_id
            )
        
        # Query memories by entity
        openai_memories = mock_graph_store.get_entity_memories('OpenAI')
        
        assert len(openai_memories) == 3
        assert sample_memories[0].id in openai_memories
        assert sample_memories[1].id in openai_memories
        assert sample_memories[3].id in openai_memories
        assert sample_memories[2].id not in openai_memories
    
    @pytest.mark.asyncio
    async def test_graph_traversal(self, mock_graph_store):
        """Test graph traversal capabilities."""
        # Create a simple graph
        nodes = {
            'A': await mock_graph_store.add_node('Company A', 'organization'),
            'B': await mock_graph_store.add_node('Product B', 'product'),
            'C': await mock_graph_store.add_node('Company C', 'organization'),
            'D': await mock_graph_store.add_node('Technology D', 'technology'),
        }
        
        # Create relationships: A -> B -> C -> D
        await mock_graph_store.add_relationship(nodes['A'], nodes['B'], 'develops', 0.9)
        await mock_graph_store.add_relationship(nodes['B'], nodes['C'], 'used_by', 0.8)
        await mock_graph_store.add_relationship(nodes['C'], nodes['D'], 'uses', 0.7)
        
        # Implement simple traversal
        def get_connected_nodes(start_id: UUID, max_depth: int = 2):
            """Get all nodes connected within max_depth."""
            visited = set()
            to_visit = [(start_id, 0)]
            connected = []
            
            while to_visit:
                current_id, depth = to_visit.pop(0)
                if current_id in visited or depth > max_depth:
                    continue
                
                visited.add(current_id)
                if depth > 0:  # Don't include start node
                    connected.append(current_id)
                
                # Find outgoing relationships
                for rel in mock_graph_store.relationships.values():
                    if rel['from_node_id'] == current_id:
                        to_visit.append((rel['to_node_id'], depth + 1))
            
            return connected
        
        # Test traversal from A
        connected_from_a = get_connected_nodes(nodes['A'], max_depth=2)
        assert nodes['B'] in connected_from_a  # Direct connection
        assert nodes['C'] in connected_from_a  # 2-hop connection
        assert nodes['D'] not in connected_from_a  # Beyond max_depth
        
        # Test with larger depth
        all_connected = get_connected_nodes(nodes['A'], max_depth=3)
        assert len(all_connected) == 3  # B, C, and D
    
    @pytest.mark.asyncio
    async def test_adm_scoring_integration(self, mock_graph_store, sample_memories):
        """Test ADM scoring integration with graph components."""
        # Simulate ADM scoring for entities based on memory importance
        entities = {}
        
        for memory in sample_memories:
            # Extract entities (simplified)
            if "OpenAI" in memory.content:
                if "OpenAI" not in entities:
                    entities["OpenAI"] = await mock_graph_store.add_node(
                        "OpenAI", "organization"
                    )
                # Update importance based on memory
                node = mock_graph_store.nodes[entities["OpenAI"]]
                node['importance_score'] = max(
                    node.get('importance_score', 0.5),
                    memory.importance_score
                )
        
        # Verify ADM influence
        openai_node = mock_graph_store.nodes[entities["OpenAI"]]
        assert openai_node['importance_score'] == 0.9  # Highest from memories
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_graph_store):
        """Test concurrent entity extraction and relationship inference."""
        # Create many memories
        memories = [
            MockMemory(f"Company {i} develops Product {i+1}", {'importance_score': 0.5})
            for i in range(10)
        ]
        
        async def process_memory(memory: MockMemory):
            """Process a single memory."""
            # Extract entities
            company = f"Company {memory.content.split()[1]}"
            product = f"Product {memory.content.split()[-1]}"
            
            # Add nodes
            company_id = await mock_graph_store.add_node(company, 'organization')
            product_id = await mock_graph_store.add_node(product, 'product')
            
            # Add relationship
            await mock_graph_store.add_relationship(
                company_id, product_id, 'develops', 0.8
            )
            
            # Link to memory
            await mock_graph_store.link_memory_to_entity(memory.id, company_id)
            await mock_graph_store.link_memory_to_entity(memory.id, product_id)
        
        # Process all memories concurrently
        await asyncio.gather(*[process_memory(m) for m in memories])
        
        # Verify results
        assert len(mock_graph_store.nodes) == 20  # 10 companies + 10 products
        assert len(mock_graph_store.relationships) == 10
        assert len(mock_graph_store.memory_entity_map) == 20  # 2 links per memory


class TestGraphQueries:
    """Test various graph query patterns."""
    
    @pytest.mark.asyncio
    async def test_entity_centric_query(self, mock_graph_store):
        """Test querying memories by entity."""
        # Setup graph
        entity_id = await mock_graph_store.add_node('Tesla', 'organization')
        
        # Create and link memories
        memory_ids = []
        for i in range(5):
            memory = MockMemory(f"Tesla news item {i}")
            memory_ids.append(memory.id)
            await mock_graph_store.link_memory_to_entity(memory.id, entity_id)
        
        # Query
        tesla_memories = mock_graph_store.get_entity_memories('Tesla')
        
        assert len(tesla_memories) == 5
        for mid in memory_ids:
            assert mid in tesla_memories
    
    @pytest.mark.asyncio
    async def test_relationship_based_query(self, mock_graph_store):
        """Test querying based on relationships."""
        # Create entities
        google = await mock_graph_store.add_node('Google', 'organization')
        deepmind = await mock_graph_store.add_node('DeepMind', 'organization')
        tensorflow = await mock_graph_store.add_node('TensorFlow', 'technology')
        
        # Create relationships
        await mock_graph_store.add_relationship(google, deepmind, 'owns', 0.9)
        await mock_graph_store.add_relationship(google, tensorflow, 'develops', 0.8)
        await mock_graph_store.add_relationship(deepmind, tensorflow, 'uses', 0.7)
        
        # Query: Find all entities that Google has relationships with
        google_relations = [
            r['to_node_id'] for r in mock_graph_store.relationships.values()
            if r['from_node_id'] == google
        ]
        
        assert len(google_relations) == 2
        assert deepmind in google_relations
        assert tensorflow in google_relations


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])