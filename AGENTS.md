# NetPulse Agent Instructions

## Project Shape

- This is a small, non-package Python utility with separate Windows and macOS implementations; there is no test suite, CI workflow, or package manifest.
- Windows entrypoints are `windows/run_main_hybrid.py` (CLI) and `windows/netpulse_gui.py` (CustomTkinter GUI). macOS entrypoint is `macos/run_main_hybrid_Mac.py`; `macos/run_main_hybrid_Mac_python2.py` is a legacy Python 2-compatible variant.
- Keep platform-specific behavior in the corresponding directory. The bundled `windows/tcping.exe` and `macos/tcping` are runtime dependencies, not generated build artifacts.

## Running

- Windows CLI: from `windows/`, run `python run_main_hybrid.py`; it reads `config.ini` and `iplist.txt` relative to its script or frozen executable directory.
- Windows GUI: from `windows/`, install `customtkinter` and `croniter`, then run `pythonw netpulse_gui.py` (use `python netpulse_gui.py` when debugging).
- macOS: install `croniter`, run `chmod +x macos/tcping` once, then from `macos/` run `python3 run_main_hybrid_Mac.py`. The script prompts for the target filename and test mode.
- These programs perform real network probes and need the system `ping`, `curl`, and the bundled `tcping` executable available. Avoid treating a live network run as a deterministic test.

## Configuration And Data

- Windows settings live in `windows/config.ini`: `[GENERAL]` controls ping counts, default TCP port, worker count, and `InputFile`; `[CRON] Timing` is a five-field Cron expression. An empty `Timing` runs once. The checked-in config currently schedules every minute, so inspect or clear it before manual runs.
- macOS settings are constants near the top of `macos/run_main_hybrid_Mac.py`, including `CronExpr`; an empty expression runs once. The legacy Python 2 script has its own constants and does not share Windows config.
- Target files accept one host per line, optional numeric port as whitespace-separated `host port`, or `host:port`; blank lines and lines beginning with `#` are ignored. IPv6 targets must use `[IPv6]` or `[IPv6]:port`.
- Results are timestamped `result_YYYYMMDD_HHMMSS.txt` beside the running script/executable. The Windows CLI also writes a timestamped `NetPulse_log_*.log`; the GUI can save edited config, target lists, and exported results.

## Build And Verification

- Rebuild the Windows GUI executable from `windows/` with `python -m PyInstaller --onefile --noconsole --windowed --name NetPulseGUI netpulse_gui.py` after installing `pyinstaller`.
- There are no project-defined lint, typecheck, or test commands. For source-only changes, at minimum run `python -m py_compile` on the edited Python file(s); validate behavior with a controlled target list and a cleared Cron setting when needed.
