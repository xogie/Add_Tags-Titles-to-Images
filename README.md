🧠 Image Captioning & Tagging Tool (with EXIF Metadata Embedding)

This Python tool batch-generates captions and keyword tags for images using a locally hosted vision-language model (e.g., BakLLaVA in LM Studio). The captions and tags are embedded directly into each image’s EXIF metadata so that Windows and other software can read them natively.

    ✅ Works with JPG and PNG
    ✅ Saves to ImageDescription and XPKeywords (Windows Tags)
    ✅ Supports LM Studio or other OpenAI-compatible local endpoints

✨ Features

    🔎 Auto captioning (max 100 chars)

    🏷️ Keyword tag generation (7–10 tags)

    💾 Embeds into EXIF metadata:

        ImageDescription → Title (Windows)

        XPKeywords → Tags (Windows)

    🧠 Works with BakLLaVA, LLaVA, etc.

    📁 GUI folder picker

    📊 Batch processing with retries

    📃 Generates processing log/report

🖥️ Requirements

    Python 3.8+

    pip install pillow aiohttp tqdm

You must run a compatible local model API (like LM Studio) at:

http://localhost:1234/v1/chat/completions

🚀 Usage

    Start your model (LM Studio or similar)

    Run the script:

    python ImageCaptioner.py

    Select a folder of images

    Captions and tags will be embedded into each image

    View results in Windows File Explorer (enable Tags/Title columns)

📝 Output

A metadata_report.txt file will be created in the same folder, showing processing results for each image.
🔧 Configuration

You can customize prompts, model endpoint, tag limits, JPEG quality, and more by editing the CONFIG section at the top of the script.
📄 License

MIT — free to use, modify, and distribute.
