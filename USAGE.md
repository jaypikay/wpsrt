# Wpsrt v2.3.4 - Command Usage Overview

# wpsort
```
Usage: wpsrt  [OPTIONS] [SOURCE] [TARGET]

  Sorts wallpapers from a source directory to a target directory.

  The sorting can be done based on different modes: - 'resolution': Sorts
  wallpapers into subdirectories named after their resolution (e.g.,
  '1920x1080'). - 'ratio': Sorts wallpapers into subdirectories named after
  their aspect ratio (e.g., '16x9'). - 'hash': Calculates and displays
  perceptual hashes of wallpapers in the target directory.           (Note:
  This mode currently only identifies potential duplicates by hash, it does
  not remove them).

  Args:     mode: The sorting mode to use ('resolution', 'ratio', or 'hash').
  source: The path to the directory containing the wallpapers to sort.
  target: The path to the directory where the sorted wallpapers will be
  placed.             If it doesn't exist, it will be created.

Options:
  -m, --mode [resolution|ratio|hash|nsfw]
                                  Sort by resolution or aspect ratio.
  -n, --nsfw-model FILE
  -d, --dry-run                   Do not perform any file actions
  --help                          Show this message and exit.
```

# Wpsrt v2.3.4 - Command Usage Overview

# wpconvert
```
Usage: wpsrt  [OPTIONS] [SOURCE]

  Convert images by extension `extension` to PNG.

Options:
  -e, --extension TEXT  Convert of type EXT to png
  -d, --delete BOOLEAN  Remove original file after conversion
  --help                Show this message and exit.
```

# Wpsrt v2.3.4 - Command Usage Overview

# nsfw-inspect
```
Usage: wpsrt  [OPTIONS] [TARGET]

Options:
  -n, --nsfw-model FILE
  -j, --jobs INTEGER
  --help                 Show this message and exit.
```

