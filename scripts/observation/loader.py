"""Read-only loader for MSM observation-layer artifacts.

MUST NOT import other scripts/* modules.
MUST NOT mutate any artifact on disk.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DIR_FAILURE = ROOT / "data" / "processed" / "failure"
DIR_STATE   = ROOT / "data" / "processed" / "state_vector"
DIR_TRADES  = ROOT / "data" / "processed" / "backtest" / "h20_nonoverlap"

VALID_CLASSES = {"INVARIANT","CONDITIONAL","TRAP","DEAD","AMBIGUOUS","INSUFFICIENT"}
VALID_MACRO   = {"BULL","BEAR","RECOVERY"}

SCHEMA = {
    "regime_pnl":       {"macro_regime","n_trades","mean","std","sum","hit_rate","sharpe_ann"},
    "state_decomp":     {"state_id","macro_regime","n","mean","std","sum","se","t_one_sample"},
    "ev_flip_map":      {"state_id","mu_bull","mu_bear","n_bull","n_bear",
                         "t_flip","t_bull_pos","t_bear_pos","reliable"},
    "regime_labels":    {"date","equity_market","dd","regime"},
    "transition_drift": {"regime","state_id","next_state","n","P"},
    "transition_kl":    {"state_id","kl_bull_bear"},
    "panel":            {"date","code","state_id"},
    "trades":           {"entry_date","exit_date","code","state_id","ret_net"},
}


def _require_cols(df, name):
    missing = SCHEMA[name] - set(df.columns)
    if missing:
        raise ValueError(f"[loader.{name}] missing columns: {sorted(missing)}; "
                         f"got {sorted(df.columns)}")
    return df


def _read(path, name):
    if not path.exists():
        raise FileNotFoundError(f"[loader.{name}] not found: {path}")
    return _require_cols(pd.read_parquet(path), name)


def load_state_class():
    p = DIR_FAILURE / "state_class.json"
    if not p.exists():
        raise FileNotFoundError(f"[loader.state_class] not found: {p}")
    raw = json.loads(p.read_text())
    out = {int(k): str(v) for k, v in raw.items()}
    bad = set(out.values()) - VALID_CLASSES
    if bad:
        raise ValueError(f"[loader.state_class] invalid classes: {bad}")
    return out


def load_regime_pnl():
    df = _read(DIR_FAILURE / "regime_pnl.parquet", "regime_pnl")
    bad = set(df["macro_regime"].unique()) - VALID_MACRO
    if bad:
        raise ValueError(f"[loader.regime_pnl] invalid macro_regime: {bad}")
    return df


def load_state_decomp():     return _read(DIR_FAILURE / "state_decomp.parquet",     "state_decomp")
def load_ev_flip():          return _read(DIR_FAILURE / "ev_flip_map.parquet",      "ev_flip_map")
def load_regime_labels():    return _read(DIR_FAILURE / "regime_labels.parquet",    "regime_labels")
def load_transition_drift(): return _read(DIR_FAILURE / "transition_drift.parquet", "transition_drift")
def load_transition_kl():    return _read(DIR_FAILURE / "transition_kl.parquet",    "transition_kl")
def load_panel():            return _read(DIR_STATE   / "panel.parquet",            "panel")
def load_trades():           return _read(DIR_TRADES  / "trades.parquet",           "trades")
