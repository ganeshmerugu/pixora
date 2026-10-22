from __future__ import annotations
from pixora.agents.state import AgentState
from pixora.agents.classifier import ClassifierAgent
from pixora.agents.router import RouterAgent
from pixora.agents.extractor import ExtractorAgent
from pixora.agents.validator import ValidatorAgent
from pixora.agents.scorer import ScorerAgent
from pixora.models.pipeline import CorrectionDelta
from pixora.providers.registry import ProviderRegistry


class SupervisorAgent:
    def __init__(self, registry: ProviderRegistry | None = None):
        self.classifier = ClassifierAgent(registry)
        self.router = RouterAgent()
        self.extractor = ExtractorAgent(
            llm=registry.get("llm") if registry else None
        ) if registry else ExtractorAgent()
        self.validator = ValidatorAgent()
        self.scorer = ScorerAgent()

    async def run(self, state: AgentState) -> AgentState:
        state = await self.classifier.run(state)
        state = await self.router.run(state)
        state = await self._extraction_loop(state)
        return state

    async def _extraction_loop(self, state: AgentState) -> AgentState:
        max_rounds = state.get("max_correction_rounds", 3)
        state["correction_round"] = 0
        state.setdefault("correction_rounds", [])
        state.setdefault("task_hypotheses", [])
        state.setdefault("failure_attributions", [])

        for round_num in range(max_rounds):
            state["correction_round"] = round_num

            state = await self.extractor.run(state)
            state = await self.validator.run(state)
            state = await self.scorer.run(state)

            score = state.get("quality_score", 0.0)
            passed = state.get("validation_passed", False)
            recommendation = state.get("recommendation", "reprocess")

            # C5: TaskHypothesis
            state["task_hypotheses"].append({
                "round_num": round_num,
                "score": score,
                "passed": passed,
                "recommendation": recommendation,
                "action": "accept" if recommendation == "accept" else (
                    "correction" if round_num < max_rounds - 1 else "exhausted"
                ),
            })

            if recommendation == "accept":
                break

            if round_num < max_rounds - 1 and recommendation == "reprocess":
                # C7: FailureAttribution
                issues = state.get("validator_issues", [])
                for issue in issues:
                    if issue.get("severity") == "error":
                        state["failure_attributions"].append({
                            "round": round_num,
                            "dimension": issue.get("dimension", ""),
                            "field": issue.get("field", ""),
                            "message": issue.get("message", ""),
                        })

                state["correction_rounds"].append(CorrectionDelta(
                    round_number=round_num,
                    issues_found=[i.get("message", "") for i in issues],
                    score_before=score,
                ))

        # C8: VerificationReport
        state["verification_report"] = {
            "document_id": state["document_id"],
            "total_rounds": state["correction_round"] + 1,
            "final_score": state.get("quality_score", 0.0),
            "final_recommendation": state.get("recommendation", "unknown"),
            "hypotheses": state["task_hypotheses"],
            "attributions": state["failure_attributions"],
        }

        return state
