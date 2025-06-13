import pytest
from pathlib import Path
import shutil
import tempfile
from PIL import Image, ImageDraw
import random

# Assuming src/wpsrt/wallpapers.py is discoverable in PYTHONPATH
from wpsrt.wallpapers import calculate_aspect_ratio, sort_wallpapers, hash_wallpapers, scan_directory, move_wallpaper

# Helper function to create a dummy image file
def create_dummy_image(path: Path, width: int, height: int, color='red', format="PNG"):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (width, height), color=color)

    # Add some noise or simple pattern to make images more distinct for phash
    draw = ImageDraw.Draw(image)
    for i in range(min(width, height) // 5): # Draw a few lines
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        line_color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        draw.line([(x1,y1), (x2,y2)], fill=line_color, width=1)

    # For very small images, ensure at least one pixel is different if all lines were off-image
    if width > 0 and height > 0 :
        draw.point((width // 2, height // 2), fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))

    image.save(path, format)
    return path

class TestCalculateAspectRatio:
    def test_common_ratios(self):
        assert calculate_aspect_ratio(1920, 1080) == "16:9"
        assert calculate_aspect_ratio(1280, 720) == "16:9"
        assert calculate_aspect_ratio(1024, 768) == "4:3"
        assert calculate_aspect_ratio(800, 600) == "4:3"

    def test_square_ratio(self):
        assert calculate_aspect_ratio(1000, 1000) == "1:1"
        assert calculate_aspect_ratio(512, 512) == "1:1"

    def test_portrait_ratios(self):
        assert calculate_aspect_ratio(1080, 1920) == "9:16"
        assert calculate_aspect_ratio(768, 1024) == "3:4"
        assert calculate_aspect_ratio(600, 800) == "3:4"

    def test_prime_dimensions(self):
        assert calculate_aspect_ratio(17, 13) == "17:13"
        assert calculate_aspect_ratio(13, 17) == "13:17"

    def test_one_dimension_is_one(self):
        assert calculate_aspect_ratio(1920, 1) == "1920:1"
        assert calculate_aspect_ratio(1, 1080) == "1:1080"

class TestWallpaperOperations:
    @pytest.fixture(autouse=True)
    def temp_dirs(self):
        self.source_dir = Path(tempfile.mkdtemp(prefix="wpsrt_test_source_"))
        self.target_dir = Path(tempfile.mkdtemp(prefix="wpsrt_test_target_"))
        # Seed random for reproducible dummy images in tests if necessary,
        # though for phash, distinctness is key, not specific hash values.
        random.seed(0) # Ensure consistent "random" elements for testing if needed
        yield
        shutil.rmtree(self.source_dir)
        shutil.rmtree(self.target_dir)

    def test_sort_wallpapers_by_resolution(self):
        img1 = create_dummy_image(self.source_dir / "img1.png", 1920, 1080)
        img2 = create_dummy_image(self.source_dir / "img2.jpg", 800, 600)
        img3 = create_dummy_image(self.source_dir / "img3.png", 1920, 1080) # Different content due to random
        img4 = create_dummy_image(self.source_dir / "img4.png", 1024, 768)

        sort_wallpapers(mode="resolution", source=self.source_dir, target=self.target_dir)

        assert (self.target_dir / "by-resolution" / "1920x1080" / "img1.png").exists()
        assert (self.target_dir / "by-resolution" / "800x600" / "img2.jpg").exists()
        assert (self.target_dir / "by-resolution" / "1920x1080" / "img3.png").exists()
        assert (self.target_dir / "by-resolution" / "1024x768" / "img4.png").exists()

        assert not img1.exists()
        assert not img2.exists()
        assert not img3.exists()
        assert not img4.exists()
        assert len(list(self.source_dir.iterdir())) == 0

    def test_sort_wallpapers_by_aspect_ratio(self):
        img1 = create_dummy_image(self.source_dir / "img1_16x9.png", 1920, 1080)
        img2 = create_dummy_image(self.source_dir / "img2_4x3.jpg", 800, 600)
        img3 = create_dummy_image(self.source_dir / "img3_16x9.png", 1280, 720)
        img4 = create_dummy_image(self.source_dir / "img4_1x1.png", 1000, 1000)

        sort_wallpapers(mode="ratio", source=self.source_dir, target=self.target_dir)

        assert (self.target_dir / "by-aspect-ratio" / "16:9" / "img1_16x9.png").exists()
        assert (self.target_dir / "by-aspect-ratio" / "4:3" / "img2_4x3.jpg").exists()
        assert (self.target_dir / "by-aspect-ratio" / "16:9" / "img3_16x9.png").exists()
        assert (self.target_dir / "by-aspect-ratio" / "1:1" / "img4_1x1.png").exists()

        assert not img1.exists()
        assert not img2.exists()
        assert not img3.exists()
        assert not img4.exists()
        assert len(list(self.source_dir.iterdir())) == 0

    def test_hash_wallpapers_identifies_hashes(self):
        # Create unique images. Seeding random ensures they are the same unique images each run.
        random.seed(10) # Seed for imgA
        create_dummy_image(self.target_dir / "imgA_unique.png", 60, 60, color='blue')
        random.seed(20) # Seed for imgB
        create_dummy_image(self.target_dir / "imgB_unique.png", 80, 80, color='green')

        # Create two identical images (imgC_dup1, imgD_dup2)
        # To make them identical for phash, they must be pixel-for-pixel identical.
        # So, create one, then copy the file. Or save the same PIL object twice.
        random.seed(30) # Seed for the identical image content
        identical_pil_image_content = Image.new('RGB', (70, 70), color='purple')
        draw = ImageDraw.Draw(identical_pil_image_content)
        for i in range(min(70, 70) // 5):
            x1 = random.randint(0, 70); y1 = random.randint(0, 70)
            x2 = random.randint(0, 70); y2 = random.randint(0, 70)
            line_color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
            draw.line([(x1,y1), (x2,y2)], fill=line_color, width=1)
        draw.point((35,35), fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))

        identical_pil_image_content.save(self.target_dir / "imgC_dup1.png", "PNG")
        identical_pil_image_content.save(self.target_dir / "imgD_dup2.png", "PNG") # Save the exact same PIL Image

        random.seed(40) # Seed for imgE
        create_dummy_image(self.target_dir / "imgE_unique.png", 90, 90, color='yellow')

        results = hash_wallpapers(target=self.target_dir)

        assert len(results) == 5

        hashes_map = {}
        for filepath_obj, file_hash_str, _ in results:
            filename = filepath_obj.name
            if file_hash_str not in hashes_map:
                hashes_map[file_hash_str] = []
            hashes_map[file_hash_str].append(filename)

        found_duplicates_list = []
        unique_hashes_count = 0
        for file_hash_str, filenames_list in hashes_map.items():
            if len(filenames_list) > 1:
                found_duplicates_list.extend(sorted(filenames_list)) # sort for consistent order
            unique_hashes_count +=1

        assert sorted(found_duplicates_list) == sorted(["imgC_dup1.png", "imgD_dup2.png"])
        assert unique_hashes_count == 4 # (A), (B), (C,D are one hash), (E)

        hash_dict = {fp.name: fh for fp, fh, _ in results}

        assert hash_dict["imgC_dup1.png"] == hash_dict["imgD_dup2.png"], \
            f"Hashes for duplicates did not match: C={hash_dict['imgC_dup1.png']}, D={hash_dict['imgD_dup2.png']}"

        distinct_hashes = {hash_dict["imgA_unique.png"],
                           hash_dict["imgB_unique.png"],
                           hash_dict["imgC_dup1.png"], # or imgD_dup2.png
                           hash_dict["imgE_unique.png"]}
        assert len(distinct_hashes) == 4, \
            f"Expected 4 distinct hashes, got {len(distinct_hashes)}. Hashes: {hash_dict}"


    def test_scan_directory_mixed_content(self):
        create_dummy_image(self.source_dir / "image1.png", 100, 100)
        (self.source_dir / "not_an_image.txt").write_text("hello")
        create_dummy_image(self.source_dir / "image2.jpg", 200, 200)

        scanned_files = list(scan_directory(self.source_dir))
        assert len(scanned_files) == 2
        filenames = sorted([item[0].name for item in scanned_files])
        assert filenames == ["image1.png", "image2.jpg"]

    def test_move_wallpaper_creates_dirs(self):
        source_file = self.source_dir / "movable.png"
        create_dummy_image(source_file, 50, 50)

        target_file_path = self.target_dir / "new" / "subdir" / "moved.png"

        assert not target_file_path.parent.exists()
        move_wallpaper(source_file, target_file_path)
        assert target_file_path.exists()
        assert not source_file.exists()
        assert target_file_path.parent.exists()

    def test_sort_wallpapers_no_files_in_source(self):
        sort_wallpapers(mode="resolution", source=self.source_dir, target=self.target_dir)
        target_items = list(item for item in self.target_dir.glob("**/*") if item.is_file())
        assert len(target_items) == 0
        assert not (self.target_dir / "by-resolution").exists()
        assert not (self.target_dir / "by-aspect-ratio").exists()

    def test_sort_wallpapers_output_overwrite(self):
        # Create initial image. Randomness in create_dummy_image ensures content.
        create_dummy_image(self.source_dir / "image.png", 100, 100, color='red')
        sort_wallpapers(mode="resolution", source=self.source_dir, target=self.target_dir)

        target_file = self.target_dir / "by-resolution" / "100x100" / "image.png"
        assert target_file.exists()
        # first_hash = imagehash.phash(Image.open(target_file)) # If we want to check content change

        # Create a new source file with the same name, different color, should result in different hash
        # The `create_dummy_image` will make it different due to random lines.
        img_src2 = create_dummy_image(self.source_dir / "image.png", 100, 100, color='blue')
        sort_wallpapers(mode="resolution", source=self.source_dir, target=self.target_dir)
        assert target_file.exists()
        assert not img_src2.exists() # Source file should be moved

        # second_hash = imagehash.phash(Image.open(target_file))
        # assert first_hash != second_hash, "Image content should have been overwritten with a new image."

        files_in_target_subdir = list((self.target_dir / "by-resolution" / "100x100").iterdir())
        assert len(files_in_target_subdir) == 1
        assert files_in_target_subdir[0].name == "image.png"
