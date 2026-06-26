# ChromIQ-MeterCheck

A small, friendly diagnostics helper for the **i1Pro3** colour measuring device
when used with **[ArgyllCMS](https://www.argyllcms.com/)**.

Some people get poor printer profiles (large Delta-E errors) when they read
charts with an i1Pro3 in ArgyllCMS. This tool collects the measurements needed
to work out **why**, and bundles them into a single `.zip` you can share so the
results can be compared across devices — and against X-Rite's i1Profiler.

It does **not** require any programming knowledge: it runs ArgyllCMS's own
measuring tool for you and walks you through every step.

## What it collects

- **The headline:** one reference surface measured in **M0, M1 and M2**, saved
  as spectra — to compare against the *same* surface measured in i1Profiler.
- Your **i1Pro3 firmware / hardware revision** (key context).
- Your **ArgyllCMS version** and OS/CPU.
- Supporting data: the device's own white-tile reference and spectral
  sensitivities (to confirm the basic calibration read is sane).

> ℹ️ This tool only uses **ArgyllCMS**. It does not touch, read or modify any
> X-Rite software. It simply records what your own instrument reports through
> ArgyllCMS's public command-line tools.

## What you need

1. An **i1Pro3** plugged in, with its **white calibration tile / dock**.
2. **ArgyllCMS** installed (free — https://www.argyllcms.com/, **v3.5.0**
   recommended). The tool drives *your* Argyll, since that's what's being tested.
3. **One surface to measure** — best to worst: a calibrated reference tile → a
   single mid-grey patch → a blank sheet of the paper you normally profile on.

## How to run

### Easiest: download a ready-made program (no Python needed)

Grab the file for your system from the [**Releases**](../../releases) page:

| System | File |
|---|---|
| **Mac (any, recommended)** | `ChromIQ-MeterCheck-macOS-universal.zip` |
| Mac (Apple Silicon only) | `ChromIQ-MeterCheck-macOS-arm64.zip` |
| Windows 64-bit | `ChromIQ-MeterCheck-Windows-x86_64.exe` |
| Windows 32-bit | `ChromIQ-MeterCheck-Windows-x86.exe` |
| Windows on ARM | `ChromIQ-MeterCheck-Windows-arm64.exe` |
| Linux x86-64 | `ChromIQ-MeterCheck-Linux-x86_64` |
| Linux ARM64 | `ChromIQ-MeterCheck-Linux-arm64` |

**macOS:** download the `.zip`, double-click to unzip, open the
`ChromIQ-MeterCheck` folder, and double-click **`Double-click to run.command`**.
The first time, macOS may block it (unsigned): right-click that file → **Open** →
**Open**. After that it just runs. (The launcher handles permissions for you, so
you never need Terminal.)

**Windows:** double-click the `.exe`. SmartScreen may warn about an unknown
publisher → *More info* → *Run anyway*.

**Linux:** `chmod +x ChromIQ-MeterCheck-Linux-x86_64 && ./ChromIQ-MeterCheck-Linux-x86_64`.

### Alternative: run the script directly (needs Python 3.7+)

```
python3 metercheck.py
```

If ArgyllCMS isn't found automatically, point at its folder:

```
python3 metercheck.py --argyll "/Applications/Argyll/bin"
```

## Afterwards — please don't skip

Now measure the **same spot** in **i1Profiler** (X-Rite's own software), so the
two tools can be compared. It's quick:

1. Open i1Profiler. On the Home screen, click the **Color Picker** tile.
2. Connect your i1Pro3. Watch the **Device Status** indicator — when it asks,
   put the device on its white tile to calibrate, and wait until it shows ready.
3. Put the device on the **exact same spot** you measured with the tool, and
   press its button to measure. The reading appears in the **Color List**.
4. Click that reading in the Color List. The **Color Preview** panel shows its
   **Lab** values (L\*, a\*, b\*). Write those three numbers down.
5. *(Optional)* Select the reading and click **Export Colors to ASE** to save it
   as a file you can attach instead of typing the numbers.
6. You don't need to change any settings in i1Profiler — just measure with
   whatever it's set to by default. We line it up with the matching reading
   from the tool.

Then share **both** the tool's `.zip` **and** your i1Profiler Lab values (or ASE
file). Also mention your **paper type** and whether your bad profiles failed a
**self-check** (re-measuring your own chart) or only looked wrong on real prints.

## Privacy

Everything stays on your computer. The tool writes a folder and a `.zip`; it
never uploads anything. You choose what to share.

## License

MIT — see [LICENSE](LICENSE).
