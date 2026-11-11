from obspy import read
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from normalization import normalize_text, normalize_location, get_event_id, get_trace_key
from processing import preprocess_trace, calculate_classic_sta, match_triggers, plot_results, plot_combination

#input experimental parameters
sta_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
lta_values = [5, 7, 10, 15, 20, 25, 30]
threshold_on = 3.0
threshold_off = 1.5

tolerance = 2.0 
SAVE_ALL_PLOTS = True


#input/output folder
input_folder = Path("data/waveforms")
input_files = sorted(input_folder.glob("*.mseed"))
reference_file = Path("data/manual_p_wave.csv")

output_folder = Path("results/sensitivity")
output_folder.mkdir(parents=True, exist_ok=True)
figure_folder = Path("results/figures")
figure_folder.mkdir(parents=True, exist_ok=True)
heatmap_folder = Path("results/heatmaps")
heatmap_folder.mkdir(parents=True, exist_ok=True)


#prepare manual p_wave reference
manual = pd.read_csv(reference_file, dtype={"event_id": str,
                                            "station": str,
                                            "location": str,
                                            "channel": str})

for column in ["event_id", "station", "channel"]:
    manual[column] = manual[column].apply(normalize_text)

manual["location"] = manual["location"].apply(normalize_location)
manual["phase"] = (manual["phase"].astype(str).str.strip().str.upper())
manual = manual[manual["phase"].str.startswith("P")].copy()

#convert manual arrival time to UTC
manual["p_arrival"] = pd.to_datetime(manual["p_arrival"], utc=True, errors="coerce")
manual = manual.dropna(subset=["p_arrival"]).copy()
manual["arrival_timestamp"] = (manual["p_arrival"].apply(lambda x: x.timestamp()))

KEY_COLUMNS = ["event_id", "station", "location", "channel"]

if "network" in manual.columns:
    manual["network"] = manual["network"].apply(normalize_text)
    KEY_COLUMNS.insert(1, "network")

manual["key"] = list(zip(*(manual[column] for column in KEY_COLUMNS)))

print("\n========== INPUT INFORMATION ==========")
print(f"MiniSEED files found: {len(input_files)}")
print(f"Manual P-wave arrivals: {len(manual)}")
print(f"Matching fields: {KEY_COLUMNS}")


#run STA/LTA sensitivity experiment
summary_results = []
waveform_data = []

total_trace_count = 0

print("\n========== READING WAVEFORMS ==========")
for filename in input_files:
    print(f"\nReading: {filename.name}")

    st = read(str(filename))
    event_id = get_event_id(filename)
    print(f"  Traces in file: {len(st)}")

    for trace_number, tr in enumerate(st):
        total_trace_count += 1
        try:
            tr_raw = tr.copy()
            tr_filtered = preprocess_trace(tr)

            key = get_trace_key(event_id, tr_filtered)
            manual_subset = manual[manual["key"] == key]

            waveform_data.append({"filename": filename,
                                  "event_id": event_id,
                                  "trace_number": trace_number,
                                  "raw": tr_raw,
                                  "filtered": tr_filtered,
                                  "key": key,
                                  "manual": manual_subset})            

        except Exception as error:
            print(f"  ERROR processing Trace {trace_number}: {error}")

print("\n========== WAVEFORM SUMMARY ==========")
print(f"Total MiniSEED files: {len(input_files)}")
print(f"Total Traces read: {total_trace_count}")
print(f"Successfully prepared Traces: {len(waveform_data)}")


