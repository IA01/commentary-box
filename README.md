# Cricket Commentary Website Analyzer 🏏

A fun and entertaining web application that analyzes websites with cricket commentary-style analysis, featuring distinct personalities of famous cricket commentators.

## Features

- Website content analysis with cricket-style commentary
- Three distinct commentator personalities:
  - Ravi's Roast 🔥 - Playful criticism with signature phrases
  - Bhogle's Balance ❄️ - Balanced and analytical insights
  - Jatin's Jubilation ⚡ - Ultra-positive and high-energy takes
- Modern, cricket-themed UI with pop-out analysis display
- Support for various website types (articles, portfolios, e-commerce, etc.)

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion

### Backend
- FastAPI
- BeautifulSoup4
- OpenAI API
- Python Request

## Setup

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables

Create a `.env` file in the backend directory:
```
OPENAI_API_KEY=your_api_key_here
```

## Development

1. Start the backend server
2. Start the frontend development server
3. Visit http://localhost:3000

## License

MIT
