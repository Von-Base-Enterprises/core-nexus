"""
ADM (Automated Decision Making) Scoring System

Implements the Core Nexus intelligent memory scoring using Darwin-Gödel principles
for data quality, relevance, and intelligence assessment.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

from .models import MemoryResponse
from .unified_store import UnifiedVectorStore

logger = logging.getLogger(__name__)


class EvolutionStrategy(Enum):
    """Memory evolution strategies based on Darwin-Gödel principles."""
    REINFORCEMENT = "reinforcement"  # Strengthen successful patterns
    DIVERSIFICATION = "diversification"  # Explore new patterns
    CONSOLIDATION = "consolidation"  # Merge similar memories
    PRUNING = "pruning"  # Remove low-value memories


@dataclass
class ADMWeights:
    """Configurable weights for ADM scoring components."""
    data_quality: float = 0.3
    data_relevance: float = 0.4
    data_intelligence: float = 0.3

    def __post_init__(self):
        total = self.data_quality + self.data_relevance + self.data_intelligence
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"ADM weights must sum to 1.0, got {total}")


@dataclass
class ADMThresholds:
    """Thresholds for ADM decision making."""
    min_quality: float = 0.5
    min_relevance: float = 0.6
    min_intelligence: float = 0.4
    evolution_threshold: float = 0.1
    pruning_threshold: float = 0.2
    consolidation_threshold: float = 0.8


class DataQualityAnalyzer:
    """
    Analyzes data quality using multiple dimensions.
    
    Implements sophisticated quality metrics beyond simple content length.
    """

    def __init__(self):
        self.quality_cache = {}

    async def analyze_quality(self, content: str, metadata: dict[str, Any]) -> float:
        """
        Calculate data quality score (0.0 - 1.0).
        
        Considers: completeness, accuracy, consistency, timeliness, uniqueness.
        """
        try:
            # Base content quality
            content_quality = self._analyze_content_quality(content)

            # Metadata completeness
            metadata_quality = self._analyze_metadata_quality(metadata)

            # Temporal freshness
            temporal_quality = self._analyze_temporal_quality(metadata)

            # Structural consistency
            structural_quality = self._analyze_structural_quality(content, metadata)

            # Weighted average
            quality_score = (
                content_quality * 0.4 +
                metadata_quality * 0.2 +
                temporal_quality * 0.2 +
                structural_quality * 0.2
            )

            return max(0.0, min(1.0, quality_score))

        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            return 0.5  # Default neutral score

    def _analyze_content_quality(self, content: str) -> float:
        """Analyze the quality of content text."""
        if not content or len(content.strip()) < 10:
            return 0.1

        # Length factor (diminishing returns)
        length_score = min(1.0, len(content) / 500)

        # Complexity factors
        word_count = len(content.split())
        sentence_count = content.count('.') + content.count('!') + content.count('?')

        if sentence_count == 0:
            complexity_score = 0.3
        else:
            avg_sentence_length = word_count / sentence_count
            complexity_score = min(1.0, avg_sentence_length / 15)  # Optimal ~15 words/sentence

        # Information density (unique words ratio)
        unique_words = len(set(content.lower().split()))
        density_score = min(1.0, unique_words / word_count) if word_count > 0 else 0.0

        return (length_score * 0.4 + complexity_score * 0.3 + density_score * 0.3)

    def _analyze_metadata_quality(self, metadata: dict[str, Any]) -> float:
        """Analyze metadata completeness and quality."""
        if not metadata:
            return 0.3

        # Essential fields
        essential_fields = ['user_id', 'conversation_id', 'created_at']
        essential_score = sum(1 for field in essential_fields if field in metadata) / len(essential_fields)

        # Additional rich metadata
        rich_fields = ['importance_score', 'topic', 'sentiment', 'entities', 'context']
        rich_score = sum(1 for field in rich_fields if field in metadata) / len(rich_fields)

        return essential_score * 0.7 + rich_score * 0.3

    def _analyze_temporal_quality(self, metadata: dict[str, Any]) -> float:
        """Analyze temporal freshness and relevance."""
        created_at = metadata.get('created_at')
        if not created_at:
            return 0.5

        try:
            if isinstance(created_at, (int, float)):
                created_time = datetime.fromtimestamp(created_at)
            else:
                created_time = datetime.fromisoformat(str(created_at))

            # Fresher content scores higher (exponential decay)
            age_days = (datetime.utcnow() - created_time).days
            freshness_score = np.exp(-age_days / 30)  # 30-day half-life

            return max(0.1, min(1.0, freshness_score))

        except Exception:
            return 0.5

    def _analyze_structural_quality(self, content: str, metadata: dict[str, Any]) -> float:
        """Analyze structural consistency and formatting."""
        # Check for structured data patterns
        structure_indicators = [
            content.count('\n') > 0,  # Multi-line structure
            ':' in content or '=' in content,  # Key-value patterns
            any(c.isdigit() for c in content),  # Contains numbers
            any(c.isupper() for c in content),  # Contains capitals
            len(content.split()) > 5  # Sufficient word count
        ]

        structure_score = sum(structure_indicators) / len(structure_indicators)
        return structure_score


class DataRelevanceAnalyzer:
    """
    Analyzes data relevance using contextual and semantic factors.
    
    Considers user patterns, conversation context, and semantic relationships.
    """

    def __init__(self, unified_store: UnifiedVectorStore):
        self.unified_store = unified_store
        self.relevance_cache = {}

    async def analyze_relevance(
        self,
        content: str,
        metadata: dict[str, Any],
        context_memories: list[MemoryResponse] | None = None
    ) -> float:
        """
        Calculate data relevance score (0.0 - 1.0).
        
        Considers: user patterns, conversation context, semantic similarity, temporal context.
        """
        try:
            # User pattern relevance
            user_relevance = await self._analyze_user_patterns(metadata)

            # Conversation context relevance
            context_relevance = await self._analyze_conversation_context(metadata)

            # Semantic relevance to existing memories
            semantic_relevance = await self._analyze_semantic_relevance(content, context_memories)

            # Topic relevance
            topic_relevance = self._analyze_topic_relevance(content, metadata)

            # Weighted combination
            relevance_score = (
                user_relevance * 0.3 +
                context_relevance * 0.3 +
                semantic_relevance * 0.25 +
                topic_relevance * 0.15
            )

            return max(0.0, min(1.0, relevance_score))

        except Exception as e:
            logger.error(f"Relevance analysis failed: {e}")
            return 0.5

    async def _analyze_user_patterns(self, metadata: dict[str, Any]) -> float:
        """Analyze relevance based on user's historical patterns."""
        user_id = metadata.get('user_id')
        if not user_id:
            return 0.5

        try:
            # Get user's recent memory patterns
            from .models import QueryRequest
            query = QueryRequest(
                query="user patterns",  # Placeholder - will be filtered by user_id
                limit=50,
                user_id=user_id,
                min_similarity=0.0
            )

            user_memories = await self.unified_store.query_memories(query)

            if not user_memories.memories:
                return 0.3  # New user, moderate relevance

            # Analyze user's topic preferences
            user_topics = {}
            total_importance = 0

            for memory in user_memories.memories:
                topic = memory.metadata.get('topic', 'general')
                importance = memory.importance_score or 0.5
                user_topics[topic] = user_topics.get(topic, 0) + importance
                total_importance += importance

            # Score based on topic alignment
            current_topic = metadata.get('topic', 'general')
            topic_score = user_topics.get(current_topic, 0) / max(1, total_importance)

            # Activity pattern bonus
            activity_bonus = min(0.2, len(user_memories.memories) / 100)

            return min(1.0, topic_score + activity_bonus)

        except Exception as e:
            logger.warning(f"User pattern analysis failed: {e}")
            return 0.5

    async def _analyze_conversation_context(self, metadata: dict[str, Any]) -> float:
        """Analyze relevance within conversation context."""
        conversation_id = metadata.get('conversation_id')
        if not conversation_id:
            return 0.5

        try:
            # Get conversation history
            from .models import QueryRequest
            query = QueryRequest(
                query="conversation context",
                limit=20,
                conversation_id=conversation_id,
                min_similarity=0.0
            )

            conv_memories = await self.unified_store.query_memories(query)

            if not conv_memories.memories:
                return 0.4  # New conversation

            # Calculate conversation coherence
            recent_memories = conv_memories.memories[:10]
            avg_importance = sum(m.importance_score or 0.5 for m in recent_memories) / len(recent_memories)

            # Conversation length factor
            length_factor = min(1.0, len(conv_memories.memories) / 20)

            return avg_importance * 0.7 + length_factor * 0.3

        except Exception as e:
            logger.warning(f"Conversation context analysis failed: {e}")
            return 0.5

    async def _analyze_semantic_relevance(
        self,
        content: str,
        context_memories: list[MemoryResponse] | None
    ) -> float:
        """Analyze semantic similarity to existing relevant memories."""
        if not context_memories:
            return 0.5

        try:
            # Calculate average similarity to context memories
            similarities = [m.similarity_score or 0.5 for m in context_memories[:10]]
            avg_similarity = sum(similarities) / len(similarities)

            # Boost for moderate similarity (novel but related content)
            if 0.3 <= avg_similarity <= 0.8:
                novelty_bonus = 0.2
            else:
                novelty_bonus = 0.0

            return min(1.0, avg_similarity + novelty_bonus)

        except Exception as e:
            logger.warning(f"Semantic relevance analysis failed: {e}")
            return 0.5

    def _analyze_topic_relevance(self, content: str, metadata: dict[str, Any]) -> float:
        """Analyze topic-based relevance."""
        # Simple keyword-based topic detection
        technical_keywords = ['api', 'code', 'function', 'database', 'algorithm', 'system']
        personal_keywords = ['feel', 'think', 'like', 'prefer', 'want', 'need']
        business_keywords = ['project', 'meeting', 'deadline', 'client', 'revenue', 'strategy']

        content_lower = content.lower()

        topic_scores = {
            'technical': sum(1 for kw in technical_keywords if kw in content_lower),
            'personal': sum(1 for kw in personal_keywords if kw in content_lower),
            'business': sum(1 for kw in business_keywords if kw in content_lower)
        }

        max_score = max(topic_scores.values()) if topic_scores.values() else 0
        return min(1.0, max_score / 3)  # Normalize by max expected keywords


