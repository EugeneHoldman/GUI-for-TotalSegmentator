# GUI for TotalSegmentator

<img width="1264" height="886" alt="Снимок экрана 2026-09-10 094645" src="https://github.com/user-attachments/assets/f2c63615-ca1e-433a-8126-d5b3b14ef84a" />

An unofficial, radiotherapy-oriented desktop interface for [TotalSegmentator](https://github.com/wasserth/TotalSegmentator).

The project is intended to make TotalSegmentator easier to use in routine CT contouring workflows, particularly when command-line interaction is inconvenient or where the person performing segmentation is not expected to work directly with Python or CLI tools. The application provides a graphical way to select segmentation tasks, manage structure templates, process patients in batches, and export the resulting contours as a **DICOM RT Structure Set** for import into a treatment planning system (TPS). TotalSegmentator remains the segmentation engine.

> **Important:** this project is an independent GUI and workflow utility. It is not part of, endorsed by, or affiliated with the TotalSegmentator project.

## Features

### TotalSegmentator features support

- **CT images**
- **CT tasks and anatomical classes provided by the installed TotalSegmentator version**
- **licensed TotalSegmentator tasks**, using a license obtained from the TotalSegmentator authors
- **custom TotalSegmentator weights location**, useful when model files need to be stored outside their default path
- currently does not support TotalSegmentator's statistics and radiomics functionality.

### Additional features

**Custom structure templates**

Reusable structure templates can be created and edited for recurring workflows.

Instead of selecting a complete TotalSegmentator task every time, a template can describe the final set of structures required for a particular use case. Templates can also combine structures originating from different TotalSegmentator tasks.

This makes it possible, for example, to prepare separate presets for different anatomical sites, planning protocols, or departments.

 *How mixed-task templates are processed*
 
The GUI runs every task needed by the template, then removes structures that are not included in it. It therefore processes complete tasks rather than running inference only for the selected structures. A template containing a small number of structures from several tasks may still take substantial time to process.

**Patient selection and batch processing**

Now it is possible: 

- browse patients available for segmentation;
- add cases to a segmentation queue;
- assign a different task or structure template to each patient;
- adjust templates while preparing the queue;
- process multiple cases sequentially.

**RT Structure Set export**

Segmentation results can be converted into a **DICOM RT Structure Set** for use in radiotherapy software.

The export workflow can:

- convert the final selected structures into RTSTRUCT contours;
- apply optional contour postprocessing before conversion;
- remove structures that are not part of the requested template;
- optionally clean the working directory after successful processing so that only the resulting RTSTRUCT remains.

The cleanup option is intended to simplify import into a TPS or other DICOM-based radiotherapy system when intermediate NIfTI masks are not needed.

**Flexible deployment**

The application supports execution using a prepared Conda environment, including portable deployment intended to avoid a conventional installation on the target workstation. This can be useful on third-party workstations, such as TPS workstations.

A prepared environment and compatible system dependencies are still required; portable deployment does not remove TotalSegmentator's underlying runtime requirements.

## Getting started

### Installation and deployment

Choose the installation guide that matches your workstation:

- [Installation guide — Windows 11 workstation with Internet access](docs/installation/INSTALL_WINDOWS_ONLINE.md)
- [Installation guide — Windows workstation without Internet access](docs/installation/INSTALL_WINDOWS_OFFLINE.md)
- [Installation guide — Legacy Windows 10 workstation without Internet access (e.g., Eclipse TPS workstation)](docs/installation/INSTALL_WINDOWS_LEGACY_ECLIPSE.md)

### GUI manual

- [TotalSegmentator UI — User Guide](docs/TotalSegmentator_UI_User_Guide.md)

## Built with

The graphical application and its backend are built using:

- [Qt for Python (PySide6)](https://doc.qt.io/qtforpython-6/)
- [NumPy](https://numpy.org/)
- [SimpleITK](https://simpleitk.org/)
- [pydicom](https://pydicom.github.io/)
- [scikit-image](https://scikit-image.org/)

Medical-image segmentation is performed by:

- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
- [nnU-Net](https://github.com/MIC-DKFZ/nnUNet), on which TotalSegmentator is based

These projects remain separate dependencies with their own licenses, documentation, citation requirements, and terms of use.

## Citation and acknowledgements

If this GUI is used in scientific work, please cite the underlying segmentation methods and any other scientific software relevant to the analysis.

For CT segmentation, the primary TotalSegmentator publication is:

> Wasserthal J, Breit H-C, Meyer MT, et al. **TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images.** *Radiology: Artificial Intelligence*. 2023;5(5):e230024.  
> https://doi.org/10.1148/ryai.230024

TotalSegmentator is heavily based on nnU-Net. The primary nnU-Net publication is:

> Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. **nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation.** *Nature Methods*. 2021;18:203-211.  
> https://doi.org/10.1038/s41592-020-01008-z

Individual TotalSegmentator tasks may have additional licensing or citation requirements. Always consult the current [TotalSegmentator documentation](https://github.com/wasserth/TotalSegmentator) for the tasks and models you use.

Please also follow the citation guidance of the scientific Python libraries used in your work where applicable.

## Development

The **project concept, radiotherapy workflow, functional requirements, and interface/layout design** were created by me.

The codebase was implemented with **OpenAI Codex** used as the coding agent under iterative direction and review.
