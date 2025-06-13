# Wallpaper Sorter - 2.1.0

Wallpaper Sorter (wpsrt) is a command-line tool that helps you organize your wallpaper collection by sorting images into folders based on different criteria. This tool can process a source directory of images and arrange them into a target directory structure according to the mode you select.

## Installation

### Pipx

```shell
pipx install git+https://github.com/jaypikay/wpsrt
```

## Usage

```shell
wpsrt [OPTIONS] [SOURCE] [TARGET]
```

### Arguments:

*   **`SOURCE`**: This is the path to the directory containing the wallpapers you want to sort.
    *   If not specified, it defaults to `~/Pictures/wallpapers`.
*   **`TARGET`**: This is the path to the directory where the sorted wallpapers will be saved. The tool will create subdirectories within this location based on the chosen sorting mode.
    *   If not specified, it defaults to `~/Pictures/wallpapers/by-resolution` (or a similar path depending on the selected mode).

### Options:

*   **`-m, --mode [resolution|ratio|hash]`**: Specifies the sorting criteria.
    *   **`resolution` (default)**: Sorts wallpapers into folders named after their image resolution (e.g., `1920x1080`, `3840x2160`).
    *   **`ratio`**: Sorts wallpapers into folders named after their aspect ratio (e.g., `16x9`, `4x3`).
    *   **`hash`**: Sorts wallpapers by moving duplicates (based on file content hash) into a `duplicates` subfolder within the target directory. This mode helps in identifying and managing identical images.
*   **`--help`**: Show the help message and exit.

## Example

To sort wallpapers located in `~/MyWallpapers` into `~/SortedWallpapers` by their aspect ratio:

```shell
wpsrt --mode ratio ~/MyWallpapers ~/SortedWallpapers
```

## How to Contribute

Contributions are welcome! If you have ideas for new features, bug fixes, or improvements, please follow these steps:

1.  **Fork the repository** on GitHub.
2.  **Create a new branch** for your feature or fix: `git checkout -b feature-name` or `git checkout -b fix-name`.
3.  **Make your changes** and commit them with clear and concise messages.
4.  **Push your changes** to your forked repository.
5.  **Open a pull request** against the main repository, describing the changes you've made.

Please ensure your code adheres to any existing style guidelines and include tests if applicable.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details. (Assuming a LICENSE file will be added, or state "This project is licensed under the MIT License." if no separate file is planned).
