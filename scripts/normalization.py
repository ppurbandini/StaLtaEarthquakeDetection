from obspy import read
import matplotlib.pyplot as plt
import os
import pandas as pd
from pathlib import Path


def normalize_text(value):
    """Normalize text fields used for matching."""
    if pd.isna(value):
        return ""
    return str(value).strip()

def normalize_location(value):
    """
    Normalize location codes.

    In MiniSEED, an empty location code is commonly represented as ''.
    In the manual-pick CSV, the same value may be written as '?', '--',
    'NaN', or 'None'. Treat these representations as equivalent.
    """
    value = normalize_text(value)

    if value.lower() in ["", "?", "--", "nan", "none", "null"]:
        return ""

    return value

def get_event_id(filename):
    """Extract the event ID from the first filename component.
    Example:
        EQ002_GE_SOEI_BHZ.mseed -> EQ002
        EQ063_GE_SOEI_BHZ.mseed -> EQ063
    """
    stem = Path(filename).stem
    event_id = stem.split("_")[0].strip()

    if not event_id:
        raise ValueError(f"Cannot extract event_id from filename: {filename}")

    return event_id

def get_trace_key(event_id, tr):
    """Create the matching key for a waveform Trace."""

    values = {"event_id": str(event_id).strip(),
              "network": normalize_text(tr.stats.network),
              "station": normalize_text(tr.stats.station),
              "location": normalize_location(tr.stats.location),
              "channel": normalize_text(tr.stats.channel)}
    
    KEY_COLUMNS = ["event_id", "station", "location", "channel"]
    return tuple(values[column] for column in KEY_COLUMNS)