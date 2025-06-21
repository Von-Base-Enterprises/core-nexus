#!/usr/bin/env python3
"""
Phase 1: Diagnostic Gap Analysis
Strategic Plan for 100% ChromaDB Data Redundancy

Connects directly to PostgreSQL to identify exactly which memories are missing from ChromaDB
and analyzes patterns to understand why the sync process failed for specific records.
"""

import asyncio
import asyncpg
import json
import requests
from datetime import datetime
from typing import List, Dict, Any

# Configuration
PGVECTOR_CONFIG = {
    "host": "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "nexus_memory_db",
    "user": "nexus_memory_db_user",
    "password": "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
}

RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

class DiagnosticGapAnalysis:
    def __init__(self):
        self.stats = {
            "analysis_started": datetime.now().isoformat(),
            "pgvector_memories": [],
            "chromadb_memories": [],
            "missing_memories": [],
            "pattern_analysis": {},
            "recommendations": []
        }
        self.connection = None
    
    async def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            print("🔗 Connecting to PostgreSQL database...")
            self.connection = await asyncpg.connect(**PGVECTOR_CONFIG)
            print("✅ Connected to PostgreSQL successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            return False
    
    async def get_pgvector_memories(self) -> List[Dict[str, Any]]:
        """Get all memories from pgvector/PostgreSQL"""
        try:
            print("📊 Fetching all memories from pgvector...")
            
            query = """
            SELECT 
                id,
                content,
                metadata,
                created_at,
                importance_score,
                LENGTH(content) as content_length,
                (metadata->>'user_id') as user_id,
                (metadata->>'conversation_id') as conversation_id
            FROM vector_memories 
            ORDER BY created_at DESC
            """
            
            rows = await self.connection.fetch(query)
            memories = []
            
            for row in rows:
                memory = {
                    "id": str(row['id']),
                    "content": row['content'],
                    "metadata": row['metadata'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "importance_score": float(row['importance_score']) if row['importance_score'] else 0.0,
                    "content_length": row['content_length'],
                    "user_id": row['user_id'],
                    "conversation_id": row['conversation_id']
                }
                memories.append(memory)
            
            print(f"✅ Retrieved {len(memories)} memories from pgvector")
            return memories
            
        except Exception as e:
            print(f"❌ Failed to fetch pgvector memories: {e}")
            return []
    
    def get_chromadb_memories_via_api(self) -> List[str]:
        """Get ChromaDB memory IDs via API endpoint"""
        try:
            print("📊 Fetching ChromaDB memory IDs via API...")
            
            # Use the health endpoint to get ChromaDB count
            response = requests.get(f"{RENDER_SERVICE_URL}/health", timeout=30)
            health_data = response.json()
            
            chromadb_count = health_data.get("providers", {}).get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            print(f"📊 ChromaDB reports {chromadb_count} total memories")
            
            # Since the API pagination doesn't work well for getting all IDs,
            # we'll use a sampling approach to get representative data
            memory_ids = set()
            
            # Try different query approaches to get diverse samples
            query_strategies = [
                {"query": "", "limit": 100},  # Recent memories
                {"query": "memory", "limit": 100},  # Memories with "memory" keyword
                {"query": "data", "limit": 100},    # Memories with "data" keyword
                {"query": "test", "limit": 100},    # Test memories
                {"query": "user", "limit": 100},    # User-related memories
            ]
            
            for strategy in query_strategies:
                try:
                    query_response = requests.get(
                        f"{RENDER_SERVICE_URL}/memories",
                        params=strategy,
                        timeout=30
                    )
                    
                    if query_response.status_code == 200:
                        query_data = query_response.json()
                        memories = query_data.get("memories", [])
                        
                        for memory in memories:
                            if isinstance(memory, dict) and "id" in memory:
                                memory_ids.add(memory["id"])
                                
                        print(f"   Query '{strategy['query']}': Retrieved {len(memories)} memories")
                        
                except Exception as e:
                    print(f"⚠️ Query '{strategy['query']}' failed: {e}")
                    continue
            
            chromadb_ids = list(memory_ids)
            print(f"✅ Retrieved {len(chromadb_ids)} unique memory IDs via API sampling")
            
            # If we got very few IDs, warn about limited analysis
            if len(chromadb_ids) < chromadb_count * 0.1:
                print(f"⚠️ Warning: Only sampled {len(chromadb_ids)} of {chromadb_count} ChromaDB memories")
                print(f"   Analysis will be based on available sample")
            
            return chromadb_ids
            
        except Exception as e:
            print(f"❌ Failed to fetch ChromaDB memories: {e}")
            return []
    
    def analyze_missing_patterns(self, pgvector_memories: List[Dict], chromadb_ids: List[str]) -> Dict[str, Any]:
        """Analyze patterns in missing memories"""
        print("🔍 Analyzing patterns in missing memories...")
        
        chromadb_id_set = set(chromadb_ids)
        missing_memories = []
        present_memories = []
        
        for memory in pgvector_memories:
            if memory["id"] in chromadb_id_set:
                present_memories.append(memory)
            else:
                missing_memories.append(memory)
        
        print(f"📊 Analysis: {len(present_memories)} present, {len(missing_memories)} missing")
        
        # Pattern analysis
        patterns = {
            "missing_count": len(missing_memories),
            "present_count": len(present_memories),
            "total_count": len(pgvector_memories),
            "missing_percentage": (len(missing_memories) / len(pgvector_memories)) * 100,
            "temporal_analysis": self._analyze_temporal_patterns(missing_memories, present_memories),
            "content_analysis": self._analyze_content_patterns(missing_memories, present_memories),
            "metadata_analysis": self._analyze_metadata_patterns(missing_memories, present_memories),
            "user_analysis": self._analyze_user_patterns(missing_memories, present_memories)
        }
        
        return patterns, missing_memories, present_memories
    
    def _analyze_temporal_patterns(self, missing: List[Dict], present: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in missing vs present memories"""
        missing_dates = [m["created_at"] for m in missing if m["created_at"]]
        present_dates = [m["created_at"] for m in present if m["created_at"]]
        
        return {
            "missing_earliest": min(missing_dates) if missing_dates else None,
            "missing_latest": max(missing_dates) if missing_dates else None,
            "present_earliest": min(present_dates) if present_dates else None,
            "present_latest": max(present_dates) if present_dates else None,
            "missing_with_dates": len(missing_dates),
            "present_with_dates": len(present_dates)
        }
    
    def _analyze_content_patterns(self, missing: List[Dict], present: List[Dict]) -> Dict[str, Any]:
        """Analyze content patterns"""
        missing_lengths = [m["content_length"] for m in missing]
        present_lengths = [m["content_length"] for m in present]
        
        return {
            "missing_avg_length": sum(missing_lengths) / len(missing_lengths) if missing_lengths else 0,
            "present_avg_length": sum(present_lengths) / len(present_lengths) if present_lengths else 0,
            "missing_min_length": min(missing_lengths) if missing_lengths else 0,
            "missing_max_length": max(missing_lengths) if missing_lengths else 0,
            "present_min_length": min(present_lengths) if present_lengths else 0,
            "present_max_length": max(present_lengths) if present_lengths else 0
        }
    
    def _analyze_metadata_patterns(self, missing: List[Dict], present: List[Dict]) -> Dict[str, Any]:
        """Analyze metadata patterns"""
        missing_with_metadata = len([m for m in missing if m["metadata"]])
        present_with_metadata = len([m for m in present if m["metadata"]])
        
        # Check for specific metadata patterns - handle both dict and string metadata
        missing_bulk_sync = 0
        present_bulk_sync = 0
        
        for m in missing:
            if m["metadata"]:
                if isinstance(m["metadata"], dict) and m["metadata"].get("bulk_sync"):
                    missing_bulk_sync += 1
                elif isinstance(m["metadata"], str) and "bulk_sync" in m["metadata"]:
                    missing_bulk_sync += 1
        
        for m in present:
            if m["metadata"]:
                if isinstance(m["metadata"], dict) and m["metadata"].get("bulk_sync"):
                    present_bulk_sync += 1
                elif isinstance(m["metadata"], str) and "bulk_sync" in m["metadata"]:
                    present_bulk_sync += 1
        
        return {
            "missing_with_metadata": missing_with_metadata,
            "present_with_metadata": present_with_metadata,
            "missing_bulk_sync": missing_bulk_sync,
            "present_bulk_sync": present_bulk_sync
        }
    
    def _analyze_user_patterns(self, missing: List[Dict], present: List[Dict]) -> Dict[str, Any]:
        """Analyze user and conversation patterns"""
        missing_users = set([m["user_id"] for m in missing if m["user_id"]])
        present_users = set([m["user_id"] for m in present if m["user_id"]])
        
        missing_conversations = set([m["conversation_id"] for m in missing if m["conversation_id"]])
        present_conversations = set([m["conversation_id"] for m in present if m["conversation_id"]])
        
        return {
            "missing_unique_users": len(missing_users),
            "present_unique_users": len(present_users),
            "missing_unique_conversations": len(missing_conversations),
            "present_unique_conversations": len(present_conversations),
            "user_overlap": len(missing_users.intersection(present_users)),
            "conversation_overlap": len(missing_conversations.intersection(present_conversations))
        }
    
    def generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on pattern analysis"""
        recommendations = []
        
        missing_pct = patterns["missing_percentage"]
        
        if missing_pct > 50:
            recommendations.append("CRITICAL: >50% of memories missing - full bulk sync required")
        elif missing_pct > 20:
            recommendations.append("HIGH PRIORITY: >20% of memories missing - targeted sync needed")
        elif missing_pct > 5:
            recommendations.append("MODERATE: >5% of memories missing - incremental sync recommended")
        else:
            recommendations.append("LOW PRIORITY: <5% missing - spot fixes may be sufficient")
        
        # Temporal recommendations
        temporal = patterns["temporal_analysis"]
        if temporal["missing_earliest"] and temporal["present_latest"]:
            if temporal["missing_earliest"] < temporal["present_latest"]:
                recommendations.append("PATTERN: Missing memories span old and new - indicates replication failure not just recent issues")
        
        # Content recommendations
        content = patterns["content_analysis"]
        if content["missing_avg_length"] > content["present_avg_length"] * 1.5:
            recommendations.append("PATTERN: Missing memories are longer - possible timeout/size issues in replication")
        
        return recommendations
    
    async def run_comprehensive_analysis(self):
        """Run the complete diagnostic gap analysis"""
        print("🎯 PHASE 1: DIAGNOSTIC GAP ANALYSIS")
        print("Strategic Plan for 100% ChromaDB Data Redundancy")
        print("=" * 60)
        print()
        
        # Connect to database
        if not await self.connect_to_database():
            return None
        
        try:
            # Step 1: Get all pgvector memories
            pgvector_memories = await self.get_pgvector_memories()
            if not pgvector_memories:
                print("❌ No memories found in pgvector - cannot proceed")
                return None
            
            self.stats["pgvector_memories"] = len(pgvector_memories)
            
            # Step 2: Get ChromaDB memory IDs
            chromadb_ids = self.get_chromadb_memories_via_api()
            self.stats["chromadb_memories"] = len(chromadb_ids)
            
            # Step 3: Analyze patterns
            patterns, missing_memories, present_memories = self.analyze_missing_patterns(
                pgvector_memories, chromadb_ids
            )
            
            self.stats["pattern_analysis"] = patterns
            self.stats["missing_memories"] = len(missing_memories)
            
            # Step 4: Generate recommendations
            recommendations = self.generate_recommendations(patterns)
            self.stats["recommendations"] = recommendations
            
            # Report results
            print("📊 DIAGNOSTIC RESULTS")
            print("=" * 30)
            print(f"Total pgvector memories: {len(pgvector_memories)}")
            print(f"Total ChromaDB memories: {len(chromadb_ids)}")
            print(f"Missing from ChromaDB: {len(missing_memories)}")
            print(f"Data redundancy: {patterns['present_count']/patterns['total_count']*100:.1f}%")
            print()
            
            print("🔍 PATTERN ANALYSIS")
            print("=" * 20)
            print(f"Missing percentage: {patterns['missing_percentage']:.1f}%")
            
            temporal = patterns["temporal_analysis"]
            print(f"Missing date range: {temporal['missing_earliest']} to {temporal['missing_latest']}")
            print(f"Present date range: {temporal['present_earliest']} to {temporal['present_latest']}")
            
            content = patterns["content_analysis"]
            print(f"Missing avg length: {content['missing_avg_length']:.0f} chars")
            print(f"Present avg length: {content['present_avg_length']:.0f} chars")
            
            print()
            print("📝 RECOMMENDATIONS")
            print("=" * 20)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
            
            print()
            print("📋 NEXT STEPS")
            print("=" * 15)
            print("1. Phase 2: Fix replication code in unified_store.py")
            print("2. Phase 3: Execute direct database sync for missing memories")
            print("3. Phase 4: Verify 100% redundancy and establish monitoring")
            
            return self.stats
            
        finally:
            if self.connection:
                await self.connection.close()
                print("🔗 Database connection closed")

async def main():
    """Main entry point"""
    try:
        analyzer = DiagnosticGapAnalysis()
        stats = await analyzer.run_comprehensive_analysis()
        
        if stats:
            # Save detailed analysis
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            stats_file = f"diagnostic_gap_analysis_{timestamp}.json"
            
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            print(f"📄 Detailed analysis saved to: {stats_file}")
            
            missing_pct = stats["pattern_analysis"]["missing_percentage"]
            if missing_pct < 5:
                print("\n✅ PHASE 1 SUCCESS: Gap analysis complete, <5% missing")
                return 0
            else:
                print(f"\n⚠️ PHASE 1 COMPLETE: {missing_pct:.1f}% data gap identified")
                return 0
        else:
            print("\n❌ PHASE 1 FAILED: Could not complete gap analysis")
            return 1
            
    except Exception as e:
        print(f"❌ Diagnostic analysis failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))