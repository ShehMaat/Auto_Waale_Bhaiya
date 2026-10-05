from typing import Any

from langgraph.graph import END, StateGraph

from packages.pipeline.nodes import PipelineNodes
from packages.pipeline.state import PipelineState


def route_eligibility(state: PipelineState) -> str:
    """Route based on eligibility status."""
    eligibility = state.get("eligibility_status")
    if eligibility == "ELIGIBLE":
        return "rank_jobs"
    return "track_result"

def route_next_job(state: PipelineState) -> str:
    """Loop through jobs or complete."""
    canonical_jobs = state.get("canonical_jobs", [])
    current_index = state.get("current_job_index", 0)
    
    if current_index < len(canonical_jobs):
        return "check_freshness"
    return END



def build_pipeline_graph() -> StateGraph[Any]:
    nodes = PipelineNodes()
    workflow = StateGraph(PipelineState)

    # Add Nodes
    workflow.add_node("load_search_policy", nodes.load_search_policy)
    workflow.add_node("discover_jobs", nodes.discover_jobs)
    workflow.add_node("normalize_jobs", nodes.normalize_jobs)
    workflow.add_node("deduplicate_jobs", nodes.deduplicate_jobs)
    
    workflow.add_node("check_freshness", nodes.check_freshness)
    workflow.add_node("match_phase4", nodes.match_phase4)
    workflow.add_node("apply_hard_constraints", nodes.apply_hard_constraints)
    workflow.add_node("preference_filter", nodes.preference_filter)
    workflow.add_node("check_application_history", nodes.check_application_history)
    workflow.add_node("determine_eligibility", nodes.determine_eligibility)
    
    workflow.add_node("rank_jobs", nodes.rank_jobs)
    workflow.add_node("queue_job", nodes.queue_job)
    workflow.add_node("run_phase10", nodes.run_phase10)
    workflow.add_node("track_result", nodes.track_result)

    # Edges
    workflow.set_entry_point("load_search_policy")
    workflow.add_edge("load_search_policy", "discover_jobs")
    workflow.add_edge("discover_jobs", "normalize_jobs")
    workflow.add_edge("normalize_jobs", "deduplicate_jobs")
    
    # Start iterating over canonical jobs
    workflow.add_conditional_edges(
        "deduplicate_jobs",
        route_next_job,
        {
            "check_freshness": "check_freshness",
            END: END,
        }
    )

    workflow.add_edge("check_freshness", "match_phase4")
    workflow.add_edge("match_phase4", "apply_hard_constraints")
    workflow.add_edge("apply_hard_constraints", "preference_filter")
    workflow.add_edge("preference_filter", "check_application_history")
    workflow.add_edge("check_application_history", "determine_eligibility")

    workflow.add_conditional_edges(
        "determine_eligibility",
        route_eligibility,
        {
            "rank_jobs": "rank_jobs",
            "track_result": "track_result",
        }
    )

    workflow.add_edge("rank_jobs", "queue_job")
    workflow.add_edge("queue_job", "run_phase10")
    workflow.add_edge("run_phase10", "track_result")

    # Loop back to next job
    workflow.add_conditional_edges(
        "track_result",
        route_next_job,
        {
            "check_freshness": "check_freshness",
            END: END,
        }
    )

    return workflow

pipeline_graph = build_pipeline_graph()
