from obspy import read
import matplotlib.pyplot as plt
import os
from processing import preprocess_waveform
from pathlib import Path

input_folder = Path("data/waveforms")
input_files = list(input_folder.glob("*.mseed"))

for file in input_files:
    st = read(file)
    tr = st[0]
    name = os.path.splitext(os.path.basename(file))[0]

    #PART 1
    #plot raw waveform
    print(f"\nProcessing: {file}")
    plt.figure(figsize=(12, 4))
    plt.plot(tr.times(), tr.data, color="black")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(f"{name} - Raw Waveform")
    plt.tight_layout()

    #save raw waveform --> .png
    os.makedirs("figures/raw", exist_ok=True)
    plt.savefig(f"figures/raw/{name}_raw.png", dpi=300)
    plt.close()
    print(f"Raw {name} Plotted!")
    # plt.show()

    #PART 2
    #filter the data
    print(f"\nProcessing Filter: {file}")
    tr2 = preprocess_waveform(file)

    #plot filtered waveform
    plt.figure(figsize=(12, 4))
    plt.plot(tr2.times(), tr2.data, color="black")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(f"{name} - Filtered Waveform")
    plt.tight_layout()

    os.makedirs("figures/filtered", exist_ok=True)
    plt.savefig(f"figures/filtered/{name}_filtered.png", dpi=300)
    plt.close()
    print(f"Filtered {name} Plotted!")
    # plt.show()