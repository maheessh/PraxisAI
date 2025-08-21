# backend/main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
import torch
import json
import fitz # PyMuPDF for reading PDFs
import logging

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. Global State for AI Model ---
class ModelStatus:
    generator = None
    is_ready = False
    error_message = ""

model_status = ModelStatus()

# --- Function to load the model ---
def load_model():
    """Loads the AI model and updates the global status."""
    try:
        logger.info("Starting AI model loading... This may take several minutes and significant memory.")
        
        # --- MODEL CHANGE HERE ---
        # We are switching to a model that is known to work well on CPUs.
        model_id = "microsoft/Phi-3-mini-4k-instruct"

        model_status.generator = pipeline(
            "text-generation",
            model=model_id,
            torch_dtype="auto",
            device_map="auto", # This will now correctly map to the CPU
            trust_remote_code=True, # Required for this model
        )
        model_status.is_ready = True
        logger.info("AI model (Phi-3-mini) loaded successfully!")
    except Exception as e:
        error_msg = f"Error loading AI model: {e}. This can be due to insufficient RAM or an internet issue during download."
        model_status.error_message = error_msg
        logger.error(error_msg)

# --- FastAPI App Initialization ---
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Load the model on application startup."""
    import threading
    threading.Thread(target=load_model).start()

# --- CORS Middleware ---
origins = ["http://localhost", "http://127.0.0.1", "null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AI Prompt Engineering Functions ---
def create_prompt(system_message: str, user_content: str) -> list:
    # Phi-3 uses a slightly different prompt format structure
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content},
    ]
    return messages

def call_ai_model(messages: list, max_tokens: int = 512) -> dict:
    if not model_status.is_ready:
        raise HTTPException(status_code=503, detail=f"AI model is not ready or failed to load. Error: {model_status.error_message}")
    try:
        # We need to apply the chat template for Phi-3
        prompt = model_status.generator.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        outputs = model_status.generator(prompt, max_new_tokens=max_tokens, do_sample=True, temperature=0.4)
        
        generated_text = outputs[0]["generated_text"]
        
        # The response includes the prompt, so we find where the model's answer starts
        answer_start = generated_text.rfind("<|assistant|>")
        if answer_start != -1:
            generated_text = generated_text[answer_start + len("<|assistant|>"):].strip()

        logger.info(f"Raw AI Output: {generated_text}")
        
        json_start = generated_text.find('{')
        json_end = generated_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON object found in the AI response.")
        json_string = generated_text[json_start:json_end]
        return json.loads(json_string)
    except Exception as e:
        logger.error(f"Error in AI call or JSON parsing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process AI response: {e}")

# --- API Endpoints (Unchanged from previous version) ---

@app.get("/")
def read_root():
    return {"message": "Praxis AI Backend is running!"}

@app.get("/status")
def get_status():
    return {"is_ready": model_status.is_ready, "error_message": model_status.error_message}

@app.post("/process-content/")
async def process_content(file: UploadFile = File(...)):
    if not model_status.is_ready:
        raise HTTPException(status_code=503, detail=f"AI model is not ready. Error: {model_status.error_message}")
    content_for_ai = ""
    filename = file.filename
    content_bytes = await file.read()
    if filename.lower().endswith('.pdf'):
        try:
            with fitz.open(stream=content_bytes, filetype="pdf") as doc:
                for page in doc:
                    content_for_ai += page.get_text()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading PDF file: {e}")
    elif filename.lower().endswith('.txt'):
        content_for_ai = content_bytes.decode('utf-8')
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    system_prompt = "You are an expert instructional designer. Analyze the provided text and create a structured lesson plan."
    user_prompt = f"Based on the text below, generate a JSON object with a single key \"slide_topics\", which is a list of 6-8 logical slide titles.\nText:\n---\n{content_for_ai[:4000]}\n---"
    messages = create_prompt(system_prompt, user_prompt)
    ai_response = call_ai_model(messages)
    return {"status": "success", "summary": f"Processed '{filename}'", "slide_topics": ai_response.get("slide_topics", []), "full_content": content_for_ai}

@app.post("/generate-quiz/")
async def generate_quiz(content: str = Form(...)):
    system_prompt = "You are a helpful teaching assistant who creates quizzes."
    user_prompt = f"Based on the text below, generate a 5-question multiple-choice quiz. Provide the output as a JSON object with a key \"quiz\"...\nText:\n---\n{content[:4000]}\n---"
    messages = create_prompt(system_prompt, user_prompt)
    return call_ai_model(messages, max_tokens=1024)

@app.post("/generate-announcement/")
async def generate_announcement(content: str = Form(...)):
    system_prompt = "You are a teacher creating a concise and engaging announcement for students."
    user_prompt = f"Based on the key topics in the text below, write a short, exciting announcement... The output should be a JSON object with a single key \"announcement_text\".\nText:\n---\n{content[:4000]}\n---"
    messages = create_prompt(system_prompt, user_prompt)
    return call_ai_model(messages)