class DataIntelligenceAnalyzer:
    """
    Analyzes data intelligence using knowledge extraction and insight generation.
    
    Focuses on the potential for learning and decision-making enhancement.
    """

    def __init__(self):
        self.intelligence_cache = {}

    async def analyze_intelligence(
        self,
        content: str,
        metadata: dict[str, Any],
        historical_performance: dict[str, float] | None = None
    ) -> float:
        """
        Calculate data intelligence score (0.0 - 1.0).
        
        Considers: knowledge density, actionability, learning potential, prediction value.
        """
        try:
            # Knowledge density analysis
            knowledge_score = self._analyze_knowledge_density(content)

            # Actionability assessment
            actionability_score = self._analyze_actionability(content, metadata)

            # Learning potential
            learning_score = self._analyze_learning_potential(content, metadata)

            # Prediction value
            prediction_score = self._analyze_prediction_value(content, metadata, historical_performance)

            # Weighted combination
            intelligence_score = (
                knowledge_score * 0.3 +
                actionability_score * 0.25 +
                learning_score * 0.25 +
                prediction_score * 0.2
            )

            return max(0.0, min(1.0, intelligence_score))

        except Exception as e:
            logger.error(f"Intelligence analysis failed: {e}")
            return 0.5

    def _analyze_knowledge_density(self, content: str) -> float:
        """Analyze the density of extractable knowledge."""
        if not content:
            return 0.0

        # Entity indicators (simplified NER)
        entity_indicators = [
            len([w for w in content.split() if w[0].isupper()]),  # Capitalized words
            content.count('@'),  # Email/mentions
            content.count('http'),  # URLs
            content.count('$'),  # Currency
            len([w for w in content.split() if w.isdigit()]),  # Numbers
        ]

        knowledge_density = sum(entity_indicators) / len(content.split())
        return min(1.0, knowledge_density * 5)  # Scale factor

    def _analyze_actionability(self, content: str, metadata: dict[str, Any]) -> float:
        """Analyze how actionable the information is."""
        action_indicators = [
            'should', 'must', 'need', 'will', 'plan', 'decide', 'action',
            'implement', 'execute', 'schedule', 'deadline', 'priority'
        ]

        content_lower = content.lower()
        action_count = sum(1 for indicator in action_indicators if indicator in content_lower)

        # Boost for temporal context
        temporal_boost = 0.2 if any(word in content_lower for word in ['today', 'tomorrow', 'next', 'soon']) else 0

        actionability = (action_count / 10) + temporal_boost  # Normalize and add boost
        return min(1.0, actionability)

    def _analyze_learning_potential(self, content: str, metadata: dict[str, Any]) -> float:
        """Analyze the potential for learning from this information."""
        learning_indicators = [
            'learn', 'understand', 'pattern', 'trend', 'insight', 'analysis',
            'conclusion', 'result', 'outcome', 'lesson', 'experience'
        ]

        content_lower = content.lower()
        learning_count = sum(1 for indicator in learning_indicators if indicator in content_lower)

        # Complexity bonus for detailed content
        complexity_bonus = 0.1 if len(content) > 200 else 0

        learning_potential = (learning_count / 8) + complexity_bonus
        return min(1.0, learning_potential)

    def _analyze_prediction_value(
        self,
        content: str,
        metadata: dict[str, Any],
        historical_performance: dict[str, float] | None
    ) -> float:
        """Analyze the value for future predictions."""
        prediction_indicators = [
            'predict', 'forecast', 'trend', 'pattern', 'behavior', 'likely',
            'probability', 'expect', 'anticipate', 'future'
        ]

        content_lower = content.lower()
        prediction_count = sum(1 for indicator in prediction_indicators if indicator in content_lower)

        # Historical performance boost
        historical_boost = 0.0
        if historical_performance:
            avg_performance = sum(historical_performance.values()) / len(historical_performance)
            historical_boost = avg_performance * 0.2

        prediction_value = (prediction_count / 8) + historical_boost
        return min(1.0, prediction_value)


