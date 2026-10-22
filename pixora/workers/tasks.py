from __future__ import annotations
from typing import Any


class TaskResult:
    def __init__(self, job_id: str, status: str, result: dict[str, Any] | None = None):
        self.job_id = job_id
        self.status = status
        self.result = result

    def to_dict(self) -> dict[str, Any]:
        return {"job_id": self.job_id, "status": self.status, "result": self.result}


class ParseTask:
    async def execute(self, job_id: str, file_id: str, tier: str = "agentic", **kwargs: Any) -> TaskResult:
        return TaskResult(job_id=job_id, status="completed", result={"file_id": file_id, "tier": tier})


class ExtractTask:
    async def execute(self, job_id: str, file_id: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> TaskResult:
        return TaskResult(job_id=job_id, status="completed", result={"file_id": file_id})


class ClassifyTask:
    async def execute(self, job_id: str, file_id: str, rules: list[dict] | None = None, **kwargs: Any) -> TaskResult:
        return TaskResult(job_id=job_id, status="completed", result={"file_id": file_id})
