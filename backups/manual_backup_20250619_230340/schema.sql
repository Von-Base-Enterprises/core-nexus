CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS entity_canonicalization (
  alias varchar(255) NOT NULL,
  canonical_name varchar(255) NOT NULL,
  canonical_id uuid NOT NULL,
  confidence double precision DEFAULT 1.0,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_edges (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_id uuid,
  target_id uuid,
  relationship_type text NOT NULL,
  strength double precision DEFAULT 1.0,
  confidence double precision DEFAULT 1.0,
  occurrence_count integer DEFAULT 1,
  last_seen timestamp without time zone DEFAULT now(),
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_nodes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  entity_name text NOT NULL,
  entity_type text NOT NULL,
  embedding USER-DEFINED,
  importance_score double precision DEFAULT 0.5,
  mention_count integer DEFAULT 1,
  last_seen timestamp without time zone DEFAULT now(),
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_relationships (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  from_node_id uuid,
  to_node_id uuid,
  relationship_type text NOT NULL,
  strength double precision DEFAULT 1.0,
  confidence double precision DEFAULT 1.0,
  adm_score double precision DEFAULT 0.5,
  occurrence_count integer DEFAULT 1,
  metadata jsonb DEFAULT '{}'::jsonb,
  last_seen timestamp without time zone DEFAULT now(),
  created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memories (
  id uuid NOT NULL,
  content text NOT NULL,
  embedding USER-DEFINED,
  metadata jsonb DEFAULT '{}'::jsonb,
  importance_score double precision DEFAULT 0.5,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_entity_map (
  memory_id uuid NOT NULL,
  entity_id uuid NOT NULL
);

CREATE TABLE IF NOT EXISTS vector_memories (
  id uuid NOT NULL,
  content text NOT NULL,
  embedding USER-DEFINED,
  metadata jsonb DEFAULT '{}'::jsonb,
  importance_score double precision DEFAULT 0.5,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now()
);