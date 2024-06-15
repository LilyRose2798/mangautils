#!/usr/bin/env python3

from sys import stderr
from fpdf import FPDF
from natsort import natsorted
from pathlib import Path
from argparse import ArgumentParser
from PIL import Image

class MangaPDF(FPDF):
    page_height = 210
    page_width = 297
    image_margin = 4.2
    text_margin = 7
    
    def write_image(self, path: Path, right_side: bool):
        name = str(path)
        if path.suffix == ".jpg" or path.suffix == ".jpeg":
            info = self._parsejpg(name)
        elif path.suffix == ".png":
            info = self._parsepng(name)
        else:
            raise ValueError("invalid image extension")
        i = len(self.images) + 1
        info["i"] = i
        self.images[name] = info
        iw = info["w"]
        ih = info["h"]
        image_ratio = iw / ih
        pw = self.page_width / 2 - self.image_margin - self.image_margin
        ph = self.page_height - self.image_margin - self.image_margin
        page_ratio = pw / ph
        px = ((self.page_width / 2) if right_side else 0) + self.image_margin
        py = self.image_margin
        if image_ratio > page_ratio:
            w = pw
            h = ph * (page_ratio / image_ratio)
            x = px
            y = py + (ph - h) / 2
        else:
            w = pw * (image_ratio / page_ratio)
            h = ph
            x = px + (pw - w) / 2
            y = py
        self._out(f"q {w * self.k:.2f} 0 0 {h * self.k:.2f} {x * self.k:.2f} {(self.h - (y + h)) * self.k:.2f} cm /I{i} Do Q")

    def text_width(self, text: str) -> float:
        return sum(self.current_font["cw"].get(c) for c in text) * self.font_size / 1000.0

    def write_page_num(self, page_num: int, right_side: bool):
        x = (self.page_width - self.text_margin - self.text_width(str(page_num))) if right_side else self.text_margin
        y = self.page_height - self.text_margin
        self._out(f"BT {x * self.k:.2f} {(self.h - y) * self.k:.2f} Td ({page_num}) Tj ET")

    def __init__(self, left_pages: list[tuple[int, Path | None]], right_pages: list[tuple[int, Path | None]]):
        super().__init__(orientation = "landscape", unit = "mm", format = (self.page_height, self.page_width))
        self.set_font(family = "Times", style = "B", size = 12)
        self.set_text_color(0, 0, 0)
        for (left_page_num, left_img_path), (right_page_num, right_img_path) in zip(left_pages, right_pages):
            self.add_page()
            if left_img_path is not None:
                self.write_image(left_img_path, False)
                self.write_page_num(left_page_num, False)
            if right_img_path is not None:
                self.write_image(right_img_path, True)
                self.write_page_num(right_page_num, True)

def iter_img_paths(imgs_path: Path):
    img_extensions = ["jpg", "jpeg", "png"]
    return (
        img_path
        for img_path_iter in (
            imgs_path.rglob(f"*.{ext}")
            for ext in img_extensions
        )
        for img_path in img_path_iter
        if img_path.is_file()
    )

def build_pdf(imgs_path: Path, num_blanks: int = 0):
    blanks = [None] * num_blanks
    img_paths = blanks + natsorted(iter_img_paths(imgs_path))
    empty_pages = [None] * ((4 - (len(img_paths) % 4)) % 4)
    padded_img_paths = img_paths + empty_pages
    num_pages = len(padded_img_paths)
    middle_index = num_pages // 2
    page_info = list(enumerate(padded_img_paths, 1 - num_blanks))
    back_right_pages = page_info[:middle_index:-2]
    back_left_pages = page_info[:middle_index:2]
    front_right_pages = page_info[1:middle_index:2]
    front_left_pages = page_info[num_pages-2:middle_index-1:-2]
    MangaPDF(back_left_pages, back_right_pages).output(imgs_path.with_name(f"{imgs_path.stem}-back.pdf"), "F")
    MangaPDF(front_left_pages, front_right_pages).output(imgs_path.with_name(f"{imgs_path.stem}-front.pdf"), "F")

def split_images(imgs_path: Path):
    for img_path in iter_img_paths(imgs_path):
        img = Image.open(img_path)
        if img.width > img.height:
            mid = img.width // 2
            img.crop((mid, 0, img.width, img.height)).save(img_path.with_stem(f"{img_path.stem}a"))
            img.crop((0, 0, mid, img.height)).save(img_path.with_stem(f"{img_path.stem}b"))
            img_path.unlink()

def main():
    parser = ArgumentParser("mangautils")
    subparsers = parser.add_subparsers(dest = "command", required = True, help = "the command to run")
    split_parser = subparsers.add_parser("split", help = "split two page spreads in the given images")
    split_parser.add_argument("input", help = "the directory containing the images")
    build_parser = subparsers.add_parser("build", help = "create a pdf from the given images")
    build_parser.add_argument("input", help = "the directory containing the images")
    build_parser.add_argument("-b", "--blanks", default = 0, type = int, help = "number of blank pages to add at the start (default: %(default)s)")
    args = parser.parse_args()
    
    try:
        input_path = Path(args.input)
        match args.command:
            case "split":
                split_images(input_path)
            case "build":
                build_pdf(input_path, args.blanks)
    except Exception as e:
        print(f"error: {e}", file = stderr)
        exit(1)

if __name__ == "__main__":
    main()