class ADMScoringEngine:
    """
    Main ADM scoring engine that combines all analysis components.
    
    Implements the Core Nexus Darwin-Gödel intelligence framework.
    """

    def __init__(
        self,
        unified_store: UnifiedVectorStore,
        weights: ADMWeights | None = None,
        thresholds: ADMThresholds | None = None
    ):
        self.unified_store = unified_store
        self.weights = weights or ADMWeights()
        self.thresholds = thresholds or ADMThresholds()

        # Initialize analyzers
        self.quality_analyzer = DataQualityAnalyzer()
        self.relevance_analyzer = DataRelevanceAnalyzer(unified_store)
        self.intelligence_analyzer = DataIntelligenceAnalyzer()

        # Performance tracking
        self.scoring_history = []
        self.evolution_decisions = []

    async def calculate_adm_score(
        self,
        content: str,
        metadata: dict[str, Any],
        context_memories: list[MemoryResponse] | None = None
    ) -> dict[str, float]:
        """
        Calculate comprehensive ADM score with component breakdown.
        
        Returns:
            Dict with 'adm_score' and component scores (dq, dr, di)
        """
        start_time = time.time()

        try:
            # Run all analyses concurrently
            dq_task = self.quality_analyzer.analyze_quality(content, metadata)
            dr_task = self.relevance_analyzer.analyze_relevance(content, metadata, context_memories)
            di_task = self.intelligence_analyzer.analyze_intelligence(content, metadata)

            dq_score, dr_score, di_score = await asyncio.gather(dq_task, dr_task, di_task)

            # Calculate weighted ADM score
            adm_score = (
                self.weights.data_quality * dq_score +
                self.weights.data_relevance * dr_score +
                self.weights.data_intelligence * di_score
            )

            # Track performance
            calculation_time = time.time() - start_time
            self.scoring_history.append({
                'timestamp': datetime.utcnow(),
                'calculation_time': calculation_time,
                'adm_score': adm_score,
                'components': {'dq': dq_score, 'dr': dr_score, 'di': di_score}
            })

            logger.debug(f"ADM score calculated in {calculation_time:.3f}s: {adm_score:.3f}")

            return {
                'adm_score': adm_score,
                'data_quality': dq_score,
                'data_relevance': dr_score,
                'data_intelligence': di_score,
                'calculation_time_ms': calculation_time * 1000
            }

        except Exception as e:
            logger.error(f"ADM scoring failed: {e}")
            return {
                'adm_score': 0.5,
                'data_quality': 0.5,
                'data_relevance': 0.5,
                'data_intelligence': 0.5,
                'error': str(e)
            }

    async def suggest_evolution_strategy(
        self,
        memory: MemoryResponse,
        performance_data: dict[str, Any] | None = None
    ) -> tuple[EvolutionStrategy, float]:
        """
        Suggest evolution strategy based on Darwin-Gödel principles.
        
        Returns:
            Tuple of (strategy, confidence_score)
        """
        try:
            # Analyze current memory performance
            current_adm = await self.calculate_adm_score(
                memory.content,
                memory.metadata
            )

            adm_score = current_adm['adm_score']
            access_count = memory.metadata.get('access_count', 0)
            age_days = (datetime.utcnow() - memory.created_at).days

            # Decision logic based on performance
            if adm_score >= 0.8 and access_count > 5:
                # High-value, frequently accessed -> Reinforce
                return EvolutionStrategy.REINFORCEMENT, 0.9

            elif adm_score < self.thresholds.pruning_threshold and access_count == 0 and age_days > 30:
                # Low-value, unused, old -> Prune
                return EvolutionStrategy.PRUNING, 0.8

            elif 0.4 <= adm_score <= 0.7 and access_count < 3:
                # Medium value, low access -> Diversify/explore
                return EvolutionStrategy.DIVERSIFICATION, 0.6

            elif adm_score >= self.thresholds.consolidation_threshold:
                # High similarity to existing memories -> Consolidate
                return EvolutionStrategy.CONSOLIDATION, 0.7

            else:
                # Default: monitor and maintain
                return EvolutionStrategy.REINFORCEMENT, 0.3

        except Exception as e:
            logger.error(f"Evolution strategy suggestion failed: {e}")
            return EvolutionStrategy.REINFORCEMENT, 0.1

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get ADM engine performance metrics."""
        if not self.scoring_history:
            return {'status': 'no_data'}

        recent_scores = self.scoring_history[-100:]  # Last 100 calculations

        avg_time = sum(s['calculation_time'] for s in recent_scores) / len(recent_scores)
        avg_adm = sum(s['adm_score'] for s in recent_scores) / len(recent_scores)

        # Component averages
        avg_dq = sum(s['components']['dq'] for s in recent_scores) / len(recent_scores)
        avg_dr = sum(s['components']['dr'] for s in recent_scores) / len(recent_scores)
        avg_di = sum(s['components']['di'] for s in recent_scores) / len(recent_scores)

        return {
            'total_calculations': len(self.scoring_history),
            'avg_calculation_time_ms': avg_time * 1000,
            'avg_adm_score': avg_adm,
            'component_averages': {
                'data_quality': avg_dq,
                'data_relevance': avg_dr,
                'data_intelligence': avg_di
            },
            'evolution_decisions': len(self.evolution_decisions),
            'weights': {
                'data_quality': self.weights.data_quality,
                'data_relevance': self.weights.data_relevance,
                'data_intelligence': self.weights.data_intelligence
            },
            'thresholds': {
                'min_quality': self.thresholds.min_quality,
                'min_relevance': self.thresholds.min_relevance,
                'min_intelligence': self.thresholds.min_intelligence,
                'evolution_threshold': self.thresholds.evolution_threshold
            }
        }
