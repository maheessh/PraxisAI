from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import google.generativeai as genai
import os
import json
import fitz  # PyMuPDF for reading PDFs
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import tempfile
from datetime import datetime
import requests

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. Configure the Google Gemini API (Free Tier) ---
try:
    api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyDn8GUgpTGq9uu2oktZIFBGgtlTkqssSU4")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set and no fallback key is provided.")
    
    genai.configure(api_key=api_key)
    
    # Initialize the model with settings for JSON output
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json"
    )
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config=generation_config
    )
    logger.info("Google Gemini API (Free Tier) configured successfully.")

except Exception as e:
    logger.error(f"FATAL: Could not configure Google Gemini API: {e}")
    model = None

# --- FastAPI App Initialization ---
app = FastAPI()

# --- CORS Middleware ---
origins = ["http://localhost", "http://127.0.0.1", "null", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Image Generation Functions ---
async def generate_slide_image(title: str, bullet_points: list, color_scheme: str = "blue") -> str:
    """
    Generate a custom slide image using PIL
    Returns base64 encoded image
    """
    try:
        # Create a high-quality slide image
        width, height = 1920, 1080  # Full HD 16:9
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Color schemes
        color_schemes = {
            "blue": {"primary": "#2E86C1", "secondary": "#1B4F72", "accent": "#5DADE2"},
            "orange": {"primary": "#E67E22", "secondary": "#A0522D", "accent": "#F8C471"},
            "green": {"primary": "#27AE60", "secondary": "#1E8449", "accent": "#58D68D"},
            "purple": {"primary": "#8E44AD", "secondary": "#6C3483", "accent": "#BB8FCE"},
            "gray": {"primary": "#34495E", "secondary": "#2C3E50", "accent": "#85929E"}
        }
        
        colors = color_schemes.get(color_scheme, color_schemes["blue"])
        
        # Load fonts with fallbacks
        try:
            if os.name == 'nt':  # Windows
                title_font = ImageFont.truetype("arial.ttf", 80)
                bullet_font = ImageFont.truetype("arial.ttf", 40)
                small_font = ImageFont.truetype("arial.ttf", 30)
            else:  # Linux/Mac
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
                bullet_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            # Fallback to default font
            title_font = ImageFont.load_default()
            bullet_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Create gradient background
        for y in range(height):
            r1, g1, b1 = tuple(int(colors["primary"][i:i+2], 16) for i in (1, 3, 5))
            r2, g2, b2 = tuple(int(colors["secondary"][i:i+2], 16) for i in (1, 3, 5))
            
            ratio = y / height
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add decorative elements
        draw.rectangle([50, 120, width-50, 140], fill="white", width=3)
        
        # Draw title
        title_lines = []
        words = title.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] <= width - 100:
                current_line = test_line
            else:
                if current_line:
                    title_lines.append(current_line)
                current_line = word
        if current_line:
            title_lines.append(current_line)
        
        # Position title
        y_offset = 180
        for line in title_lines[:2]:  # Max 2 lines
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) // 2
            draw.text((x_pos, y_offset), line, fill='white', font=title_font)
            y_offset += 100
        
        # Draw bullet points
        bullet_y = 400
        for i, bullet in enumerate(bullet_points[:4]):  # Max 4 bullets
            # Bullet point circle
            draw.ellipse([100, bullet_y + 10, 130, bullet_y + 40], fill=colors["accent"])
            
            # Bullet text with word wrapping
            bullet_words = bullet.split()
            bullet_lines = []
            current_bullet_line = ""
            
            for word in bullet_words:
                test_line = current_bullet_line + " " + word if current_bullet_line else word
                bbox = draw.textbbox((0, 0), test_line, font=bullet_font)
                if bbox[2] - bbox[0] <= width - 200:
                    current_bullet_line = test_line
                else:
                    if current_bullet_line:
                        bullet_lines.append(current_bullet_line)
                    current_bullet_line = word
            if current_bullet_line:
                bullet_lines.append(current_bullet_line)
            
            # Draw bullet lines
            line_y = bullet_y
            for line in bullet_lines[:2]:  # Max 2 lines per bullet
                draw.text((160, line_y), line, fill='white', font=bullet_font)
                line_y += 50
                
            bullet_y += 120
        
        # Add "AI Generated" watermark
        watermark = "AI Generated Slide"
        bbox = draw.textbbox((0, 0), watermark, font=small_font)
        watermark_width = bbox[2] - bbox[0]
        draw.text((width - watermark_width - 50, height - 80), watermark, fill="white", font=small_font)
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return img_base64
        
    except Exception as e:
        logger.error(f"Error creating slide image: {e}")
        return None

