# Week 1 Data Handover: Syscall Watcher & Practice Datasets

**Author:** Saharsh (Person A)
**For:** Person B (Detector Modeling), Person C & D (Feature Mapping & Alerts)

This document summarizes the data collection infrastructure and practice datasets prepared during Week 1. The goal was to establish a foundation for host-based (syscall) monitoring without disrupting the existing network-based detection demo.

## 1. Network Features (Frozen)
The legacy network feature list has been kept completely **frozen**. No changes were made to `legacy/autoencoder_def.py` or any existing detection pipelines. The current network demo will not break.

## 2. eBPF Syscall Watcher (`capture/ebpf_syscall_watcher.py`)
To monitor what programs are doing inside the host computer, a new watcher script was created using eBPF and the BPF Compiler Collection (BCC).

* **What it does:** It attaches hooks directly to the Linux kernel to watch 8 crucial actions (system calls) in real-time.
* **Tracked Actions:** 
  1. `open`, `openat` (File opening)
  2. `execve`, `execveat` (Starting programs)
  3. `connect` (Connecting to the internet)
  4. `setuid`, `setgid`, `setresuid` (Changing user privileges)
* **Output Format:** It streams these events to standard output as `SyscallRecord` objects (simple JSON records containing `timestamp`, `pid`, `uid`, `comm`, `syscall`, and parsed `args`).
* **Why build this now?** Setting up eBPF watchers requires a compatible Linux environment and root privileges. Getting this foundational piece built in Week 1 ensures we catch any infrastructure or permission problems early, rather than scrambling in Week 6.

### Action for Team:
* **Linux Requirement:** You must run this script with `sudo python3 capture/ebpf_syscall_watcher.py` on a Linux environment equipped with BCC (`python3-bpfcc`) and kernel headers.

## 3. Practice Datasets (`data/download_practice_datasets.py`)
To avoid being blocked while the live eBPF watcher is being tested and deployed, two standard Host-based Intrusion Detection (HIDS) practice datasets have been set up.

* **What the script does:** It automatically downloads, extracts, and parses the datasets, standardizing them into the same `SyscallRecord` JSONL format that the live watcher produces.
* **Datasets provided:**
  * **ADFA-LD (Quick Test):** Fully downloaded and parsed. Since ADFA-LD only provides raw syscall integer sequences without timestamps or arguments, the script automatically mocks the missing fields so it exactly matches the `SyscallRecord` schema.
  * **LID-DS 2021 (Main):** The repository scaffolding is downloaded. (Note: The actual full LID-DS dataset is massive and must be pulled using their specific dataloader scripts).

### Action for Team:
* **For Person B:** You can run `python data/download_practice_datasets.py` locally. Check the `data/practice/` folder for the `.jsonl` files. You can start using these mock `SyscallRecord` JSONs immediately to begin building the new host-based detector.
* **For Person C & D:** Review the JSON structures generated in `data/practice/`. This gives you the exact key-value layouts and feature names you will need to map program actions (e.g., `ptrace`) into attacker techniques (e.g., `T1055`).
