"""Pipeline orchestration.

Heavy libraries must be imported inside functions when used.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import traceback
from time import perf_counter
from typing import Callable, Dict, Iterable, List, Tuple

from app import mask_filter, ts_commands

DICOM_EXTENSIONS = {".dcm", ".dicom", ".ima"}


class PipelineCancelled(Exception):
    """Raised when a user requests pipeline cancellation."""


def _windows_hidden_subprocess_kwargs() -> Dict[str, object]:
    """Return Windows-specific subprocess kwargs that suppress console windows."""
    if os.name != "nt":
        return {}
    kwargs: Dict[str, object] = {}
    create_no_window = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window
    startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_cls is not None:
        startupinfo = startupinfo_cls()
        startf_use_showwindow = int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0))
        if startf_use_showwindow:
            startupinfo.dwFlags |= startf_use_showwindow
        startupinfo.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _last_nonempty_line(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _last_text_block(text: str, limit: int = 12) -> str | None:
    """Return the trailing non-empty stderr/traceback block."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return None
    return "\n".join(lines[-limit:])


def _format_mm_ss(elapsed_seconds: float) -> str:
    """Format seconds as mm:ss with zero padding."""
    total = int(elapsed_seconds + 0.5)
    minutes, seconds = divmod(total, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _run_command(
    command: List[str],
    cwd: Path,
    env: Dict[str, str] | None = None,
) -> Tuple[bool, str | None]:
    """Run a subprocess, returning (success, trailing_stderr_or_traceback)."""
    return _run_command_with_stop(command, cwd, should_stop=None, env=env)


def _is_stop_requested(should_stop: Callable[[], bool] | None) -> bool:
    return bool(should_stop and should_stop())


def _raise_if_stopped(should_stop: Callable[[], bool] | None) -> None:
    if _is_stop_requested(should_stop):
        raise PipelineCancelled("Stopped by user.")


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Terminate a process and its children, with Windows-first behavior."""
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
                **_windows_hidden_subprocess_kwargs(),
            )
            return
        except Exception:
            # Fall back to direct termination if taskkill fails.
            pass
    try:
        process.terminate()
    except Exception:
        pass
    try:
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _run_command_with_stop(
    command: List[str],
    cwd: Path,
    should_stop: Callable[[], bool] | None,
    env: Dict[str, str] | None = None,
) -> Tuple[bool, str | None]:
    """Run a subprocess and terminate it if stop is requested."""
    _raise_if_stopped(should_stop)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            **_windows_hidden_subprocess_kwargs(),
        )
    except FileNotFoundError:
        return False, f"{command[0]} (not found)"
    except Exception:  # noqa: BLE001 - propagate traceback detail
        return False, _last_text_block(traceback.format_exc())

    stdout_text = ""
    stderr_text = ""
    while True:
        try:
            stdout_text, stderr_text = process.communicate(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            if not _is_stop_requested(should_stop):
                continue
            _terminate_process_tree(process)
            try:
                stdout_text, stderr_text = process.communicate(timeout=2)
            except Exception:
                stdout_text = ""
                stderr_text = ""
            raise PipelineCancelled("Stopped by user.")

    completed_return_code = process.returncode
    if completed_return_code is None:
        return False, "Process ended unexpectedly."

    if completed_return_code != 0:
        detail = (
            _last_text_block(stderr_text)
            or _last_text_block(stdout_text)
            or f"Exit code {completed_return_code}"
        )
        return False, detail
    return True, None


def _normalize_overlay_tasks(tasks: Dict[str, object]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {}
    for task_name, structures in tasks.items():
        if not isinstance(task_name, str) or not isinstance(structures, list):
            continue
        cleaned = ts_commands.normalize_structure_list(structures)
        if cleaned:
            normalized[task_name] = cleaned
    return normalized


def _resolve_row_path(value: object, patients_root: Path) -> Path | None:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        candidate = Path(text)
    else:
        return None
    if not candidate.is_absolute():
        candidate = patients_root / candidate
    return candidate


def _queue_ref_from_row(row: Dict[str, object] | object, patients_root: Path, patient_id: str) -> str:
    if isinstance(row, dict):
        candidate = _resolve_row_path(row.get("scan_dir"), patients_root)
        if candidate is None:
            candidate = _resolve_row_path(row.get("patient_dir"), patients_root)
        if candidate is not None:
            return str(candidate)
    return str(patients_root / str(patient_id))


def _delete_segmentations_dir(patient_dir: Path) -> Tuple[bool, str | None]:
    segmentations_dir = patient_dir / "segmentations"
    if not segmentations_dir.exists() or not segmentations_dir.is_dir():
        return False, None
    if segmentations_dir.parent != patient_dir:
        return False, "Unexpected path for segmentations directory."
    try:
        shutil.rmtree(segmentations_dir)
    except OSError as exc:
        return False, str(exc)
    return True, None


def _delete_ct_files(patient_dir: Path, rtss_path: Path | None) -> Tuple[int, str | None]:
    try:
        import pydicom
    except Exception as exc:  # noqa: BLE001
        return 0, f"pydicom import failed: {exc}"

    def _read_modality(dcm_path: Path) -> str | None:
        try:
            dataset = pydicom.dcmread(str(dcm_path), stop_before_pixels=True, force=True)
        except Exception:
            return None
        return getattr(dataset, "Modality", None)

    deleted = 0
    rtss_resolved = None
    if rtss_path is not None:
        try:
            rtss_resolved = rtss_path.resolve()
        except OSError:
            rtss_resolved = None
    try:
        for path in patient_dir.iterdir():
            if not path.is_file():
                continue
            if rtss_resolved is not None:
                try:
                    if path.resolve() == rtss_resolved:
                        continue
                except OSError:
                    continue
            suffix = path.suffix.lower()
            if suffix not in DICOM_EXTENSIONS and suffix != "":
                continue
            modality = _read_modality(path)
            if modality != "CT":
                continue
            try:
                path.unlink()
                deleted += 1
            except OSError:
                continue
    except OSError as exc:
        return deleted, str(exc)
    return deleted, None


def _is_nifti_file(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".nii") or name.endswith(".nii.gz")


def _has_nifti_outputs(segmentations_dir: Path) -> bool:
    if not segmentations_dir.exists() or not segmentations_dir.is_dir():
        return False
    try:
        for entry in segmentations_dir.iterdir():
            if entry.is_file() and _is_nifti_file(entry):
                return True
    except OSError:
        return False
    return False


def _has_patient_outputs(segmentations_dir: Path, rtss_path: Path | None) -> bool:
    has_rtss = False
    if rtss_path is not None:
        try:
            has_rtss = rtss_path.exists() and rtss_path.is_file()
        except OSError:
            has_rtss = False
    return has_rtss or _has_nifti_outputs(segmentations_dir)


def _remove_mask_files(segmentations_dir: Path, mask_names: Iterable[str]) -> None:
    """Best-effort cleanup of intermediate NIfTI masks by base name."""
    for name in mask_names:
        base = str(name).strip()
        if not base:
            continue
        for suffix in (".nii.gz", ".nii"):
            candidate = segmentations_dir / f"{base}{suffix}"
            try:
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()
            except OSError:
                continue


def _classify_patient_status(
    *,
    task_success_count: int,
    task_failure_count: int,
    segmentations_dir: Path,
    rtss_path: Path | None,
    hard_failure: bool,
) -> str:
    has_outputs = _has_patient_outputs(segmentations_dir, rtss_path)
    if hard_failure:
        if has_outputs or task_success_count > 0:
            return "partial"
        return "failed"
    if task_failure_count > 0:
        if has_outputs or task_success_count > 0:
            return "partial"
        return "failed"
    if task_success_count > 0 or has_outputs:
        return "ok"
    return "failed"


def _run_postprocess_hook(output_rtss_path: Path) -> Tuple[bool, str | None]:
    try:
        from app import rtss_convert
    except Exception:  # noqa: BLE001
        return True, None
    hook = getattr(rtss_convert, "run_postprocess_hook", None)
    if not callable(hook):
        return True, None
    try:
        hook(output_rtss_path, None)
    except Exception:  # noqa: BLE001 - capture traceback
        detail = _last_text_block(traceback.format_exc()) or "Unknown error"
        return False, detail
    return True, None


def _run_tasks_for_patient(
    patient_id: str,
    patient_dir: Path,
    overlay_tasks: Dict[str, List[str]],
    task_definitions: Dict[str, List[str]],
    total_structures: List[str],
    ts_executable: str,
    combine_masks_executable: str,
    command_env: Dict[str, str] | None,
    logger,
    should_stop: Callable[[], bool] | None = None,
) -> Tuple[int, int, List[Tuple[str, str | None]]]:
    """Run TS tasks for one patient and continue across task-level failures."""
    segmentations_dir = patient_dir / "segmentations"
    attempted_count = 0
    success_count = 0
    failures: List[Tuple[str, str | None]] = []
    for task_name in sorted(overlay_tasks.keys(), key=str.lower):
        _raise_if_stopped(should_stop)
        structures = overlay_tasks.get(task_name, [])
        if not structures:
            continue
        attempted_count += 1

        task_label = task_name
        task_start = perf_counter()
        logger.info(f"Patient {patient_id}: TS run \u2192 {task_label} \u2026")
        stage_label = f"TS {task_label}"
        try:
            if ts_commands.is_total_task(task_name):
                is_total_all = bool(total_structures) and ts_commands.is_total_all(
                    structures, total_structures
                )
                command = (
                    ts_commands.build_total_command(patient_dir, executable=ts_executable)
                    if is_total_all
                    else ts_commands.build_total_command(
                        patient_dir,
                        roi_subset=structures,
                        executable=ts_executable,
                    )
                )
                ok, detail = _run_command_with_stop(
                    command,
                    patient_dir,
                    should_stop,
                    command_env,
                )
                if not ok:
                    failures.append((stage_label, detail))
                    logger.error(f"Patient {patient_id}: FAILED at {stage_label}.", detail=detail)
                    continue
                duration = _format_mm_ss(perf_counter() - task_start)
                logger.info(f"Patient {patient_id}: TS done \u2192 {task_label}. Time {duration}.")
                success_count += 1
                continue

            if ts_commands.is_combined_organs_task(task_name):
                combined_failed = False
                combined_detail: str | None = None
                for requested_structure in structures:
                    resolved = ts_commands.resolve_combined_organs_sources(requested_structure)
                    if not resolved:
                        combined_failed = True
                        combined_detail = (
                            f'Unsupported Combined_organs class "{requested_structure}".'
                        )
                        break
                    mask_name, roi_subset = resolved

                    command = ts_commands.build_total_command(
                        patient_dir,
                        roi_subset=roi_subset,
                        executable=ts_executable,
                    )
                    ok, detail = _run_command_with_stop(
                        command,
                        patient_dir,
                        should_stop,
                        command_env,
                    )
                    if not ok:
                        combined_failed = True
                        combined_detail = detail
                        break

                    combine_cmd = ts_commands.build_combine_masks_command(
                        segmentations_dir=segmentations_dir,
                        output_filename=f"{mask_name}.nii.gz",
                        mask_name=mask_name,
                        executable=combine_masks_executable,
                    )
                    ok, detail = _run_command_with_stop(
                        combine_cmd,
                        patient_dir,
                        should_stop,
                        command_env,
                    )
                    if not ok:
                        combined_failed = True
                        combined_detail = detail
                        break
                    _remove_mask_files(segmentations_dir, roi_subset)

                if combined_failed:
                    failures.append((stage_label, combined_detail))
                    logger.error(
                        f"Patient {patient_id}: FAILED at {stage_label}.",
                        detail=combined_detail,
                    )
                    continue
                duration = _format_mm_ss(perf_counter() - task_start)
                logger.info(f"Patient {patient_id}: TS done \u2192 {task_label}. Time {duration}.")
                success_count += 1
                continue

            command = ts_commands.build_task_command(
                patient_dir,
                task_name,
                executable=ts_executable,
            )
            ok, detail = _run_command_with_stop(
                command,
                patient_dir,
                should_stop,
                command_env,
            )
            if not ok:
                failures.append((stage_label, detail))
                logger.error(f"Patient {patient_id}: FAILED at {stage_label}.", detail=detail)
                continue
            duration = _format_mm_ss(perf_counter() - task_start)
            logger.info(f"Patient {patient_id}: TS done \u2192 {task_label}. Time {duration}.")

            _raise_if_stopped(should_stop)
            logger.info(f"Patient {patient_id}: filtering masks to match template \u2026")
            task_structures = ts_commands.resolve_task_structures(task_definitions, task_name)
            removed, kept = mask_filter.remove_unwanted_masks(
                segmentations_dir,
                keep_names=structures,
                only_names=task_structures,
            )
            logger.info(
                f"Patient {patient_id}: mask filtering done. Kept {kept}, removed {removed}."
            )
            success_count += 1
        except PipelineCancelled:
            raise
        except Exception:  # noqa: BLE001
            detail = _last_text_block(traceback.format_exc()) or "Unknown error"
            failures.append((stage_label, detail))
            logger.error(f"Patient {patient_id}: FAILED at {stage_label}.", detail=detail)
            continue

    return attempted_count, success_count, failures


def run_pipeline(
    patients_root: Path,
    queue_rows: List[Dict[str, object]],
    totalseg_config_path: Path,
    options: Dict[str, object],
    logger,
    should_stop: Callable[[], bool] | None = None,
) -> List[Dict[str, object]]:
    """Run the TotalSegmentator pipeline for queued patients."""
    patients_root = Path(patients_root)
    results: List[Dict[str, object]] = []

    total_count = len(queue_rows)
    if total_count == 0 or not patients_root.exists():
        return results

    task_definitions = ts_commands.load_task_definitions(totalseg_config_path)
    total_structures = ts_commands.resolve_task_structures(task_definitions, "Total") or []

    to_rtss_postproc = bool(options.get("to_rtss_postproc"))
    to_rtss = bool(options.get("to_rtss")) or to_rtss_postproc
    delete_ct = bool(options.get("delete_ct"))
    delete_segmentations = bool(options.get("delete_segmentations"))
    auto_open = bool(options.get("auto_open"))
    ts_executable, combine_masks_executable = ts_commands.resolve_command_binaries(options)
    ts_home_dir = ""
    if not bool(options.get("ts_weights_default", True)):
        raw_home = options.get("ts_weights_path")
        if isinstance(raw_home, str):
            ts_home_dir = raw_home.strip()
    command_env: Dict[str, str] | None = None
    if ts_home_dir:
        command_env = dict(os.environ)
        command_env["TOTALSEG_HOME_DIR"] = ts_home_dir

    # Destructive cleanup is only valid for RTSS workflows.
    # In NIfTI-only mode we keep CT + segmentations so outputs remain available.
    cleanup_deletes_enabled = to_rtss
    effective_delete_ct = delete_ct and cleanup_deletes_enabled
    effective_delete_segmentations = delete_segmentations and cleanup_deletes_enabled

    mode_label = "NIfTI-only"
    if to_rtss_postproc:
        mode_label = "NIfTI + RTSS (postproc)"
    elif to_rtss:
        mode_label = "NIfTI + RTSS"

    logger.info(f"Run started. Patients in queue: {total_count}.")
    logger.info(f"Patients folder: {patients_root}.")
    logger.info(
        "Mode: {mode}.".format(
            mode=mode_label,
        )
    )
    logger.info(
        "Cleanup: DelSegm={seg}, DelCT={ct}, AutoOpen={auto}.".format(
            seg=str(effective_delete_segmentations).lower(),
            ct=str(effective_delete_ct).lower(),
            auto=str(auto_open).lower(),
        )
    )

    success_count = 0
    partial_count = 0
    fail_count = 0
    skip_count = 0

    for index, row in enumerate(queue_rows, start=1):
        if _is_stop_requested(should_stop):
            logger.warn("Run stopped by user.")
            break
        patient_id = str(row.get("patient_id") or "").strip() if isinstance(row, dict) else ""
        if not patient_id:
            continue
        queue_ref = _queue_ref_from_row(row, patients_root, patient_id)

        logger.info(f"[{index}/{total_count}] Patient {patient_id}: start.")

        template_name = row.get("template") if isinstance(row, dict) else None
        overlay_tasks = _normalize_overlay_tasks(row.get("overlay_tasks") or {}) if isinstance(row, dict) else {}
        if not template_name:
            skip_count += 1
            results.append(
                {
                    "patient_id": patient_id,
                    "queue_ref": queue_ref,
                    "status": "skipped",
                    "reason": "no_template",
                }
            )
            logger.info(f"Patient {patient_id}: skipped (no template).")
            continue

        patient_dir = None
        if isinstance(row, dict):
            patient_dir = _resolve_row_path(row.get("scan_dir"), patients_root)
            if patient_dir is None:
                patient_dir = _resolve_row_path(row.get("patient_dir"), patients_root)
        if patient_dir is None:
            patient_dir = patients_root / str(patient_id)
        if not patient_dir.exists() or not patient_dir.is_dir():
            skip_count += 1
            results.append(
                {
                    "patient_id": patient_id,
                    "queue_ref": queue_ref,
                    "status": "skipped",
                    "reason": "missing_folder",
                }
            )
            logger.info(f"Patient {patient_id}: skipped (folder missing).")
            continue

        if not overlay_tasks:
            skip_count += 1
            results.append(
                {
                    "patient_id": patient_id,
                    "queue_ref": queue_ref,
                    "status": "skipped",
                    "reason": "no_tasks",
                }
            )
            logger.info(f"Patient {patient_id}: skipped (no tasks in template).")
            continue

        task_count = len(overlay_tasks)
        struct_count = sum(len(structures) for structures in overlay_tasks.values())
        logger.info(
            f'Patient {patient_id}: template "{template_name}", tasks {task_count}, structures requested {struct_count}.'
        )

        patient_timer = perf_counter()
        segmentations_dir = patient_dir / "segmentations"
        rtss_path: Path | None = patient_dir / "rtss.dcm" if to_rtss else None

        def _finalize_patient(status: str) -> None:
            nonlocal success_count, partial_count, fail_count
            elapsed = _format_mm_ss(perf_counter() - patient_timer)
            if status == "ok":
                success_count += 1
                logger.info(f"Patient {patient_id}: SUCCESS. Total time {elapsed}.")
            elif status == "partial":
                partial_count += 1
                logger.warn(f"Patient {patient_id}: PARTIALLY SUCCESSFUL. Total time {elapsed}.")
            else:
                fail_count += 1
                logger.warn(f"Patient {patient_id}: FAILED. Total time {elapsed}.")
            results.append({"patient_id": patient_id, "queue_ref": queue_ref, "status": status})

        try:
            attempted_tasks, succeeded_tasks, task_failures = _run_tasks_for_patient(
                patient_id=patient_id,
                patient_dir=patient_dir,
                overlay_tasks=overlay_tasks,
                task_definitions=task_definitions,
                total_structures=total_structures,
                ts_executable=ts_executable,
                combine_masks_executable=combine_masks_executable,
                command_env=command_env,
                logger=logger,
                should_stop=should_stop,
            )
        except PipelineCancelled:
            results.append({"patient_id": patient_id, "queue_ref": queue_ref, "status": "stopped"})
            logger.warn(f"Patient {patient_id}: stopped by user.")
            break
        except Exception:  # noqa: BLE001
            stage_detail = _last_text_block(traceback.format_exc()) or "Unknown error"
            logger.error(f"Patient {patient_id}: FAILED at TS tasks.", detail=stage_detail)
            _finalize_patient("failed")
            continue

        if task_failures:
            logger.warn(
                f"Patient {patient_id}: task failures {len(task_failures)}/{attempted_tasks}; continuing with available outputs."
            )

        hard_failure = False
        if to_rtss and rtss_path is not None:
            if _is_stop_requested(should_stop):
                results.append({"patient_id": patient_id, "queue_ref": queue_ref, "status": "stopped"})
                logger.warn(f"Patient {patient_id}: stopped by user.")
                break
            if not _has_nifti_outputs(segmentations_dir):
                hard_failure = True
                logger.error(
                    f"Patient {patient_id}: FAILED at RTSS conversion.",
                    detail=f"No NIfTI masks found in {segmentations_dir}.",
                )
            else:
                logger.info(f"Patient {patient_id}: RTSS conversion started \u2026")
                try:
                    from app.rtss_convert import convert_nifti_dir_to_rtss

                    written, skipped_empty, missing = convert_nifti_dir_to_rtss(
                        patient_dir=patient_dir,
                        segmentations_dir=segmentations_dir,
                        output_rtss_path=rtss_path,
                        logger=logger,
                        apply_postprocess=to_rtss_postproc,
                    )
                except Exception:  # noqa: BLE001 - log traceback detail
                    hard_failure = True
                    stage_detail = _last_text_block(traceback.format_exc()) or "Unknown error"
                    logger.error(
                        f"Patient {patient_id}: FAILED at RTSS conversion.", detail=stage_detail
                    )
                else:
                    logger.info(f"Patient {patient_id}: RTSS created: {rtss_path}.")
                    logger.info(
                        f"Patient {patient_id}: RTSS summary: written {written}, skipped empty {skipped_empty}, missing {missing}."
                    )

                    if to_rtss_postproc:
                        post_start = perf_counter()
                        logger.info(f"Patient {patient_id}: postprocessing started \u2026")
                        ok_post, detail_post = _run_postprocess_hook(rtss_path)
                        if not ok_post:
                            hard_failure = True
                            logger.error(
                                f"Patient {patient_id}: FAILED at postprocessing.", detail=detail_post
                            )
                        else:
                            logger.info(
                                f"Patient {patient_id}: postprocessing done. Time {_format_mm_ss(perf_counter() - post_start)}."
                            )

        if hard_failure:
            _finalize_patient(
                _classify_patient_status(
                    task_success_count=succeeded_tasks,
                    task_failure_count=len(task_failures),
                    segmentations_dir=segmentations_dir,
                    rtss_path=rtss_path,
                    hard_failure=True,
                )
            )
            continue

        logger.info(f"Patient {patient_id}: cleanup started \u2026")
        if _is_stop_requested(should_stop):
            results.append({"patient_id": patient_id, "queue_ref": queue_ref, "status": "stopped"})
            logger.warn(f"Patient {patient_id}: stopped by user.")
            break
        allow_destructive_cleanup = len(task_failures) == 0
        if not allow_destructive_cleanup and (
            effective_delete_segmentations or effective_delete_ct
        ):
            logger.warn(f"Patient {patient_id}: cleanup deletes skipped due task failures.")
        if effective_delete_segmentations and allow_destructive_cleanup:
            deleted_seg, detail = _delete_segmentations_dir(patient_dir)
            if detail:
                logger.error(f"Patient {patient_id}: FAILED at cleanup.", detail=detail)
                _finalize_patient(
                    _classify_patient_status(
                        task_success_count=succeeded_tasks,
                        task_failure_count=len(task_failures),
                        segmentations_dir=segmentations_dir,
                        rtss_path=rtss_path,
                        hard_failure=True,
                    )
                )
                continue
            if deleted_seg:
                logger.info(f"Patient {patient_id}: deleted segmentations folder.")

        if effective_delete_ct and allow_destructive_cleanup:
            deleted_ct, detail = _delete_ct_files(patient_dir, rtss_path if to_rtss else None)
            if detail:
                logger.error(f"Patient {patient_id}: FAILED at cleanup.", detail=detail)
                _finalize_patient(
                    _classify_patient_status(
                        task_success_count=succeeded_tasks,
                        task_failure_count=len(task_failures),
                        segmentations_dir=segmentations_dir,
                        rtss_path=rtss_path,
                        hard_failure=True,
                    )
                )
                continue
            logger.info(f"Patient {patient_id}: deleted CT DICOM files: {deleted_ct}.")

        if auto_open:
            try:
                subprocess.Popen(["explorer", str(patient_dir.resolve())])
                logger.info(f"Patient {patient_id}: opened output folder in Explorer.")
            except Exception:  # noqa: BLE001
                detail = _last_text_block(traceback.format_exc()) or "Failed to open Explorer."
                logger.error(f"Patient {patient_id}: FAILED at cleanup.", detail=detail)
                _finalize_patient(
                    _classify_patient_status(
                        task_success_count=succeeded_tasks,
                        task_failure_count=len(task_failures),
                        segmentations_dir=segmentations_dir,
                        rtss_path=rtss_path,
                        hard_failure=True,
                    )
                )
                continue

        _finalize_patient(
            _classify_patient_status(
                task_success_count=succeeded_tasks,
                task_failure_count=len(task_failures),
                segmentations_dir=segmentations_dir,
                rtss_path=rtss_path,
                hard_failure=False,
            )
        )

    logger.info(
        f"Run finished. Success {success_count}, Partial {partial_count}, Failed {fail_count}, Skipped {skip_count}."
    )
    return results