#run experiment
for sta_value in sta_values:
    for lta_value in lta_values:
        if lta_value <= sta_value:
            continue
        
        print("\n======================================")
        print(f"STA = {sta_value}, LTA = {lta_value}")
        print("======================================")

        combination_folder = (figure_folder / f"sta{sta_value}_lta{lta_value}_"
                              f"on{threshold_on}_off{threshold_off}")

        combination_folder.mkdir(parents=True, exist_ok=True)

        #initialize counters
        total_manual_p = 0
        total_triggers = 0

        total_TP = 0
        total_FP = 0
        total_FN = 0

        total_duration_hours = 0
        evaluated_waveforms = 0

        trigger_records = []

        for item in waveform_data:
            filename = item["filename"]
            event_id = item["event_id"]

            tr = item["raw"]
            tr_filtered = item["filtered"]

            manual_subset = item["manual"]

            try:
                cft, triggers = calculate_classic_sta(tr_filtered, sta_value, lta_value, threshold_on, threshold_off)
            except Exception as error:
                print(f"  STA/LTA error: {filename.name} "
                      f"{tr.id}: {error}")
                continue

            total_triggers += len(triggers)

            #convert trigger sample indices to UTC times.
            trigger_times = []
            for on, off in triggers:
                onset_time = (tr_filtered.stats.starttime + on / tr_filtered.stats.sampling_rate)
                offset_time = (tr_filtered.stats.starttime + off / tr_filtered.stats.sampling_rate)

                trigger_times.append(onset_time.timestamp)
                trigger_records.append({"filename": filename.name,
                                        "event_id": event_id,
                                        "network": tr_filtered.stats.network,
                                        "station": tr_filtered.stats.station,
                                        "location": tr_filtered.stats.location,
                                        "channel": tr_filtered.stats.channel,
                                        "trigger_onset_sample": int(on),
                                        "trigger_offset_sample": int(off),
                                        "trigger_onset_time": str(onset_time),
                                        "trigger_offset_time": str(offset_time),
                                        "trigger_duration_seconds": ((off - on) / tr_filtered.stats.sampling_rate),
                                        "sta": sta_value,
                                        "lta": lta_value,
                                        "threshold_on": threshold_on,
                                        "threshold_off": threshold_off})

            #save plots
            if SAVE_ALL_PLOTS:
                plot_results(filename, tr, tr_filtered, triggers, cft, sta_value, lta_value, threshold_on, threshold_off, combination_folder)

            if manual_subset.empty:
                continue

            start_timestamp = tr_filtered.stats.starttime.timestamp
            end_timestamp = tr_filtered.stats.endtime.timestamp

            manual_times = manual_subset["arrival_timestamp"].tolist()
            manual_times = sorted([t for t in manual_times if start_timestamp <= t <= end_timestamp])

            if not manual_times:
                continue

            #match manual P arrivals and detected trigger onsets.
            TP, FP, FN = match_triggers(manual_times, trigger_times, tolerance)
            total_manual_p += len(manual_times)

            total_TP += TP
            total_FP += FP
            total_FN += FN

            evaluated_waveforms += 1
            duration_seconds = (tr_filtered.stats.npts / tr_filtered.stats.sampling_rate)
            total_duration_hours += duration_seconds / 3600

        #calculate performance metrics
        if total_TP + total_FN != total_manual_p:
            raise RuntimeError("Performance-count inconsistency: TP + FN does not equal "
                               "the number of evaluated manual P arrivals.")

        detection_rate = (total_TP / total_manual_p * 100 if total_manual_p > 0 else np.nan)
        false_alarm_ratio = (total_FP / (total_TP + total_FP) * 100 if (total_TP + total_FP) > 0 else np.nan)
        miss_rate = (total_FN / total_manual_p * 100 if total_manual_p > 0 else np.nan)
        false_triggers_per_hour = (total_FP / total_duration_hours if total_duration_hours > 0 else np.nan)

        #save results
        result = {"sta": sta_value,
                  "lta": lta_value,
                  "threshold_on": threshold_on,
                  "threshold_off": threshold_off,
                  "evaluated_waveforms": evaluated_waveforms,
                  "total_manual_p": total_manual_p,
                  "total_triggers": total_triggers,
                  "true_positive": total_TP,
                  "false_positive": total_FP,
                  "false_negative": total_FN,
                  "detection_rate": detection_rate,
                  "false_alarm_ratio": false_alarm_ratio,
                  "miss_rate": miss_rate,
                  "false_triggers_per_hour": false_triggers_per_hour,
                  "evaluated_duration_hours": total_duration_hours}
        summary_results.append(result)
        
        trigger_df = pd.DataFrame(trigger_records)
        trigger_file = (output_folder / f"triggers_sta{sta_value}_lta{lta_value}_"
                        f"on{threshold_on}_off{threshold_off}.csv")
        trigger_df.to_csv(trigger_file, index=False)

        plot_combination(result, combination_folder)

        print(f"Evaluated waveforms with in-window manual picks: {evaluated_waveforms}")
        print(f"Manual P arrivals evaluated: {total_manual_p}")
        print(f"Total triggers: {total_triggers}")

        print(f"TP: {total_TP}")
        print(f"FP: {total_FP}")
        print(f"FN: {total_FN}")

        print(f"Detection rate: {detection_rate:.2f}%")
        print(f"False alarm ratio: {false_alarm_ratio:.2f}%")
        print(f"Miss rate: {miss_rate:.2f}%")

        print(f"False triggers per hour: "
              f"{false_triggers_per_hour:.3f}")


#save overall process
summary_df = pd.DataFrame(summary_results)
summary_file = (output_folder / "sta_lta_sensitivity_summary.csv")
summary_df.to_csv(summary_file, index=False)

print("\nSensitivity Analysis Completed!")
print(f"Valid parameter combinations: {len(summary_df)}")
print(f"Summary saved to: {summary_file}")


#generate heatmap
def create_heatmap(dataframe, metric, title, filename, cmap="viridis"):
    pivot = dataframe.pivot(index="sta", columns="lta", values=metric)
    pivot = pivot.reindex(index=sta_values, columns=lta_values)

    values = pivot.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(10, 7))
    image = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, aspect="auto", origin="upper")

    ax.set_xticks(range(len(lta_values)))
    ax.set_xticklabels(lta_values)

    ax.set_yticks(range(len(sta_values)))
    ax.set_yticklabels(sta_values)

    ax.set_xlabel("LTA Window (seconds)")
    ax.set_ylabel("STA Window (seconds)")
    ax.set_title(title)

    for i in range(len(sta_values)):
        for j in range(len(lta_values)):
            value = values[i, j]

            if np.isfinite(value):
                if metric == "false_triggers_per_hour":
                    label = f"{value:.2f}"
                else:
                    label = f"{value:.1f}%"
                ax.text(j, i, label, ha="center", va="center", color="black")
            else:
                ax.text(j, i, "N/A", ha="center", va="center")
                
    colorbar = fig.colorbar(image, ax=ax)

    if metric == "false_triggers_per_hour":
        colorbar.set_label("False Triggers per Hour")
    else:
        colorbar.set_label("Percentage (%)")

    plt.tight_layout()
    plt.savefig(heatmap_folder / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)
    
create_heatmap(summary_df, "detection_rate", "STA/LTA P-wave Detection Rate", "detection_rate.png")
create_heatmap(summary_df, "false_alarm_ratio", "STA/LTA False Alarm Ratio", "false_alarm_ratio.png")
create_heatmap(summary_df, "miss_rate", "STA/LTA Miss Rate", "miss_rate.png")
create_heatmap(summary_df, "false_triggers_per_hour", "False Triggers per Hour", "false_triggers_per_hour.png")

print("\nAll heatmaps saved!")