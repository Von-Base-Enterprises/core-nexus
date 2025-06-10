"""
Lightweight Graph Store using SQLite for node and relationship storage.
Optimized for Day-1 slice with minimal dependencies.
"""

import json
import os
import sqlite3
from typing import Any


class LiteGraphStore:
    """Simple SQLite-based graph store for Day-1 slice demo"""

    def __init__(self, db_file: str = "graph_store.db"):
        self.db_file = db_file
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        os.makedirs(os.path.dirname(self.db_file) if os.path.dirname(self.db_file) else ".", exist_ok=True)

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # Create nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create edges table for relationships
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT,
                    target_id TEXT,
                    relationship_type TEXT,
                    properties TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES nodes (id),
                    FOREIGN KEY (target_id) REFERENCES nodes (id)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_id ON nodes (id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges (source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges (target_id)")

            conn.commit()

    def add_node(self, node_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add or update a node"""
        metadata_json = json.dumps(metadata or {})

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO nodes (id, content, metadata)
                VALUES (?, ?, ?)
            """, (node_id, content, metadata_json))
            conn.commit()

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Get node by ID"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, content, metadata, created_at
                FROM nodes WHERE id = ?
            """, (node_id,))

            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "content": result[1],
                    "metadata": json.loads(result[2]) if result[2] else {},
                    "created_at": result[3]
                }
        return None

    def add_edge(self, source_id: str, target_id: str, relationship_type: str,
                 properties: dict[str, Any] | None = None) -> int:
        """Add relationship between nodes"""
        properties_json = json.dumps(properties or {})

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO edges (source_id, target_id, relationship_type, properties)
                VALUES (?, ?, ?, ?)
            """, (source_id, target_id, relationship_type, properties_json))
            conn.commit()
            return cursor.lastrowid

    def get_neighbors(self, node_id: str, relationship_type: str | None = None) -> list[dict[str, Any]]:
        """Get neighboring nodes"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            query = """
                SELECT n.id, n.content, n.metadata, e.relationship_type, e.properties
                FROM nodes n
                JOIN edges e ON (n.id = e.target_id OR n.id = e.source_id)
                WHERE (e.source_id = ? OR e.target_id = ?) AND n.id != ?
            """
            params = [node_id, node_id, node_id]

            if relationship_type:
                query += " AND e.relationship_type = ?"
                params.append(relationship_type)

            cursor.execute(query, params)
            results = cursor.fetchall()

            neighbors = []
            for result in results:
                neighbors.append({
                    "id": result[0],
                    "content": result[1],
                    "metadata": json.loads(result[2]) if result[2] else {},
                    "relationship_type": result[3],
                    "relationship_properties": json.loads(result[4]) if result[4] else {}
                })

            return neighbors

    def search_nodes(self, content_pattern: str) -> list[dict[str, Any]]:
        """Search nodes by content pattern"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, content, metadata, created_at
                FROM nodes
                WHERE content LIKE ?
            """, (f"%{content_pattern}%",))

            results = cursor.fetchall()
            nodes = []
            for result in results:
                nodes.append({
                    "id": result[0],
                    "content": result[1],
                    "metadata": json.loads(result[2]) if result[2] else {},
                    "created_at": result[3]
                })

            return nodes

    def delete_node(self, node_id: str) -> bool:
        """Delete node and its edges"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # Delete edges first
            cursor.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))

            # Delete node
            cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))

            conn.commit()
            return cursor.rowcount > 0

    def count_nodes(self) -> int:
        """Get total number of nodes"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM nodes")
            return cursor.fetchone()[0]

    def count_edges(self) -> int:
        """Get total number of edges"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM edges")
            return cursor.fetchone()[0]
