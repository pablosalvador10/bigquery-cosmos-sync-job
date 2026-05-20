"""Pipeline registry — name → Pipeline factory."""

from collections.abc import Callable

from bq_cosmos_sync.pipelines.base import Pipeline
from bq_cosmos_sync.pipelines.courses import CoursesPipeline
from bq_cosmos_sync.pipelines.learners import LearnersPipeline
from bq_cosmos_sync.pipelines.recommendations import RecommendationsPipeline

PipelineFactory = Callable[[], Pipeline]


class PipelineRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, PipelineFactory] = {}

    def register(self, name: str, factory: PipelineFactory) -> None:
        if name in self._factories:
            msg = f"Pipeline already registered: {name}"
            raise ValueError(msg)
        self._factories[name] = factory

    def names(self) -> list[str]:
        return sorted(self._factories.keys())

    def build(self, name: str) -> Pipeline:
        if name not in self._factories:
            msg = f"Unknown pipeline: {name!r}. Registered: {self.names()}"
            raise KeyError(msg)
        return self._factories[name]()

    def build_many(self, names: list[str] | None) -> list[Pipeline]:
        selected = names or self.names()
        return [self.build(n) for n in selected]


def default_registry() -> PipelineRegistry:
    r = PipelineRegistry()
    r.register("courses", CoursesPipeline)
    r.register("learners", LearnersPipeline)
    r.register("recommendations", RecommendationsPipeline)
    return r
