import pandas as pd
from tools.predict import simple_rules

def test_simple_rules_basic():
    df = pd.DataFrame({
        "ip_freq": [1, 1000, 5, 2, 3],
        "ip_night_density": [0, 200, 0, 0, 0],
        "ip_hour_freq": [2, 500, 3, 1, 1],
        "ip_channel_freq": [1, 50, 1, 1, 1]
    })
    flags = simple_rules(
        df,
        ip_freq_quantile=0.8,      # keep test fast/deterministic
        night_quantile=0.8,
        hour_quantile=0.8,
        channel_quantile=0.8
    )
    # Expect high-frequency row(s) flagged
    assert flags.sum() >= 1
