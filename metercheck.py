#!/usr/bin/env python3
"""
ChromIQ-MeterCheck
==================
A friendly diagnostics collector for the i1Pro3 + ArgyllCMS.

Purpose
-------
Some people get bad printer profiles (double-digit Delta-E) when they read
charts with an *i1Pro3* (the regular one, not the "Plus") using ArgyllCMS.
The i1Pro3 has no measuring lamp -- it uses UV-multiplexed LEDs and stores its
per-unit factory calibration on the device itself. ArgyllCMS reverse-engineers
that processing, so the suspicion is that Argyll's reconstruction and/or its
reading of the on-device calibration diverges from X-Rite's own i1Profiler.

This script collects everything needed to investigate that, in one shareable
bundle, WITHOUT needing any programming knowledge. It only uses ArgyllCMS's
own `spotread` tool plus the Python standard library, so you can hand it to
another i1Pro3 owner and they can run it too.

THE HEADLINE: the spectral comparison
-------------------------------------
The single most useful thing this collects is a measurement of one known
reference surface in M0, M1 and M2, saved as spectra -- so it can be compared
directly against the SAME surface measured in i1Profiler. That comparison is
what actually answers the question, because the suspect stage is the i1Pro3's
lamp-less reconstruction of the reflectance, NOT whether Argyll can read the
device's calibration. If Argyll's M0/M1/M2 spectra of a surface diverge from
i1Profiler's, the fault is in the reconstruction/processing; if they match,
the colour engine is fine and the problem is elsewhere (e.g. scan registration).

It captures:
  1. [HEADLINE] One reflective measurement of a reference surface in M0, M1
     and M2, saved as spectra -- to compare against i1Profiler's reading of
     the same surface.
  2. Your OS / CPU (Intel vs Apple-Silicon-under-Rosetta matters here).
  3. Your exact ArgyllCMS version.
  4. The instrument's identity + firmware + EEPROM/init log (debug capture).
  5. [SUPPORTING] The device's OWN white-tile reference spectrum (spotread
     -Y W:) and raw & XYZ spectral sensitivities (spotread -Y S:).

Item 5 is SUPPORTING evidence only. Being able to dump those values just shows
Argyll can read two EEPROM fields -- it does not prove the reflective
reconstruction that consumes them matches X-Rite. We collect them to rule the
basic calibration read in or out, not as the main signal. The main signal is
item 1: the i1Profiler-vs-Argyll spectral comparison.

What you need
-------------
  * macOS, Linux or Windows
  * ArgyllCMS installed (https://www.argyllcms.com/) -- v3.5.0 recommended
  * An i1Pro3 plugged in, with its calibration tile/dock handy
  * A reference surface to measure (the headline step). Best options, in order:
      - a known calibrated tile, OR
      - a single mid-grey patch you ALSO measure in i1Profiler, OR
      - just a sheet of the paper you actually profile on.
    Whatever you pick, measure the SAME physical spot in i1Profiler too and
    export it, so the two can be compared.

How to run
----------
    python3 metercheck.py

Then just follow spotread's on-screen prompts (place on the white tile and
press a key to calibrate; place on the surface and press a key to measure).
At the end you get a folder and a .zip you can attach to the forum thread.

If `spotread` isn't found automatically, pass its folder:
    python3 metercheck.py --argyll "/Applications/Argyll/bin"
"""

from __future__ import annotations  # so 'str | None' hints work on Python 3.7-3.9

import argparse
import datetime
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Common places ArgyllCMS gets installed, per OS.
_CANDIDATE_DIRS = [
    "/Applications/Argyll/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    str(Path.home() / "Argyll" / "bin"),
    r"C:\Argyll\bin",
    r"C:\Program Files\Argyll\bin",
]


