from obspy import read
from obspy.signal.trigger import classic_sta_lta
from obspy.signal.trigger import trigger_onset
from obspy.signal.trigger import plot_trigger
from pathlib import Path
from normalization import normalize_text, normalize_location
import matplotlib.pyplot as plt
import os
import pandas as pd
import numpy as np


def preprocess_trace(tr):
    tr_filtered = tr.copy()

    tr_filtered.detrend("demean")
    tr_filtered.detrend("linear")
    tr_filtered.taper(max_percentage=0.05)

    #intended bandpass: 1–10 Hz
    #high-pass fallback when the sampling rate is 20 Hz
    nyquist = tr_filtered.stats.sampling_rate / 2.0
    freqmin = 1.0
    requested_freqmax = 10.0
    freqmax = min(requested_freqmax, 0.95 * nyquist)

    if freqmax <= freqmin:
        raise ValueError(
            f"Sampling rate {tr_filtered.stats.sampling_rate:g} Hz is too "
            "low for the requested 1 Hz high-pass corner."
        )
    tr_filtered.filter("bandpass", freqmin=freqmin, freqmax=freqmax)
    
    return tr_filtered


def calculate_classic_sta(tr, sta_value, lta_value, threshold_on, threshold_off):
    sampling_rate = tr.stats.sampling_rate

    nsta = int(sta_value * sampling_rate)
    nlta = int(lta_value * sampling_rate)

    if nsta < 1 or nlta < 1:
        raise ValueError("STA/LTA window is shorter than one sample.")

    if nlta <= nsta:
        raise ValueError("LTA window must be longer than STA window.")

    if tr.stats.npts <= nlta:
        return np.array([]), []

    cft = classic_sta_lta(tr.data, nsta, nlta)
    triggers = trigger_onset(cft, threshold_on, threshold_off)

    return cft, triggers


def match_triggers(manual_times, trigger_times, tolerance):
    candidates = []

    for p_idx, p_time in enumerate(manual_times):
        for t_idx, t_time in enumerate(trigger_times):

            difference = abs(p_time - t_time)

            if difference <= tolerance:
                candidates.append((difference, p_idx, t_idx))

    candidates.sort(key=lambda x: x[0])

    matched_manual = set()
    matched_triggers = set()

    for difference, p_idx, t_idx in candidates:
        if (p_idx not in matched_manual and t_idx not in matched_triggers):
            matched_manual.add(p_idx)
            matched_triggers.add(t_idx)

    TP = len(matched_manual)
    FN = len(manual_times) - TP
    FP = len(trigger_times) - len(matched_triggers)

    return TP, FP, FN


def plot_results(filename, tr, tr_filtered, triggers, cft, sta_value, lta_value, threshold_on, threshold_off, output_directory):
    trace_id = ".".join([normalize_text(tr.stats.network), 
                         normalize_text(tr.stats.station),
                         normalize_location(tr.stats.location),
                         normalize_text(tr.stats.channel)])

    name = f"{Path(filename).stem}_{trace_id}"
    fig, ax = plt.subplots(4, 1, figsize=(12, 11), sharex=True)

    #filtered seismic signal plot
    ax[0].plot(tr_filtered.times(), tr_filtered.data, color="black", linewidth=0.8)
    ax[0].set_ylabel("Amplitude")
    ax[0].set_title(f"{name} - Filtered Seismic Signal")

    #seismic signal with STA/LTA detection
    ax[1].plot(tr_filtered.times(), tr_filtered.data, color="black", linewidth=0.8)

    for on, off in triggers:
        trigger_start = on / tr_filtered.stats.sampling_rate
        trigger_end = off / tr_filtered.stats.sampling_rate
        
        ax[1].axvspan(trigger_start, trigger_end, alpha=0.3, color="orange")

    ax[1].set_ylabel("Amplitude")
    ax[1].set_title("Seismic Signal with STA/LTA Detection")

    #STA/LTA characteristic function
    if len(cft) > 0:
        ax[2].plot(tr_filtered.times(), cft, color="black", linewidth=0.8)
        ax[2].axhline(threshold_on, linestyle="--", label=f"Trigger On = {threshold_on}")
        ax[2].axhline(threshold_off, linestyle="--", color="red", label=f"Trigger Off = {threshold_off}")

    ax[2].set_ylabel("STA/LTA")
    ax[2].set_title(f"Classic STA/LTA - (STA={sta_value}s, LTA={lta_value}s)")
    ax[2].legend()

    #raw seismic waveform
    ax[3].plot(tr.times(), tr.data, color="black", linewidth=0.8)
    ax[3].set_xlabel("Time (s)")
    ax[3].set_ylabel("Amplitude")
    ax[3].set_title("Original Raw Seismic Signal")

    plt.tight_layout()

    output_directory.mkdir(parents=True, exist_ok=True)
    output_file = output_directory / f"{name}.png"

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    
    
def plot_combination(result, output_directory):
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))

    labels = ["TP", "FP", "FN"]
    values = [result["true_positive"],
              result["false_positive"],
              result["false_negative"]]

    bars = ax[0].bar(labels, values)

    ax[0].set_ylabel("Number of arrivals / triggers")
    ax[0].set_title("Overall Detection Classification")
    ax[0].grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        ax[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(value), ha="center", va="bottom")

    #performance metrics
    metric_labels = ["Detection rate",
                     "False alarm ratio",
                     "Miss rate"]

    metric_values = [result["detection_rate"],
                     result["false_alarm_ratio"],
                     result["miss_rate"]]

    bars = ax[1].bar(metric_labels, metric_values)
    ax[1].set_ylabel("Percentage (%)")
    ax[1].set_ylim(0, 105)
    ax[1].set_title("Overall Detection Performance")
    ax[1].tick_params(axis="x", rotation=15)
    ax[1].grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, metric_values):
        if pd.notna(value):
            ax[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}%", ha="center", va="bottom")

    fig.suptitle(f"STA={result['sta']}s, LTA={result['lta']}s | "
                 f"On={result['threshold_on']}, "
                 f"Off={result['threshold_off']}", fontsize=13)
    plt.tight_layout()
    output_file = output_directory / "overall_performance.png"

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    


