# Installation — Windows 11 workstation with Internet access

This is the recommended installation method for a **current Windows 11 workstation with Internet access**.

The installation consists of three main parts:

1. download **GUI for TotalSegmentator**;
2. install Python, PyTorch, and **TotalSegmentator** normally on Windows;
3. start the GUI and verify that it can call TotalSegmentator.

This guide assumes little or no previous experience with Python or command-line tools.

> **Before you start**
>
> - This guide is for **64-bit Windows 11**.
> - An NVIDIA GPU is strongly recommended for routine TotalSegmentator use, although CPU inference is also possible.
> - You need administrator permission only if your local Windows/IT policy requires it for software installation.
> - On hospital or vendor-controlled workstations, follow local IT and change-control requirements.
> - TotalSegmentator model weights are downloaded separately from the Python package and can require several gigabytes of disk space.

Last reviewed against the upstream TotalSegmentator installation information: **September 2026**.

---

## 1. Download GUI for TotalSegmentator

1. Open the project page:

   [GUI for TotalSegmentator on GitHub](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator)

2. Open **Releases**:

   [Project releases](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator/releases)

3. Download the latest Windows distribution supplied with the release.

4. Create a permanent folder for the application, for example:

   ```text
   C:\TotalSegGUI
   ```

5. Extract the downloaded archive into that folder.

   Do **not** run the program directly from inside the downloaded ZIP file.

---

## 2. Install Python if necessary

Download Python from the official Python website:

