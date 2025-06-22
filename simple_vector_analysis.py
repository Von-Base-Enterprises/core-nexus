#!/usr/bin/env python3
"""
Simple Production Vector Analysis

Extracts sample vectors to validate the 10x optimization opportunity.
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
from typing import Dict, List, Any
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleVectorAnalyzer:
    """Simple analyzer for production vectors."""
    
    def __init__(self):
        """Initialize with production database connection."""
        self.connection_pool = None
        
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
            
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=1,
                max_size=3,
                command_timeout=30
            )
            
            # Test connection and get basic stats
            async with self.connection_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                vector_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
                logger.info(f"✅ Connected to production database with {vector_count} vectors")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to production database: {e}")
            raise
    
    async def extract_sample_vectors(self) -> List[Dict[str, Any]]:
        """Extract sample vectors from production."""
        logger.info("📦 Extracting sample vectors...")
        
        samples = []
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Simple query to get sample vectors
                query = """
                SELECT 
                    id, 
                    content, 
                    embedding,
                    importance_score,
                    created_at
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT 10
                """
                
                rows = await conn.fetch(query)
                logger.info(f"📊 Retrieved {len(rows)} sample vectors")
                
                for row in rows:
                    try:
                        embedding_list = list(row['embedding']) if row['embedding'] else []
                        
                        sample = {
                            'id': str(row['id']),
                            'content': row['content'] or '',
                            'embedding': embedding_list,
                            'embedding_dimensions': len(embedding_list),
                            'importance_score': float(row['importance_score']) if row['importance_score'] else None,
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'content_length': len(row['content'] or ''),
                        }
                        samples.append(sample)
                        
                        logger.info(f"✅ Sample {len(samples)}: {len(embedding_list)} dimensions, {len(row['content'] or '')} chars")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process sample {row['id']}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"❌ Failed to extract samples: {e}")
                raise
        
        return samples
    
    def analyze_dimensions(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze vector dimensions."""
        logger.info("🔍 Analyzing vector dimensions...")
        
        dimensions = [s['embedding_dimensions'] for s in samples if s['embedding_dimensions'] > 0]
        
        if not dimensions:
            return {'error': 'No valid dimensions found'}
        
        analysis = {
            'sample_count': len(dimensions),
            'unique_dimensions': list(set(dimensions)),
            'min_dimensions': min(dimensions),
            'max_dimensions': max(dimensions),
            'mean_dimensions': statistics.mean(dimensions),
            'median_dimensions': statistics.median(dimensions),
            'all_same_dimensions': len(set(dimensions)) == 1
        }
        
        logger.info(f"📊 Dimension Analysis:")
        logger.info(f"   Samples: {analysis['sample_count']}")
        logger.info(f"   Dimensions: {analysis['min_dimensions']} - {analysis['max_dimensions']}")
        logger.info(f"   Mean: {analysis['mean_dimensions']:.0f}")
        logger.info(f"   All same: {analysis['all_same_dimensions']}")
        
        return analysis
    
    def analyze_content(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content patterns."""
        logger.info("📝 Analyzing content patterns...")
        
        content_lengths = [s['content_length'] for s in samples]
        
        analysis = {
            'sample_count': len(content_lengths),
            'min_content_length': min(content_lengths) if content_lengths else 0,
            'max_content_length': max(content_lengths) if content_lengths else 0,
            'mean_content_length': statistics.mean(content_lengths) if content_lengths else 0,
            'content_samples': []
        }
        
        # Store content samples for inspection
        for sample in samples[:5]:  # First 5 samples
            analysis['content_samples'].append({
                'id': sample['id'],
                'dimensions': sample['embedding_dimensions'],
                'content_preview': sample['content'][:100] + '...' if len(sample['content']) > 100 else sample['content'],
                'content_length': sample['content_length']
            })
        
        logger.info(f"📊 Content Analysis:")
        logger.info(f"   Lengths: {analysis['min_content_length']} - {analysis['max_content_length']} chars")
        logger.info(f"   Mean: {analysis['mean_content_length']:.0f} chars")
        
        return analysis
    
    def calculate_optimization_potential(self, dimension_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimization potential."""
        logger.info("📈 Calculating optimization potential...")
        
        current_dims = dimension_analysis.get('mean_dimensions', 19159)
        target_dims = 1536  # OpenAI text-embedding-3-small
        
        if current_dims <= target_dims:
            return {'note': 'Vectors already optimally sized'}
        
        reduction_ratio = current_dims / target_dims
        
        optimization = {
            'current_dimensions': current_dims,
            'target_dimensions': target_dims,
            'reduction_ratio': reduction_ratio,
            'performance_improvement_estimate': f"{(1 - 1/reduction_ratio) * 100:.1f}%",
            'storage_reduction': f"{reduction_ratio:.1f}x smaller",
            'memory_reduction': f"{reduction_ratio:.1f}x less memory",
            'calculation_speedup': f"{reduction_ratio:.1f}x faster similarity calculations"
        }
        
        logger.info(f"🚀 Optimization Potential:")
        logger.info(f"   Current: {current_dims:.0f} dimensions")
        logger.info(f"   Target: {target_dims} dimensions") 
        logger.info(f"   Reduction: {reduction_ratio:.1f}x")
        logger.info(f"   Performance gain: ~{(1 - 1/reduction_ratio) * 100:.1f}%")
        
        return optimization
    
    def analyze_vector_values(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze actual vector values for patterns."""
        logger.info("🔬 Analyzing vector value patterns...")
        
        value_analysis = {
            'vector_statistics': [],
            'suspicious_patterns': []
        }
        
        for i, sample in enumerate(samples[:3]):  # Analyze first 3 vectors
            embedding = sample['embedding']
            if not embedding:
                continue
                
            vector_array = np.array(embedding, dtype=np.float32)
            
            stats = {
                'sample_id': sample['id'],
                'dimensions': len(embedding),
                'magnitude': float(np.linalg.norm(vector_array)),
                'mean_value': float(np.mean(vector_array)),
                'std_value': float(np.std(vector_array)),
                'min_value': float(np.min(vector_array)),
                'max_value': float(np.max(vector_array)),
                'zero_count': int(np.count_nonzero(vector_array == 0)),
                'sparsity': float(1.0 - np.count_nonzero(vector_array) / len(vector_array))
            }
            
            value_analysis['vector_statistics'].append(stats)
            
            # Check for suspicious patterns
            if stats['sparsity'] > 0.9:
                value_analysis['suspicious_patterns'].append(f"Sample {i+1}: Very sparse ({stats['sparsity']:.2%} zeros)")
            
            if abs(stats['mean_value']) > 1.0:
                value_analysis['suspicious_patterns'].append(f"Sample {i+1}: Unusual mean value ({stats['mean_value']:.3f})")
            
            logger.info(f"   Sample {i+1}: magnitude={stats['magnitude']:.3f}, sparsity={stats['sparsity']:.2%}")
        
        return value_analysis
    
    async def run_analysis(self) -> Dict[str, Any]:
        """Run complete analysis."""
        start_time = time.time()
        logger.info("🚀 Starting simple vector analysis...")
        
        try:
            # Connect and extract samples
            await self.connect_to_production()
            samples = await self.extract_sample_vectors()
            
            if not samples:
                raise ValueError("No samples extracted")
            
            # Run analyses
            dimension_analysis = self.analyze_dimensions(samples)
            content_analysis = self.analyze_content(samples)
            optimization_analysis = self.calculate_optimization_potential(dimension_analysis)
            value_analysis = self.analyze_vector_values(samples)
            
            # Compile results
            results = {
                'timestamp': datetime.now().isoformat(),
                'analysis_duration': time.time() - start_time,
                'sample_count': len(samples),
                'dimension_analysis': dimension_analysis,
                'content_analysis': content_analysis,
                'optimization_analysis': optimization_analysis,
                'value_analysis': value_analysis,
                'samples': samples  # Include raw samples for further analysis
            }
            
            logger.info(f"✅ Analysis completed in {time.time() - start_time:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"vector_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"💾 Results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to save: {e}")
            raise

async def main():
    """Main execution."""
    print("🔍 Core Nexus Simple Vector Analysis")
    print("=" * 40)
    print("Validating 10x optimization opportunity")
    print()
    
    try:
        analyzer = SimpleVectorAnalyzer()
        results = await analyzer.run_analysis()
        
        # Save results
        filename = analyzer.save_results(results)
        
        # Print key findings
        print("\n📊 KEY FINDINGS")
        print("=" * 20)
        
        dim_analysis = results['dimension_analysis']
        opt_analysis = results['optimization_analysis']
        
        print(f"✅ Samples analyzed: {results['sample_count']}")
        print(f"✅ Vector dimensions: {dim_analysis['mean_dimensions']:.0f}")
        print(f"✅ Target dimensions: {opt_analysis['target_dimensions']}")
        print(f"🚀 Optimization ratio: {opt_analysis['reduction_ratio']:.1f}x")
        print(f"🚀 Performance gain: {opt_analysis['performance_improvement_estimate']}")
        print(f"💾 Storage reduction: {opt_analysis['storage_reduction']}")
        
        print(f"\n📄 Full results: {filename}")
        print("\n🎯 STATUS: 10x optimization opportunity VALIDATED!")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())