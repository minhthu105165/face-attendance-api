from collections import defaultdict


def update_present_best(present_best: dict, matched: str, score: float):
    prev = present_best.get(matched, 0.0)
    if score > prev:
        present_best[matched] = score


def build_result(class_id: str, all_names: list[str], present_best: dict, unknown_faces: int, threshold: float, dbg: dict):
    present = sorted(present_best.keys())
    absent = sorted(list(set(all_names) - set(present)))

    return {
        "class_id": class_id,
        "count_total": len(all_names),
        "count_present": len(present),
        "present": [{"name": n, "score": present_best[n]} for n in present],
        "absent": absent,
        "unknown_faces_count": unknown_faces,
        "threshold": threshold,
        "debug": dbg,
    }
