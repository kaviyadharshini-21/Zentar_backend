import os
import json
import logging
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Simple logger setup
def get_logger(name: str):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger

logger = get_logger(__name__)

def clean_text(text: str) -> str:
    """Clean and format text output from AI models."""
    if not text:
        return ""
    
    # First, try to extract JSON from markdown code blocks
    import re
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        # Remove markdown code blocks if no JSON found
        text = text.replace('```json', '').replace('```', '')
        
        # Try to extract JSON if it's wrapped in other text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
    
    # Remove leading/trailing whitespace and newlines
    text = text.strip()
    
    # Remove any trailing commas and extra whitespace
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    # Handle escaped characters
    text = text.replace('\\n', '\n')
    text = text.replace('\\t', '\t')
    text = text.replace('\\"', '"')
    text = text.replace('\\\\', '\\')
    text = text.replace("\\'", "'")  # Handle escaped apostrophes
    
    return text

def classify_email(subject:str,body:str) -> dict:
    """
    Classify email into one of four categories: Urgent to Respond, For Your Information, Office Work, or Spam.
    """
    prompt_template = PromptTemplate(
        input_variables=["subject", "body"],
        template=("""
You are an AI Email Classifier.  

Your task: Analyze the given email subject and body, then classify it into one of the following categories:  

1. "Urgent to Respond"  
   - Time-sensitive emails requiring immediate reply or action  
   - Examples: deadlines, escalations, critical issues  

2. "For Your Information"  
   - Informational emails that do not require direct response  
   - Examples: announcements, newsletters, updates, FYI messages  

3. "Office Work"  
   - Regular work-related communication  
   - Examples: task assignments, meeting scheduling, reports, project updates  

4. "Spam"  
   - Unwanted, irrelevant, or promotional emails  
   - Examples: ads, phishing attempts, unrelated content  

### Critical Instructions:
- Always classify into exactly **one** of the four categories above.  
- Output must be in **strict JSON** format only.  
- JSON must contain exactly one key `"output"` with the classification string as the value.  
- Do not add explanations or extra text.  

### JSON Output Format:
{{
  "output": "Urgent to Respond"
}}

OR  

{{
  "output": "For Your Information"
}}

OR  

{{
  "output": "Office Work"
}}

OR  

{{
  "output": "Spam"
}}

### Input:
Subject: {subject}  
Body: {body}  

"""
        )
    )

    prompt = prompt_template.format(
        subject=subject,
        body=body
    )

    # Initialize Gemini model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        google_api_key=GEMINI_API_KEY
    )

    raw_output = model.invoke(prompt)

    logger.debug("Raw model output: %s", raw_output)

    # Extract text only
    text_output = str(raw_output)

    # Clean and parse JSON
    cleaned = clean_text(text_output)
    
    # Try to parse the cleaned JSON
    try:
        parsed_json = json.loads(cleaned)
        logger.info("Successfully parsed JSON")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        
        # Try to extract JSON from the raw output more aggressively
        import re
        
        # First, try to extract the content from the Gemini response
        content_match = re.search(r"content='(.*?)'", text_output, re.DOTALL)
        if content_match:
            content = content_match.group(1)
            # Look for JSON between ```json and ``` markers
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    extracted_json = json_match.group(1)
                    # Clean the extracted JSON
                    extracted_json = extracted_json.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace("\\'", "'")
                    # Remove trailing commas
                    extracted_json = re.sub(r',\s*}', '}', extracted_json)
                    extracted_json = re.sub(r',\s*]', ']', extracted_json)
                    return json.loads(extracted_json)
                except json.JSONDecodeError:
                    pass
        
        # Try to find just the JSON object without extra metadata
        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text_output, re.DOTALL)
        if json_match:
            try:
                extracted_json = json_match.group(1)
                # Clean the extracted JSON
                extracted_json = extracted_json.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace("\\'", "'")
                # Remove trailing commas
                extracted_json = re.sub(r',\s*}', '}', extracted_json)
                extracted_json = re.sub(r',\s*]', ']', extracted_json)
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                pass
        
        # If all else fails, return the raw output
        return {"raw_output": cleaned, "error": "Failed to parse JSON"}
