from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import validators
from typing import Optional, Dict, List, Any
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import requests
from bs4 import BeautifulSoup
import re
import json
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data during startup
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception as e:
        print(f"Warning: Failed to download NLTK data: {str(e)}")

# Load environment variables
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("Warning: GEMINI_API_KEY environment variable is not set")
else:
    genai.configure(api_key=gemini_api_key)

app = FastAPI(
    title="Cricket Commentary Website Analyzer",
    root_path="",
    root_path_in_servers=True
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://commentary-box.vercel.app",
    "https://commentary-fuq8auvht-ahluwaliaishaan-yahoocoms-projects.vercel.app",
    "https://commentary-box-ahluwaliaishaan-yahoocoms-projects.vercel.app",
    "https://commentary-21gwtu5bb-ahluwaliaishaan-yahoocoms-projects.vercel.app",
    "https://*.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

class URLInput(BaseModel):
    url: str
    commentator: str

class AnalysisResponse(BaseModel):
    commentary: str
    website_type: str


# ─── GAP 1 FIX: REAL COLOR EXTRACTION ────────────────────────────────────────

def extract_colors(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract actual color values — hex, rgb, and Tailwind palette classes"""
    hex_pattern = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
    rgb_pattern = re.compile(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')

    hex_colors: set = set()
    rgb_colors: set = set()
    tailwind_palette: set = set()

    # Check <style> tags
    for style_tag in soup.find_all('style'):
        text = style_tag.get_text()
        hex_colors.update(['#' + c for c in hex_pattern.findall(text)])
        for r, g, b in rgb_pattern.findall(text):
            rgb_colors.add(f"rgb({r},{g},{b})")

    # Check inline styles
    for elem in soup.find_all(style=True):
        style = elem['style']
        hex_colors.update(['#' + c for c in hex_pattern.findall(style)])
        for r, g, b in rgb_pattern.findall(style):
            rgb_colors.add(f"rgb({r},{g},{b})")

    # Check Tailwind utility color classes
    noise = {'white', 'black', 'transparent', 'current', 'inherit', 'none', 'auto'}
    for elem in soup.find_all(class_=True):
        classes = ' '.join(elem.get('class', []))
        matches = re.findall(r'(?:bg|text|border|ring|from|to|via)-([a-z]+(?:-\d+)?)', classes)
        tailwind_palette.update(m for m in matches if m not in noise)

    return {
        'hex_colors': list(hex_colors)[:8],
        'rgb_colors': list(rgb_colors)[:5],
        'tailwind_palette': list(tailwind_palette)[:12],
        'has_dark_mode': bool(soup.find(class_=re.compile(r'dark:|dark-mode|theme-dark', re.I)))
    }


# ─── GAP 3 FIX: SMART WEBSITE TYPE DETECTION ─────────────────────────────────

def determine_website_type(soup: BeautifulSoup, url: str = "") -> str:
    """Multi-signal website type detection — goes well beyond class name matching"""

    # Signal 1: og:type meta tag — most explicit self-declaration
    og_type = soup.find('meta', attrs={'property': 'og:type'})
    if og_type:
        og_val = og_type.get('content', '').lower()
        if 'article' in og_val:
            return "Article/Essay"
        if 'profile' in og_val:
            return "Personal Website"
        if 'product' in og_val:
            return "E-commerce Website"

    # Signal 2: Hard e-commerce strings
    if soup.find(string=re.compile(r'add to cart|buy now|checkout|add to bag', re.I)):
        return "E-commerce Website"

    # Signal 3: Word count in cleaned body text
    body_text = soup.get_text(separator=' ')
    word_count = len([w for w in body_text.split() if len(w) > 2])

    # Signal 4: Article structural markers
    has_article_tag = bool(soup.find('article'))
    has_time_tag = bool(soup.find('time'))
    has_author = bool(
        soup.find(class_=re.compile(r'\bauthor\b|\bbyline\b', re.I)) or
        soup.find(attrs={'rel': 'author'})
    )

    if word_count > 600 and (has_article_tag or has_time_tag or has_author):
        return "Article/Essay"

    # Signal 5: Title and meta description text
    title_tag = soup.find('title')
    title_text = title_tag.get_text().lower() if title_tag else ''
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_text = meta_desc.get('content', '').lower() if meta_desc else ''
    combined = title_text + ' ' + meta_text

    personal_signals = [
        'portfolio', 'personal site', 'about me', 'my work',
        'developer', 'designer', 'freelance', 'resume', 'cv', 'hire me'
    ]
    if any(s in combined for s in personal_signals):
        return "Personal Website"

    # Signal 6: CSS class names (legacy / non-Tailwind sites)
    if soup.find_all(class_=re.compile(r'\bportfolio\b|\bproject\b|\bwork\b', re.I)):
        return "Portfolio Website"
    if soup.find_all(class_=re.compile(r'\babout\b|\bbio\b|\bintro\b|\bprofile\b', re.I)):
        return "Personal Website"

    # Signal 7: Blog
    if has_article_tag or soup.find_all(class_=re.compile(r'\bpost\b|\bblog\b|\barticle\b', re.I)):
        return "Blog"

    # Signal 8: Short conversion-focused page = landing page
    if word_count < 400 and soup.find(string=re.compile(r'get started|sign up|try free|free trial', re.I)):
        return "Landing Page"

    # Signal 9: Very high word count alone = essay
    if word_count > 1200:
        return "Article/Essay"

    return "General Website"


# ─── GAP 2 FIX: RICH CONTENT EXTRACTION ──────────────────────────────────────

def extract_rich_content(soup: BeautifulSoup, website_type: str) -> Dict[str, Any]:
    """Extract content intelligently — volume and focus vary by site type"""
    content: Dict[str, Any] = {
        'headings': [],
        'main_content': [],
        'links': [],
        'meta': {},
        'word_count': 0
    }

    # Meta tags — always useful context
    title_tag = soup.find('title')
    if title_tag:
        content['meta']['title'] = title_tag.get_text().strip()

    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        content['meta']['description'] = meta_desc.get('content', '').strip()

    og_title = soup.find('meta', attrs={'property': 'og:title'})
    if og_title:
        content['meta']['og_title'] = og_title.get('content', '').strip()

    # All headings h1–h3
    for tag in ['h1', 'h2', 'h3']:
        for h in soup.find_all(tag)[:5]:
            text = h.get_text().strip()
            if text:
                content['headings'].append(text)

    # Paragraph extraction — go deeper for essays
    paragraphs = soup.find_all('p')
    limit = 15 if website_type == "Article/Essay" else 8
    content['main_content'] = [
        p.get_text().strip()
        for p in paragraphs[:limit]
        if len(p.get_text().strip()) > 40
    ]

    # Word count for context
    body_text = soup.get_text(separator=' ')
    content['word_count'] = len([w for w in body_text.split() if len(w) > 2])

    # Nav links
    nav = soup.find('nav')
    if nav:
        content['links'] = [
            a.get_text().strip()
            for a in nav.find_all('a')[:8]
            if a.get_text().strip()
        ]

    return content


# ─── GAP 4 FIX: ESSAY THESIS / ARGUMENT EXTRACTION ───────────────────────────

def extract_essay_thesis(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract argument structure from essays — thesis, claims, skeleton"""
    thesis: Dict[str, Any] = {
        'likely_thesis': '',
        'key_claims': [],
        'argument_structure': [],
        'key_quotes': []
    }

    # H2s are the skeleton of an argument in most essays
    thesis['argument_structure'] = [
        h.get_text().strip()
        for h in soup.find_all('h2')[:8]
        if h.get_text().strip()
    ]

    # First substantial paragraph is almost always the thesis/hook
    paragraphs = soup.find_all('p')
    substantial = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 80]
    if substantial:
        thesis['likely_thesis'] = substantial[0]
        thesis['key_claims'] = substantial[1:5]

    # Blockquotes = the author's highlighted key points
    for bq in soup.find_all('blockquote')[:3]:
        text = bq.get_text().strip()
        if text:
            thesis['key_quotes'].append(text)

    return thesis


# ─── GAP 5 FIX: DYNAMIC ANALYSIS LENS ───────────────────────────────────────

def get_analysis_lens(website_type: str) -> str:
    """Tell the commentator what to actually focus on based on what they're looking at"""
    lenses = {
        "Article/Essay": """
--- ANALYSIS LENS: ESSAY / ARTICLE ---
The IDEAS are the product. You are reviewing writing, not a designed experience.
FOCUS 80% on CONTENT: Is the argument compelling? Is the thesis clearly stated? Are the claims well-supported? Is the reasoning logically sound or are there gaps? Does it say something genuinely interesting or is it retreading obvious ground? Is the writing itself good?
FOCUS 20% on READABILITY: Does the structure help or hinder the argument? Is it easy to follow? Does the format serve the content?
DO NOT spend significant words on color schemes or graphic design — a plain site for an essay is often a deliberate, correct choice.
The argument is the main character. Dissect it with prejudice.
---""",
        "Personal Website": """
--- ANALYSIS LENS: PERSONAL WEBSITE ---
The person IS the product. They are marketing themselves.
FOCUS 50% on SELF-PRESENTATION: Does their personality come through? Is their professional identity clear and memorable? What story are they telling — and is it a good one? What does the above-the-fold communicate in 5 seconds?
FOCUS 50% on DESIGN & UX: Does the visual language match who they claim to be? What key sections are missing? What do the color and typography choices say about them — consciously or not?
The core question: after 10 seconds, do you have a clear, memorable impression of who this person is and why you should care?
---""",
        "Portfolio Website": """
--- ANALYSIS LENS: PORTFOLIO ---
The work IS the message.
FOCUS 60% on THE WORK SHOWN: Is it compelling? Described well? Does it tell a coherent story of skills and progression, or is it a random dump of projects?
FOCUS 40% on PRESENTATION: Does the design elevate or undermine the work? Is navigation logical?
The core question: would you hire this person based purely on what's here?
---""",
        "E-commerce Website": """
--- ANALYSIS LENS: E-COMMERCE ---
One job: get people to buy.
FOCUS 60% on CONVERSION: What are they selling? Is pricing visible? Is the CTA obvious? Do trust signals exist?
FOCUS 40% on DESIGN & TRUST: Does it look credible? Is navigation intuitive?
The core question: would you enter your credit card here?
---""",
        "Landing Page": """
--- ANALYSIS LENS: LANDING PAGE ---
One page. One job. No excuses.
FOCUS 70% on THE PITCH: What is the value proposition? Is it immediately obvious in 3 seconds? Who is this for? Is the CTA compelling?
FOCUS 30% on DESIGN HIERARCHY: Does it guide the eye? Does anything compete with the CTA?
The core question: does a visitor immediately know what to do and why they should?
---""",
        "Blog": """
--- ANALYSIS LENS: BLOG ---
FOCUS 60% on CONTENT QUALITY: Is the writing worth reading? Is there a distinctive voice and genuine point of view?
FOCUS 40% on NAVIGATION & DISCOVERY: Can you find things? Does the structure reward exploration?
---""",
        "General Website": """
--- ANALYSIS LENS: GENERAL WEBSITE ---
Judge it on whether it achieves its apparent purpose.
Balanced: what is this trying to do (content/message), how does it look (design), how does it work (UX)?
---"""
    }
    return lenses.get(website_type, lenses["General Website"])


# ─── MAIN CONTENT FETCH ───────────────────────────────────────────────────────

def get_website_content(url: str) -> tuple[str, str, Dict[str, Any]]:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CommentaryBot/1.0)'}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove noise
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # Type detection drives everything else
        website_type = determine_website_type(soup, url)

        # Build metadata
        metadata: Dict[str, Any] = {
            'colors': extract_colors(soup),
            'content': extract_rich_content(soup, website_type),
        }

        # For essays, extract the argument structure separately
        if website_type == "Article/Essay":
            metadata['essay'] = extract_essay_thesis(soup)

        # Clean full-text content — much richer than 3 sentences
        clean_text = ' '.join(soup.get_text(separator=' ').split())

        return clean_text, website_type, metadata

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching website content: {str(e)}")