[Python downloads for Windows](https://www.python.org/downloads/windows/)

For this setup, **Python 3.11, 64-bit** is recommended.

When running the Python installer:

1. enable the option similar to:

   ```text
   Add python.exe to PATH
   ```

2. continue with the normal installation;
3. when installation is complete, close any Command Prompt windows that were already open;
4. open a **new** Command Prompt.

Check the installation:

```bat
python --version
```

Example:

```text
Python 3.11.x
```

Also check `pip`:

```bat
python -m pip --version
```

Upgrade `pip`:

```bat
python -m pip install --upgrade pip
```

> Do not simply install the newest Python major version available without checking compatibility. Scientific Python packages sometimes need time to add support for a newly released Python version.

Current TotalSegmentator requirements can be checked here:

[TotalSegmentator — Installation](https://github.com/wasserth/TotalSegmentator#installation)

---

## 3. Check whether the workstation has an NVIDIA GPU

In **Command Prompt**, run:

```bat
nvidia-smi
```

If a table appears showing an NVIDIA GPU, driver version, GPU memory, and related information, Windows can see the NVIDIA driver.

If Windows reports that `nvidia-smi` is not recognized:

- the workstation may not contain an NVIDIA GPU;
- the NVIDIA driver may not be installed;
- or access to the driver may be restricted.

TotalSegmentator can run on CPU, but processing will generally be much slower.

> On a vendor-controlled radiotherapy workstation, do not update the NVIDIA driver simply to install a particular PyTorch build unless that change is approved by the workstation vendor or your IT department.

---

## 4. Install PyTorch

TotalSegmentator uses [PyTorch](https://pytorch.org/) for neural-network inference.

The correct PyTorch command can change over time and depends on whether you want to use an NVIDIA GPU or CPU. Therefore, use the current official PyTorch installation selector rather than copying an old command from a tutorial.

Open:

[PyTorch — Start Locally](https://pytorch.org/get-started/locally/)

Choose:

- **OS:** Windows
- **Package:** Pip
- **Language:** Python
- **Compute Platform:** the appropriate CUDA option for your NVIDIA setup, or **CPU**

The website will generate a command.

A GPU command may look similar to:

```bat
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

A CPU-only command may look similar to:

```bat
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

These are **examples only**. Use the command shown by the current PyTorch website.

If you specifically need an older PyTorch release, use:

[PyTorch — Previous Versions](https://pytorch.org/get-started/previous-versions/)

After installation, check PyTorch:

```bat
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda); print('GPU available:', torch.cuda.is_available())"
```

For an NVIDIA-GPU installation, the final line should normally be:

```text
GPU available: True
```

If it says `False`, TotalSegmentator may still run, but it will not use the NVIDIA GPU.

---

## 5. Install TotalSegmentator

In the same **Command Prompt**, run:

```bat
python -m pip install TotalSegmentator
```

This follows the standard upstream installation method.

Official project:

[TotalSegmentator](https://github.com/wasserth/TotalSegmentator)

When installation finishes, verify it:

```bat
TotalSegmentator --version
```

Then check that Python does not report broken package requirements:

```bat
python -m pip check
```

If `TotalSegmentator` is reported as an unknown command, close Command Prompt, open a new one, and try again.

You can also check where Windows found the executable:

```bat
where TotalSegmentator
```

---

## 6. Configure a TotalSegmentator license if needed

Some TotalSegmentator tasks require a license obtained from the TotalSegmentator authors.

See the current upstream task and licensing information:

[TotalSegmentator — Tasks and licensing](https://github.com/wasserth/TotalSegmentator#subtasks)

After receiving a license, open **Command Prompt** and run:

```bat
totalseg_set_license -l YOUR_LICENSE_NUMBER
```

Example of the command format:

```bat
totalseg_set_license -l aca_12345678910
```

Replace the example with your real license number.

The GUI does not provide the TotalSegmentator license itself.

---

## 8. TotalSegmentator model weights

Installing the Python package does **not** install every segmentation model immediately.

Normally, TotalSegmentator downloads the required model weights automatically the first time a task is used.

By default, on Windows they are stored under your Windows user profile:

```text
%USERPROFILE%\.totalsegmentator\nnunet\results
```

For example, if the Windows user is `John`:

```text
C:\Users\John\.totalsegmentator\nnunet\results
```

### Download one task manually

If you want to download a task before using it, open **Command Prompt** and run:

```bat
totalseg_download_weights -t TASK_NAME
```

For example:

```bat
totalseg_download_weights -t total
```

### Download all weights known to the installed TotalSegmentator version

Current TotalSegmentator versions also provide:

```bat
totalseg_download_weights -t all
```

This requests **all downloadable model weights known to that installed TotalSegmentator version**.

Be aware that:

- the download can be very large;
- it includes models that this CT-only GUI may never use, including non-CT tasks;
- licensed models require the corresponding TotalSegmentator license to be configured first.

For a normal Internet-connected workstation, downloading everything in advance is usually unnecessary. Allowing TotalSegmentator to download the required task on first use is simpler.

The current implementation of the weight-download command can be viewed here:

[TotalSegmentator — `totalseg_download_weights.py`](https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/bin/totalseg_download_weights.py)

---

## Troubleshooting

### `python` is not recognized

Python is either not installed or was not added to Windows `PATH`.

Re-run the Python installer and make sure **Add python.exe to PATH** is enabled, then open a new Command Prompt.

### Windows opens the Microsoft Store when you type `python`

Windows may be using an App Execution Alias instead of the Python installation you intended to use.

Install Python from [python.org](https://www.python.org/downloads/windows/), enable the PATH option, and reopen Command Prompt.

### `TotalSegmentator` is not recognized

First check:

```bat
python -m pip show TotalSegmentator
```

Then check:

```bat
where python
```

and:

```bat
where TotalSegmentator
```

If the package is installed but the command is not found, the Python `Scripts` directory may not be available in `PATH`.

### `nvidia-smi` is not recognized

The NVIDIA driver may not be installed, the PC may not contain an NVIDIA GPU, or the driver may not be available to your account.

### PyTorch reports `GPU available: False`

Typical causes are:

- a CPU-only PyTorch build was installed;
- the NVIDIA driver is missing;
- the installed PyTorch CUDA build is unsuitable for the available driver.

Return to the official PyTorch installation selector and choose the appropriate build.

### TotalSegmentator starts downloading files

That is normal when a task is used for the first time. The Python package and model weights are separate.

### A licensed task does not work

Confirm that:

1. you obtained the license from the TotalSegmentator authors;
2. the license was entered correctly;
3. the required task weights are available.

---

## Related documentation

- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
- [TotalSegmentator weight downloader source](https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/bin/totalseg_download_weights.py)
- [Python downloads for Windows](https://www.python.org/downloads/windows/)
- [PyTorch — Start Locally](https://pytorch.org/get-started/locally/)
- [PyTorch — Previous Versions](https://pytorch.org/get-started/previous-versions/)
