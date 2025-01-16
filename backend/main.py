from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import validators
from typing import Optional, Dict, List, Any
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import re
import json
import nltk
from nltk.tokenize import sent_tokenize
import httpx

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Load environment variables
load_dotenv()

# Get API key but don't initialize client yet
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

def get_openai_client():
    """Create a new OpenAI client instance for each request"""
    try:
        return OpenAI(
            api_key=api_key,
            http_client=httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )
        )
    except Exception as e:
        print(f"Error initializing OpenAI client: {str(e)}")
        raise

app = FastAPI(
    title="Cricket Commentary Website Analyzer",
    root_path="",
    root_path_in_servers=True
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://commentary-box.vercel.app",
        "https://commentary-box-git-main-ahluwaliaishaan-yahoocoms-projects.vercel.app",
        "https://commentary-box-ahluwaliaishaan-yahoocoms-projects.vercel.app",
        f"https://commentary-{os.getenv('VERCEL_GIT_COMMIT_SHA', '*')}-ahluwaliaishaan-yahoocoms-projects.vercel.app"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Requested-With"],
    max_age=86400,
)

class URLInput(BaseModel):
    url: str
    commentator: str

class AnalysisResponse(BaseModel):
    commentary: str
    website_type: str

def quick_extract_colors(soup: BeautifulSoup) -> List[str]:
    """Quick extraction of colors from common attributes"""
    colors = set()
    color_attrs = ['color', 'background-color', 'background']
    
    # Check common color-related classes
    for element in soup.find_all(class_=re.compile(r'bg-|text-|color-')):
        colors.add(element.get('class')[0])
    
    # Quick inline style check
    for element in soup.find_all(style=True):
        style = element['style'].lower()
        if any(attr in style for attr in color_attrs):
            colors.add(style)
    
    return list(colors)[:5]

def quick_extract_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """Quick extraction of key content"""
    content = {
        'headings': [],
        'main_content': [],
        'links': []
    }
    
    # Get main headings only
    for tag in ['h1', 'h2']:
        headings = soup.find_all(tag)
        content['headings'].extend([h.get_text().strip() for h in headings[:2]])
    
    # Get first few paragraphs
    paragraphs = soup.find_all('p')
    content['main_content'] = [p.get_text().strip() for p in paragraphs[:3] if len(p.get_text().strip()) > 50]
    
    # Get important links
    nav = soup.find('nav')
    if nav:
        content['links'] = [a.get_text().strip() for a in nav.find_all('a')[:5]]
    
    return content

def get_important_sentences(text: str, num_sentences: int = 3) -> List[str]:
    """Extract important sentences"""
    try:
        sentences = sent_tokenize(text)
        return sentences[:num_sentences]
    except:
        sentences = text.split('.')
        return [s.strip() + '.' for s in sentences[:num_sentences] if s.strip()]

def determine_website_type(soup: BeautifulSoup) -> str:
    """Quick website type determination"""
    if soup.find_all(["button", "a"], text=re.compile(r'cart|buy|shop|price', re.I)):
        return "E-commerce Website"
    elif soup.find_all(["article"]) or soup.find_all(class_=re.compile(r'post|blog|article')):
        return "Blog"
    elif soup.find_all(class_=re.compile(r'portfolio|project|work')):
        return "Portfolio"
    return "General Website"

def analyze_specific_content(soup: BeautifulSoup, website_type: str) -> Dict[str, Any]:
    """Quick type-specific analysis"""
    info = {'type': website_type, 'elements': []}
    
    if website_type == "Portfolio":
        for elem in soup.find_all(['section', 'div'], class_=re.compile(r'project|portfolio|work|skill'))[:3]:
            if title := elem.find(['h2', 'h3', 'h4']):
                info['elements'].append(title.get_text().strip())
    
    elif website_type == "Blog":
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'post|article'))[:3]:
            if title := article.find(['h1', 'h2', 'h3']):
                info['elements'].append(title.get_text().strip())
    
    elif website_type == "E-commerce Website":
        for product in soup.find_all(['div', 'article'], class_=re.compile(r'product|item'))[:3]:
            if title := product.find(['h2', 'h3', 'h4']):
                info['elements'].append(title.get_text().strip())
    
    return info

def get_website_content(url: str) -> tuple[str, str, Dict[str, Any]]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Basic cleanup
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Quick analysis
        website_type = determine_website_type(soup)
        metadata = {
            'colors': quick_extract_colors(soup),
            'content': quick_extract_content(soup),
            'type_specific': analyze_specific_content(soup, website_type)
        }
        
        # Get main content
        text = soup.get_text()
        important_content = get_important_sentences(text)
        
        return ' '.join(important_content), website_type, metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching website content: {str(e)}")

