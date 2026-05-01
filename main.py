from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import requests
import json
import base64
from io import BytesIO
from PIL import Image

app = FastAPI(title="VibeCap API")



class RewriteCaptionRequest(BaseModel):
    caption: str
    tone: str
    platform: str 
    language: str 
    count: int = 5

@app.get("/")
def home():
    return {"message": "VibeCap API is running"}

## upload file media
@app.post("/generate-caption")
async def generate_caption_from_image(
    image: UploadFile = File(...),
    platform: str = Form("tiktok"),
    tone: str = Form("Gen Z, viral"),
    language: str = Form("vi"),
    count: int = Form(5),
    hashtags: bool = Form(True)
):
    
    
    image_bytes = await image.read()

    img = Image.open(BytesIO(image_bytes))
    img.thumbnail((768, 768))

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)

    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Step 1: VLM read Photo
    vision_prompt = """
Describe this image for social media caption writing.
also discribe person if that a boy or girl.
"""

    vision_response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen2.5vl:7b",
            "messages": [
                {
                    "role": "user",
                    "content": vision_prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        },
    )

    image_description = vision_response.json()["message"]["content"]

    # Step 2: Qwen3 viết caption
    caption_prompt = f"""
You are a professional social media copywriter.

Write {count} captions for {platform} based on this image description:

Image description:
{image_description}

Requirements:
- Tone: {tone}
- Language: {language}
- Include hashtags: {"yes" if hashtags else "no"}
- Short, engaging, natural
- Strong hook at the beginning
- Use emojis if appropriate
- Do not explain anything

Output ONLY valid JSON:
{{
  "image_description": "...",
  "captions": [
    "caption 1",
    "caption 2"
  ]
}}
"""

    caption_response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3:8b",
            "prompt": caption_prompt,
            "stream": False,
            "options": {
                "temperature": 0.9,
                "top_p": 0.9
            }
        },
        timeout=120
    )

    result = caption_response.json()["response"]

    try:
        data = json.loads(result)
        data["image_description"] = image_description
        return data
    except Exception:
        return {
            "image_description": image_description,
            "raw": result
        }
        
        
        
        
        
        
        
        
        
        
    
##rewrite caption
@app.post("/rewrite-caption")
def rewrite_caption(req: RewriteCaptionRequest):
    prompt = f"""
You are a professional social media copywriter.

Rewrite the caption below into {req.count} better versions.

Original caption:
"{req.caption}"

Context:
- Platform: {req.platform}
- Tone: {req.tone}
- Language: {req.language}

Requirements:
- Make it more engaging
- Keep the original meaning
- Make it natural and human-like
- Suitable for TikTok/Instagram
- Use emojis if appropriate
- Do not explain anything

Output ONLY valid JSON:
{{
  "rewrites": [
    "rewrite 1",
    "rewrite 2"
  ]
}}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.9,
                "top_p": 0.9
            }
        },
        timeout=120
    )

    result = response.json()["response"]

    try:
        return json.loads(result)
    except Exception:
        return {"raw": result}