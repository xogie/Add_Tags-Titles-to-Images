import os, base64, logging, asyncio, aiohttp, re, json
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
from PIL import Image, ImageFile, PngImagePlugin
from io import BytesIO
from typing import Optional, List, Tuple
from dataclasses import dataclass
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True

CONFIG = {
    "api": {
        "url": "http://localhost:1234/v1/chat/completions",
        "model": "mys/ggml_bakllava-1",
        "timeout": 30,
        "max_retries": 3
    },
    "prompt": {
        "caption": "Describe the image concisely in one sentence (max 100 chars).",
        "tags": "List 7-10 specific keywords describing the main objects, themes and elements in the image. Return only comma-separated keywords, no sentences."
    },
    "processing": {
        "batch_size": 50,
        "supported_formats": [".jpg", ".jpeg", ".png"],
        "jpeg_quality": 90,
        "min_file_size": 100,
        "force_overwrite": True
    },
    "metadata": {
        "description_field": 270,
        "keywords_field": 40094,
        "max_tag_length": 25,
        "min_tags": 7,
        "max_tags": 10
    }
}

@dataclass
class ImageCaptionResult:
    file_path: Path
    original_name: str
    caption: Optional[str] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None
    skipped: bool = False

class ImageCaptioner:
    def __init__(self):
        self.config = CONFIG
        self.logger = self._setup_logger()
        self.processed_files = 0
        self.skipped_files = 0
        self.failed_files = 0

    def _setup_logger(self):
        logger = logging.getLogger("ImageCaptioner")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def select_folder(self) -> Optional[Path]:
        Tk().withdraw()
        folder = filedialog.askdirectory(title="Select Image Folder", mustexist=True)
        return Path(folder) if folder else None

    def _validate_filename(self, filename: str) -> Tuple[bool, str]:
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        return clean_name != filename, clean_name

    def _extract_caption(self, text: str) -> Optional[str]:
        first = re.split(r'[.!?]\s*', text.strip())[0]
        first = re.sub(r"^(in (this|the) (image|photo|picture)[,:]?\s*)", "", first, flags=re.IGNORECASE)
        return first.strip()[:100]

    def _extract_tags(self, text: str, caption: str) -> Optional[List[str]]:
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'is', 'are', 'was', 'were', 'with', 'of', 'image', 'photo', 'picture',
            'shows', 'there', 'this', 'that', 'these', 'those', 'you', 'it', 'they',
            'we', 'he', 'she', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
            'what', 'which', 'where', 'when', 'who', 'how', 'why', 'some', 'any',
            'all', 'many', 'much', 'more', 'most', 'few', 'several', 'such', 'own',
            'in_the_image'
        }

        clean_text = re.sub(r'[\'"\[\](){}]', '', text.lower())
        words = re.findall(r'\b[a-z]{3,20}\b', clean_text)
        caption_words = re.findall(r'\b[a-z]{3,20}\b', caption.lower())

        potential_tags = list(dict.fromkeys(words + caption_words))
        final_tags, seen = [], set()

        for tag in potential_tags:
            tag = tag.strip().replace('_', ' ')
            if (tag in stop_words or not tag or len(tag) > self.config["metadata"]["max_tag_length"] or tag in seen):
                continue
            final_tags.append(tag)
            seen.add(tag)
            if len(final_tags) >= self.config["metadata"]["max_tags"]:
                break

        return final_tags if len(final_tags) >= self.config["metadata"]["min_tags"] else None

    async def get_caption_and_tags(self, session, b64: str) -> Tuple[Optional[str], Optional[List[str]]]:
        for attempt in range(self.config["api"]["max_retries"]):
            try:
                # Caption
                payload_caption = {
                    "model": self.config["api"]["model"],
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.config["prompt"]["caption"]},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }],
                    "temperature": 0.0,
                    "max_tokens": 100
                }

                async with session.post(self.config["api"]["url"], headers={"Content-Type": "application/json"}, json=payload_caption, timeout=self.config["api"]["timeout"]) as r:
                    result = await r.json()
                    caption = self._extract_caption(result["choices"][0]["message"]["content"])

                # Tags
                payload_tags = {
                    "model": self.config["api"]["model"],
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.config["prompt"]["tags"]},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }],
                    "temperature": 0.0,
                    "max_tokens": 100
                }

                async with session.post(self.config["api"]["url"], headers={"Content-Type": "application/json"}, json=payload_tags, timeout=self.config["api"]["timeout"]) as r:
                    result = await r.json()
                    tags = self._extract_tags(result["choices"][0]["message"]["content"], caption)

                return caption, tags
            except Exception as e:
                self.logger.warning(f"Retry {attempt + 1}: {e}")
                if attempt == self.config["api"]["max_retries"] - 1:
                    return None, None
                await asyncio.sleep(1)

    def image_to_base64(self, image_path: Path) -> Optional[str]:
        try:
            with Image.open(image_path) as img:
                if img.format not in ["JPEG", "PNG"]:
                    img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=100, subsampling=0)
                return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            self.logger.error(f"Base64 error: {e}")
            return None

    def embed_metadata(self, image_path: Path, caption: str, tags: List[str]) -> bool:
        try:
            with Image.open(image_path) as img:
                tag_str = ';'.join(tags) + ';'

                if img.format == "PNG":
                    info = PngImagePlugin.PngInfo()
                    info.add_text("Description", caption)
                    info.add_text("Keywords", tag_str)
                    img.save(image_path, "PNG", pnginfo=info)
                else:
                    exif = img.getexif()
                    exif[self.config["metadata"]["description_field"]] = caption
                    exif[self.config["metadata"]["keywords_field"]] = tag_str.encode("utf-16le")
                    img.save(image_path, "JPEG", exif=exif.tobytes(), quality=self.config["processing"]["jpeg_quality"], subsampling=0)

                self.logger.info(f"Saved: {image_path.name} | Tags: {tags}")
                return True
        except Exception as e:
            self.logger.error(f"Metadata error: {e}")
            return False

    async def _process_single_file(self, session, path: Path) -> ImageCaptionResult:
        changed, new_name = self._validate_filename(path.name)
        if changed:
            try:
                new_path = path.with_name(new_name)
                path.rename(new_path)
                path = new_path
            except Exception as e:
                return ImageCaptionResult(path, path.name, error=str(e))

        b64 = self.image_to_base64(path)
        if not b64:
            return ImageCaptionResult(path, path.name, error="Base64 failed")

        caption, tags = await self.get_caption_and_tags(session, b64)
        if not caption or not tags:
            return ImageCaptionResult(path, path.name, error="Missing caption/tags")

        if not self.embed_metadata(path, caption, tags):
            return ImageCaptionResult(path, path.name, error="Embed failed")

        return ImageCaptionResult(path, path.name, caption, tags)

    async def process_folder(self, folder: Path):
        files = [f for f in folder.iterdir() if f.suffix.lower() in self.config["processing"]["supported_formats"] and f.stat().st_size / 1024 >= self.config["processing"]["min_file_size"]]
        if not files:
            self.logger.error("No valid images.")
            return []

        results = []
        async with aiohttp.ClientSession() as session:
            for i in tqdm(range(0, len(files), self.config["processing"]["batch_size"]), desc="Processing"):
                batch = files[i:i + self.config["processing"]["batch_size"]]
                for f in batch:
                    result = await self._process_single_file(session, f)
                    results.append(result)
                    if result.skipped: self.skipped_files += 1
                    elif result.error: self.failed_files += 1
                    else: self.processed_files += 1
        return results

    def generate_report(self, results):
        lines = [
            f"Processed: {self.processed_files}",
            f"Skipped: {self.skipped_files}",
            f"Failed: {self.failed_files}",
            "\nFailures:"
        ]
        for r in results:
            if r.error:
                lines.append(f"{r.file_path.name}: {r.error}")
        return "\n".join(lines)

    async def run(self):
        folder = self.select_folder()
        if not folder:
            messagebox.showwarning("No folder", "Nothing selected.")
            return

        self.logger.info(f"Starting folder: {folder}")
        results = await self.process_folder(folder)
        report = self.generate_report(results)

        with open(folder / "metadata_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        self.logger.info("Finished. Report saved.")
        messagebox.showinfo("Done", report)

if __name__ == "__main__":
    try:
        asyncio.run(ImageCaptioner().run())
    except Exception as e:
        print("Error:", e)
        input("Press Enter to exit...")