async def create_slide_pdf(slides_data: dict) -> str:
    """
    Create a professional PDF from slides data
    """
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        # Create PDF document
        doc = SimpleDocTemplate(temp_path, pagesize=A4, topMargin=0.5*inch)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=20,
            textColor=HexColor('#2E86C1'),
            alignment=1,  # Center alignment
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            textColor=HexColor('#5DADE2'),
            alignment=1,
            fontName='Helvetica-Oblique'
        )
        
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        notes_style = ParagraphStyle(
            'CustomNotes',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=15,
            textColor=HexColor('#7F8C8D'),
            leftIndent=20,
            fontName='Helvetica-Oblique'
        )
        
        takeaway_style = ParagraphStyle(
            'CustomTakeaway',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=15,
            textColor=HexColor('#E67E22'),
            leftIndent=20,
            fontName='Helvetica-Bold'
        )
        
        story = []
        
        # Title page
        story.append(Paragraph("AI Generated Presentation", title_style))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Professional Slide Deck", subtitle_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Total Slides: {len(slides_data.get('slides', []))}", styles['Normal']))
        story.append(PageBreak())
        
        # Table of contents
        story.append(Paragraph("Table of Contents", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        for i, slide in enumerate(slides_data.get('slides', [])):
            story.append(Paragraph(f"{i+1}. {slide.get('title', 'Untitled')}", styles['Normal']))
        
        story.append(PageBreak())
        
        # Individual slides
        for i, slide in enumerate(slides_data.get('slides', [])):
            # Slide number and title
            story.append(Paragraph(f"Slide {i+1}", styles['Heading3']))
            story.append(Paragraph(slide.get('title', 'Untitled'), title_style))
            
            # Subtitle
            if slide.get('subtitle'):
                story.append(Paragraph(slide.get('subtitle'), subtitle_style))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Bullet points
            if slide.get('bullet_points'):
                story.append(Paragraph("Key Points:", styles['Heading3']))
                for bullet in slide.get('bullet_points', []):
                    story.append(Paragraph(f"• {bullet}", bullet_style))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Key takeaway
            if slide.get('key_takeaway'):
                story.append(Paragraph("🎯 Key Takeaway:", styles['Heading3']))
                story.append(Paragraph(slide.get('key_takeaway'), takeaway_style))
                story.append(Spacer(1, 0.2*inch))
            
            # Speaker notes
            if slide.get('speaker_notes'):
                story.append(Paragraph("📝 Speaker Notes:", styles['Heading3']))
                story.append(Paragraph(slide.get('speaker_notes'), notes_style))
            
            # Slide metadata
            if slide.get('visual_theme') or slide.get('slide_type'):
                story.append(Spacer(1, 0.1*inch))
                metadata = []
                if slide.get('slide_type'):
                    metadata.append(f"Type: {slide.get('slide_type')}")
                if slide.get('visual_theme'):
                    metadata.append(f"Theme: {slide.get('visual_theme')}")
                story.append(Paragraph(" | ".join(metadata), styles['Normal']))
            
            story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        logger.info(f"PDF created successfully: {temp_path}")
        
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating PDF: {e}")

# --- AI Prompt Engineering and API Call ---
async def call_ai_model(prompt: str, expect_json: bool = True) -> dict:
    """
    Calls the free-tier Gemini API asynchronously.
    """
    if not model:
        raise HTTPException(
            status_code=503, 
            detail="AI service is not configured. Check server logs for API key errors."
        )
    try:
        logger.info("Sending request to Google Gemini API...")
        response = await model.generate_content_async(prompt)
        logger.info("Received valid JSON response from Gemini API.")
        return json.loads(response.text)
        
    except Exception as e:
        error_msg = f"Error calling Google Gemini API or parsing its response: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Praxis AI Backend (Full Enhanced Edition) is running!"}

@app.get("/features-status/")
def get_features_status():
    """Check which features are available"""
    return {
        "pdf_generation": True,
        "image_generation": True,
        "html_generation": True,
        "visual_slides": True,
        "enhanced_prompts": True
    }

@app.post("/process-content/")
async def process_content(file: UploadFile = File(...)):
    content_for_ai = ""
    filename = file.filename
    content_bytes = await file.read()

    if filename.lower().endswith('.pdf'):
        try:
            with fitz.open(stream=content_bytes, filetype="pdf") as doc:
                content_for_ai = "".join(page.get_text() for page in doc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading PDF file: {e}")
    elif filename.lower().endswith('.txt'):
        content_for_ai = content_bytes.decode('utf-8')
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    if not content_for_ai.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty or contains no text.")

    system_prompt = "You are an expert instructional designer. Your entire response must be a single, valid JSON object."
    user_prompt = f"""
    Based on the text provided below, generate a JSON object with a single key "slide_topics", which is a list of 6-8 logical, concise slide titles.

    Text:
    ---
    {content_for_ai[:8000]}
    ---
    """
    
    ai_response = await call_ai_model(f"{system_prompt}\n\n{user_prompt}")
    
    return {
        "status": "success",
        "summary": f"Processed '{filename}'",
        "slide_topics": ai_response.get("slide_topics", []),
        "full_content": content_for_ai
    }

@app.post("/generate-detailed-slides/")
async def generate_detailed_slides(content: str = Form(...)):
    system_prompt = """You are an expert instructional designer creating engaging, visually-focused presentations. 
    Your entire response must be a single, valid JSON object."""
    
    user_prompt = f"""
    Based on the text below, generate a detailed, engaging slide deck optimized for visual presentation.
    
    The output must be a JSON object with a single key "slides".
    Each slide object must have these keys:
    1. "title" (string): A compelling, concise title (max 8 words)
    2. "subtitle" (string): An engaging subtitle or tagline (max 12 words)
    3. "bullet_points" (list): 3-4 impactful bullet points (each max 15 words)
    4. "speaker_notes" (string): Detailed presenter notes (2-3 sentences)
    5. "visual_theme" (string): Suggested visual theme (e.g., "modern tech", "nature", "business professional")
    6. "key_takeaway" (string): Main message for the slide (max 20 words)
    7. "slide_type" (string): Type of slide ("title", "content", "comparison", "conclusion", etc.)
    8. "color_scheme" (string): One of: "blue", "orange", "green", "purple", "gray"

    Make the content:
    - Visually engaging and memorable
    - Easy to understand at a glance
    - Professionally structured
    - Action-oriented with strong verbs
    - Include relevant statistics or examples where possible

    Text:
    ---
    {content[:8000]}
    ---
    """
    
    ai_response = await call_ai_model(f"{system_prompt}\n\n{user_prompt}")
    
    # Generate images for each slide
    enhanced_slides = []
    for i, slide in enumerate(ai_response.get('slides', [])):
        logger.info(f"Generating image for slide {i+1}: {slide.get('title', 'Untitled')}")
        
        # Generate slide image
        slide_image = await generate_slide_image(
            slide.get('title', 'Untitled'),
            slide.get('bullet_points', []),
            slide.get('color_scheme', 'blue')
        )
        
        # Add image data to slide
        slide['image_base64'] = slide_image
        enhanced_slides.append(slide)
    
    return {
        "slides": enhanced_slides,
        "total_slides": len(enhanced_slides),
        "presentation_theme": "Professional & Engaging"
    }

@app.post("/download-slides-pdf/")
async def download_slides_pdf(slides_json: str = Form(...)):
    """
    Generate and download PDF of slides
    """
    try:
        slides_data = json.loads(slides_json)
        pdf_path = await create_slide_pdf(slides_data)
        
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=f"presentation_slides_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error in download_slides_pdf: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {e}")

@app.post("/generate-quiz/")
async def generate_quiz(content: str = Form(...)):
    system_prompt = "You are a helpful teaching assistant who creates engaging quizzes. Your entire response must be a single, valid JSON object."
    user_prompt = f"""
    Based on the text below, generate an engaging 5-question multiple-choice quiz. 
    The output must be a JSON object with a single key "quiz".
    Each question object must have: "question" (string), "options" (4 strings), "answer" (string), and "explanation" (string).

    Text:
    ---
    {content[:8000]}
    ---
    """
    return await call_ai_model(f"{system_prompt}\n\n{user_prompt}")

@app.post("/generate-exam/")
async def generate_exam(content: str = Form(...)):
    system_prompt = "You are an expert educator designing a comprehensive final exam. Your entire response must be a single, valid JSON object."
    user_prompt = f"""
    Based on the text below, generate a comprehensive exam.
    The output must be a JSON object with a single key "exam".
    The exam should have "multiple_choice" (5 questions) and "short_answer" (3 questions) sections.
    Each multiple choice question needs: "question", "options", "answer", "explanation".
    Each short answer question needs: "question", "points", "sample_answer".

    Text:
    ---
    {content[:8000]}
    ---
    """
    return await call_ai_model(f"{system_prompt}\n\n{user_prompt}")

@app.post("/generate-announcement/")
async def generate_announcement(content: str = Form(...)):
    system_prompt = "You are a teacher creating engaging announcements. Your entire response must be a single, valid JSON object."
    user_prompt = f"""
    Based on the key topics in the text below, create an exciting announcement for students.
    The output must be a JSON object with keys: "announcement_text", "emoji", "call_to_action".

    Text:
    ---
    {content[:8000]}
    ---
    """
    return await call_ai_model(f"{system_prompt}\n\n{user_prompt}")