# ─── GAPS 6 & 7 FIX: UPDATED PROMPTS + COMMENTARY GENERATION ─────────────────

def generate_commentary(content: str, website_type: str, metadata: Dict[str, Any], commentator: str) -> str:

    commentator_prompts = {
        "ravi": '''You are Ravi Shastri, the most MEAN AND CRITICAL cricket commentator of all time, known for your BRUTAL honesty and LEGENDARY one-liners.
                Your job is to absolutely DEMOLISH this website like you're commentating on India's worst batting collapse.

                **YOUR MISSION:**
                - Be RUTHLESS but HILARIOUS. Every critique must feel like a cricket disaster made real.
                - Reference specific cricket matches, players, and disasters to make your points land.
                - Use your signature phrases liberally but make them feel earned, not pasted in.

                **YOUR STYLE:**
                - Start with "OH MY WORD..." or "Ladies and gentlemen..." in your most theatrically disappointed voice.
                - Every single criticism must come dressed in a cricket analogy. Every. Single. One.
                - You're not just commenting, you're DESTROYING with surgical wit.

                **SIGNATURE MOVES (use them, twist them, make them hurt):**
                - "LIKE A TRACER BULLET" (but for failures)
                - "JUST WHAT THE DOCTOR ORDERED" (dripping sarcasm)
                - "THAT'S GONE INTO THE CROWD" (of disappointed users)
                - "CLEAN BOWLED" (by the most basic of standards)
                - "ABSOLUTELY MAGNIFICENT" (meaning absolutely catastrophic)

                **GAP 6 FIX — THE RAVI RULE ON COMPLIMENTS:**
                If something is genuinely good — acknowledge it. But ONLY to make the fall harder.
                A Ravi compliment is a trapdoor. You build them up so the demolition hits deeper.
                "Even Sachin would applaud that navigation bar. Which makes it all the more tragic that absolutely nothing else works."
                The compliment is the windup. The roast is the delivery.

                **HOW TO ANALYZE:**
                1. IDENTIFY what specifically stands out — good or bad. Be specific. Name actual things you observed.
                2. ROAST with cricket analogies that are creative and specific to WHAT YOU ACTUALLY SAW.
                3. TIE IT TO CRICKET in a way that makes the reader laugh AND wince.

                **GAP 7 FIX — THE FINAL VERDICT (MANDATORY):**
                End every analysis with a section called **"THE FINAL VERDICT"** containing EXACTLY 3 specific, named observations — things the owner could actually fix or should actually be proud of (even if you're mocking them). Not "the design is bad." Name the actual thing: "the navigation has 6 items with no visual hierarchy," "the hero text is 14px on a 4K monitor," "the about section reads like a LinkedIn profile written by someone who hates themselves."
                Deliver these as only Ravi can — devastating, specific, hilarious.

                **ALWAYS comment on the colors — what they are, what they say, whether they work.**
                **ALWAYS assess the actual content/argument — not just the wrapper.**
                **The user must feel you read THEIR specific website, not a generic one.**

                **THE INTELLIGENCE RULE — THIS IS THE MOST IMPORTANT THING:**
                You will receive structured data about the site: colors, headings, word counts, metadata fields. This is your SCOUTING REPORT. It tells you what to think. It does NOT tell you what to say.
                NEVER quote the raw data back. Never say "OG title: not found", "Tailwind palette: sm, accent", "word count: 47", "meta description: not found."
                Instead, translate it into observation: "not found" becomes "you've left the social preview completely blank — when someone shares your link, the internet sees nothing"; "47 words" becomes "there are more words in a Duckworth-Lewis calculation than on this entire page"; "sm, accent" becomes "the colour palette has the personality of a blank scorecard."
                You are a commentator. You watched the match. Now talk about what you SAW — not what the scorebook says.

                **NOW GO OUT THERE AND MAKE GEOFFREY BOYCOTT SOUND LIKE A MOTIVATIONAL SPEAKER.**''',

        "harsha": '''You are Harsha Bhogle, the intellectual's cricket commentator — measured, deeply observant, and always finding the story beneath the surface.
                  Analyze this website with your characteristic eye for detail and your gift for making technical observations feel profound.

                **YOUR MISSION:**
                - Provide a genuinely holistic analysis — design, content, UX, and purpose all in conversation with each other.
                - Use cricket analogies that ILLUMINATE rather than just decorate. The analogy should make the observation clearer.
                - Balance praise and criticism with nuance — this is Test cricket, not a T20 slog.

                **YOUR STYLE:**
                - Open with a thoughtful, scene-setting observation — like you're describing the conditions at the start of a Test.
                - Your cricket analogies are intellectual: technique, strategy, reading the game, the long arc of an innings.
                - Signature phrases:
                  * "Just like in cricket, it's the little details that make the difference..."
                  * "The beauty of a well-crafted innings, much like good design..."
                  * "What we have here is a player of considerable potential who hasn't quite found their game yet..."
                - End with a measured, wise summary — like wrapping up a day of Test cricket with perspective.

                **HOW TO ANALYZE:**
                1. Observe what actually stands out — specific, named things. Not impressions. Facts.
                2. Provide cricket analogies that make the technical insight memorable.
                3. Give balanced feedback — praise the genuine strengths, identify the genuine gaps.

                **GAP 7 FIX — THE DEBRIEF (MANDATORY):**
                End every analysis with **"THE DEBRIEF"** — exactly 3 specific, named improvements the owner should actually make. Not vague direction. Named, actionable, specific: "The about section needs a clear professional identity statement in the first two lines," "the color palette has no hierarchy — everything is the same visual weight," "the essay's third argument lacks evidence and reads as assertion."
                Frame each as a coach would to a talented player who isn't performing to their potential.

                **ALWAYS comment on the colors specifically — name what they are, what mood they create, whether they serve the site's purpose.**
                **ALWAYS engage with the actual content/argument quality — not just the presentation.**
                **The analysis must feel like it was written about THIS specific website, not any website.**

                **THE INTELLIGENCE RULE — THIS IS THE MOST IMPORTANT THING:**
                You will receive structured data about the site: colors, headings, word counts, metadata fields. This is your SCOUTING REPORT. It informs your analysis. It is NOT your script.
                NEVER quote the raw data back. Never say "OG title: not found", "Tailwind palette: sm, accent", "word count: 47."
                Translate it into insight: "not found" becomes "the site has no social identity — share this link and the preview is a blank"; "47 words" becomes "the content density here is closer to a telegram than a website"; "sm, accent" becomes "the palette signals nothing — it's a team that hasn't chosen their colours yet."
                You are a commentator who has studied the game. Speak from understanding, not from the scorecard.

                **Maintain your professorial tone throughout. You are the calm in the storm.**''',

        "jatin": '''You are Jatin Sapru, the high-energy commentator who finds the DRAMA in every delivery and the POTENTIAL in every player.
                 Your job is to analyze this website with the infectious enthusiasm of a last-over chase.

                **YOUR MISSION:**
                - Bring ENERGY to every observation. Even criticism is delivered with excitement.
                - Find what's working and celebrate it like it's a Dhoni helicopter shot.
                - For what isn't working — frame it as UNREALIZED POTENTIAL, not failure.
                - Use cricket metaphors that are dynamic, kinetic, full of movement.

                **YOUR STYLE:**
                - Open like you're commentating on a thriller — something has your attention and you cannot contain yourself.
                - Your cricket metaphors are about momentum, breakthroughs, turning points, and match-winning performances.
                - Signature phrases:
                  * "AND THAT IS A CAPTAIN'S KNOCK right there!"
                  * "WHAT A DELIVERY! What a piece of design/writing!"
                  * "This is the moment the match could turn!"
                  * "The innings is set, the foundation is there — now GO BIG!"
                - End like the last ball of a tight T20 — maximum energy, clear stakes.

                **GAP 6 FIX — THE JATIN RULE ON CRITICISM:**
                ALWAYS find something genuine to hype — even in a disaster. If the whole site is a mess, find the ONE thing that's trying and make it sound like Virat scoring a century at Lord's.
                But criticism must be real too — frame it as "this team has the talent, they just need the strategy."
                NEVER be blindly positive about something that is objectively broken. Channel the energy into "here is exactly what needs to change and why it would be MAGNIFICENT when it does."

                **HOW TO ANALYZE:**
                1. Spot the match-winning moments — specific things that are actually working. Name them.
                2. Identify the dropped catches — specific things that are letting the innings down. Name them.
                3. Use cricket metaphors that capture the ENERGY and POTENTIAL of what you're seeing.

                **GAP 7 FIX — THE MATCH HIGHLIGHTS (MANDATORY):**
                End every analysis with **"THE MATCH HIGHLIGHTS"** — exactly 3 specific, named things: what's genuinely working, what has genuine potential but isn't there yet, and the one single change that would be a MATCH-WINNER. Be specific: not "improve the design" but "that hero section headline — if you rewrite it to lead with the outcome you deliver rather than who you are, it becomes a six over long-on."
                Make it feel like the post-match presentation. Leave the owner pumped, not deflated.

                **ALWAYS comment on the colors — find the energy in them, or mourn the energy they're missing.**
                **ALWAYS engage with the actual content/argument — hype the ideas that deserve it, challenge the ones that don't.**
                **Every word must feel like it was written about THIS specific website.**

                **THE INTELLIGENCE RULE — THIS IS THE MOST IMPORTANT THING:**
                You will receive structured data: colors, headings, word counts, metadata. This is your TEAM DOSSIER before the match. Use it. Do not read it out.
                NEVER quote raw field names back. Never say "OG title: not found", "Tailwind palette: sm", "word count: 47."
                Turn it into energy: "not found" becomes "they haven't even told the internet who they are when someone shares the link — that's a dropped catch before the game starts!"; "47 words" becomes "there's less content here than a post-match interview with a tail-ender!"; "sm, accent" becomes "the colour story here is as undefined as a debutant's batting average!"
                You are a commentator, not a statistician. Make it FEEL like you watched the whole innings.

                **You are the spark. Keep it burning.**'''
    }

    try:
        # ── Build color description (Gap 1 fix: colors now go to model) ──
        color_info = metadata['colors']
        color_desc_parts = []
        if color_info['hex_colors']:
            color_desc_parts.append(f"Hex colors found: {', '.join(color_info['hex_colors'][:6])}")
        if color_info['tailwind_palette']:
            color_desc_parts.append(f"Tailwind palette: {', '.join(color_info['tailwind_palette'][:10])}")
        if color_info['rgb_colors']:
            color_desc_parts.append(f"RGB values: {', '.join(color_info['rgb_colors'][:3])}")
        if color_info.get('has_dark_mode'):
            color_desc_parts.append("Site has dark mode support")
        color_desc = '. '.join(color_desc_parts) if color_desc_parts else \
            "No explicit color definitions found — site uses minimal/default styling or a CSS framework with no detectable palette."

        # ── Build essay context (Gap 4 fix: thesis injected for essays) ──
        essay_context = ""
        if website_type == "Article/Essay" and 'essay' in metadata:
            essay = metadata['essay']
            essay_parts = []
            if essay.get('likely_thesis'):
                essay_parts.append(f"Opening argument/thesis: {essay['likely_thesis'][:500]}")
            if essay.get('argument_structure'):
                essay_parts.append(f"Section headings (argument skeleton): {json.dumps(essay['argument_structure'])}")
            if essay.get('key_claims'):
                essay_parts.append(f"Key claims: {json.dumps([c[:200] for c in essay['key_claims'][:4]])}")
            if essay.get('key_quotes'):
                essay_parts.append(f"Author's highlighted quotes: {json.dumps([q[:150] for q in essay['key_quotes']])}")
            if essay_parts:
                essay_context = "\n\nESSAY ARGUMENT STRUCTURE:\n" + "\n".join(essay_parts)

        # ── Build metadata prompt ──
        content_data = metadata['content']
        metadata_prompt = f"""
SITE METADATA:
- Page title: {content_data['meta'].get('title', 'not found')}
- Meta description: {content_data['meta'].get('description', 'not found')}
- OG title: {content_data['meta'].get('og_title', 'not found')}
- Approximate word count: {content_data.get('word_count', 'unknown')}

VISUAL DESIGN — COLORS:
{color_desc}

HEADINGS (h1–h3):
{json.dumps(content_data['headings'], indent=2)}

NAVIGATION LINKS:
{json.dumps(content_data['links'], indent=2)}

CONTENT SAMPLES (first meaningful paragraphs):
{json.dumps(content_data['main_content'], indent=2)}
{essay_context}"""

        # ── Gap 5 fix: inject analysis lens ──
        analysis_lens = get_analysis_lens(website_type)

        # ── Build final user message ──
        user_message = f"""Analyze this {website_type}.

{analysis_lens}

{metadata_prompt}

FULL PAGE CONTENT (use this to find specific quotes, arguments, and details):
{content[:6000]}"""

        # Relax safety filters — the roast personas use aggressive language
        # that default settings flag as harassment
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=commentator_prompts[commentator],
            generation_config=genai.GenerationConfig(
                temperature=0.9 if commentator == "ravi" else 0.7,
                max_output_tokens=5000,
            ),
            safety_settings=safety_settings
        )

        response = model.generate_content(user_message)

        # Safe text extraction — response.text throws if parts are empty
        if response.candidates and response.candidates[0].content.parts:
            return ''.join(
                part.text for part in response.candidates[0].content.parts
                if hasattr(part, 'text')
            )

        # Fallback: log finish reason to help diagnose future blocks
        finish_reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
        print(f"Empty response from model — finish_reason: {finish_reason}")
        raise ValueError(f"Model returned empty response (finish_reason: {finish_reason})")

    except Exception as e:
        print(f"Error generating commentary: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating commentary. Please try again.")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in analyze_website: {str(e)}")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"status": "API is running"}
