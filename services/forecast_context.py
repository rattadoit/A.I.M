from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ExternalForecastContext:
    sns_by_product: Dict[str, float] = field(default_factory=dict)
    event_by_product: Dict[str, float] = field(default_factory=dict)
    reason_snippets: Dict[str, str] = field(default_factory=dict)
    trend_summaries: List[str] = field(default_factory=list)
    event_summaries: List[str] = field(default_factory=list)
    total_sns_uplift: float = 0.0
    total_event_uplift: float = 0.0

    @classmethod
    def empty(cls) -> "ExternalForecastContext":
        return cls()
