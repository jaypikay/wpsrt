# Wpsrt v2.6.1 - Command Usage Overview

# wpsort
```
Usage: wpsrt  [OPTIONS] [SOURCE] [TARGET]

  Sorts wallpapers from a source directory to a target directory.

  The sorting can be done based on different modes:

  - 'resolution': Sorts wallpapers into subdirectories named after their
  resolution (e.g., '1920x1080').

  - 'ratio': Sorts wallpapers into subdirectories named after their aspect
  ratio (e.g., '16:9').

  - 'nsfw': Sorts wallpapers by SFW / NSFW content.

  - 'clip': Sorts wallpapers into category subdirectories using CLIP.

Options:
  -m, --mode [resolution|ratio|nsfw|clip]
                                  Sort by resolution, aspect ratio, NSFW
                                  rating, or CLIP category.
  -n, --nsfw-model FILE           Custom ONNX model path for NSFW detection.
  -d, --dry-run                   Do not perform any file actions.
  --help                          Show this message and exit.
```

# Wpsrt v2.6.1 - Command Usage Overview

# wphash
```
Usage: wpsrt  [OPTIONS] [TARGET]

  Hash, compare and clean image hashes.

  Example usage:

      wphash -m compare | swiv -t -i

      wphash -m compare -o similarities.dhash

Options:
  -m, --mode [clean|hash|compare]
                                  Operational mode selection
  -h, --hash [phash|dhash|colorhash|average_hash]
                                  Hash used for comparison during similarity
                                  check
  -t, --threshold INTEGER         Threshold distance during similarity check
  -o, --output FILE               Output file for similarity results
  --help                          Show this message and exit.
```

# Wpsrt v2.6.1 - Command Usage Overview

# wpconvert
```
Usage: wpsrt  [OPTIONS] [SOURCE]

  Convert images with specific extension to PNG.

Options:
  -e, --extension TEXT  Convert of type EXT to png
  -d, --delete          Remove original file after conversion
  --help                Show this message and exit.
```

# Wpsrt v2.6.1 - Command Usage Overview

# nsfw-inspect
```
Usage: wpsrt  [OPTIONS] [TARGET]

  Inspects wallpapers using NudeDetector and prints classifications.

Options:
  -n, --nsfw-model FILE
  --help                 Show this message and exit.
```

