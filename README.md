# 🚀 GMB Pro Tool - Local Business Finder

Professional tool to find and analyze local businesses from Google Maps with pagination support, caching, and real-time website data.

## ✨ Features

- 🔍 **Advanced Search** - Find local businesses by keyword and location
- 📊 **Pagination** - Load more results on demand (up to 60+ businesses)
- ⚡ **Lightning Fast** - Built-in caching for instant repeat searches
- 🎨 **Beautiful UI** - Modern gradient design with smooth animations
- 📱 **Responsive** - Works perfectly on desktop and mobile
- 🔐 **Secure** - API key protected with environment variables
- 🌐 **Real Websites** - Fetches actual website links for each business
- ⭐ **Ratings & Reviews** - Shows Google ratings and review counts

## 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Harish225-phr/GMB-TOOL.git
cd GMB-TOOL
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a `.env` file in the project root:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

**Get your API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Places API" and "Maps API"
4. Create an API key credential
5. Copy the key to `.env`

### 5. Run the Application
```bash
python app.py
```

Open your browser and go to: **http://localhost:5000**

## 📖 How to Use

1. **Enter Search Keyword** - What you want to find (e.g., "Restaurant", "Plumber")
2. **Enter Location** - Where to search (e.g., "New York", "Mumbai")
3. **Click Search** - Results load with smooth animation
4. **View Results** - See 20 businesses with ratings and websites
5. **Load More** - Click "Load More Results" to fetch next batch
6. **Repeat Searches** - Second search is instant (cached!)

## 🏗️ Project Structure

```
GMB-TOOL/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── .env                   # API keys (keep secret!)
├── .gitignore            # Hide sensitive files
├── scraper/
│   ├── __init__.py       # Package init
│   └── gmb_scraper.py    # Google Places API wrapper
└── templates/
    └── index.html        # Frontend UI
```

## ⚙️ Technical Details

- **Backend**: Flask with Flask-Caching
- **API**: Google Places API (Text Search + Details)
- **Frontend**: Vanilla JavaScript (no framework)
- **Concurrency**: ThreadPoolExecutor for parallel API calls
- **Caching**: In-memory cache (1 hour TTL)
- **Performance**: ~3-5s first search, instant repeats

## 🔒 Security

- ✅ API key stored in `.env` (not in code)
- ✅ `.env` in `.gitignore` (never committed)
- ✅ Secure environment variable loading
- ✅ Input validation on backend
- ✅ Error handling for API failures

## 📝 License

Free to use and modify!

## 💡 Tips

- Cache stores results for 1 hour
- Google gives max 60 results (3 pages × 20)
- Each page takes 2-3 seconds to load
- First page caches automatically

---

**Built with ❤️ for efficient local business research**
