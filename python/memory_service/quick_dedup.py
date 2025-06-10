#!/usr/bin/env python3
"""Quick deduplication - just delete duplicates"""

import asyncio

import asyncpg


async def quick_dedup():
    conn = await asyncpg.connect(
        'postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@'
        'dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db'
    )

    print("🧹 Quick Entity Deduplication")
    print("="*50)

    # Get initial count
    before = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
    print(f"Before: {before} entities")

    # Delete specific duplicates we know about
    deletions = [
        # VBE variants
        ("VBE", "Von Base Enterprises"),
        ("Von Base", "Von Base Enterprises"),
        ("von base", "Von Base Enterprises"),
        ("VBE (Von Base Enterprises)", "Von Base Enterprises"),
        ("Von Base Enterprises (VBE)", "Von Base Enterprises"),
        ("VBE XR Labs", "Von Base Enterprises"),

        # AI variants
        ("AI", "Artificial Intelligence"),
        ("artificial intelligence", "Artificial Intelligence"),

        # Database variants
        ("Postgres", "PostgreSQL"),
        ("postgres", "PostgreSQL"),

        # Test/junk entries
        ("The", None),
        ("Testing", None),
        ("test", None),

        # Other duplicates
        ("drones", "Drone Technology"),
        ("drone technology", "Drone Technology"),
        ("digital media", "Digital Media Services"),
        ("3d mapping", "3D Mapping"),
        ("langchain", "Langchain"),
        ("nike", "Nike"),
        ("openai", "OpenAI"),
        ("chroma", "ChromaDB"),
        ("pinecone", "Pinecone"),
        ("python", "Python"),
        ("core nexus", "Core Nexus"),
        ("gpt-4", "GPT-4")
    ]

    deleted = 0
    for old_name, canonical in deletions:
        try:
            if canonical:
                # Delete the duplicate (keep the canonical one)
                result = await conn.execute(
                    "DELETE FROM graph_nodes WHERE entity_name = $1 AND entity_name != $2",
                    old_name, canonical
                )
            else:
                # Just delete (test entries)
                result = await conn.execute(
                    "DELETE FROM graph_nodes WHERE entity_name = $1",
                    old_name
                )

            count = int(result.split()[-1])
            if count > 0:
                deleted += count
                print(f"  ✓ Deleted '{old_name}' ({count} rows)")
        except Exception:
            # Ignore if already deleted or doesn't exist
            pass

    # Get final count
    after = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")

    print("\n✅ Deduplication Complete!")
    print(f"Before: {before} entities")
    print(f"After: {after} entities")
    print(f"Removed: {before - after} duplicates")

    await conn.close()
    return after

if __name__ == "__main__":
    final_count = asyncio.run(quick_dedup())
    print(f"\n📊 Final entity count: {final_count}")
