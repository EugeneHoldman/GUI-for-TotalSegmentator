# GUI for TotalSegmentator

A graphical interface for [TotalSegmentator](https://github.com/wasserth/TotalSegmentator), designed to make CT segmentation easier to use in radiotherapy workflows—particularly for users with limited command-line experience.

The application provides a graphical way to select segmentation tasks, manage structure templates, process patients in batches, and export the resulting contours as a **DICOM RT Structure Set (RTSTRUCT, also referred to as RTSS)** for import into a treatment planning system (TPS). Segmentation is performed by TotalSegmentator; this project provides the interface and additional workflow tools.

## Features

### CT segmentation

- Access TotalSegmentator's CT segmentation tasks and anatomical classes.
- Configure a TotalSegmentator license for tasks that require one.
- Set a custom path for TotalSegmentator model weights.
- Search tasks and structures in the Task and Template managers.

**The GUI currently supports CT images only. TotalSegmentator's radiomics features are not exposed through the interface.** Available tasks and classes depend on the TotalSegmentator version used, and some tasks require a separate license.

### Custom structure templates

Create and edit reusable templates containing the structures needed for a particular workflow. Templates can combine structures from different TotalSegmentator tasks and can be modified while preparing a segmentation run.

**How mixed-task templates work:** the GUI runs every task needed by the template, then removes structures that are not included in it. It therefore processes complete tasks rather than running inference only for the selected structures. A template containing a small number of structures from several tasks may still take substantial time to process.

### Patient selection and batch processing

- Browse a list of patients available for segmentation.
- Build a queue for batch processing.
- Assign an individual structure template to each patient in the queue.

### RT Structure Set export

- Convert the final set of selected structures into a DICOM RT Structure Set.
- Optionally apply additional postprocessing before conversion to smooth the structures for subsequent treatment-planning review.
- Use the cleanup option to retain only the resulting RT Structure Set in the segmentation output, simplifying the TPS import workflow.

### Flexible deployment

The application supports execution using a prepared Conda environment, including portable deployment intended to avoid a conventional installation on the target workstation. This can be useful on third-party workstations, such as TPS workstations.

A prepared environment and compatible system dependencies are still required; portable deployment does not remove TotalSegmentator's underlying runtime requirements.

## Getting started

Application source code, distribution files, and step-by-step setup instructions have not yet been added to this repository. This README describes the application's current functionality; installation and launch instructions will be added alongside the distribution.

For the segmentation engine's installation instructions, requirements, and model information, see the [TotalSegmentator documentation](https://github.com/wasserth/TotalSegmentator#installation). Installing TotalSegmentator alone does not install this GUI.

## Typical workflow

1. **Configure the segmentation environment.** Set up access to TotalSegmentator, choose a custom weights location if needed, and configure a license if your selected tasks require one.
2. **Choose patients.** Select the cases to process from the patient list.
3. **Choose the required structures.** Select a task or create, select, or edit a structure template. Use the search tools to find tasks and structures.
4. **Prepare a batch if needed.** Add patients to the queue and assign the appropriate template to each patient.
5. **Choose export options.** Enable optional postprocessing and output cleanup as required.
6. **Run segmentation.** The GUI invokes the required TotalSegmentator tasks and retains the structures selected for the final output.
7. **Import and review the RT Structure Set.** Import the exported file into your TPS and review the contours against the corresponding CT images.

## Scope and limitations

- **CT only:** MRI segmentation is not currently supported by this GUI.
- **No radiomics interface:** TotalSegmentator's radiomics functionality is not currently available through the GUI.
- **Complete-task processing for templates:** selecting individual structures across tasks does not limit inference to those structures.
- **Upstream dependencies:** segmentation quality, task availability, and model requirements depend on TotalSegmentator and the models used.
- **Postprocessing:** smoothing changes contour geometry and does not establish anatomical accuracy or suitability for a particular planning protocol.

The interface is intended to simplify a radiotherapy-oriented workflow. This does not establish clinical validation. TotalSegmentator's [upstream documentation](https://github.com/wasserth/TotalSegmentator#usage) states that it is not a medical device and is not intended for clinical use.

## Licensing

### This GUI

A license for this GUI has not yet been added to the repository.

### TotalSegmentator and third-party components

TotalSegmentator, its model weights, and the libraries used by this application have their own licensing terms.

Some TotalSegmentator tasks require a license obtained directly from the TotalSegmentator authors. The GUI supports configuring that license, but does not provide one. See the [upstream task and licensing instructions](https://github.com/wasserth/TotalSegmentator#subtasks) for the current requirements and application process.

## Acknowledgements and citations

Medical-image segmentation is performed using [TotalSegmentator](https://github.com/wasserth/TotalSegmentator), which is based on [nnU-Net](https://github.com/MIC-DKFZ/nnUNet).

This application is built with:

- [Qt for Python (PySide6)](https://doc.qt.io/qtforpython-6/)
- [NumPy](https://numpy.org/)
- [SimpleITK](https://simpleitk.org/)
- [pydicom](https://pydicom.github.io/)
- [scikit-image](https://scikit-image.org/)

If you use this software in scientific work, please cite the applicable TotalSegmentator and nnU-Net publications, along with the relevant scientific Python libraries.

For CT segmentation, the primary TotalSegmentator publication is:

> Wasserthal J, et al. **TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images.** Radiology: Artificial Intelligence, 2023. [DOI: 10.1148/ryai.230024](https://doi.org/10.1148/ryai.230024).

See the [TotalSegmentator citation guidance](https://github.com/wasserth/TotalSegmentator#reference) and [nnU-Net repository](https://github.com/MIC-DKFZ/nnUNet) for the applicable references. Individual TotalSegmentator tasks may have additional licensing and citation requirements; consult the upstream documentation for the tasks you use.
