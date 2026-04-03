import logging

import numpy as np

logger = logging.getLogger("phishguard.ml_inference")


def predict(feature_dict: dict, model, feature_names: list) -> float:
    try:
        values = [feature_dict[name] for name in feature_names]
        array = np.array([values], dtype=np.float32)  # shape (1, N)
        score = model.predict_proba(array)[0][1]
        return float(score)
    except Exception as exc:
        logger.error(f"ml_inference predict failed: {exc}")
        return 0.5
