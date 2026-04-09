import inspect

import pytest

from services.routing_agent.service import RoutingAgentService

pytestmark = pytest.mark.unit


def test_routing_agent_service_uses_canonical_engine_for_selection():
    service = RoutingAgentService()

    response = service.route(
        "code_refactor",
        context={
            "agents": [
                {
                    "id": "agent-low",
                    "name": "agent-low",
                    "url": "http://agent-low",
                    "capabilities": ["analysis.code", "code.refactor"],
                    "estimated_cost_per_token": 0.008,
                    "avg_response_time": 5.0,
                    "traits": {"trust_level": "trusted", "availability": "online"},
                },
                {
                    "id": "agent-high",
                    "name": "agent-high",
                    "url": "http://agent-high",
                    "capabilities": ["analysis.code", "code.refactor"],
                    "estimated_cost_per_token": 0.001,
                    "avg_response_time": 1.0,
                    "traits": {"trust_level": "trusted", "availability": "online"},
                },
            ]
        },
    )

    assert response["target_worker"] == "agent-high"
    assert response["decision"]["selected_agent_id"] == "agent-high"


def test_routing_agent_service_does_not_use_legacy_nn_manager_or_meta_learner():
    source = inspect.getsource(RoutingAgentService)

    assert "NNManager" not in source
    assert "MetaLearner" not in source
