🧠 Image Captioning & Tagging Tool

Batch-generate captions and keyword tags for JPG/PNG images using a local model like BakLLaVA (via LM Studio). Captions and tags are embedded into EXIF metadata so they show up in Windows Explorer.

✅ Features

    Auto caption (max 100 characters)

    7–10 keyword tags

    Tags saved to XPKeywords (Windows “Tags”)

    Captions saved to ImageDescription (Windows “Title”)

    JPG & PNG support

    GUI folder picker

    Batch processing + retry logic

    Creates metadata_report.txt

💻 Requirements

    Python 3.8+

    pip install pillow aiohttp tqdm

    A local model API (e.g. LM Studio at: http://localhost:1234/v1/chat/completions)

🚀 How to Use

python ImageCaptioner.py

    Start LM Studio (BakLLaVA model)

    Run the script

    Pick a folder of images

    Captions/tags will be added to EXIF

    View tags and titles in Windows Explorer

⚙️ Customization

Edit the CONFIG section in the script to change prompts, limits, model settings, etc.
📄 License

MIT – free to use and modify.

![image](https://github.com/user-attachments/assets/71fad027-4f70-41ee-89f1-a8477cbd4a7a)

