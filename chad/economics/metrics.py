from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LatencyMetrics:
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float


@dataclass(slots=True)
class RequestMetric:
    request_id: str
    model_id: str
    latency_ms: float
    success: bool = True
    error_type: str | None = None


class MetricsTracker:
    def __init__(self) -> None:
        self._metrics: list[RequestMetric] = []

    def record_request(
        self,
        request_id: str,
        model_id: str,
        latency_ms: float,
        success: bool = True,
        error_type: str | None = None,
    ) -> RequestMetric:
        metric = RequestMetric(
            request_id=request_id,
            model_id=model_id,
            latency_ms=latency_ms,
            success=success,
            error_type=error_type,
        )
        self._metrics.append(metric)
        return metric

    def get_latency_metrics(self, model_id: str | None = None) -> LatencyMetrics:
        metrics = self._metrics
        if model_id is not None:
            metrics = [m for m in metrics if m.model_id == model_id]

        if not metrics:
            return LatencyMetrics(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                error_rate=0.0,
                min_ms=0.0,
                max_ms=0.0,
                avg_ms=0.0,
                p50_ms=0.0,
                p95_ms=0.0,
            )

        total_requests = len(metrics)
        successful_requests = sum(1 for m in metrics if m.success)
        failed_requests = total_requests - successful_requests
        error_rate = failed_requests / total_requests

        latencies = sorted(m.latency_ms for m in metrics)
        min_ms = latencies[0]
        max_ms = latencies[-1]
        avg_ms = sum(latencies) / total_requests

        p50_ms = self._calculate_percentile(latencies, 50.0)
        p95_ms = self._calculate_percentile(latencies, 95.0)

        return LatencyMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            error_rate=error_rate,
            min_ms=min_ms,
            max_ms=max_ms,
            avg_ms=avg_ms,
            p50_ms=p50_ms,
            p95_ms=p95_ms,
        )

    @staticmethod
    def _calculate_percentile(sorted_values: list[float], percentile: float) -> float:
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]

        rank = (percentile / 100.0) * (len(sorted_values) - 1)
        lower_idx = math.floor(rank)
        upper_idx = math.ceil(rank)
        weight = rank - lower_idx

        if lower_idx == upper_idx:
            return sorted_values[lower_idx]
        return sorted_values[lower_idx] * (1.0 - weight) + sorted_values[upper_idx] * weight