def find_spotread(explicit_dir: str | None) -> str:
    """Return a usable path to the spotread executable, or exit with help."""
    exe = "spotread.exe" if os.name == "nt" else "spotread"

    search = []
    if explicit_dir:
        search.append(Path(explicit_dir) / exe)
    # PATH first, then the well-known locations.
    on_path = shutil.which(exe)
    if on_path:
        search.append(Path(on_path))
    search += [Path(d) / exe for d in _CANDIDATE_DIRS]

    for cand in search:
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    sys.exit(
        "ERROR: could not find ArgyllCMS 'spotread'.\n"
        "Install ArgyllCMS (https://www.argyllcms.com/) and/or re-run with:\n"
        "    python3 metercheck.py --argyll /path/to/Argyll/bin\n"
    )


def pause(msg: str = "When you're ready, press ENTER to continue... ") -> None:
    """Wait for the user, so nobody feels rushed. Ctrl-C exits cleanly."""
    try:
        input("\n" + msg)
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nStopped. You can re-run any time.")


def welcome() -> None:
    """Plain-language overview for people who've never used a terminal tool."""
    print(
        "\n" + "=" * 70 + "\n"
        "  ChromIQ-MeterCheck - friendly i1Pro3 diagnostics helper\n"
        + "=" * 70 + "\n\n"
        "Hi! This little helper collects some measurements so we can work out\n"
        "why the i1Pro3 sometimes makes bad printer profiles. You do NOT need\n"
        "any technical knowledge - just follow the prompts. It takes about 5\n"
        "minutes.\n\n"
        "WHAT YOU NEED BEFORE STARTING:\n"
        "  1. Your i1Pro3 plugged in.\n"
        "  2. Its white calibration tile / dock (the helper will ask you to\n"
        "     put the device on it - that's the 'calibrate' step).\n"
        "  3. ONE surface to measure. Pick the best you have, in this order:\n"
        "       - a proper calibrated reference tile, or\n"
        "       - a single mid-grey patch, or\n"
        "       - just a blank sheet of the paper you normally profile on.\n"
        "     Whatever you choose, remember the EXACT spot - you'll measure\n"
        "     that same spot again in i1Profiler afterwards.\n\n"
        "WHAT HAPPENS:\n"
        "  - The helper runs Argyll's measuring tool for you.\n"
        "  - Each time, it asks you to (a) put the device on the white tile\n"
        "    and press a key to calibrate, then (b) put it on your surface\n"
        "    and press a key to measure. That's it.\n"
        "  - At the end you get ONE .zip file to attach to the forum thread.\n\n"
        "AFTERWARDS (important - please don't skip):\n"
        "  - Measure the SAME spot in i1Profiler and export it, and attach\n"
        "    that too. The comparison is the whole point.\n"
    )
    pause("Press ENTER to begin (or Ctrl-C to quit)... ")


def run_capture(cmd: list[str], stderr_path: Path, interactive: bool) -> int:
    """
    Run a spotread command.

    stderr (where Argyll's -D debug + init/EEPROM info goes) is always
    captured to a file. stdin/stdout are inherited when interactive so the
    user can see and answer spotread's prompts.
    """
    print("\n>>> running: " + " ".join(cmd) + "\n")
    with open(stderr_path, "w") as err:
        proc = subprocess.run(
            cmd,
            stdin=None if interactive else subprocess.DEVNULL,
            stdout=None,            # inherit -> user sees prompts
            stderr=err,             # capture debug/init log
        )
    return proc.returncode


