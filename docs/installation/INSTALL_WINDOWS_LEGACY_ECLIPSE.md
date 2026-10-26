# Installation — Legacy Windows 10 workstation without Internet access

## Example: Windows 10 Eclipse treatment-planning workstation

This guide is for a **legacy/offline Windows 10 workstation**, such as a Varian Eclipse workstation, where current Python/PyTorch packages may not work reliably with the existing operating system, GPU driver, or vendor-controlled software environment.

The deployment method is the same basic method used for a modern offline workstation:

1. build the environment on another Windows PC with Internet access;
2. pack it with `conda-pack`;
3. transfer the environment, GUI, TotalSegmentator model weights, and the project's path patch;
4. unpack and repair the environment on the offline workstation.

The important difference is that the Python environment is deliberately constrained to versions tested for this legacy setup.

> **Tested legacy constraints**
>
> - **Windows 10** target
> - **Python 3.10 or 3.11**
> - **NumPy 1.26.4**
> - **PyTorch 2.1.2**
>
> The example setup was tested on a Windows 10 Eclipse workstation. Other older workstations may require different package, CUDA, or driver versions.
>
> Do not update a TPS workstation's GPU driver, Windows components, or vendor software merely to satisfy this guide without approval from the responsible IT/vendor team.

Last checked against upstream documentation: **September 2026**.

---

# Part A — Inspect the legacy target workstation

## 1. Confirm Windows and architecture

1. Press **Windows + I**.
2. Open **System → About**.
3. Confirm that the system is Windows 10 and that **System type** indicates a 64-bit operating system.

This guide assumes:

```text
64-bit operating system, x64-based processor
```

---

## 2. Check the NVIDIA GPU and existing driver

1. Press **Windows + R**.
2. Type:

   ```text
   cmd
   ```

3. Press **Enter**.
4. Run:

   ```bat
   nvidia-smi
   ```

Write down:

- GPU model;
- NVIDIA **Driver Version**;
- CUDA version shown by `nvidia-smi`.

Do **not** assume that an old TPS workstation can use the newest PyTorch CUDA build.

If `nvidia-smi` is not available, a CPU-only PyTorch 2.1.2 environment can be prepared, but TotalSegmentator may be too slow for routine use.

---

# Part B — Prepare the legacy environment on a Windows PC with Internet

## 3. Download the GUI and path patch

Open:

[GUI for TotalSegmentator](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator)

Then:

[Project releases](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator/releases)

Download:

