#!/usr/bin/env python3
"""
Production Proof-of-Concept Validation

Validates the 10x optimization with real OpenAI embeddings on 100-200 production vectors.
This is Phase 3.1 of the implementation roadmap.
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
from typing import Dict, List, Any, Tuple
import statistics
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionPoCValidator:
    """Production proof-of-concept validator with real OpenAI embeddings."""
    
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
                max_size=3,
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
            
            # Rate limit to ~30 calls per minute (2 seconds between calls)
            min_interval = 2.0
            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                logger.info(f"⏳ Rate limiting: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
            
            self.last_api_call = time.time()
            self.api_calls_made += 1
    
    def get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API with rate limiting."""
        try:
            self._rate_limit_openai_call()
            
            logger.info(f"🔄 API call #{self.api_calls_made}: Getting embedding for {len(text)} chars")
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.info(f"✅ API call #{self.api_calls_made}: Got {len(embedding)}D embedding")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            raise
    
    async def extract_production_samples(self, sample_count: int = 150) -> List[Dict[str, Any]]:
        """Extract diverse production samples for validation."""
        logger.info(f"📦 Extracting {sample_count} diverse production samples...")
        
        samples = []
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Extract diverse samples with stratified sampling
                query = """
                WITH diverse_samples AS (
                    SELECT 
                        id, 
                        content, 
                        embedding,
                        LENGTH(content) as content_length,
                        NTILE(5) OVER (ORDER BY LENGTH(content)) as length_bucket
                    FROM vector_memories 
                    WHERE embedding IS NOT NULL 
                        AND content IS NOT NULL 
                        AND LENGTH(content) > 50
                        AND LENGTH(content) < 2000
                )
                SELECT * FROM diverse_samples 
                ORDER BY length_bucket, RANDOM()
                LIMIT $1
                """
                
                rows = await conn.fetch(query, sample_count)
                logger.info(f"📊 Retrieved {len(rows)} diverse samples")
                
                for i, row in enumerate(rows):
                    try:
                        # Convert embedding properly
                        if row['embedding']:
                            original_embedding = list(row['embedding'])
                        else:
                            continue
                        
                        content = row['content'] or ''
                        
                        if len(original_embedding) > 0 and len(content) > 50:
                            sample = {
                                'id': str(row['id']),
                                'content': content,
                                'content_length': len(content),
                                'original_embedding': original_embedding,
                                'original_dimensions': len(original_embedding),
                                'length_bucket': row['length_bucket']
                            }
                            samples.append(sample)
                            
                            if (i + 1) % 25 == 0:
                                logger.info(f"✅ Processed {i + 1}/{len(rows)} samples")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process sample {row['id']}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"❌ Failed to extract samples: {e}")
                raise
        
        logger.info(f"📊 Successfully extracted {len(samples)} diverse samples")
        return samples
    
    async def generate_openai_embeddings(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate OpenAI embeddings for all samples."""
        logger.info(f"🤖 Generating OpenAI embeddings for {len(samples)} samples...")
        
        # Process in smaller batches to manage rate limits
        batch_size = 10
        batches = [samples[i:i + batch_size] for i in range(0, len(samples), batch_size)]
        
        processed_samples = []
        
        for batch_idx, batch in enumerate(batches):
            logger.info(f"🔄 Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} samples)")
            
            # Use ThreadPoolExecutor for concurrent API calls within rate limits
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Create futures for each sample in the batch
                futures = []
                for sample in batch:
                    future = executor.submit(self._process_sample_embedding, sample)
                    futures.append((sample, future))
                
                # Collect results
                for sample, future in futures:
                    try:
                        result = future.result(timeout=60)  # 60 second timeout per call
                        if result:
                            processed_samples.append(result)
                            logger.info(f"✅ Processed sample {result['id']}: {result['original_dimensions']}D → {result['new_dimensions']}D")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process sample {sample['id']}: {e}")
            
            # Batch cooldown
            if batch_idx < len(batches) - 1:
                logger.info(f"⏸️ Batch cooldown: 10 seconds...")
                time.sleep(10)
        
        logger.info(f"🎉 Successfully generated embeddings for {len(processed_samples)}/{len(samples)} samples")
        return processed_samples
    
    def _process_sample_embedding(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single sample to get OpenAI embedding."""
        try:
            # Get OpenAI embedding
            new_embedding = self.get_openai_embedding(sample['content'])
            
            # Add new embedding to sample
            enhanced_sample = sample.copy()
            enhanced_sample['new_embedding'] = new_embedding
            enhanced_sample['new_dimensions'] = len(new_embedding)
            
            return enhanced_sample
            
        except Exception as e:
            logger.error(f"❌ Failed to process sample {sample['id']}: {e}")
            return None
    
    def analyze_dimension_optimization(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze dimensional optimization characteristics."""
        logger.info("🔍 Analyzing dimension optimization...")
        
        original_dims = [s['original_dimensions'] for s in samples]
        new_dims = [s['new_dimensions'] for s in samples]
        
        analysis = {
            'sample_count': len(samples),
            'original_dimensions': {
                'min': min(original_dims),
                'max': max(original_dims),
                'mean': statistics.mean(original_dims),
                'median': statistics.median(original_dims),
                'std_dev': statistics.stdev(original_dims) if len(original_dims) > 1 else 0
            },
            'new_dimensions': {
                'target': 1536,
                'actual_mean': statistics.mean(new_dims),
                'consistent': len(set(new_dims)) == 1 and new_dims[0] == 1536
            },
            'optimization_metrics': {
                'reduction_ratio': statistics.mean(original_dims) / 1536,
                'dimension_efficiency_gain': f"{((statistics.mean(original_dims) / 1536 - 1) / (statistics.mean(original_dims) / 1536) * 100):.1f}%",
                'storage_reduction_factor': statistics.mean(original_dims) / 1536
            }
        }
        
        logger.info(f"📊 Dimensions: {analysis['original_dimensions']['mean']:.0f} → 1536 ({analysis['optimization_metrics']['reduction_ratio']:.1f}x reduction)")
        return analysis
    
    def benchmark_performance_improvements(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Benchmark performance improvements with real embeddings."""
        logger.info("⚡ Benchmarking performance improvements...")
        
        # Test similarity calculation speed
        iterations = 100
        sample_pairs = min(20, len(samples) - 1)  # Test with up to 20 pairs
        
        old_times = []
        new_times = []
        
        logger.info(f"🏃 Running {iterations} iterations with {sample_pairs} vector pairs...")
        
        for iteration in range(iterations):
            # Benchmark original embeddings
            start_time = time.perf_counter()
            for i in range(sample_pairs):
                # Ensure original_embedding is a list/array
                old_emb1 = samples[i]['original_embedding']
                old_emb2 = samples[i + 1]['original_embedding']
                if isinstance(old_emb1, list) and isinstance(old_emb2, list):
                    old_vec1 = np.array(old_emb1, dtype=np.float32)
                    old_vec2 = np.array(old_emb2, dtype=np.float32)
                    similarity = np.dot(old_vec1, old_vec2) / (np.linalg.norm(old_vec1) * np.linalg.norm(old_vec2))
            old_times.append((time.perf_counter() - start_time) * 1000)
            
            # Benchmark new embeddings
            start_time = time.perf_counter()
            for i in range(sample_pairs):
                # Ensure new_embedding is a list/array
                new_emb1 = samples[i]['new_embedding']
                new_emb2 = samples[i + 1]['new_embedding']
                if isinstance(new_emb1, list) and isinstance(new_emb2, list):
                    new_vec1 = np.array(new_emb1, dtype=np.float32)
                    new_vec2 = np.array(new_emb2, dtype=np.float32)
                    similarity = np.dot(new_vec1, new_vec2) / (np.linalg.norm(new_vec1) * np.linalg.norm(new_vec2))
            new_times.append((time.perf_counter() - start_time) * 1000)
            
            if (iteration + 1) % 25 == 0:
                logger.info(f"🏃 Completed {iteration + 1}/{iterations} benchmark iterations")
        
        old_avg = statistics.mean(old_times)
        new_avg = statistics.mean(new_times)
        speedup = old_avg / new_avg if new_avg > 0 else 1
        
        # Storage calculations
        avg_original_dims = statistics.mean([s['original_dimensions'] for s in samples])
        storage_reduction = avg_original_dims / 1536
        
        analysis = {
            'similarity_calculation': {
                'old_avg_time_ms': old_avg,
                'new_avg_time_ms': new_avg,
                'speedup_factor': speedup,
                'improvement_percentage': f"{((speedup - 1) * 100):.1f}%",
                'iterations_tested': iterations,
                'vector_pairs_tested': sample_pairs
            },
            'storage_analysis': {
                'avg_original_dimensions': avg_original_dims,
                'new_dimensions': 1536,
                'storage_reduction_ratio': storage_reduction,
                'memory_per_vector_old_kb': avg_original_dims * 4 / 1024,
                'memory_per_vector_new_kb': 1536 * 4 / 1024,
                'storage_savings_per_vector_kb': (avg_original_dims - 1536) * 4 / 1024
            },
            'projected_production_impact': {
                'total_vectors': 1470,  # From production analysis
                'total_storage_current_mb': (avg_original_dims * 4 * 1470) / (1024 * 1024),
                'total_storage_target_mb': (1536 * 4 * 1470) / (1024 * 1024),
                'total_storage_saved_mb': ((avg_original_dims - 1536) * 4 * 1470) / (1024 * 1024)
            }
        }
        
        logger.info(f"🚀 Performance: {speedup:.1f}x speedup, {storage_reduction:.1f}x storage reduction")
        return analysis
    
    def test_search_accuracy_preservation(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test search accuracy preservation with real embeddings."""
        logger.info("🎯 Testing search accuracy preservation...")
        
        accuracy_scores = []
        detailed_results = []
        
        # Test with first 20 samples as queries (or all if fewer)
        query_samples = samples[:min(20, len(samples))]
        target_samples = samples  # Search against all samples
        
        logger.info(f"🔍 Testing {len(query_samples)} queries against {len(target_samples)} targets")
        
        for query_idx, query_sample in enumerate(query_samples):
            try:
                logger.info(f"🔍 Testing query {query_idx + 1}/{len(query_samples)}: {query_sample['content'][:50]}...")
                
                # Calculate similarities with original embeddings
                old_similarities = []
                new_similarities = []
                
                # Ensure embeddings are lists before converting to numpy
                if not isinstance(query_sample['original_embedding'], list) or not isinstance(query_sample['new_embedding'], list):
                    logger.warning(f"⚠️ Query {query_idx} has invalid embedding format, skipping")
                    continue
                    
                query_old = np.array(query_sample['original_embedding'], dtype=np.float32)
                query_new = np.array(query_sample['new_embedding'], dtype=np.float32)
                
                for target_idx, target_sample in enumerate(target_samples):
                    if query_sample['id'] == target_sample['id']:
                        continue  # Skip self-comparison
                    
                    # Ensure target embeddings are lists
                    if not isinstance(target_sample['original_embedding'], list) or not isinstance(target_sample['new_embedding'], list):
                        continue
                    
                    target_old = np.array(target_sample['original_embedding'], dtype=np.float32)
                    target_new = np.array(target_sample['new_embedding'], dtype=np.float32)
                    
                    # Calculate cosine similarities
                    old_sim = np.dot(query_old, target_old) / (np.linalg.norm(query_old) * np.linalg.norm(target_old))
                    new_sim = np.dot(query_new, target_new) / (np.linalg.norm(query_new) * np.linalg.norm(target_new))
                    
                    old_similarities.append((target_sample['id'], float(old_sim), target_sample['content'][:100]))
                    new_similarities.append((target_sample['id'], float(new_sim), target_sample['content'][:100]))
                
                # Sort by similarity
                old_similarities.sort(key=lambda x: x[1], reverse=True)
                new_similarities.sort(key=lambda x: x[1], reverse=True)
                
                # Calculate ranking preservation for top-k results
                top_k_values = [3, 5, 10]
                ranking_preservation = {}
                
                for k in top_k_values:
                    old_top_k = set([item[0] for item in old_similarities[:k]])
                    new_top_k = set([item[0] for item in new_similarities[:k]])
                    overlap = len(old_top_k.intersection(new_top_k))
                    preservation = overlap / min(k, len(old_similarities))
                    ranking_preservation[f'top_{k}'] = preservation
                
                overall_accuracy = ranking_preservation['top_5']  # Use top-5 as primary metric
                accuracy_scores.append(overall_accuracy)
                
                detailed_result = {
                    'query_id': query_sample['id'],
                    'query_content_preview': query_sample['content'][:100],
                    'ranking_preservation': ranking_preservation,
                    'old_top_3': [(item[0], f"{item[1]:.3f}", item[2]) for item in old_similarities[:3]],
                    'new_top_3': [(item[0], f"{item[1]:.3f}", item[2]) for item in new_similarities[:3]]
                }
                detailed_results.append(detailed_result)
                
                logger.info(f"✅ Query {query_idx + 1}: Top-5 preservation = {overall_accuracy:.1%}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to test query {query_idx}: {e}")
                continue
        
        overall_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        accuracy_std = statistics.stdev(accuracy_scores) if len(accuracy_scores) > 1 else 0.0
        
        analysis = {
            'overall_metrics': {
                'mean_accuracy': overall_accuracy,
                'accuracy_std_dev': accuracy_std,
                'queries_tested': len(accuracy_scores),
                'accuracy_assessment': self._assess_accuracy_level(overall_accuracy)
            },
            'top_k_analysis': {
                'top_3_mean': statistics.mean([r['ranking_preservation']['top_3'] for r in detailed_results]) if detailed_results else 0,
                'top_5_mean': statistics.mean([r['ranking_preservation']['top_5'] for r in detailed_results]) if detailed_results else 0,
                'top_10_mean': statistics.mean([r['ranking_preservation']['top_10'] for r in detailed_results]) if detailed_results else 0
            },
            'detailed_results': detailed_results,
            'accuracy_distribution': accuracy_scores
        }
        
        logger.info(f"🎯 Overall search accuracy: {overall_accuracy:.1%} ± {accuracy_std:.1%} ({analysis['overall_metrics']['accuracy_assessment']})")
        return analysis
    
    def _assess_accuracy_level(self, accuracy: float) -> str:
        """Assess accuracy level."""
        if accuracy >= 0.9:
            return "EXCELLENT"
        elif accuracy >= 0.8:
            return "VERY_GOOD"
        elif accuracy >= 0.7:
            return "GOOD"
        elif accuracy >= 0.6:
            return "FAIR"
        else:
            return "POOR"
    
    def generate_comprehensive_assessment(self, dimension_analysis: Dict[str, Any], 
                                        performance_analysis: Dict[str, Any], 
                                        accuracy_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive optimization assessment."""
        logger.info("🏆 Generating comprehensive assessment...")
        
        reduction_ratio = dimension_analysis['optimization_metrics']['reduction_ratio']
        speedup = performance_analysis['similarity_calculation']['speedup_factor']
        accuracy = accuracy_analysis['overall_metrics']['mean_accuracy']
        
        # Calculate weighted quality score
        quality_score = 0
        
        # Performance factor (35%)
        if speedup >= 10:
            performance_factor = 1.0
        elif speedup >= 5:
            performance_factor = 0.8
        elif speedup >= 2:
            performance_factor = 0.6
        else:
            performance_factor = 0.4
        quality_score += performance_factor * 0.35
        
        # Accuracy factor (40%)
        if accuracy >= 0.9:
            accuracy_factor = 1.0
        elif accuracy >= 0.8:
            accuracy_factor = 0.9
        elif accuracy >= 0.7:
            accuracy_factor = 0.7
        elif accuracy >= 0.6:
            accuracy_factor = 0.5
        else:
            accuracy_factor = 0.3
        quality_score += accuracy_factor * 0.40
        
        # Storage factor (25%)
        if reduction_ratio >= 10:
            storage_factor = 1.0
        elif reduction_ratio >= 5:
            storage_factor = 0.8
        else:
            storage_factor = 0.6
        quality_score += storage_factor * 0.25
        
        # Overall recommendation
        if quality_score >= 0.85 and accuracy >= 0.8:
            recommendation = "HIGHLY RECOMMENDED - Proceed with full production migration"
            confidence = "VERY_HIGH"
            risk_level = "LOW"
        elif quality_score >= 0.75 and accuracy >= 0.7:
            recommendation = "RECOMMENDED - Proceed with careful monitoring"
            confidence = "HIGH"
            risk_level = "LOW"
        elif quality_score >= 0.65 and accuracy >= 0.6:
            recommendation = "CAUTIOUS APPROVAL - Extensive testing recommended"
            confidence = "MEDIUM"
            risk_level = "MEDIUM"
        else:
            recommendation = "NOT RECOMMENDED - Investigate alternatives"
            confidence = "LOW"
            risk_level = "HIGH"
        
        assessment = {
            'quality_score': quality_score,
            'recommendation': recommendation,
            'confidence_level': confidence,
            'risk_level': risk_level,
            'key_metrics': {
                'dimension_reduction': f"{reduction_ratio:.1f}x",
                'performance_improvement': f"{speedup:.1f}x",
                'accuracy_preservation': f"{accuracy:.1%}",
                'storage_reduction': f"{reduction_ratio:.1f}x"
            },
            'business_impact': {
                'estimated_latency_improvement': f"{((speedup - 1) * 100):.0f}%",
                'estimated_cost_reduction': f"{((reduction_ratio - 1) / reduction_ratio * 100):.0f}%",
                'projected_storage_savings_mb': performance_analysis['projected_production_impact']['total_storage_saved_mb'],
                'competitive_advantage': "HIGH" if speedup >= 10 else "MEDIUM"
            },
            'next_steps': self._generate_next_steps(quality_score, accuracy, confidence)
        }
        
        logger.info(f"🎯 Quality Score: {quality_score:.2f}/1.0 - {recommendation}")
        return assessment
    
    def _generate_next_steps(self, quality_score: float, accuracy: float, confidence: str) -> List[str]:
        """Generate contextual next steps."""
        if quality_score >= 0.85 and accuracy >= 0.8:
            return [
                "Design zero-downtime migration strategy",
                "Create comprehensive monitoring framework",
                "Plan gradual rollout with A/B testing",
                "Implement parallel table migration approach"
            ]
        elif quality_score >= 0.75:
            return [
                "Expand validation to larger sample size (500+ vectors)",
                "Implement enhanced monitoring for pilot testing",
                "Design limited pilot migration (10-20% of data)",
                "Create detailed rollback procedures"
            ]
        else:
            return [
                "Investigate accuracy optimization techniques",
                "Test alternative embedding models",
                "Analyze failing cases for improvement opportunities",
                "Consider hybrid approach with selective optimization"
            ]
    
    async def run_production_poc_validation(self, sample_count: int = 150) -> Dict[str, Any]:
        """Run complete production proof-of-concept validation."""
        start_time = time.time()
        logger.info(f"🚀 Starting production PoC validation with {sample_count} samples...")
        
        try:
            await self.connect_to_production()
            
            # Extract diverse production samples
            samples = await self.extract_production_samples(sample_count)
            
            if len(samples) < 50:
                raise ValueError(f"Insufficient samples extracted: {len(samples)} < 50")
            
            # Generate OpenAI embeddings
            processed_samples = await self.generate_openai_embeddings(samples)
            
            if len(processed_samples) < len(samples) * 0.8:
                logger.warning(f"⚠️ Lower success rate: {len(processed_samples)}/{len(samples)} samples processed")
            
            # Perform comprehensive analysis
            dimension_analysis = self.analyze_dimension_optimization(processed_samples)
            performance_analysis = self.benchmark_performance_improvements(processed_samples)
            accuracy_analysis = self.test_search_accuracy_preservation(processed_samples)
            comprehensive_assessment = self.generate_comprehensive_assessment(
                dimension_analysis, performance_analysis, accuracy_analysis
            )
            
            # Compile final results
            results = {
                'validation_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': time.time() - start_time,
                    'validation_type': 'production_poc_validation',
                    'samples_requested': sample_count,
                    'samples_extracted': len(samples),
                    'samples_processed': len(processed_samples),
                    'openai_api_calls': self.api_calls_made
                },
                'dimension_analysis': dimension_analysis,
                'performance_analysis': performance_analysis,
                'accuracy_analysis': accuracy_analysis,
                'comprehensive_assessment': comprehensive_assessment,
                'sample_data': processed_samples[:10],  # Include first 10 for reference
                'validation_status': 'COMPLETED_SUCCESSFULLY'
            }
            
            logger.info(f"✅ Production PoC validation completed in {time.time() - start_time:.1f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"❌ Production PoC validation failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"production_poc_validation_{timestamp}.json"
        
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
    print("🎯 Core Nexus Production PoC Validation")
    print("=" * 50)
    print("Phase 3.1: Proof-of-Concept with Real OpenAI Embeddings")
    print()
    
    try:
        validator = ProductionPoCValidator()
        results = await validator.run_production_poc_validation()
        
        # Save results
        filename = validator.save_results(results)
        
        # Print comprehensive summary
        print("\n🏆 PRODUCTION POC VALIDATION RESULTS")
        print("=" * 45)
        
        metadata = results['validation_metadata']
        print(f"✅ Samples Processed: {metadata['samples_processed']}/{metadata['samples_requested']}")
        print(f"✅ OpenAI API Calls: {metadata['openai_api_calls']}")
        print(f"✅ Duration: {metadata['duration_seconds']:.1f} seconds")
        
        dimension = results['dimension_analysis']
        print(f"\n📊 DIMENSION OPTIMIZATION")
        print("=" * 30)
        print(f"📏 Original: {dimension['original_dimensions']['mean']:.0f}D")
        print(f"📏 New: {dimension['new_dimensions']['target']}D")
        print(f"📏 Reduction: {dimension['optimization_metrics']['reduction_ratio']:.1f}x")
        
        performance = results['performance_analysis']
        print(f"\n🚀 PERFORMANCE ANALYSIS")
        print("=" * 30)
        sim_calc = performance['similarity_calculation']
        print(f"⚡ Speedup: {sim_calc['speedup_factor']:.1f}x")
        print(f"⚡ Improvement: {sim_calc['improvement_percentage']}")
        
        storage = performance['storage_analysis']
        print(f"💾 Storage Reduction: {storage['storage_reduction_ratio']:.1f}x")
        
        projected = performance['projected_production_impact']
        print(f"💾 Projected Savings: {projected['total_storage_saved_mb']:.1f} MB")
        
        accuracy = results['accuracy_analysis']
        print(f"\n🎯 SEARCH ACCURACY")
        print("=" * 25)
        overall = accuracy['overall_metrics']
        print(f"🔍 Overall Accuracy: {overall['mean_accuracy']:.1%}")
        print(f"🔍 Assessment: {overall['accuracy_assessment']}")
        print(f"🔍 Queries Tested: {overall['queries_tested']}")
        
        top_k = accuracy['top_k_analysis']
        print(f"🔍 Top-3 Preservation: {top_k['top_3_mean']:.1%}")
        print(f"🔍 Top-5 Preservation: {top_k['top_5_mean']:.1%}")
        print(f"🔍 Top-10 Preservation: {top_k['top_10_mean']:.1%}")
        
        assessment = results['comprehensive_assessment']
        print(f"\n🏆 COMPREHENSIVE ASSESSMENT")
        print("=" * 35)
        print(f"🎯 Quality Score: {assessment['quality_score']:.2f}/1.0")
        print(f"🎯 Recommendation: {assessment['recommendation']}")
        print(f"🎯 Confidence: {assessment['confidence_level']}")
        print(f"⚠️ Risk Level: {assessment['risk_level']}")
        
        business = assessment['business_impact']
        print(f"\n💼 BUSINESS IMPACT")
        print("=" * 20)
        print(f"📈 Latency Improvement: {business['estimated_latency_improvement']}")
        print(f"💰 Cost Reduction: {business['estimated_cost_reduction']}")
        print(f"🏆 Competitive Advantage: {business['competitive_advantage']}")
        
        print(f"\n🎯 NEXT STEPS")
        print("=" * 15)
        for i, step in enumerate(assessment['next_steps'], 1):
            print(f"{i}. {step}")
        
        print(f"\n💾 Complete results: {filename}")
        
        if assessment['quality_score'] >= 0.85:
            print("\n🚀 STATUS: PRODUCTION MIGRATION APPROVED!")
            print("✅ Ready to proceed with zero-downtime migration strategy")
        elif assessment['quality_score'] >= 0.75:
            print("\n🧪 STATUS: PILOT TESTING RECOMMENDED")
            print("⚠️ Proceed with limited pilot before full migration")
        else:
            print("\n🔬 STATUS: FURTHER INVESTIGATION NEEDED")
            print("❌ Address accuracy concerns before proceeding")
        
    except Exception as e:
        logger.error(f"❌ Production PoC validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())