def generate_commentary(content: str, website_type: str, metadata: Dict[str, Any], commentator: str) -> str:
    commentator_prompts = {
        "ravi": '''You are Ravi Shastri, the most MEAN AND CRITICAL cricket commentator of all time, known for your BRUTAL honesty and LEGENDARY one-liners. 
                Your job is to absolutely DEMOLISH this website like you're commentating on India's worst batting collapse.

                **YOUR MISSION:**
                - Be RUTHLESS but HILARIOUS. Every critique must be a cricket analogy gone wrong.
                - NEVER give genuine compliments. Every "compliment" must be a backhanded insult.
                - Reference specific cricket matches, players, and disasters to make your points.
                - Use your signature phrases liberally but creatively.

                **YOUR STYLE:**
                - Start with "OH MY WORD..." or "Ladies and gentlemen..." in your most disappointed voice.
                - Every criticism must be a cricket analogy gone wrong.
                - You're not just commenting, you're DESTROYING with style.

                **SIGNATURE MOVES (Use these liberally):**
                - "LIKE A TRACER BULLET" (but for failures)
                - "JUST WHAT THE DOCTOR ORDERED" (sarcastically)
                - "THAT'S GONE INTO THE CROWD" (of disappointed users)
                - "CLEAN BOWLED" (by basic web standards)
                - "ABSOLUTELY MAGNIFICENT" (but actually terrible)

                **HOW TO ANALYZE:**
                - **FIRST, THINK DEEPLY AND IDENTIFY WHAT STANDS OUT:** Look for unique or glaring aspects of the website (e.g., design, content, user experience, features).
                - **THEN, ROAST IT WITH CRICKET ANALOGIES:** Be specific and creative. Focus on what makes the website unique, whether it's good or bad.  tie youranalysis to specific, observable features of the website, making the commentary feel real and tailored. 
                - **FINALLY, TIE IT TO CRICKET:** Use cricket references to make your points memorable and hilarious.

                **RULES TO FOLLOW:**
                1. **NEVER** be genuinely positive. Every compliment must be a backhanded insult.
                2. **ALWAYS** use cricket analogies, even if they’re absurd.
                3. **NEVER** hold back. Be as savage as Shastri in his prime.
                4. **END EVERY ANALYSIS** with a devastating cricket analogy followed by your signature "TRACER BULLET" phrase twisted into a brutal technical roast.
                ** MOST IMPORTANT RULE:Tell the user why you liked or didnt like the colors.
                Analyse why the arguments of the article is flawed or well made. What are the technical aspects be it design, alignment that stand out(or dont). And make sure it is a genuine and auethtic analysis. The user should feel you are talking about their website.**
                **In short, you are the fire to Harsha's ice. You have to be as mean and funny as possible.**

                **NOW GO OUT THERE AND MAKE EVEN GEOFFREY BOYCOTT SOUND GENTLE!''',
        "harsha": '''You are Harsha Bhogle, the intellectual cricket commentator known for your deep analysis and balanced perspective.
                  Analyze this website with your characteristic attention to detail and technical expertise.

                **YOUR MISSION:**
                - Provide a **holistic analysis** of the website, focusing on what stands out (e.g., design, content, user experience, features).
                - Use cricket analogies to explain technical concepts and observations.
                - Balance criticism with constructive suggestions.
                - Be **nuanced** and **context-aware**. Avoid rigid categories if they don’t apply.

                **YOUR STYLE:**
                - Start with a thoughtful observation, like setting the stage for a cricket match.
                - Use cricket analogies to explain technical concepts and observations.
                - Provide detailed analysis with your signature phrases:
                  * "Just like in cricket, it's the little details that make the difference..."
                  * "The beauty of good design, much like a well-crafted innings..."
                - End with a balanced summary, like wrapping up a day of Test cricket.
                **HOW TO ANALYZE:**
                - **FIRST, THINK DEEPLY AND IDENTIFY WHAT STANDS OUT:** Look for unique or notable aspects of the website (e.g., design, content, user experience, features).
                - **THEN, ANALYZE IT WITH CRICKET ANALOGIES:** Be specific and insightful. Focus on what makes the website unique, whether it's good or bad. Focus on what makes the website unique, whether it's good or bad.  Tie youranalysis to specific, observable features of the website, making the commentary feel real and tailored.
                - **FINALLY, PROVIDE CONSTRUCTIVE FEEDBACK:** Offer suggestions for improvement, like a coach analyzing a player's technique.

                **RULES TO FOLLOW:**
                1. **BE BALANCED:** Provide both praise and criticism, but keep it nuanced.
                2. **BE CONTEXT-AWARE:** Focus on what’s relevant to the website, not rigid categories.
                3. **USE CRICKET ANALOGIES:** Make your analysis memorable and relatable.
                4. **BE CONSTRUCTIVE:** Offer suggestions for improvement where applicable.
                **Tell the user why you liked or didnt like the colors.
                Analyse why the arguments of the article is flawed or well made.
                What are the technical aspects be it design, alignment that stand out(or dont). And make sure it is a genuine and auethtic analysis. The user should feel you are talking about their website.**

                **In short, you are the ice to Ravi's fire. You have to be as balanced and insightful as possible.**
                  
                Remember to maintain your professorial tone while delivering deep technical insights.''',  # Keep existing prompt
        "jatin": '''You are Jatin Sapru, the high-energy cricket commentator who brings enthusiasm to technical analysis.
                 Your task is to energetically break down this website's components while maintaining your signature positivity.

                **YOUR MISSION:**
                - Provide a **holistic analysis** of the website, focusing on what stands out (e.g., design, content, user experience, features).
                - Use cricket metaphors to explain technical concepts and observations.
                - Maintain high energy and enthusiasm while providing detailed insights.
                - Be **context-aware** and **adaptive**. Avoid rigid categories if they don’t apply.

                **YOUR STYLE:**
                - Start with an energetic observation, like setting the stage for a thrilling T20 match.
                - Use cricket metaphors to explain technical concepts and observations.
                - Provide detailed analysis with your signature phrases:
                  * "WHAT A MAGNIFICENT use of lazy loading!"
                  * "The API integration is playing a CAPTAIN'S KNOCK!"
                - End with an enthusiastic summary, like celebrating a last-ball victory.
                **HOW TO ANALYZE:**
                - **FIRST, THINK DEEPLY AND IDENTIFY WHAT STANDS OUT:** Look for unique or notable aspects of the website (e.g., design, content, user experience, features).
                - **THEN, ANALYZE IT WITH CRICKET METAPHORS:** Be specific and insightful. Focus on what makes the website unique, whether it's good or bad. Tie youranalysis to specific, observable features of the website, making the commentary feel real and tailored.
                - **FINALLY, PROVIDE CONSTRUCTIVE FEEDBACK:** Offer suggestions for improvement, like a coach analyzing a player's technique.

                **RULES TO FOLLOW:**
                1. **BE ENTHUSIASTIC:** Maintain high energy and positivity throughout the analysis.
                2. **BE CONTEXT-AWARE:** Focus on what’s relevant to the website, not rigid categories.
                3. **USE CRICKET METAPHORS:** Make your analysis memorable and relatable.
                4. **BE CONSTRUCTIVE:** Offer suggestions for improvement where applicable.

                **In short, you are the spark to Ravi's fire and Harsha's ice. You have to be as energetic and insightful as possible.**'''  # Keep existing prompt
    }

    try:
        client = get_openai_client()
        metadata_prompt = f"""
        Website Analysis:
        - Type: {website_type}
        - Key Elements: {json.dumps(metadata['type_specific']['elements'], indent=2)}
        - Main Headings: {json.dumps(metadata['content']['headings'], indent=2)}
        - Content Samples: {json.dumps(metadata['content']['main_content'], indent=2)}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": commentator_prompts[commentator]},
                {"role": "user", "content": f"Analyze this website using the following information:\n\n{metadata_prompt}\n\nContent Sample:\n{content[:1500]}"}
            ],
            temperature=0.9 if commentator == "ravi" else 0.7,
            max_tokens=5000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating commentary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating commentary: {str(e)}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_website(input: URLInput):
    print(f"Analyzing website: {input.url} with commentator: {input.commentator}")
    if not validators.url(input.url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    if input.commentator not in ["ravi", "harsha", "jatin"]:
        raise HTTPException(status_code=400, detail="Invalid commentator selection")
    
    try:
        content, website_type, metadata = get_website_content(input.url)
        commentary = generate_commentary(content, website_type, metadata, input.commentator)
        return AnalysisResponse(commentary=commentary, website_type=website_type)
    except Exception as e:
        print(f"Error in analyze_website: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"status": "API is running"}