- the Windows GUI distribution;
- the standalone Windows path-repair utility, **[hf_pattern_scan.exe](https://raw.githubusercontent.com/EugeneHoldman/GUI-for-TotalSegmentator/main/tools/hf_pattern_scan.exe)**.

The utility is downloaded separately from the repository, not necessarily from Releases. If needed, open [its GitHub file page](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator/blob/main/tools/hf_pattern_scan.exe) and select **Download raw file**. Keep `hf_pattern_scan.exe` for transfer to the offline workstation.

---

## 4. Install Miniforge on the preparation PC

Download:

[Miniforge](https://github.com/conda-forge/miniforge)

Choose the Windows x86_64 installer.

Use the **Miniforge Prompt** created by the installer. There is normally no need to add Miniforge to the global Windows PATH.

Prefer a simple installation path without spaces or unusual characters, for example:

```text
C:\Miniforge3
```

---

## 5. Open Miniforge Prompt

1. Press the **Windows key**.
2. Type:

   ```text
   Miniforge Prompt
   ```

3. Open it.

---

## 6. Create the legacy environment

This guide uses Python 3.11:

```bat
conda create -n totalseg_legacy python=3.11 pip -y
```

Python 3.10 may also be used for this tested legacy setup:

```bat
conda create -n totalseg_legacy python=3.10 pip -y
```

Use **one** of these commands, not both.

Activate the environment:

```bat
conda activate totalseg_legacy
```

Upgrade `pip`:

```bat
python -m pip install --upgrade pip
```

---

## 7. Install NumPy 1.26.4

Install the tested NumPy version before PyTorch:

```bat
python -m pip install numpy==1.26.4
```

Verify:

```bat
python -c "import numpy; print(numpy.__version__)"
```

Expected output:

```text
1.26.4
```

---

## 8. Install PyTorch 2.1.2

This legacy recipe uses **PyTorch 2.1.2**.

Official commands for old PyTorch releases are available here:

[PyTorch — Previous Versions](https://pytorch.org/get-started/previous-versions/)

For PyTorch 2.1.2 on Windows, the official page provides CUDA 11.8, CUDA 12.1, and CPU variants.

### Recommended starting point for an older NVIDIA workstation: CUDA 11.8 build

If the target driver is compatible with CUDA 11.8, run:

```bat
python -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

### CUDA 12.1 build

Only use this if you have confirmed that the target workstation's NVIDIA driver is suitable:

```bat
python -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
```

### CPU-only build

If GPU acceleration cannot be used:

```bat
python -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
```

Use **one** PyTorch command only.

> If `nvidia-smi` on the target workstation reports an older driver that cannot support either CUDA build above, do not update the TPS workstation driver casually. The safe choices are to involve the workstation/vendor administrator, use a CPU build, or develop a different tested legacy environment.

---

## 9. Verify the legacy numerical stack before installing TotalSegmentator

Run:

```bat
python -c "import numpy, torch; print('NumPy:', numpy.__version__); print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda)"
```

For this legacy recipe, the important versions are:

```text
NumPy: 1.26.4
PyTorch: 2.1.2
```

For a CUDA build, the PyTorch version may be displayed with an additional suffix such as `+cu118`. That is normal.

---

## 10. Install TotalSegmentator

Run:

```bat
python -m pip install TotalSegmentator
```

Current upstream documentation:

[TotalSegmentator](https://github.com/wasserth/TotalSegmentator)

Then verify the versions again:

```bat
python -c "import numpy, torch; print('NumPy:', numpy.__version__); print('PyTorch:', torch.__version__)"
```

They should still correspond to:

```text
NumPy 1.26.4
PyTorch 2.1.2
```

Check dependency consistency:

```bat
python -m pip check
```

### Important future-version warning

This legacy recipe is intentionally version-sensitive.

A future TotalSegmentator or nnU-Net release may require a newer PyTorch version. If a GUI release specifies a particular tested TotalSegmentator version for legacy deployment, install that exact version instead of blindly using the newest package.

The command format is:

```bat
python -m pip install TotalSegmentator==VERSION
```

Example:

```bat
python -m pip install TotalSegmentator==2.18.0
```

The version above is an example of a concrete pinned command. Use the TotalSegmentator version documented as tested with the GUI/legacy environment you are deploying.

Do **not** allow `pip` to silently replace the tested PyTorch 2.1.2 environment with a newer stack and then assume that it is still validated for the Eclipse workstation.

---

## 11. Configure licensed tasks while Internet is available

If you need licensed TotalSegmentator tasks, obtain and validate the license on the Internet-connected preparation PC.

See:

[TotalSegmentator tasks and licensing](https://github.com/wasserth/TotalSegmentator#subtasks)

Then run:

```bat
totalseg_set_license -l YOUR_LICENSE_NUMBER
```

Example format:

```bat
totalseg_set_license -l aca_12345678910
```

Use your actual license.

---

## 12. Download the TotalSegmentator model weights needed on the Eclipse workstation

The Eclipse workstation is offline, so every model that will be used there must be downloaded in advance on the Internet-connected preparation PC.

Make sure the legacy environment is active:

```bat
conda activate totalseg_legacy
```

### Option A — download only the tasks you need

List the tasks known to the installed TotalSegmentator version:

```bat
TotalSegmentator --list-tasks
```

Download a required task with:

```bat
totalseg_download_weights -t TASK_NAME
```

Example:

```bat
totalseg_download_weights -t total
```

Repeat this for every task that will be used by the GUI.

### Option B — download all available weights

Current TotalSegmentator versions also provide:

```bat
totalseg_download_weights -t all
```

This requests all downloadable weights known to that installed TotalSegmentator version.

For a legacy Eclipse deployment, downloading everything may be convenient, but it also:

- requires substantially more disk space;
- includes models that this CT-only GUI may not use;
- can include licensed models.

Configure the TotalSegmentator license first if licensed tasks are required.

### Where are the weights stored?

The fact that the command is entered in **Miniforge Prompt** does not mean that the weights are stored inside the Conda environment.

By default they are stored in:

```text
%USERPROFILE%\.totalsegmentator\nnunet\results
```

For example:

```text
C:\Users\John\.totalsegmentator\nnunet\results
```

The complete TotalSegmentator configuration folder is:

```text
%USERPROFILE%\.totalsegmentator
```

Check the actual profile path:

```bat
echo %USERPROFILE%
```

Check that the downloaded weights are present:

```bat
dir "%USERPROFILE%\.totalsegmentator\nnunet\results"
```

You will transfer the entire:

```text
%USERPROFILE%\.totalsegmentator
```

folder to the Eclipse workstation separately from the packed Conda environment.

This separation is important: **`conda-pack` packs the Python environment, not the default TotalSegmentator model directory.**

Current TotalSegmentator weight-download command:

[TotalSegmentator — `totalseg_download_weights.py`](https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/bin/totalseg_download_weights.py)

### Optional custom weights location

GUI for TotalSegmentator can use a custom weights location. That can be useful on a controlled workstation if you prefer an explicit folder such as:

```text
C:\TotalSeg\weights
```

However, this legacy guide uses the default `.totalsegmentator` location because it follows the standard TotalSegmentator behavior and reduces the number of custom settings.

## 13. Final verification before packing

Run:

```bat
python --version
```

Expected:

```text
Python 3.10.x
```

or:

```text
Python 3.11.x
```

Check NumPy and PyTorch:

```bat
python -c "import numpy, torch; print('NumPy:', numpy.__version__); print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda)"
```

Check TotalSegmentator:

```bat
TotalSegmentator --version
```

Check package dependencies:

```bat
python -m pip check
```

Do not pack the environment until these checks are successful.

---

## 14. Install conda-pack

Deactivate the legacy environment:

```bat
conda deactivate
```

Install conda-pack in the Miniforge base environment:

```bat
conda install -n base -c conda-forge conda-pack -y
```

Documentation:

[conda-pack](https://conda.github.io/conda-pack/)

---

## 15. Pack the legacy environment

Run:

```bat
conda pack -n totalseg_legacy -o "%USERPROFILE%\Downloads\TotalSegmentator_legacy_env.zip" --format zip
```

The resulting file should appear in your Downloads folder:

```text
TotalSegmentator_legacy_env.zip
```

Do not manually copy the original Conda environment folder.

---

## 16. Prepare files for the offline Eclipse workstation

Transfer:

1. GUI for TotalSegmentator Windows distribution;
2. `TotalSegmentator_legacy_env.zip`;
3. the downloaded `hf_pattern_scan.exe` path-repair utility;
4. the entire:

   ```text
   %USERPROFILE%\.totalsegmentator
   ```

   folder;
5. this guide.

### Optional but useful: Microsoft Visual C++ Redistributable

Older Windows workstations are more likely to be missing a runtime required by a Python DLL or the packaged GUI.

Microsoft's official download page:

[Latest supported Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

For the 64-bit workstation described in this guide, download the **x64** installer on the Internet-connected PC if your local deployment procedure allows it.

Do not install it on the Eclipse workstation unless it is needed and permitted by your IT/vendor policy.

---

# Part C — Install on the offline Windows 10 Eclipse workstation

## 17. Use a short permanent path

Create:

```text
C:\TotalSeg
```

and inside it:

```text
C:\TotalSeg\GUI
C:\TotalSeg\env
```

A short path is particularly important on older Windows installations.

If you cannot create these folders because of workstation permissions, use a short permanent path approved by the workstation administrator.

---

## 18. Extract the GUI

Extract the Windows GUI distribution into:

```text
C:\TotalSeg\GUI
```

Do not run it from inside its ZIP file.

---

## 19. Extract the legacy Conda environment

Extract:

```text
TotalSegmentator_legacy_env.zip
```

into:

```text
C:\TotalSeg\env
```

Verify that:

```text
C:\TotalSeg\env\python.exe
```

exists.

Also verify:

```text
C:\TotalSeg\env\Lib
C:\TotalSeg\env\Scripts
```

Do not leave an extra archive folder level between `env` and `python.exe`.

---

## 20. Copy TotalSegmentator weights/configuration

Open File Explorer on the Eclipse workstation.

Click the address bar and enter:

```text
%USERPROFILE%
```

Copy the transferred `.totalsegmentator` folder here.

The final location must be:

```text
%USERPROFILE%\.totalsegmentator
```

---

## 21. Put the Windows path-repair utility into the environment

Copy the downloaded `hf_pattern_scan.exe` into the root of the extracted environment:

```text
C:\TotalSeg\env
```

The complete path should be:

```text
C:\TotalSeg\env\hf_pattern_scan.exe
```

This is a standalone Windows executable, not a Python script.

---

## 22. Run conda-unpack

1. Press **Windows + R**.
2. Type:

   ```text
   cmd
   ```

3. Press **Enter**.

Run:

```bat
cd /d C:\TotalSeg\env
```

Activate the packed environment:

```bat
call Scripts\activate.bat
```

Run the standard Conda relocation repair:

```bat
Scripts\conda-unpack.exe
```

Wait for it to finish.

---

## 23. Run the additional project path patch

With the environment still activated and Command Prompt in `C:\TotalSeg\env`, run:

```bat
hf_pattern_scan.exe
```

Run this executable directly, without `python`.

> **Do not move this environment afterwards.**
>
> Both `conda-unpack` and the custom patch repair paths for the environment's current location. If you later need another installation folder, extract a fresh copy of the archive into the new final path and repeat both repair steps.

---

## 24. Verify the legacy environment on the Eclipse workstation

Run:

```bat
where python
```

The first path should be:

```text
C:\TotalSeg\env\python.exe
```

Check Python:

```bat
python --version
```

Check NumPy and PyTorch:

```bat
python -c "import numpy, torch; print('NumPy:', numpy.__version__); print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda); print('GPU available:', torch.cuda.is_available())"
```

Expected core versions:

```text
NumPy: 1.26.4
PyTorch: 2.1.2
```

For a GPU deployment:

```text
GPU available: True
```

Check TotalSegmentator:

```bat
TotalSegmentator --version
```

Check the Python dependency state:

```bat
python -m pip check
```

---

## 25. If `GPU available` is False

First run:

```bat
nvidia-smi
```

If the NVIDIA GPU and driver are visible but PyTorch still reports `False`, the likely problem is the compatibility between:

- the existing vendor-approved NVIDIA driver;
- the PyTorch 2.1.2 CUDA build that you packed.

Do not replace the Eclipse workstation's driver as an ordinary troubleshooting step.

Instead, rebuild the environment on the Internet-connected PC with the appropriate PyTorch 2.1.2 variant, or use the CPU build if performance is acceptable.

Official PyTorch 2.1.2 commands:

[PyTorch — Previous Versions](https://pytorch.org/get-started/previous-versions/)

---


# Troubleshooting

## The environment worked on the preparation PC but not on the Eclipse PC

Check:

```bat
where python
```

and confirm that the active Python is:

```text
C:\TotalSeg\env\python.exe
```

Then confirm that both relocation steps were run:

```bat
Scripts\conda-unpack.exe
```

and:

```bat
hf_pattern_scan.exe
```

---

## NumPy is no longer 1.26.4 or PyTorch is no longer 2.1.2

Do not use that environment as the tested legacy environment.

Rebuild it on the Internet-connected PC with:

```bat
python -m pip install numpy==1.26.4
```

followed by the appropriate PyTorch 2.1.2 command from the official previous-versions page.

Then install a TotalSegmentator version compatible with that stack.

---

## Missing DLL / `DLL load failed`

The machine may be missing a Microsoft Visual C++ runtime needed by a package.

Use the official Microsoft package only:

[Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

For the 64-bit setup in this guide, the relevant package is normally the x64 redistributable.

On a TPS workstation, install it only with appropriate local approval.

---

## TotalSegmentator tries to access the Internet

A required model is probably missing.

On the preparation PC:

```bat
conda activate totalseg_legacy
```

then:

```bat
totalseg_download_weights -t TASK_NAME
```

Copy the updated `.totalsegmentator` folder back to the Eclipse workstation.

---

## A licensed task fails

Make sure that the license was configured and the licensed model was downloaded on the Internet-connected preparation PC before the `.totalsegmentator` folder was copied.

---

# Related documentation

- [GUI for TotalSegmentator](https://github.com/EugeneHoldman/GUI-for-TotalSegmentator)
- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
- [PyTorch — Previous Versions](https://pytorch.org/get-started/previous-versions/)
- [Miniforge](https://github.com/conda-forge/miniforge)
- [conda-pack](https://conda.github.io/conda-pack/)
- [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
