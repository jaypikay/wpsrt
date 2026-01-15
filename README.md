# Wallpaper Sorter - 2.3.0

Sort wallpapers by their resolution.

## Installation

### Pipx

```shell
pipx install git+https://github.com/jaypikay/wpsrt
```

### UV

```shell
uv tool install git+https://github.com/jaypikay/wpsrt
```

## Usage

```shell
Usage: wpsrt [OPTIONS] [SOURCE] [TARGET]

  Sorts wallpapers from a source directory to a target directory.

  The sorting can be done based on different modes:

  - 'resolution': Sorts wallpapers into subdirectories named after their
                  resolution (e.g., '1920x1080').
  - 'ratio':      Sorts wallpapers into subdirectories named after their
                  aspect ratio (e.g., '16x9').
  - 'hash':       Calculates and displays perceptual hashes of wallpapers in
                  the target directory. (Note: This mode currently only
                  identifies potential duplicates by hash, it does not remove
                  them).

  Args:
    mode:   The sorting mode to use ('resolution', 'ratio', or 'hash').
    source: The path to the directory containing the wallpapers to sort.
    target: The path to the directory where the sorted wallpapers will be
            placed. If it doesn't exist, it will be created.

Options:
  -m, --mode [resolution|ratio|hash]
                                  Sort by resolution or aspect ratio.
  --help                          Show this message and exit.
```

**SOURCE** currently defaults to `~/Pictures/wallpapers` and **TARGET** to `~/Pictures/wallpapers/by-resolution`.
