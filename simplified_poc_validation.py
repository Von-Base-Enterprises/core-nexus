#!/usr/bin/env python3
"""
Simplified Production PoC Validation

Focus on core validation metrics without complex performance benchmarking.
"""

import asyncio
import asyncpg
import json
import logging
import numpy as np
import os
import sys
import time
import openai
from datetime import datetime
from typing import Dict, List, Any
import statistics
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedPoCValidator:
    """Simplified production proof-of-concept validator."""
    
    def __init__(self):
        """Initialize the validator."""
        self.connection_pool = None
        self.openai_client = None
        self.rate_limit_lock = threading.Lock()
        self.last_api_call = 0
        self.api_calls_made = 0
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
            'port': int(os.getenv('PGVECTOR_PORT', '5432')),
            'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            'password': os.getenv('PGVECTOR_PASSWORD')
        }
        
        # OpenAI configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.db_config['password']:
            raise ValueError("PGVECTOR_PASSWORD environment variable must be set")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
    
    async def connect_to_production(self):
        """Connect to production database."""
        try:
            logger.info("🔌 Connecting to production database...")
            
            conn_str = (
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=1,
                max_size=2,
                command_timeout=30
            )
            
            async with self.connection_pool.acquire() as conn:
                vector_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
                logger.info(f"✅ Connected to production with {vector_count} vectors")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise
    
    def _rate_limit_openai_call(self):
        """Implement rate limiting for OpenAI API calls."""
        with self.rate_limit_lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_api_call
            
            # Rate limit to ~30 calls per minute
            min_interval = 2.0
            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                time.sleep(sleep_time)
            
            self.last_api_call = time.time()
            self.api_calls_made += 1
    
    def get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API with rate limiting."""
        try:
            self._rate_limit_openai_call()
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            raise
    
    async def extract_and_validate_samples(self, sample_count: int = 30) -> Dict[str, Any]:
        """Extract samples and perform validation."""
        logger.info(f"📦 Extracting and validating {sample_count} samples...")
        
        samples = []
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Extract diverse samples
                query = """
                SELECT 
                    id, 
                    content, 
                    embedding
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                    AND content IS NOT NULL 
                    AND LENGTH(content) > 50
                    AND LENGTH(content) < 1000
                ORDER BY RANDOM()
                LIMIT $1
                """
                
                rows = await conn.fetch(query, sample_count)
                logger.info(f"📊 Retrieved {len(rows)} samples")
                
                for i, row in enumerate(rows):
                    try:
                        # Extract original embedding dimensions
                        if row['embedding']:
                            original_embedding = list(row['embedding'])
                            original_dimensions = len(original_embedding)
                        else:
                            continue
                        
                        content = row['content'] or ''
                        
                        if len(content) > 50:
                            # Get OpenAI embedding
                            logger.info(f"🔄 Processing sample {i+1}/{len(rows)}: {len(content)} chars")
                            new_embedding = self.get_openai_embedding(content)
                            
                            sample = {
                                'id': str(row['id']),
                                'content': content,
                                'content_length': len(content),
                                'original_dimensions': original_dimensions,
                                'new_dimensions': len(new_embedding),
                                'dimension_reduction': original_dimensions / len(new_embedding)
                            }
                            samples.append(sample)
                            
                            logger.info(f"✅ Sample {i+1}: {original_dimensions}D → {len(new_embedding)}D ({sample['dimension_reduction']:.1f}x reduction)")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process sample {row['id']}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"❌ Failed to extract samples: {e}")
                raise
        
        if not samples:
            raise ValueError("No valid samples extracted")
        
        # Analyze results
        original_dims = [s['original_dimensions'] for s in samples]
        new_dims = [s['new_dimensions'] for s in samples]
        reductions = [s['dimension_reduction'] for s in samples]
        
        analysis = {
            'sample_count': len(samples),
            'original_dimensions': {
                'min': min(original_dims),
                'max': max(original_dims),
                'mean': statistics.mean(original_dims),
                'median': statistics.median(original_dims)
            },
            'new_dimensions': {
                'target': 1536,
                'actual_mean': statistics.mean(new_dims),
                'consistent': len(set(new_dims)) == 1 and new_dims[0] == 1536
            },
            'optimization_metrics': {
                'mean_reduction_ratio': statistics.mean(reductions),
                'min_reduction_ratio': min(reductions),
                'max_reduction_ratio': max(reductions),
                'dimension_efficiency_gain': f"{((statistics.mean(reductions) - 1) / statistics.mean(reductions) * 100):.1f}%"
            },
            'storage_analysis': {
                'storage_per_vector_old_kb': statistics.mean(original_dims) * 4 / 1024,
                'storage_per_vector_new_kb': 1536 * 4 / 1024,
                'storage_reduction_factor': statistics.mean(original_dims) / 1536,
                'total_production_storage_current_mb': (statistics.mean(original_dims) * 4 * 1470) / (1024 * 1024),
                'total_production_storage_target_mb': (1536 * 4 * 1470) / (1024 * 1024),
                'projected_storage_savings_mb': ((statistics.mean(original_dims) - 1536) * 4 * 1470) / (1024 * 1024)
            },
            'samples': samples,
            'api_calls_made': self.api_calls_made
        }
        
        return analysis
    
    def generate_assessment(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization assessment."""
        logger.info("🏆 Generating optimization assessment...")
        
        reduction_ratio = analysis['optimization_metrics']['mean_reduction_ratio']
        storage_reduction = analysis['storage_analysis']['storage_reduction_factor']
        
        # Calculate quality score
        quality_score = 0
        
        # Dimension reduction factor (50%)
        if reduction_ratio >= 12:
            dimension_factor = 1.0
        elif reduction_ratio >= 10:
            dimension_factor = 0.9
        elif reduction_ratio >= 8:
            dimension_factor = 0.8
        elif reduction_ratio >= 5:
            dimension_factor = 0.6
        else:
            dimension_factor = 0.4
        quality_score += dimension_factor * 0.5
        
        # Consistency factor (25%)
        if analysis['new_dimensions']['consistent']:
            consistency_factor = 1.0
        else:
            consistency_factor = 0.7
        quality_score += consistency_factor * 0.25
        
        # Sample size factor (25%)
        sample_count = analysis['sample_count']
        if sample_count >= 25:
            sample_factor = 1.0
        elif sample_count >= 15:
            sample_factor = 0.8
        else:
            sample_factor = 0.6
        quality_score += sample_factor * 0.25
        
        # Overall recommendation
        if quality_score >= 0.9 and reduction_ratio >= 10:
            recommendation = "HIGHLY RECOMMENDED - Proceed with full validation"
            confidence = "VERY_HIGH"
            next_step = "Expand to 100+ samples and run comprehensive accuracy testing"
        elif quality_score >= 0.8 and reduction_ratio >= 8:
            recommendation = "RECOMMENDED - Proceed with expanded testing"
            confidence = "HIGH"
            next_step = "Expand to 50+ samples and test search accuracy"
        elif quality_score >= 0.7:
            recommendation = "CAUTIOUS - Investigate further"
            confidence = "MEDIUM"
            next_step = "Analyze dimension variance and test with more samples"
        else:
            recommendation = "NOT RECOMMENDED - Investigate alternatives"
            confidence = "LOW"
            next_step = "Review embedding generation process"
        
        assessment = {
            'quality_score': quality_score,
            'recommendation': recommendation,
            'confidence_level': confidence,
            'next_step': next_step,
            'key_metrics': {
                'dimension_reduction': f"{reduction_ratio:.1f}x",
                'storage_reduction': f"{storage_reduction:.1f}x",
                'efficiency_gain': analysis['optimization_metrics']['dimension_efficiency_gain'],
                'consistency': "EXCELLENT" if analysis['new_dimensions']['consistent'] else "GOOD"
            },
            'business_impact': {
                'estimated_performance_improvement': f"{((reduction_ratio - 1) / reduction_ratio * 100):.0f}%",
                'estimated_storage_savings': f"{analysis['storage_analysis']['projected_storage_savings_mb']:.1f} MB",
                'storage_cost_reduction': f"{((storage_reduction - 1) / storage_reduction * 100):.0f}%"
            }
        }
        
        logger.info(f"🎯 Quality Score: {quality_score:.2f}/1.0 - {recommendation}")
        return assessment
    
    async def run_validation(self, sample_count: int = 30) -> Dict[str, Any]:
        """Run simplified validation."""
        start_time = time.time()
        logger.info(f"🚀 Starting simplified PoC validation with {sample_count} samples...")
        
        try:
            await self.connect_to_production()
            
            # Extract and validate samples
            analysis = await self.extract_and_validate_samples(sample_count)
            
            # Generate assessment
            assessment = self.generate_assessment(analysis)
            
            # Compile results
            results = {
                'validation_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': time.time() - start_time,
                    'validation_type': 'simplified_poc_validation',
                    'samples_processed': analysis['sample_count'],
                    'openai_api_calls': analysis['api_calls_made']
                },
                'analysis': analysis,
                'assessment': assessment,
                'validation_status': 'COMPLETED_SUCCESSFULLY'
            }
            
            logger.info(f"✅ Simplified PoC validation completed in {time.time() - start_time:.1f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"❌ Simplified PoC validation failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"simplified_poc_validation_{timestamp}.json"
        
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
    print("🎯 Core Nexus Simplified PoC Validation")
    print("=" * 45)
    print("Phase 3.1: Quick validation with real OpenAI embeddings")
    print()
    
    try:
        validator = SimplifiedPoCValidator()
        results = await validator.run_validation(30)  # Test with 30 samples
        
        # Save results
        filename = validator.save_results(results)
        
        # Print comprehensive summary
        print("\n🏆 SIMPLIFIED POC VALIDATION RESULTS")
        print("=" * 40)
        
        metadata = results['validation_metadata']
        print(f"✅ Samples Processed: {metadata['samples_processed']}")
        print(f"✅ OpenAI API Calls: {metadata['openai_api_calls']}")
        print(f"✅ Duration: {metadata['duration_seconds']:.1f} seconds")
        
        analysis = results['analysis']
        print(f"\n📊 DIMENSION ANALYSIS")
        print("=" * 25)
        orig_dims = analysis['original_dimensions']
        new_dims = analysis['new_dimensions']
        print(f"📏 Original Dimensions: {orig_dims['mean']:.0f} (range: {orig_dims['min']}-{orig_dims['max']})")
        print(f"📏 New Dimensions: {new_dims['target']} (consistent: {new_dims['consistent']})")
        
        opt_metrics = analysis['optimization_metrics']
        print(f"📏 Reduction Ratio: {opt_metrics['mean_reduction_ratio']:.1f}x")
        print(f"📏 Efficiency Gain: {opt_metrics['dimension_efficiency_gain']}")
        
        storage = analysis['storage_analysis']
        print(f"\n💾 STORAGE ANALYSIS")
        print("=" * 20)
        print(f"💿 Per Vector: {storage['storage_per_vector_old_kb']:.1f} KB → {storage['storage_per_vector_new_kb']:.1f} KB")
        print(f"💿 Reduction Factor: {storage['storage_reduction_factor']:.1f}x")
        print(f"💿 Production Savings: {storage['projected_storage_savings_mb']:.1f} MB")
        
        assessment = results['assessment']
        print(f"\n🏆 ASSESSMENT")
        print("=" * 15)
        print(f"🎯 Quality Score: {assessment['quality_score']:.2f}/1.0")
        print(f"🎯 Recommendation: {assessment['recommendation']}")
        print(f"🎯 Confidence: {assessment['confidence_level']}")
        print(f"🎯 Next Step: {assessment['next_step']}")
        
        business = assessment['business_impact']
        print(f"\n💼 BUSINESS IMPACT")
        print("=" * 20)
        print(f"📈 Performance Improvement: {business['estimated_performance_improvement']}")
        print(f"💰 Storage Savings: {business['estimated_storage_savings']}")
        print(f"💰 Cost Reduction: {business['storage_cost_reduction']}")
        
        print(f"\n💾 Complete results: {filename}")
        
        if assessment['quality_score'] >= 0.9:
            print("\n🚀 STATUS: OPTIMIZATION VALIDATED!")
            print("✅ Ready for expanded validation")
        elif assessment['quality_score'] >= 0.8:
            print("\n🧪 STATUS: PROMISING RESULTS")
            print("⚠️ Expand testing before full validation")
        else:
            print("\n🔬 STATUS: REQUIRES INVESTIGATION")
            print("❌ Address concerns before proceeding")
        
    except Exception as e:
        logger.error(f"❌ Simplified PoC validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())