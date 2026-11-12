# EARTHQUAKE DETECTION USING THE STA/LTA ALGORITHM

Independent Research Project

## 1. Project Overview

This project explores the application of the Short-Time Average / Long-Time Average (STA/LTA) algorithm for automatic seismic event detection using earthquake waveform data.

The study examines how different STA/LTA window lengths and triggering thresholds influence the identification of seismic signals. In addition to examining waveform triggering behavior, the project evaluates detection results against manually picked P-wave arrivals to assess the reliability of different parameter configurations. The analysis involves waveform acquisition, preprocessing, filtering, STA/LTA triggering, manual P-wave reference matching, performance evaluation, and visualization of detection results.

The project uses waveform recordings from 61 catalog earthquake events obtained through FDSN web services.

## 2. Research Objectives

The main objectives of this project are:
1. To develop a Python-based workflow for seismic waveform preprocessing and STA/LTA triggering.
2. To investigate the influence of STA and LTA window lengths on detection behavior.
3. To evaluate STA/LTA detection performance using manually picked P-wave arrivals as reference observations.
4. To quantify detection performance using detection rate, false alarm ratio, false triggers per hour, and miss rate.

## 3. Study Area and Dataset

Earthquake events were selected from the USGS Earthquake Catalog between January and March 2024.

Earthquake catalog selection:
* Data provider: USGS
* Time period: January 1 -  March 31, 2024
* Minimum magnitude: M 4.0
* Latitude: −11.379° to −3.980°
* Longitude: 115.269° to 128.188°
* Number of earthquake events: 61

Seismic waveform data:
* Data format: MiniSEED
* Channel: BHZ
* Requested time window: -60 s to 300 s relative to origin time
* Waveform duration requested: 360 s
* Waveform providers: GFZ and EarthScope

Further information about the datasets is available in data/README.md.

## 4. Methodology Overview

The processing workflow consists of four main stages:

1. Waveform preprocessing: Seismic waveforms are prepared and bandpass-filtered between 1 and 10 Hz.
2. STA/LTA triggering: The classic STA/LTA algorithm is applied to identify candidate seismic signal arrivals.
3. Manual P-wave comparison: Automatic trigger onsets are compared with manually picked P-wave arrival times.
4. Performance evaluation: Detection performance is evaluated using detection rate, false alarm ratio, false triggers per hour, and miss rate.

The STA/LTA window lengths and triggering thresholds can be configured in scripts/main.py.

## 5. Results and Visualizations

The processing workflow generates three categories of outputs:

1. STA/LTA Detection Examples
Representative waveform plots illustrating the preprocessing and classic STA/LTA triggering process are available in:
results/figures/

2. Parameter Sensitivity Analysis
Performance heatmaps illustrating the influence of different STA and LTA window combinations on detection performance are available in:
results/heatmaps/

The visualizations include:
o Detection rate
o False alarm ratio
o False triggers per hour
o Miss rate

The experiments vary the STA and LTA window lengths while keeping the trigger ON and OFF thresholds fixed. Therefore, the heatmaps illustrate detection performance under the selected threshold configuration.

3. Experimental Summary
The quantitative results of the parameter sensitivity experiments are provided in CSV format:
results/sensitivity/sta_lta_sensitivity_summary.csv

The summary contains the tested STA and LTA window configurations, fixed trigger thresholds, detection counts, and calculated performance metrics.

## 6. Tools and Libraries

o Python
o ObsPy
o SeisGram2K
o NumPy
o Pandas
o Matplotlib

## 7. Limitations

This project uses waveform recordings from a single seismic station due to data availability constraints. Therefore, the analysis focuses on single-station STA/LTA triggering rather than multi-station earthquake association or earthquake location.

Additionally, the waveform dataset consists of catalog-selected earthquake recordings rather than an independently scanned continuous waveform archive. Consequently, the project focuses on examining triggering behavior and parameter sensitivity within known earthquake waveform windows.

## 8. Reproducibility

The Python scripts and processing parameters are provided in this repository to document the analysis workflow.

Raw MiniSEED waveform files are excluded from the repository. Refer to data/README.md for dataset information and retrieval procedures.

## 9. Author

Independent research project in seismology and computational geophysics, with an interest in numerical modeling, scientific computing, and earthquake-related deformation processes.
