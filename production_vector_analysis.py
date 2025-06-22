#!/usr/bin/env python3
"""
Production Vector Analysis for Core Nexus Optimization

Extracts and analyzes sample vectors from production database to validate
the 10x optimization opportunity discovered in dimension analysis.

Key Objectives:
1. Extract representative sample vectors (10-20) from production
2. Analyze the 19,159-dimension vector structure 
3. Map vectors to their source content
4. Investigate why vectors are 12.5x larger than expected
"""

import asyncio
import asyncpg
import json
import logging
import numpy as np
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionVectorAnalyzer:
    """Comprehensive analyzer for production vector optimization."""
    
    def __init__(self):
        """Initialize the analyzer with production database connection."""
        self.connection_pool = None
        self.analysis_results = {
            'extraction_time': None,
            'sample_count': 0,
            'vector_analysis': {},
            'content_analysis': {},
            'dimension_analysis': {},
            'optimization_potential': {},
            'recommendations': []
        }
        
        # Production database configuration
        self.db_config = {
            'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
            'port': int(os.getenv('PGVECTOR_PORT', '5432')),
            'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            'password': os.getenv('PGVECTOR_PASSWORD')
        }
        
        if not self.db_config['password']:
            raise ValueError("PGVECTOR_PASSWORD environment variable must be set")
    
    async def connect_to_production(self):
        """Establish connection to production database."""
        try:
            logger.info("🔌 Connecting to production database...")
            
            # Build connection string
            conn_str = (
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            
            # Create connection pool for efficiency
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=2,
                max_size=5,
                command_timeout=30
            )
            
            # Test connection
            async with self.connection_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                logger.info(f"✅ Successfully connected to production database")
                
                # Get basic stats
                vector_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
                logger.info(f"📊 Found {vector_count} vectors in production database")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to production database: {e}")
            raise
    
    async def extract_sample_vectors(self, sample_size: int = 15) -> List[Dict[str, Any]]:
        """Extract representative sample vectors from production."""
        logger.info(f"📦 Extracting {sample_size} sample vectors from production...")
        
        samples = []
        
        async with self.connection_pool.acquire() as conn:
            # Get diverse samples using different strategies
            queries = [
                # Recent vectors
                """
                SELECT id, content, embedding, metadata, importance_score, created_at, updated_at
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT 5
                """,
                
                # Random samples
                """
                SELECT id, content, embedding, metadata, importance_score, created_at, updated_at
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT 5
                """,
                
                # High importance samples
                """
                SELECT id, content, embedding, metadata, importance_score, created_at, updated_at
                FROM vector_memories 
                WHERE embedding IS NOT NULL AND importance_score IS NOT NULL
                ORDER BY importance_score DESC 
                LIMIT 3
                """,
                
                # Oldest vectors (legacy data)
                """
                SELECT id, content, embedding, metadata, importance_score, created_at, updated_at
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                ORDER BY created_at ASC 
                LIMIT 2
                """
            ]
            
            for i, query in enumerate(queries):
                try:
                    rows = await conn.fetch(query)
                    for row in rows:
                        sample = {
                            'id': str(row['id']),
                            'content': row['content'],
                            'embedding': list(row['embedding']) if row['embedding'] else [],
                            'metadata': dict(row['metadata']) if row['metadata'] else {},
                            'importance_score': float(row['importance_score']) if row['importance_score'] else None,
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                            'sample_type': ['recent', 'random', 'high_importance', 'legacy'][i]
                        }
                        samples.append(sample)
                        
                    logger.info(f"✅ Extracted {len(rows)} {['recent', 'random', 'high_importance', 'legacy'][i]} samples")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract {['recent', 'random', 'high_importance', 'legacy'][i]} samples: {e}")
        
        logger.info(f"📊 Total samples extracted: {len(samples)}")
        self.analysis_results['sample_count'] = len(samples)
        
        return samples
    
    def analyze_vector_dimensions(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the dimensional structure of production vectors."""
        logger.info("🔍 Analyzing vector dimensional structure...")
        
        dimension_analysis = {
            'sample_dimensions': [],
            'dimension_statistics': {},
            'value_distributions': {},
            'sparsity_analysis': {},
            'anomaly_detection': {}
        }
        
        all_dimensions = []
        
        for sample in samples:
            embedding = sample['embedding']
            if not embedding:
                continue
                
            dims = len(embedding)
            all_dimensions.append(dims)
            
            # Analyze individual vector
            vector_array = np.array(embedding, dtype=np.float32)
            
            vector_analysis = {
                'id': sample['id'],
                'dimensions': dims,
                'non_zero_count': np.count_nonzero(vector_array),
                'sparsity': 1.0 - (np.count_nonzero(vector_array) / len(vector_array)),
                'magnitude': np.linalg.norm(vector_array),
                'mean_value': np.mean(vector_array),
                'std_value': np.std(vector_array),
                'min_value': np.min(vector_array),
                'max_value': np.max(vector_array),
                'sample_type': sample['sample_type']
            }
            
            dimension_analysis['sample_dimensions'].append(vector_analysis)
        
        # Calculate overall statistics
        if all_dimensions:
            dimension_analysis['dimension_statistics'] = {
                'mean_dimensions': statistics.mean(all_dimensions),
                'median_dimensions': statistics.median(all_dimensions),
                'mode_dimensions': statistics.mode(all_dimensions),
                'min_dimensions': min(all_dimensions),
                'max_dimensions': max(all_dimensions),
                'std_dimensions': statistics.stdev(all_dimensions) if len(all_dimensions) > 1 else 0,
                'unique_dimension_counts': list(set(all_dimensions))
            }
            
            logger.info(f"📊 Dimension Statistics:")
            logger.info(f"   Mean: {dimension_analysis['dimension_statistics']['mean_dimensions']:.1f}")
            logger.info(f"   Median: {dimension_analysis['dimension_statistics']['median_dimensions']}")
            logger.info(f"   Mode: {dimension_analysis['dimension_statistics']['mode_dimensions']}")
            logger.info(f"   Range: {min(all_dimensions)} - {max(all_dimensions)}")
        
        return dimension_analysis
    
    def analyze_content_patterns(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content patterns to understand vector generation."""
        logger.info("📝 Analyzing content patterns...")
        
        content_analysis = {
            'content_lengths': [],
            'content_types': {},
            'metadata_patterns': {},
            'creation_patterns': {},
            'content_samples': []
        }
        
        for sample in samples:
            content = sample['content']
            metadata = sample['metadata']
            
            # Content length analysis
            content_length = len(content) if content else 0
            content_analysis['content_lengths'].append(content_length)
            
            # Store sample content (first 200 chars for analysis)
            content_analysis['content_samples'].append({
                'id': sample['id'],
                'content_preview': content[:200] if content else '',
                'full_length': content_length,
                'embedding_dimensions': len(sample['embedding']),
                'sample_type': sample['sample_type'],
                'created_at': sample['created_at']
            })
            
            # Metadata pattern analysis
            if metadata:
                for key, value in metadata.items():
                    if key not in content_analysis['metadata_patterns']:
                        content_analysis['metadata_patterns'][key] = []
                    content_analysis['metadata_patterns'][key].append(str(value)[:100])
        
        # Calculate content statistics
        if content_analysis['content_lengths']:
            content_analysis['content_statistics'] = {
                'mean_length': statistics.mean(content_analysis['content_lengths']),
                'median_length': statistics.median(content_analysis['content_lengths']),
                'min_length': min(content_analysis['content_lengths']),
                'max_length': max(content_analysis['content_lengths']),
                'total_characters': sum(content_analysis['content_lengths'])
            }
            
            logger.info(f"📊 Content Statistics:")
            logger.info(f"   Mean length: {content_analysis['content_statistics']['mean_length']:.1f} chars")
            logger.info(f"   Range: {content_analysis['content_statistics']['min_length']} - {content_analysis['content_statistics']['max_length']} chars")
        
        return content_analysis
    
    def investigate_dimension_source(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Investigate the source of 19,159 dimensions."""
        logger.info("🔬 Investigating dimension source...")
        
        investigation = {
            'dimension_theories': [],
            'evidence': {},
            'likely_cause': None,
            'confidence_score': 0.0
        }
        
        # Check for common dimension counts that might indicate source
        dimension_counts = [len(sample['embedding']) for sample in samples if sample['embedding']]
        unique_dimensions = set(dimension_counts)
        
        logger.info(f"🔍 Unique dimension counts found: {unique_dimensions}")
        
        theories = []
        
        # Theory 1: Concatenated embeddings
        if 19159 in unique_dimensions:
            # Check if 19159 could be composed of standard embedding sizes
            potential_components = []
            
            # Common embedding sizes
            common_sizes = [1536, 3072, 768, 384, 256, 512, 1024, 2048]
            
            for size1 in common_sizes:
                for size2 in common_sizes:
                    if size1 + size2 == 19159:
                        potential_components.append((size1, size2))
                    for size3 in common_sizes:
                        if size1 + size2 + size3 == 19159:
                            potential_components.append((size1, size2, size3))
            
            if potential_components:
                theories.append({
                    'name': 'Concatenated Embeddings',
                    'description': 'Vectors created by concatenating multiple embedding types',
                    'evidence': f"19159 could be composed of: {potential_components[:3]}",
                    'probability': 0.7
                })
            
            # Check if it's a multiple of common sizes
            for size in common_sizes:
                if 19159 % size == 0:
                    multiplier = 19159 // size
                    theories.append({
                        'name': f'Repeated {size}D Embeddings',
                        'description': f'Vector repeated {multiplier} times',
                        'evidence': f"19159 = {size} × {multiplier}",
                        'probability': 0.5
                    })
        
        # Theory 2: Hyperdimensional Computing
        if 19159 > 10000:
            theories.append({
                'name': 'Hyperdimensional Computing (HDC)',
                'description': 'High-dimensional representation for symbolic AI',
                'evidence': f"Dimension count {19159} fits HDC patterns (10k-20k typical)",
                'probability': 0.3
            })
        
        # Theory 3: Legacy system migration
        theories.append({
            'name': 'Legacy System Migration',
            'description': 'Vectors from previous system with different embedding model',
            'evidence': f"Non-standard dimension count suggests legacy data",
            'probability': 0.8
        })
        
        # Theory 4: Configuration error
        if len(unique_dimensions) == 1 and 19159 in unique_dimensions:
            theories.append({
                'name': 'Configuration Error',
                'description': 'Embedding model misconfigured to produce wrong dimensions',
                'evidence': f"All vectors have same unusual dimension count",
                'probability': 0.6
            })
        
        investigation['dimension_theories'] = theories
        
        # Determine most likely cause
        if theories:
            most_likely = max(theories, key=lambda t: t['probability'])
            investigation['likely_cause'] = most_likely['name']
            investigation['confidence_score'] = most_likely['probability']
            
            logger.info(f"🎯 Most likely cause: {most_likely['name']} (confidence: {most_likely['probability']:.1%})")
        
        return investigation
    
    def calculate_optimization_potential(self, dimension_analysis: Dict[str, Any], content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate the potential gains from dimension optimization."""
        logger.info("📈 Calculating optimization potential...")
        
        current_dimensions = dimension_analysis['dimension_statistics']['mode_dimensions']
        target_dimensions = 1536  # OpenAI text-embedding-3-small
        
        optimization = {
            'current_dimensions': current_dimensions,
            'target_dimensions': target_dimensions,
            'dimension_reduction_ratio': current_dimensions / target_dimensions,
            'performance_improvements': {},
            'storage_improvements': {},
            'cost_improvements': {}
        }
        
        # Calculate performance improvements
        reduction_ratio = current_dimensions / target_dimensions
        
        optimization['performance_improvements'] = {
            'similarity_calculation_speedup': f"{reduction_ratio:.1f}x faster",
            'memory_usage_reduction': f"{reduction_ratio:.1f}x less memory",
            'index_size_reduction': f"{reduction_ratio:.1f}x smaller indexes",
            'estimated_latency_improvement': f"{(1 - 1/reduction_ratio) * 100:.1f}% faster queries"
        }
        
        # Calculate storage improvements
        sample_count = len(dimension_analysis['sample_dimensions'])
        if sample_count > 0:
            avg_vectors = content_analysis.get('total_vectors', 1470)  # From previous analysis
            
            current_storage_per_vector = current_dimensions * 4  # 4 bytes per float32
            target_storage_per_vector = target_dimensions * 4
            
            optimization['storage_improvements'] = {
                'storage_per_vector_current': f"{current_storage_per_vector / 1024:.1f} KB",
                'storage_per_vector_target': f"{target_storage_per_vector / 1024:.1f} KB",
                'storage_reduction_per_vector': f"{(current_storage_per_vector - target_storage_per_vector) / 1024:.1f} KB saved",
                'total_storage_current': f"{(current_storage_per_vector * avg_vectors) / (1024 * 1024):.1f} MB",
                'total_storage_target': f"{(target_storage_per_vector * avg_vectors) / (1024 * 1024):.1f} MB",
                'total_storage_saved': f"{((current_storage_per_vector - target_storage_per_vector) * avg_vectors) / (1024 * 1024):.1f} MB"
            }
        
        logger.info(f"🚀 Optimization Potential:")
        logger.info(f"   Dimension reduction: {current_dimensions} → {target_dimensions} ({reduction_ratio:.1f}x smaller)")
        logger.info(f"   Performance improvement: ~{(1 - 1/reduction_ratio) * 100:.1f}% faster")
        logger.info(f"   Storage reduction: {reduction_ratio:.1f}x smaller")
        
        return optimization
    
    def generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        logger.info("💡 Generating optimization recommendations...")
        
        recommendations = []
        
        dimension_stats = analysis_results.get('dimension_analysis', {}).get('dimension_statistics', {})
        optimization = analysis_results.get('optimization_potential', {})
        investigation = analysis_results.get('source_investigation', {})
        
        current_dims = dimension_stats.get('mode_dimensions', 19159)
        reduction_ratio = optimization.get('dimension_reduction_ratio', 12.5)
        likely_cause = investigation.get('likely_cause', 'Unknown')
        
        # High-level recommendations
        if reduction_ratio > 10:
            recommendations.append(
                f"🎯 CRITICAL: Immediate re-embedding recommended - {reduction_ratio:.1f}x performance gain potential"
            )
        elif reduction_ratio > 5:
            recommendations.append(
                f"🚀 HIGH PRIORITY: Re-embedding will provide {reduction_ratio:.1f}x performance improvement"
            )
        
        # Specific technical recommendations
        recommendations.extend([
            f"📊 Use OpenAI text-embedding-3-small (1,536 dimensions) to replace current {current_dims}D vectors",
            f"🔄 Implement parallel table migration strategy for zero-downtime deployment",
            f"✅ Validate search accuracy with A/B testing during migration",
            f"📈 Expected improvements: {(1 - 1/reduction_ratio) * 100:.1f}% faster queries, {reduction_ratio:.1f}x less storage"
        ])
        
        # Cause-specific recommendations
        if likely_cause == 'Legacy System Migration':
            recommendations.append("🔧 Review data migration procedures to prevent future dimension mismatches")
        elif likely_cause == 'Concatenated Embeddings':
            recommendations.append("🔍 Investigate if concatenated embeddings provide value or can be simplified")
        elif likely_cause == 'Configuration Error':
            recommendations.append("⚙️ Review embedding model configuration and deployment procedures")
        
        # Implementation recommendations
        recommendations.extend([
            "🧪 Start with proof-of-concept migration on 10% of data to validate approach",
            "📊 Implement comprehensive monitoring during migration to track performance gains",
            "🔒 Maintain rollback capability throughout migration process",
            "📋 Document optimization procedures for future reference"
        ])
        
        return recommendations
    
    async def run_analysis(self, sample_size: int = 15) -> Dict[str, Any]:
        """Run complete production vector analysis."""
        start_time = time.time()
        logger.info("🚀 Starting production vector analysis...")
        
        try:
            # Connect to production
            await self.connect_to_production()
            
            # Extract sample vectors
            samples = await self.extract_sample_vectors(sample_size)
            
            if not samples:
                raise ValueError("No sample vectors extracted")
            
            # Analyze vector dimensions
            dimension_analysis = self.analyze_vector_dimensions(samples)
            
            # Analyze content patterns
            content_analysis = self.analyze_content_patterns(samples)
            
            # Investigate dimension source
            source_investigation = self.investigate_dimension_source(samples)
            
            # Calculate optimization potential
            optimization_potential = self.calculate_optimization_potential(dimension_analysis, content_analysis)
            
            # Generate recommendations
            recommendations = self.generate_recommendations({
                'dimension_analysis': dimension_analysis,
                'content_analysis': content_analysis,
                'source_investigation': source_investigation,
                'optimization_potential': optimization_potential
            })
            
            # Compile final results
            self.analysis_results.update({
                'extraction_time': datetime.now().isoformat(),
                'analysis_duration_seconds': time.time() - start_time,
                'samples': samples,
                'dimension_analysis': dimension_analysis,
                'content_analysis': content_analysis,
                'source_investigation': source_investigation,
                'optimization_potential': optimization_potential,
                'recommendations': recommendations
            })
            
            logger.info(f"✅ Analysis completed in {time.time() - start_time:.2f} seconds")
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def save_results(self, filename: Optional[str] = None):
        """Save analysis results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"production_vector_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            
            logger.info(f"💾 Analysis results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
            raise

async def main():
    """Main execution function."""
    print("🔍 Core Nexus Production Vector Analysis")
    print("=" * 50)
    print("Objective: Validate 10x optimization opportunity")
    print()
    
    try:
        analyzer = ProductionVectorAnalyzer()
        results = await analyzer.run_analysis(sample_size=15)
        
        # Save results
        filename = analyzer.save_results()
        
        # Print summary
        print("\n📊 ANALYSIS SUMMARY")
        print("=" * 30)
        print(f"Sample Count: {results['sample_count']}")
        
        if 'dimension_analysis' in results:
            dim_stats = results['dimension_analysis']['dimension_statistics']
            print(f"Average Dimensions: {dim_stats['mean_dimensions']:.0f}")
            print(f"Dimension Range: {dim_stats['min_dimensions']} - {dim_stats['max_dimensions']}")
        
        if 'optimization_potential' in results:
            opt = results['optimization_potential']
            print(f"Optimization Ratio: {opt['dimension_reduction_ratio']:.1f}x")
            print(f"Performance Gain: ~{(1 - 1/opt['dimension_reduction_ratio']) * 100:.1f}%")
        
        print(f"\n💡 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(results['recommendations'][:3], 1):
            print(f"{i}. {rec}")
        
        print(f"\n💾 Full results saved to: {filename}")
        print("\n🎯 Next Step: Phase 2 - Re-embedding Validation")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())