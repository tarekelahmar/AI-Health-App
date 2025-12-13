from app.domain.metric_policies import METRIC_POLICIES


def generate_coverage_matrix() -> dict:
    matrix = {}
    for metric_key, policy in METRIC_POLICIES.items():
        matrix[metric_key] = {
            "change": policy.change is not None,
            "trend": policy.trend is not None,
            "instability": policy.instability is not None,
        }
    return matrix