def collect_system_info(outdir: Path, spotread: str) -> None:
    """Write OS/CPU + ArgyllCMS version to a text file."""
    lines = []
    lines.append("=== System ===")
    lines.append(f"timestamp:  {datetime.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"platform:   {platform.platform()}")
    lines.append(f"machine:    {platform.machine()}")
    lines.append(f"processor:  {platform.processor()}")
    lines.append(f"python:     {platform.python_version()}")
    # On Apple Silicon the X-Rite i1Pro3 plug-in is Intel-only (runs via
    # Rosetta) -- worth recording in case it correlates with problems.
    lines.append("")
    lines.append("=== ArgyllCMS ===")
    lines.append(f"spotread:   {spotread}")

    # spotread prints its version on the usage/error screen.
    try:
        ver = subprocess.run(
            [spotread, "-??"], capture_output=True, text=True, timeout=20
        )
        blob = (ver.stdout or "") + (ver.stderr or "")
        first = next((l for l in blob.splitlines() if "Argyll" in l or "spotread" in l), "")
        lines.append(f"version:    {first.strip() or '(see version_raw.txt)'}")
        (outdir / "version_raw.txt").write_text(blob)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"version:    (could not query: {exc})")

    (outdir / "system_info.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def step_calibration_dump(outdir: Path, spotread: str) -> None:
    """
    Calibrate the instrument and dump its per-unit calibration:
      -Y W:  the white-tile reference spectrum
      -Y S:  the raw & XYZ spectral sensitivities
      -D5    init/EEPROM/firmware debug to stderr (captured)
      -O     do one calibrate+measure then exit
    """
    print("\n" + "=" * 70)
    print("STEP 2 of 2 - Supporting: per-unit calibration dump")
    print("=" * 70)
    print("One last reading. Follow the prompts: place the i1Pro3 on its WHITE")
    print("TILE and press a key to calibrate. It then takes one reading -- you")
    print("can place it on anything for that one, it's just to finish the dump.")
    pause()

    white_sp = outdir / "device_white_reference.sp"
    sens_stub = outdir / "device_sensitivities"     # Argyll appends suffixes
    cmd = [
        spotread,
        "-v",
        "-D5",
        f"-YW:{white_sp}",
        f"-YS:{sens_stub}",
        "-O",
    ]
    run_capture(cmd, outdir / "calibration_debug.log", interactive=True)


def step_measure_conditions(outdir: Path, spotread: str) -> None:
    """Measure the reference surface in M0, M1, M2 and save each spectrum."""
    print("\n" + "=" * 70)
    print("STEP 1 of 2  [HEADLINE] - Measure your reference surface in M0/M1/M2")
    print("=" * 70)
    print("This is the measurement we most want to compare against i1Profiler.")
    print("You'll be asked to calibrate and measure THREE times (one per")
    print("measurement condition). Measure the SAME physical spot each time,")
    print("and -- importantly -- measure that same spot in i1Profiler too and")
    print("export it, so we can compare.")

    conditions = [("M0", "n"), ("M1", "5"), ("M2", "u")]
    for i, (label, filt) in enumerate(conditions, 1):
        print(f"\n--- Reading {i} of 3: condition {label} ---")
        print("    1) Put the device on its WHITE TILE, press a key to calibrate.")
        print("    2) Put it on YOUR reference spot, press a key to measure.")
        pause()
        sp = outdir / f"measure_{label}.sp"
        log = outdir / f"measure_{label}_result.txt"
        cmd = [
            spotread,
            "-v",
            "-s",            # print spectrum for the reading
            "-F", filt,      # n=M0, 5=M1(D50), u=M2(UV cut)
            "-O", str(sp),   # one cal+measure, save spectrum
            str(log),        # logfile with CIE result text
        ]
        run_capture(cmd, outdir / f"measure_{label}_debug.log", interactive=True)


def extract_firmware(outdir: Path) -> None:
    """
    Pull instrument identity (model / serial / firmware version) out of the
    captured debug logs and write it to a prominent file.

    This is KEY CONTEXT: if bad profiles turn out to cluster on a particular
    firmware/hardware revision, that points to ArgyllCMS reading the device's
    EEPROM at offsets that don't match that revision.
    """
    keys = ("serial", "firmware", "fwver", "chip id", "date manufactured",
            "aperture", "i1pro3", "model")
    found: list[str] = []
    for log in sorted(outdir.glob("*.log")):
        try:
            for line in log.read_text(errors="replace").splitlines():
                low = line.lower()
                if any(k in low for k in keys) and len(line) < 120:
                    s = line.strip()
                    if s and s not in found:
                        found.append(s)
        except OSError:
            continue

    body = ["=== Instrument identity (KEY CONTEXT) ==="]
    body += found if found else [
        "(Nothing auto-detected. The raw details are still in the *_debug.log",
        " files - please attach the whole .zip and we'll read them.)"
    ]
    (outdir / "instrument_identity.txt").write_text("\n".join(body) + "\n")
    print("\n".join(body))


def make_readme(outdir: Path) -> None:
    (outdir / "README_FIRST.txt").write_text(
        "i1Pro3 ArgyllCMS diagnostics bundle\n"
        "===================================\n\n"
        "THE HEADLINE DATA (what actually answers the question):\n"
        "  measure_M0/M1/M2.sp          reference surface in 3 conditions <== compare\n"
        "                               these against the SAME surface in i1Profiler\n"
        "  measure_M0/M1/M2_result.txt  CIE values for each\n"
        "  measure_*_debug.log          per-measurement debug\n\n"
        "KEY CONTEXT (firmware/hardware revision):\n"
        "  instrument_identity.txt      model / serial / firmware version. If bad\n"
        "                               profiles cluster on one firmware revision,\n"
        "                               that points to an EEPROM-map mismatch in\n"
        "                               ArgyllCMS rather than a maths error.\n\n"
        "SUPPORTING DATA (rules the basic calibration read in or out):\n"
        "  device_white_reference.sp    the device's own white-tile reference\n"
        "  device_sensitivities*        the device's own spectral sensitivities\n"
        "  calibration_debug.log        instrument init / firmware / EEPROM log\n\n"
        "CONTEXT:\n"
        "  system_info.txt              OS, CPU, ArgyllCMS version\n"
        "  version_raw.txt              full spotread version/usage dump\n\n"
        "PLEASE ALSO ATTACH -- THIS IS THE IMPORTANT BIT:\n"
        "  * the SAME reference spot measured & exported from i1Profiler, so the\n"
        "    Argyll spectra above can be diffed against it. Without this, the\n"
        "    headline comparison can't be done.\n"
        "  * a note of what the reference surface was (tile / grey patch / paper)\n"
        "  * whether your bad profiles failed a SELF-check (re-measure your own\n"
        "    chart) or only an EXTERNAL check (vs another instrument / by eye)\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect i1Pro3 + ArgyllCMS diagnostics.")
    ap.add_argument("--argyll", help="folder containing spotread, if not auto-found")
    ap.add_argument("--out", help="output folder (default: ./ChromIQ-MeterCheck_<timestamp>)")
    ap.add_argument("--no-zip", action="store_true", help="don't create the .zip")
    args = ap.parse_args()

    welcome()
    spotread = find_spotread(args.argyll)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.out) if args.out else Path.cwd() / f"ChromIQ-MeterCheck_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {outdir}\n")

    collect_system_info(outdir, spotread)
    step_measure_conditions(outdir, spotread)   # HEADLINE: the spectra to compare
    step_calibration_dump(outdir, spotread)     # SUPPORTING: rule the EEPROM read in/out
    extract_firmware(outdir)                     # KEY CONTEXT: firmware/hw revision
    make_readme(outdir)

    out_target = outdir
    if not args.no_zip:
        zip_path = outdir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in outdir.rglob("*"):
                zf.write(p, p.relative_to(outdir.parent))
        out_target = zip_path

    print(
        "\n" + "=" * 70 + "\n"
        "  ALL DONE - thank you!\n"
        + "=" * 70 + "\n\n"
        f"Your results are here:\n    {out_target}\n\n"
        "NEXT, PLEASE (this is what makes the data useful):\n"
        "  1. Open i1Profiler and measure the SAME spot you just measured.\n"
        "  2. Export that measurement and keep the file.\n"
        "  3. On the forum thread, attach BOTH:\n"
        "       - the file above, and\n"
        "       - your i1Profiler export.\n"
        "     And mention: your paper type, and whether your bad profiles\n"
        "     failed a self-check or only looked wrong on real prints.\n"
    )


if __name__ == "__main__":
    main()
