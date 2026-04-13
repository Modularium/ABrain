"""Canonical agent decision models for ABrain."""

from .agent_descriptor import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentLatencyProfile,
    AgentSourceType,
    AgentTrustLevel,
)
from .agent_quality import AgentQualitySummary, MIN_EXECUTIONS, compute_agent_quality
from .agent_registry import AgentRegistry
from .agent_creation import AgentCreationEngine
from .candidate_filter import CandidateAgent, CandidateAgentSet, CandidateFilter
from .capabilities import Capability, CapabilityRisk
from .feedback_loop import FeedbackLoop, FeedbackUpdate
from .feature_encoder import EncodedCandidateFeatures, FeatureEncoder
from .learning.dataset import TrainingDataset, TrainingSample
from .learning.online_updater import OnlineUpdater
from .learning.reward_model import RewardModel
from .learning.trainer import NeuralTrainer, TrainingMetrics
from .neural_policy import NeuralPolicyModel, ScoredCandidate
from .plan_builder import PlanBuilder
from .plan_models import ExecutionPlan, PlanStep, PlanStrategy
from .performance_history import AgentPerformanceHistory, PerformanceHistoryStore
from .planner import Planner, PlannerResult
from .routing_engine import RankedCandidate, RoutingDecision, RoutingEngine, RoutingPreferences
from .task_intent import TaskIntent

__all__ = [
    "AgentAvailability",
    "AgentQualitySummary",
    "MIN_EXECUTIONS",
    "compute_agent_quality",
    "AgentCreationEngine",
    "AgentCostProfile",
    "AgentDescriptor",
    "AgentExecutionKind",
    "AgentLatencyProfile",
    "AgentRegistry",
    "AgentSourceType",
    "AgentTrustLevel",
    "AgentPerformanceHistory",
    "Capability",
    "CapabilityRisk",
    "CandidateAgent",
    "CandidateAgentSet",
    "CandidateFilter",
    "EncodedCandidateFeatures",
    "FeedbackLoop",
    "FeedbackUpdate",
    "FeatureEncoder",
    "NeuralTrainer",
    "OnlineUpdater",
    "RewardModel",
    "NeuralPolicyModel",
    "ExecutionPlan",
    "PlanBuilder",
    "PlanStep",
    "PlanStrategy",
    "PerformanceHistoryStore",
    "Planner",
    "PlannerResult",
    "RankedCandidate",
    "RoutingDecision",
    "RoutingEngine",
    "RoutingPreferences",
    "ScoredCandidate",
    "TaskIntent",
    "TrainingDataset",
    "TrainingMetrics",
    "TrainingSample",
]
