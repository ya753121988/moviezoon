from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, session
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import os
import json
import time # Added for caching
from urllib.parse import unquote  # %20 URL decoding fix

app = Flask(__name__)
app.secret_key = "dooplay_ultra_pro_max_secret"

# ==========================================
# MongoDB Database Connection
# ==========================================
MONGO_URI = "mongodb+srv://Akash:Akash@cluster0.n8ngrpu.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_website']

movies_col = db['movies']
settings_col = db['settings']
options_col = db['options']

# ==========================================
# High Traffic In-Memory Cache System (For 30k/sec users)
# ==========================================
CACHE_STORE = {}
CACHE_TIMEOUT = 60 # Seconds to keep page in cache

def get_cached_data(key):
    if key in CACHE_STORE and (time.time() - CACHE_STORE[key]['time']) < CACHE_TIMEOUT:
        return CACHE_STORE[key]['data']
    return None

def set_cached_data(key, data):
    CACHE_STORE[key] = {'time': time.time(), 'data': data}

def clear_cache():
    global CACHE_STORE
    CACHE_STORE = {}

# Initialize default settings and admin credentials
if not settings_col.find_one({"type": "general"}):
    settings_col.insert_one({
        "type": "general",
        "ad_status_banner": "off",
        "ad_status_direct": "off",
        "ad_banner_home_desktop": "",
        "ad_banner_home_mobile": "",
        "ad_banner_detail_desktop": "",
        "ad_banner_detail_mobile": "",
        "ad_banner_popular": "", 
        "direct_links": [],
        "notice": "Welcome to our Premium Movie Site!",
        "popup_notice": "Join our Telegram Group!",
        "telegram_link": "https://t.me/yourchannel",
        "tmdb_api_key": "",
        "admin_user": "admin",
        "admin_pass": "admin",
        "limit_movie": "10",
        "limit_series": "10",
        "limit_drama": "10",
        "promos": []
    })

# ==========================================
# Admin Authentication Decorator
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# HTML Templates - FRONTEND (User Side)
# ==========================================
FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>DooPlay Pro - Movie Site</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #0b0f19; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; touch-action: manipulation; }
        .navbar { background-color: #151b2b; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .search-bar { max-width: 400px; width: 100%; flex: 1; }
        
        /* Grid fixed for Mobile: guaranteed exactly 2 columns on small screens */
        .movie-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 15px 0; width: 100%; }
        @media (min-width: 576px) { .movie-grid { grid-template-columns: repeat(3, 1fr); } }
        @media (min-width: 768px) { .movie-grid { grid-template-columns: repeat(4, 1fr); gap: 15px; } }
        @media (min-width: 992px) { .movie-grid { grid-template-columns: repeat(5, 1fr); } }
        
        .movie-card { background: #1e2738; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; height: 100%; border: 1px solid #2d3748; transition: box-shadow 0.3s ease; }
        .movie-card:hover { box-shadow: 0 8px 15px rgba(0,123,255,0.3); }
        
        .poster-wrapper { position: relative; width: 100%; aspect-ratio: 2/3; overflow: hidden; border-bottom: 1px solid #2d3748; }
        .movie-poster { width: 100%; height: 100%; object-fit: cover; }
        
        .movie-badge { position: absolute; top: 8px; right: 8px; background: #e50914; color: #fff; padding: 3px 8px; font-size: 11px; border-radius: 4px; font-weight: bold; z-index: 2; box-shadow: 0 2px 4px rgba(0,0,0,0.5);}
        .movie-quality { position: absolute; top: 8px; left: 8px; background: #007bff; color: #fff; padding: 3px 8px; font-size: 11px; border-radius: 4px; font-weight: bold; z-index: 2; box-shadow: 0 2px 4px rgba(0,0,0,0.5);}
        .movie-views { position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.85); color: #fff; padding: 3px 8px; font-size: 11px; border-radius: 4px; z-index: 2; border: 1px solid #333; }
        
        .movie-info { padding: 10px 8px; text-align: center; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; background: #1e2738; }
        .movie-title { font-size: 14px; font-weight: 600; color: #e2e8f0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; margin-bottom: 6px; }
        .movie-meta { font-size: 11px; color: #8c98a4; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 4px; }
        
        .episodes-grid { display: flex; flex-direction: column; gap: 10px; max-height: 500px; overflow-y: auto; overflow-x: hidden; padding-right: 5px; padding-bottom: 12px; scrollbar-width: thin; }
        .ep-box { background: #151b2b; padding: 10px; border-radius: 8px; border-left: 4px solid #007bff; width: 100%; display: flex; flex-direction: column; justify-content: start; border: 1px solid #1e2738; }
        
        .nav-pills .nav-link { background: #1e2738; color: #fff; border: 1px solid #2d3748; padding: 8px 20px; }
        .nav-pills .nav-link.active { background: #007bff; color: #fff; border-color: #007bff; box-shadow: 0 4px 6px rgba(0,123,255,0.3); }

        .cat-scroll { display: flex; overflow-x: auto; gap: 10px; padding: 10px 0; }
        .cat-scroll::-webkit-scrollbar { display: none; }
        .cat-badge { background: #1e2738; color: #fff; padding: 5px 15px; border-radius: 20px; text-decoration: none; font-size: 13px; border: 1px solid #2d3748; white-space: nowrap;}
        .cat-badge:hover { background: #007bff; }
        
        /* Slider Overlay styles */
        .carousel-caption { background: linear-gradient(0deg, rgba(11,15,25,1) 0%, rgba(11,15,25,0.6) 50%, rgba(0,212,255,0) 100%); bottom: 0; left: 0; right: 0; padding-bottom: 20px; }
        
        /* Promo styling */
        .promo-box { border-radius: 8px; overflow: hidden; border: 1px solid #ffc107; transition: 0.3s; }
        .promo-box:hover { box-shadow: 0 0 15px rgba(255, 193, 7, 0.5); }

        /* Loading Overlay Styling */
        #page-loader { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(11, 15, 25, 0.85); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; backdrop-filter: blur(5px); }
        .spinner { width: 60px; height: 60px; border: 6px solid #1e2738; border-top: 6px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <!-- Fullscreen Loading Overlay -->
    <div id="page-loader">
        <div class="spinner"></div>
        <h5 class="mt-3 text-white fw-bold">Please Wait...</h5>
    </div>

    <nav class="navbar navbar-expand-lg navbar-dark sticky-top">
        <div class="container d-flex flex-wrap align-items-center justify-content-between">
            <a class="navbar-brand fw-bold me-auto" href="/"><i class="fas fa-play text-primary"></i> DooPlay</a>
            <form action="/search" method="GET" class="d-flex search-bar mx-2 mx-lg-auto order-3 order-lg-2 mt-2 mt-lg-0 w-100" style="max-width: 400px;">
                <input class="form-control me-2 bg-dark text-white border-secondary" type="search" name="q" placeholder="Search Movies, Series..." required>
                <button class="btn btn-primary" type="submit"><i class="fas fa-search"></i></button>
            </form>
            <button class="navbar-toggler ms-2 order-2 order-lg-3" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse order-4" id="navMenu" style="flex-grow: 0;">
                <ul class="navbar-nav ms-auto mt-3 mt-lg-0" style="max-height: 350px; overflow-y: auto; overflow-x: hidden;">
                    <!-- Auto Categories in 3-dot menu -->
                    {% set nav_cats = db.options.find({"type": "category"}) %}
                    <li class="nav-item"><a class="nav-link text-white fw-bold" href="/"><i class="fas fa-home text-primary"></i> Home</a></li>
                    {% for c in nav_cats %}
                    <li class="nav-item"><a class="nav-link text-white" href="/category/{{ c.value }}"><i class="fas fa-tags text-warning"></i> {{ c.value }}</a></li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </nav>
    
    {% set settings = db.settings.find_one({"type": "general"}) %}
    
    <div class="container mt-3">
        {% if settings.get('notice') %}
            <div class="alert alert-info text-center shadow-sm" style="background:#1e2738; color:#fff; border:none;">
                <i class="fas fa-bell text-warning"></i> {{ settings.get('notice') }}
            </div>
        {% endif %}
        
        <!-- BANNER ADS SYSTEM (Desktop & Mobile Specific) -->
        {% if settings.get('ad_status_banner') == 'on' %}
            <!-- Popular Ad Section -->
            {% if settings.get('ad_banner_popular') %}
                <div class="text-center mb-3 ad-box w-100">
                    <div style="font-size: 11px; color: #8c98a4; margin-bottom: 2px;">- Popular Advertisement -</div>
                    {{ settings.get('ad_banner_popular') | safe }}
                </div>
            {% endif %}

            {% if page_name in ['home', 'search', 'category'] %}
                <div class="d-none d-md-block text-center mb-3 ad-box">{{ settings.get('ad_banner_home_desktop') | safe }}</div>
                <div class="d-block d-md-none text-center mb-3 ad-box">{{ settings.get('ad_banner_home_mobile') | safe }}</div>
            {% elif page_name == 'detail' %}
                <div class="d-none d-md-block text-center mb-3 ad-box">{{ settings.get('ad_banner_detail_desktop') | safe }}</div>
                <div class="d-block d-md-none text-center mb-3 ad-box">{{ settings.get('ad_banner_detail_mobile') | safe }}</div>
            {% endif %}
        {% endif %}
    </div>

    <div class="container">
        <!-- CONTENT_BLOCK -->
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- DIRECT LINKS AUTO-SWITCH JS SYSTEM -->
    <script>
        const adStatusDirect = "{{ settings.get('ad_status_direct', 'off') }}";
        const rawLinks = '{{ settings.get("direct_links", []) | tojson | safe }}';
        let directLinks = [];
        try { directLinks = JSON.parse(rawLinks); } catch(e) {}
        
        let adClickIndex = parseInt(localStorage.getItem('dooplay_ad_index')) || 0;

        function checkAd(event, url) {
            if(adStatusDirect === 'on' && directLinks.length > 0) {
                event.preventDefault();
                let clickUrl = directLinks[adClickIndex % directLinks.length];
                adClickIndex++;
                localStorage.setItem('dooplay_ad_index', adClickIndex);
                window.open(clickUrl, '_blank');
                setTimeout(() => { window.location.href = url; }, 500);
            }
        }

        // Show Loader Function
        function showLoader() {
            document.getElementById('page-loader').style.display = 'flex';
        }
    </script>
</body>
</html>
"""

# ==========================================
# HTML Templates - ADMIN (Backend)
# ==========================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Admin Panel - DooPlay Pro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #0b0f19; color: #fff; font-family: 'Segoe UI', sans-serif; touch-action: manipulation; }
        .sidebar { min-height: 100vh; background-color: #151b2b; padding-top: 20px; border-right: 1px solid #2d3748; }
        .sidebar a { color: #8c98a4; text-decoration: none; padding: 15px 20px; display: block; font-weight: 500; transition: 0.3s; font-size: 15px; }
        .sidebar a:hover, .sidebar a.active { background-color: #1e2738; color: #007bff; border-left: 4px solid #007bff; }
        .content { padding: 30px; }
        .card { background-color: #151b2b; border: 1px solid #2d3748; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
        .form-control, .form-select { background-color: #0b0f19; border: 1px solid #3b475c; color: #fff; }
        .form-control:focus, .form-select:focus { border-color: #007bff; background-color: #0b0f19; color: #fff; box-shadow: 0 0 5px rgba(0,123,255,0.5); }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar d-none d-md-block">
                <h4 class="text-center text-white mb-4 fw-bold"><i class="fas fa-play text-primary"></i> Admin Pro</h4>
                <a href="/admin"><i class="fas fa-tachometer-alt me-2"></i> ড্যাশবোর্ড</a>
                <a href="/admin/add_movie"><i class="fas fa-plus-circle me-2"></i> মুভি/সিরিজ এড</a>
                <a href="/admin/all_movies"><i class="fas fa-list me-2"></i> অল মুভি ও ডিলেট</a>
                <a href="/admin/options"><i class="fas fa-tags me-2"></i> ব্যাজ/ক্যাটাগরি এড</a>
                <a href="/admin/settings"><i class="fas fa-cog me-2"></i> সেটিংস ও এডস</a>
                <a href="/" target="_blank"><i class="fas fa-external-link-alt me-2"></i> সাইট দেখুন</a>
                <a href="/logout" class="text-danger mt-5"><i class="fas fa-sign-out-alt me-2"></i> লগআউট</a>
            </div>
            
            <div class="col-12 d-md-none bg-dark p-3 d-flex justify-content-between align-items-center mb-3 border-bottom border-secondary">
                <h5 class="m-0 fw-bold"><i class="fas fa-play text-primary"></i> Admin Pro</h5>
                <select class="form-select w-50" onchange="location = this.value;">
                    <option value="/admin">ড্যাশবোর্ড</option>
                    <option value="/admin/add_movie">মুভি এড</option>
                    <option value="/admin/all_movies">অল মুভি</option>
                    <option value="/admin/options">ব্যাজ/ক্যাটাগরি</option>
                    <option value="/admin/settings">সেটিংস</option>
                    <option value="/">সাইট দেখুন</option>
                    <option value="/logout">লগআউট</option>
                </select>
            </div>

            <div class="col-md-10 content">
                {% if get_flashed_messages() %}
                    {% for msg in get_flashed_messages() %}
                        <div class="alert alert-success alert-dismissible fade show" style="background:#198754; color:#fff; border:none;">
                            <i class="fas fa-check-circle"></i> {{ msg }} 
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
                
                <!-- CONTENT_BLOCK -->
                
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <!-- SCRIPTS_BLOCK -->
</body>
</html>
"""

# ==========================================
# PUBLIC ROUTES (Frontend)
# ==========================================

@app.route('/')
def home():
    # Cache System for high traffic (30k/sec)
    cached_html = get_cached_data('home_page')
    if cached_html:
        return cached_html

    settings = settings_col.find_one({"type": "general"}) or {}
    
    # Get Limits from admin
    lim_m = int(settings.get('limit_movie', 10))
    lim_s = int(settings.get('limit_series', 10))
    lim_d = int(settings.get('limit_drama', 10))
    promos = settings.get('promos', [])
    
    top_slider = list(movies_col.find().sort('views', -1).limit(5))
    movies = list(movies_col.find({"type": "Movie"}).sort('_id', -1).limit(lim_m))
    series = list(movies_col.find({"type": "Series"}).sort('_id', -1).limit(lim_s))
    dramas = list(movies_col.find({"type": "Drama"}).sort('_id', -1).limit(lim_d))
    
    categories = list(options_col.find({"type": "category"}))
    
    # Macro for Promo Display
    promo_html = """
    {% if promos %}
    <div class="row my-4">
        {% for p in promos %}
        <div class="col-6 col-md-4 col-lg-3 mb-3">
            <a href="{{ p.url }}" target="_blank" class="text-decoration-none">
                <div class="promo-box bg-dark text-white text-center">
                    <img src="{{ p.image }}" class="w-100" style="height:120px; object-fit:cover;" alt="Promo">
                    <div class="p-2">
                        <span class="text-warning fw-bold small"><i class="fas fa-star"></i> {{ p.text }}</span>
                    </div>
                </div>
            </a>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    """

    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <div class="cat-scroll mb-3">
        <a href="/" class="cat-badge bg-primary text-white">All</a>
        {% for c in categories %}
            <a href="/category/{{ c.value }}" class="cat-badge">{{ c.value }}</a>
        {% endfor %}
    </div>

    <!-- TOP MOVIE SLIDER WITH LANDSCAPE POSTER -->
    <div id="topMoviesCarousel" class="carousel slide mb-4 rounded overflow-hidden shadow-lg border border-secondary" data-bs-ride="carousel">
        <div class="carousel-inner">
            {% for m in top_slider %}
            <div class="carousel-item {% if loop.first %}active{% endif %}">
                <a href="/movie/{{ m._id }}" onclick="showLoader()">
                    <!-- SLIDER Uses BACKDROP (Landscape) fallback to Poster -->
                    <div style="height: 300px; width: 100%; background: url('{{ m.backdrop or m.poster }}') center/cover; position: relative;">
                        <div class="carousel-caption text-start">
                            <h3 class="fw-bold text-white shadow-sm">{{ m.title }}</h3>
                            <span class="badge bg-danger">{{ m.type }}</span>
                            <span class="badge bg-primary"><i class="fas fa-eye"></i> {{ m.views }} Views</span>
                        </div>
                    </div>
                </a>
            </div>
            {% endfor %}
        </div>
        <button class="carousel-control-prev" type="button" data-bs-target="#topMoviesCarousel" data-bs-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#topMoviesCarousel" data-bs-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
        </button>
    </div>

    <!-- MOVIES SECTION (PORTRAIT POSTERS IN GRID) -->
    {% if movies %}
    <div class="d-flex justify-content-between align-items-center mb-3 border-start border-primary border-4 ps-2">
        <h4 class="fw-bold text-uppercase m-0">Latest Movies</h4>
        <a href="/category/Movie" class="btn btn-sm btn-outline-primary">View All</a>
    </div>
    <div class="movie-grid">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none" onclick="showLoader()">
            <div class="movie-card">
                <div class="poster-wrapper">
                    {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                    {% if m.quality %}<span class="movie-quality">{{ m.quality }}</span>{% endif %}
                    <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                    <!-- Uses normal portrait poster in Home Grid -->
                    <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <div class="movie-meta">
                        <span class="text-warning fw-bold">{{ m.type }}</span>
                        {% if m.date %} <span class="ms-1">• {{ m.date[:4] }}</span> {% endif %}
                    </div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    """ + promo_html + """
    {% endif %}

    <!-- SERIES SECTION -->
    {% if series %}
    <div class="d-flex justify-content-between align-items-center mt-4 mb-3 border-start border-success border-4 ps-2">
        <h4 class="fw-bold text-uppercase m-0 text-success">Latest Series & Episodes</h4>
        <a href="/category/Series" class="btn btn-sm btn-outline-success">View All</a>
    </div>
    <div class="movie-grid">
        {% for m in series %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none" onclick="showLoader()">
            <div class="movie-card" style="border-color: #198754;">
                <div class="poster-wrapper">
                    {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                    <span class="movie-quality bg-success">Episodes Added</span>
                    <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                    <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <div class="movie-meta"><span class="text-success fw-bold">{{ m.type }}</span></div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    """ + promo_html + """
    {% endif %}

    <!-- DRAMA SECTION -->
    {% if dramas %}
    <div class="d-flex justify-content-between align-items-center mt-4 mb-3 border-start border-warning border-4 ps-2">
        <h4 class="fw-bold text-uppercase m-0 text-warning">Latest Drama</h4>
        <a href="/category/Drama" class="btn btn-sm btn-outline-warning">View All</a>
    </div>
    <div class="movie-grid">
        {% for m in dramas %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none" onclick="showLoader()">
            <div class="movie-card" style="border-color: #ffc107;">
                <div class="poster-wrapper">
                    {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                    <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                    <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <div class="movie-meta"><span class="text-warning fw-bold">{{ m.type }}</span></div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    """ + promo_html + """
    {% endif %}
    
    {% if not movies and not series and not dramas %}
        <div class="alert alert-secondary text-center mt-5">কোনো পোস্ট পাওয়া যায়নি!</div>
    {% endif %}
    """)
    
    rendered_html = render_template_string(html, top_slider=top_slider, movies=movies, series=series, dramas=dramas, categories=categories, db=db, page_name='home', promos=promos)
    set_cached_data('home_page', rendered_html) # Save to Cache
    return rendered_html

@app.route('/search')
def search():
    query = request.args.get('q', '')
    movies = list(movies_col.find({"title": {"$regex": query, "$options": "i"}}).sort('_id', -1))
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h4 class="mb-3 border-start border-primary border-4 ps-2">Search Results for: <span class="text-warning">{{ query }}</span></h4>
    <div class="movie-grid">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none" onclick="showLoader()">
            <div class="movie-card">
                <div class="poster-wrapper">
                    {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                    {% if m.quality %}<span class="movie-quality">{{ m.quality }}</span>{% endif %}
                    <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                    <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <div class="movie-meta">
                        <span class="text-warning fw-bold">{{ m.type }}</span>
                        {% if m.date %} <span class="ms-1">• {{ m.date[:4] }}</span> {% endif %}
                        {% if m.language %} <span class="ms-1">• {{ m.language }}</span> {% endif %}
                    </div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    {% if not movies %}<h5 class="text-center text-muted mt-5">No results found!</h5>{% endif %}
    """)
    return render_template_string(html, movies=movies, query=query, db=db, page_name='search')

@app.route('/category/<cat_name>')
def category_filter(cat_name):
    cat_name = unquote(cat_name) # Fix URL Encoding (%20 to space)
    if cat_name in ['Movie', 'Series', 'Drama']:
        movies = list(movies_col.find({"type": cat_name}).sort('_id', -1))
    else:
        movies = list(movies_col.find({"categories": cat_name}).sort('_id', -1))
    
    categories = list(options_col.find({"type": "category"}))
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <div class="cat-scroll mb-3">
        <a href="/" class="cat-badge">All</a>
        {% for c in categories %}
            <a href="/category/{{ c.value }}" class="cat-badge {% if cat_name == c.value %}bg-primary{% endif %}">{{ c.value }}</a>
        {% endfor %}
    </div>
    <h4 class="mb-3 border-start border-primary border-4 ps-2">Category: <span class="text-warning">{{ cat_name }}</span></h4>
    <div class="movie-grid">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none" onclick="showLoader()">
            <div class="movie-card">
                <div class="poster-wrapper">
                    {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                    {% if m.quality %}<span class="movie-quality">{{ m.quality }}</span>{% endif %}
                    <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                    <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <div class="movie-meta">
                        <span class="text-warning fw-bold">{{ m.type }}</span>
                        {% if m.date %} <span class="ms-1">• {{ m.date[:4] }}</span> {% endif %}
                        {% if m.language %} <span class="ms-1">• {{ m.language }}</span> {% endif %}
                    </div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    """)
    return render_template_string(html, movies=movies, cat_name=cat_name, categories=categories, db=db, page_name='category')

@app.route('/movie/<id>')
def movie_details(id):
    movies_col.update_one({"_id": ObjectId(id)}, {"$inc": {"views": 1}})
    movie = movies_col.find_one({"_id": ObjectId(id)})
    
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <div class="row mt-3">
        <!-- FULL WIDTH LANDSCAPE BANNER HEADER -->
        <div class="col-12 mb-4">
            <div class="position-relative w-100 shadow-lg border border-secondary" style="height: 350px; border-radius: 12px; overflow: hidden;">
                <img src="{{ m.backdrop or m.poster }}" class="w-100 h-100" style="object-fit: cover; filter: brightness(0.6);" alt="Banner Backdrop" onerror="this.src='{{ m.poster }}'">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(0deg, rgba(11,15,25,1) 0%, rgba(11,15,25,0) 100%); height: 250px;"></div>
                
                {% if m.badge %}<span class="movie-badge shadow" style="font-size: 16px; padding: 6px 20px; top: 15px; right: 15px;">{{ m.badge }}</span>{% endif %}
                
                <div style="position: absolute; bottom: 20px; left: 20px; right: 20px;">
                    <h1 class="fw-bold text-white mb-3" style="text-shadow: 2px 2px 5px #000; font-size: 28px;">{{ m.title }}</h1>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-danger fs-6 shadow-sm"><i class="fas fa-video"></i> {{ m.type }}</span>
                        {% if m.date %}<span class="badge bg-info text-dark fs-6 shadow-sm"><i class="far fa-calendar-alt"></i> {{ m.date[:4] }}</span>{% endif %}
                        {% if m.quality %}<span class="badge bg-primary fs-6 shadow-sm">{{ m.quality }}</span>{% endif %}
                        {% if m.language %}<span class="badge bg-success fs-6 shadow-sm"><i class="fas fa-language"></i> {{ m.language }}</span>{% endif %}
                        {% for cat in m.categories %}
                            <span class="badge bg-secondary fs-6 shadow-sm">{{ cat }}</span>
                        {% endfor %}
                        <span class="badge bg-dark border border-secondary fs-6 shadow-sm"><i class="fas fa-eye text-primary"></i> Views: {{ m.views }}</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-12">
            <p class="text-light p-3 rounded shadow-sm" style="background: #151b2b; font-size: 15px; line-height: 1.7; border-left: 4px solid #007bff; border-bottom: 1px solid #2d3748; border-right: 1px solid #2d3748; border-top: 1px solid #2d3748;">{{ m.description }}</p>
            <hr class="border-secondary my-4">
            
            {% if m.type == 'Movie' %}
                <h4 class="mb-3 fw-bold border-start border-warning border-4 ps-2">Download & Watch Links</h4>
                
                <div class="d-flex flex-column gap-3">
                    {% if m.links %}
                        {% for group_name, items in m.links|groupby('name') %}
                        <div class="link-group border border-secondary rounded bg-dark p-2">
                            <button class="btn btn-outline-warning w-100 fw-bold d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#col_movie_{{ loop.index }}">
                                <span class="fs-5">
                                    {% if 'online' in group_name.lower() or 'watch' in group_name.lower() %}<i class="fas fa-play-circle"></i>
                                    {% elif 'telegram' in group_name.lower() %}<i class="fab fa-telegram"></i>
                                    {% else %}<i class="fas fa-download"></i>{% endif %}
                                    {{ group_name }}
                                </span>
                                <i class="fas fa-chevron-down"></i>
                            </button>
                            <div class="collapse mt-2" id="col_movie_{{ loop.index }}">
                                <div class="d-flex flex-column gap-2">
                                    {% for item in items %}
                                    <a href="{{ item.url }}" onclick="checkAd(event, '{{ item.url }}')" class="btn btn-primary w-100 d-flex justify-content-between align-items-center p-2 shadow-sm">
                                        <span><i class="fas fa-link"></i> Click to Open</span>
                                        {% if item.quality %}<span class="badge bg-light text-dark px-2 py-1 fs-6">{{ item.quality }}</span>{% endif %}
                                    </a>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="alert alert-secondary w-100 text-center">No links available yet.</div>
                    {% endif %}
                </div>
            {% else %}
                <h4 class="mb-3 fw-bold border-start border-warning border-4 ps-2">Seasons & Episodes</h4>
                
                <!-- Vertical Scroll for Seasons -->
                <div class="p-2 border border-secondary rounded mb-3 shadow-sm" style="background:#151b2b; max-height: 250px; overflow-y: auto; scrollbar-width: thin;">
                    <ul class="nav nav-pills flex-column gap-2" id="seasonTabs" role="tablist">
                        {% for s in m.seasons %}
                        <li class="nav-item" role="presentation">
                            <button class="nav-link w-100 text-start {% if loop.first %}active{% endif %} fw-bold rounded" data-bs-toggle="pill" data-bs-target="#season_{{ s.season }}" type="button" role="tab">
                                <i class="fas fa-folder-open me-2"></i> Season {{ "%02d"|format(s.season|int) }}
                            </button>
                        </li>
                        {% endfor %}
                    </ul>
                </div>

                <div class="tab-content" id="seasonTabsContent">
                    {% for s in m.seasons %}
                    <div class="tab-pane fade {% if loop.first %}show active{% endif %}" id="season_{{ s.season }}" role="tabpanel">
                        
                        <!-- Episodes are vertically scrollable here -->
                        <div class="episodes-grid">
                            {% for ep in s.episodes %}
                                <div class="ep-box">
                                    <!-- EPISODE POSTER INCLUDED HERE -->
                                    <button class="btn btn-outline-primary w-100 text-start fw-bold d-flex justify-content-between align-items-center p-2" data-bs-toggle="collapse" data-bs-target="#links_S{{s.season}}_E{{ep.episode}}">
                                        <div class="d-flex align-items-center gap-3">
                                            <!-- Thumb Image: Episode Poster fallback to main backdrop fallback to portrait -->
                                            <img src="{{ ep.poster or m.backdrop or m.poster }}" style="width: 75px; height: 42px; object-fit: cover; border-radius: 4px; border: 1px solid #2d3748;" onerror="this.src='{{ m.backdrop or m.poster }}'">
                                            <span class="fs-6"><i class="fas fa-tv me-1"></i> Season {{ "%02d"|format(s.season|int) }} - Episode {{ "%02d"|format(ep.episode|int) }}</span> 
                                        </div>
                                        <i class="fas fa-chevron-down ms-2"></i>
                                    </button>
                                    
                                    <div id="links_S{{s.season}}_E{{ep.episode}}" class="collapse mt-2">
                                        <div class="d-flex flex-column gap-2">
                                            {% if ep.links %}
                                                {% for group_name, items in ep.links|groupby('name') %}
                                                <div class="border border-secondary rounded p-2" style="background: rgba(0,0,0,0.3);">
                                                    <button class="btn btn-sm btn-outline-warning w-100 fw-bold d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#col_s{{s.season}}_e{{ep.episode}}_g{{loop.index}}">
                                                        <span>
                                                            {% if 'online' in group_name.lower() or 'watch' in group_name.lower() %}<i class="fas fa-play-circle"></i>
                                                            {% else %}<i class="fas fa-download"></i>{% endif %}
                                                            {{ group_name }}
                                                        </span>
                                                        <i class="fas fa-chevron-down"></i>
                                                    </button>
                                                    <div class="collapse mt-2" id="col_s{{s.season}}_e{{ep.episode}}_g{{loop.index}}">
                                                        <div class="d-flex flex-column gap-2">
                                                            {% for item in items %}
                                                            <a href="{{ item.url }}" onclick="checkAd(event, '{{ item.url }}')" class="btn btn-sm btn-primary w-100 d-flex justify-content-between align-items-center">
                                                                <span><i class="fas fa-link"></i> Click to Open</span>
                                                                {% if item.quality %}<span class="badge bg-light text-dark">{{ item.quality }}</span>{% endif %}
                                                            </a>
                                                            {% endfor %}
                                                        </div>
                                                    </div>
                                                </div>
                                                {% endfor %}
                                            {% else %}
                                                <span class="text-muted small text-center w-100 d-block border border-secondary rounded p-2">No links available</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>

                    </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    </div>
    """)
    return render_template_string(html, m=movie, db=db, page_name='detail')

# ==========================================
# ADMIN AUTHENTICATION
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        settings = settings_col.find_one({"type": "general"})
        user = request.form.get('username')
        password = request.form.get('password')
        if user == settings.get('admin_user') and password == settings.get('admin_pass'):
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("ভুল ইউজারনেম বা পাসওয়ার্ড!")
            
    html = """
    <!DOCTYPE html><html data-bs-theme="dark"><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Admin Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body style="background:#0b0f19;" class="d-flex justify-content-center align-items-center vh-100">
        <div class="card p-4 shadow-lg border-primary" style="background:#151b2b; width: 350px;">
            <h3 class="text-center text-white mb-4">Admin Login</h3>
            {% if get_flashed_messages() %}
                <div class="alert alert-danger p-2 text-center">{{ get_flashed_messages()[0] }}</div>
            {% endif %}
            <form method="POST">
                <input type="text" name="username" class="form-control mb-3 bg-dark text-white border-secondary" placeholder="Username" required>
                <input type="password" name="password" class="form-control mb-3 bg-dark text-white border-secondary" placeholder="Password" required>
                <button type="submit" class="btn btn-primary w-100 fw-bold">Login</button>
            </form>
        </div>
    </body></html>
    """
    return render_template_string(html)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

# ==========================================
# ADMIN ROUTES (Backend)
# ==========================================

@app.route('/admin')
@login_required
def admin_dashboard():
    total_movies = movies_col.count_documents({"type": "Movie"})
    total_series = movies_col.count_documents({"type": {"$in": ["Series", "Drama"]}})
    total_views = sum([m.get('views', 0) for m in movies_col.find()])
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">ড্যাশবোর্ড (Dashboard)</h2>
    <div class="row">
        <div class="col-md-4 mb-3">
            <div class="card p-4 text-center border-bottom border-primary border-4">
                <h2 class="text-primary fw-bold">{{ tm }}</h2>
                <h6 class="text-muted m-0 text-uppercase">Total Movies</h6>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card p-4 text-center border-bottom border-success border-4">
                <h2 class="text-success fw-bold">{{ ts }}</h2>
                <h6 class="text-muted m-0 text-uppercase">Total Series/Drama</h6>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card p-4 text-center border-bottom border-warning border-4">
                <h2 class="text-warning fw-bold">{{ tv }}</h2>
                <h6 class="text-muted m-0 text-uppercase">Total Views</h6>
            </div>
        </div>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', "")
    return render_template_string(html, tm=total_movies, ts=total_series, tv=total_views)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if request.method == 'POST':
        # Clear Home Cache on Setting changes
        clear_cache()

        d_links = request.form.getlist('direct_links[]')
        d_links = [url for url in d_links if url.strip()]
        
        # Promos Processing
        p_texts = request.form.getlist('promo_text[]')
        p_images = request.form.getlist('promo_image[]')
        p_urls = request.form.getlist('promo_url[]')
        promos = [{"text": t, "image": i, "url": u} for t, i, u in zip(p_texts, p_images, p_urls) if t and u]
        
        settings_col.update_one({"type": "general"}, {"$set": {
            "ad_status_banner": request.form.get('ad_status_banner'),
            "ad_status_direct": request.form.get('ad_status_direct'),
            "ad_banner_home_desktop": request.form.get('ad_banner_home_desktop'),
            "ad_banner_home_mobile": request.form.get('ad_banner_home_mobile'),
            "ad_banner_detail_desktop": request.form.get('ad_banner_detail_desktop'),
            "ad_banner_detail_mobile": request.form.get('ad_banner_detail_mobile'),
            "ad_banner_popular": request.form.get('ad_banner_popular'),
            "direct_links": d_links,
            "telegram_link": request.form.get('telegram_link'),
            "notice": request.form.get('notice'),
            "popup_notice": request.form.get('popup_notice'),
            "tmdb_api_key": request.form.get('tmdb_api_key'),
            "admin_user": request.form.get('admin_user'),
            "admin_pass": request.form.get('admin_pass'),
            "limit_movie": request.form.get('limit_movie', '10'),
            "limit_series": request.form.get('limit_series', '10'),
            "limit_drama": request.form.get('limit_drama', '10'),
            "promos": promos
        }})
        flash("সেটিংস এবং অ্যাডস সফলভাবে আপডেট হয়েছে!")
        return redirect(url_for('admin_settings'))
    
    s = settings_col.find_one({"type": "general"})
    if not s:
        s = {}
        
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">সেটিংস ও এডস প্যানেল (Advanced)</h2>
    <form method="POST" class="card p-4">
        
        <h5 class="text-danger border-bottom border-secondary pb-2"><i class="fas fa-layer-group"></i> Homepage Category Post Limits</h5>
        <div class="row mb-4 bg-dark p-3 rounded border border-secondary">
            <div class="col-md-4 mb-2">
                <label class="text-white">Movie Section Limit</label>
                <input type="number" name="limit_movie" class="form-control" value="{{ s.get('limit_movie', '10') }}" min="1">
            </div>
            <div class="col-md-4 mb-2">
                <label class="text-white">Series Section Limit</label>
                <input type="number" name="limit_series" class="form-control" value="{{ s.get('limit_series', '10') }}" min="1">
            </div>
            <div class="col-md-4 mb-2">
                <label class="text-white">Drama Section Limit</label>
                <input type="number" name="limit_drama" class="form-control" value="{{ s.get('limit_drama', '10') }}" min="1">
            </div>
        </div>

        <h5 class="text-warning border-bottom border-secondary pb-2"><i class="fas fa-money-bill-wave"></i> Unlimited Promote & Income System (Home Page)</h5>
        <div class="row mb-4 bg-dark p-3 rounded border border-warning">
            <div class="col-12">
                <label class="mb-2 text-warning">এই প্রোমোগুলো হোমপেজের প্রতি ক্যাটাগরির নিচে শো করবে (ছবি, লেখা, লিঙ্ক সহ)</label>
                <div id="promoContainer">
                    {% for p in s.get('promos', []) %}
                    <div class="input-group mb-2 border border-secondary p-1 bg-black rounded">
                        <input type="text" name="promo_text[]" class="form-control" value="{{ p.text }}" placeholder="Promo Text Title" required>
                        <input type="url" name="promo_image[]" class="form-control" value="{{ p.image }}" placeholder="Image/Screenshot URL" required>
                        <input type="url" name="promo_url[]" class="form-control" value="{{ p.url }}" placeholder="Destination Link" required>
                        <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
                    </div>
                    {% endfor %}
                </div>
                <button type="button" class="btn btn-outline-warning mt-2 fw-bold w-100" onclick="addPromo()"><i class="fas fa-plus"></i> Add New Promo</button>
            </div>
        </div>

        <h5 class="text-info border-bottom border-secondary pb-2"><i class="fas fa-link"></i> Direct Ads (Auto Switch on Click)</h5>
        <div class="row mb-4 bg-dark p-3 rounded">
            <div class="col-md-12 mb-3">
                <label class="text-warning fw-bold">Direct Ads Status</label>
                <select name="ad_status_direct" class="form-select border-warning">
                    <option value="on" {% if s.get('ad_status_direct') == 'on' %}selected{% endif %}>ON (চালু)</option>
                    <option value="off" {% if s.get('ad_status_direct') == 'off' %}selected{% endif %}>OFF (বন্ধ)</option>
                </select>
            </div>
            <div class="col-12">
                <label class="mb-2 text-info">Add Unlimited Direct Links (প্রতি ক্লিকে অটো পরিবর্তন হবে)</label>
                <div id="directLinkContainer">
                    {% for d_link in s.get('direct_links', []) %}
                    <div class="input-group mb-2">
                        <span class="input-group-text bg-secondary text-white"><i class="fas fa-external-link-alt"></i></span>
                        <input type="url" name="direct_links[]" class="form-control" value="{{ d_link }}" placeholder="https://ad-network.com/..." required>
                        <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>
                    </div>
                    {% endfor %}
                </div>
                <button type="button" class="btn btn-outline-info mt-2 btn-sm fw-bold" onclick="addDirectLink()"><i class="fas fa-plus"></i> Add Link</button>
            </div>
        </div>

        <h5 class="text-success border-bottom border-secondary pb-2"><i class="fas fa-image"></i> Banner Ads (HTML Code)</h5>
        <div class="row mb-4 bg-dark p-3 rounded">
            <div class="col-md-12 mb-3">
                <label class="text-warning fw-bold">Banner Ads Status</label>
                <select name="ad_status_banner" class="form-select border-warning">
                    <option value="on" {% if s.get('ad_status_banner') == 'on' %}selected{% endif %}>ON (চালু)</option>
                    <option value="off" {% if s.get('ad_status_banner') == 'off' %}selected{% endif %}>OFF (বন্ধ)</option>
                </select>
            </div>
            <div class="col-md-12 mb-3">
                <label class="text-warning"><i class="fas fa-star"></i> Popular Ad Banner (All Pages, Top Section)</label>
                <textarea name="ad_banner_popular" class="form-control border-warning" rows="3" placeholder="Paste popular banner code here">{{ s.get('ad_banner_popular', '') }}</textarea>
            </div>
            <div class="col-md-6 mb-3">
                <label class="text-white"><i class="fas fa-home"></i> Home Page (Desktop)</label>
                <textarea name="ad_banner_home_desktop" class="form-control" rows="3" placeholder="Paste desktop banner code here">{{ s.get('ad_banner_home_desktop', '') }}</textarea>
            </div>
            <div class="col-md-6 mb-3">
                <label class="text-white"><i class="fas fa-mobile-alt"></i> Home Page (Mobile)</label>
                <textarea name="ad_banner_home_mobile" class="form-control" rows="3" placeholder="Paste mobile banner code here">{{ s.get('ad_banner_home_mobile', '') }}</textarea>
            </div>
            <div class="col-md-6 mb-3">
                <label class="text-white"><i class="fas fa-film"></i> Detail Page (Desktop)</label>
                <textarea name="ad_banner_detail_desktop" class="form-control" rows="3" placeholder="Paste desktop banner code here">{{ s.get('ad_banner_detail_desktop', '') }}</textarea>
            </div>
            <div class="col-md-6 mb-3">
                <label class="text-white"><i class="fas fa-mobile-alt"></i> Detail Page (Mobile)</label>
                <textarea name="ad_banner_detail_mobile" class="form-control" rows="3" placeholder="Paste mobile banner code here">{{ s.get('ad_banner_detail_mobile', '') }}</textarea>
            </div>
        </div>

        <h5 class="text-warning border-bottom border-secondary pb-2"><i class="fas fa-shield-alt"></i> Security / API</h5>
        <div class="row mb-4">
            <div class="col-md-4 mb-2"><label>Admin Username</label><input type="text" name="admin_user" class="form-control" value="{{ s.get('admin_user', 'admin') }}" required></div>
            <div class="col-md-4 mb-2"><label>Admin Password</label><input type="text" name="admin_pass" class="form-control" value="{{ s.get('admin_pass', 'admin') }}" required></div>
            <div class="col-md-4 mb-2"><label>TMDB API Key V3</label><input type="text" name="tmdb_api_key" class="form-control" value="{{ s.get('tmdb_api_key', '') }}" placeholder="Required for TMDB Import"></div>
        </div>

        <h5 class="text-primary border-bottom border-secondary pb-2"><i class="fas fa-bullhorn"></i> Notice & Telegram</h5>
        <div class="row mb-4">
            <div class="col-md-12 mb-2"><label>Telegram Link</label><input type="text" name="telegram_link" class="form-control" value="{{ s.get('telegram_link', '') }}"></div>
            <div class="col-md-12 mb-2"><label>General Notice (Top bar)</label><input type="text" name="notice" class="form-control" value="{{ s.get('notice', '') }}"></div>
        </div>
        
        <button type="submit" class="btn btn-primary fw-bold px-5 fs-5 w-100">Save All Settings</button>
    </form>
    """).replace('<!-- SCRIPTS_BLOCK -->', """
    <script>
        function addDirectLink() {
            let div = document.createElement('div');
            div.className = "input-group mb-2";
            div.innerHTML = `
                <span class="input-group-text bg-secondary text-white"><i class="fas fa-external-link-alt"></i></span>
                <input type="url" name="direct_links[]" class="form-control" placeholder="https://ad-network.com/..." required>
                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>`;
            document.getElementById('directLinkContainer').appendChild(div);
        }
        function addPromo() {
            let div = document.createElement('div');
            div.className = "input-group mb-2 border border-secondary p-1 bg-black rounded";
            div.innerHTML = `
                <input type="text" name="promo_text[]" class="form-control" placeholder="Promo Text Title" required>
                <input type="url" name="promo_image[]" class="form-control" placeholder="Image/Screenshot URL" required>
                <input type="url" name="promo_url[]" class="form-control" placeholder="Destination Link" required>
                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-trash"></i></button>`;
            document.getElementById('promoContainer').appendChild(div);
        }
    </script>
    """)
    return render_template_string(html, s=s)

@app.route('/admin/options', methods=['GET', 'POST'])
@login_required
def admin_options():
    if request.method == 'POST':
        item_type = request.form.get('type')
        item_val = request.form.get('value')
        options_col.insert_one({"type": item_type, "value": item_val})
        flash(f"{item_val} যোগ করা হয়েছে!")
        return redirect(url_for('admin_options'))
    
    badges = list(options_col.find({"type": "badge"}))
    qualities = list(options_col.find({"type": "quality"}))
    langs = list(options_col.find({"type": "language"}))
    cats = list(options_col.find({"type": "category"}))
    link_names = list(options_col.find({"type": "link_name"}))
    
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">ক্যাটাগরি, ব্যাজ, লিংক নাম ও কোয়ালিটি</h2>
    <div class="card p-4">
        <form method="POST" class="d-flex gap-2 mb-4 flex-wrap">
            <select name="type" class="form-select" style="width: auto;">
                <option value="category">Category (Action..)</option>
                <option value="badge">Badge (CAM, HD..)</option>
                <option value="quality">Quality (1080p..)</option>
                <option value="language">Language (Hindi..)</option>
                <option value="link_name">Link Name (Download, Watch..)</option>
            </select>
            <input type="text" name="value" class="form-control flex-grow-1" placeholder="নাম লিখুন..." required>
            <button type="submit" class="btn btn-success fw-bold px-4">Add New</button>
        </form>
        
        <div class="row">
            <div class="col-md-3">
                <h5 class="text-info border-bottom pb-2">Categories</h5>
                <ul class="list-group list-group-flush bg-transparent">
                    {% for c in cats %}<li class="list-group-item bg-transparent text-white d-flex justify-content-between align-items-center border-secondary">{{ c.value }} <a href="/admin/del_opt/{{c._id}}" class="text-danger"><i class="fas fa-trash"></i></a></li>{% endfor %}
                </ul>
            </div>
            <div class="col-md-3">
                <h5 class="text-warning border-bottom pb-2">Badges</h5>
                <ul class="list-group list-group-flush">
                    {% for b in badges %}<li class="list-group-item bg-transparent text-white d-flex justify-content-between align-items-center border-secondary">{{ b.value }} <a href="/admin/del_opt/{{b._id}}" class="text-danger"><i class="fas fa-trash"></i></a></li>{% endfor %}
                </ul>
            </div>
            <div class="col-md-3">
                <h5 class="text-primary border-bottom pb-2">Qualities</h5>
                <ul class="list-group list-group-flush">
                    {% for q in qualities %}<li class="list-group-item bg-transparent text-white d-flex justify-content-between align-items-center border-secondary">{{ q.value }} <a href="/admin/del_opt/{{q._id}}" class="text-danger"><i class="fas fa-trash"></i></a></li>{% endfor %}
                </ul>
            </div>
            <div class="col-md-3">
                <h5 class="text-success border-bottom pb-2">Languages</h5>
                <ul class="list-group list-group-flush">
                    {% for l in langs %}<li class="list-group-item bg-transparent text-white d-flex justify-content-between align-items-center border-secondary">{{ l.value }} <a href="/admin/del_opt/{{l._id}}" class="text-danger"><i class="fas fa-trash"></i></a></li>{% endfor %}
                </ul>
            </div>
            
            <div class="col-12 mt-4">
                <h5 class="text-secondary border-bottom pb-2">Pre-added Link Names (For Download Buttons)</h5>
                <div class="d-flex flex-wrap gap-2">
                    {% for lnk in link_names %}
                        <span class="badge bg-secondary p-2 fs-6">{{ lnk.value }} <a href="/admin/del_opt/{{lnk._id}}" class="text-danger ms-2"><i class="fas fa-times"></i></a></span>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', "")
    return render_template_string(html, badges=badges, qualities=qualities, langs=langs, cats=cats, link_names=link_names)

@app.route('/admin/del_opt/<id>')
@login_required
def del_opt(id):
    options_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin_options'))

@app.route('/admin/tmdb_search')
@login_required
def tmdb_search():
    query = request.args.get('q')
    api_key = settings_col.find_one({"type": "general"}).get('tmdb_api_key')
    if not api_key or not query:
        return jsonify([])
    
    url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=en-US&page=1"
    try:
        res = requests.get(url).json()
        results = []
        for item in res.get('results', []):
            if item.get('media_type') in ['movie', 'tv']:
                title = item.get('title') if item.get('media_type') == 'movie' else item.get('name')
                date = item.get('release_date') if item.get('media_type') == 'movie' else item.get('first_air_date')
                poster = f"https://image.tmdb.org/t/p/w92{item.get('poster_path')}" if item.get('poster_path') else "https://via.placeholder.com/92x138?text=No+Image"
                results.append({
                    'id': item.get('id'),
                    'title': title,
                    'type': item.get('media_type'),
                    'date': date,
                    'poster': poster
                })
        return jsonify(results)
    except:
        return jsonify([])

@app.route('/admin/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    settings = settings_col.find_one({"type": "general"})
    
    if request.method == 'POST':
        clear_cache() # Clear cache on new post
        action = request.form.get('action')
        
        if action == 'fetch_tmdb':
            tmdb_id = request.form.get('tmdb_id')
            m_type = request.form.get('fetch_type')
            api_key = settings.get('tmdb_api_key')
            
            if not api_key:
                flash("Error: TMDB API Key সেটিংসে দেওয়া নেই!")
                return redirect(url_for('add_movie'))
            
            url = f"https://api.themoviedb.org/3/{m_type}/{tmdb_id}?api_key={api_key}&language=en-US"
            try:
                res = requests.get(url).json()
                if 'id' not in res:
                    flash("Error: TMDB ID সঠিক নয় বা ডাটা পাওয়া যায়নি!")
                    return redirect(url_for('add_movie'))
                
                title = res.get('title') if m_type == 'movie' else res.get('name')
                date = res.get('release_date') if m_type == 'movie' else res.get('first_air_date')
                
                poster = f"https://image.tmdb.org/t/p/w500{res.get('poster_path')}" if res.get('poster_path') else ""
                # Added Backdrop Import
                backdrop = f"https://image.tmdb.org/t/p/w780{res.get('backdrop_path')}" if res.get('backdrop_path') else poster
                
                desc = res.get('overview', '')
                
                genres = [g['name'] for g in res.get('genres', [])]
                for g in genres:
                    if not options_col.find_one({"type": "category", "value": g}):
                        options_col.insert_one({"type": "category", "value": g})
                
                new_doc = {
                    "title": title, "type": "Movie" if m_type == 'movie' else "Series",
                    "poster": poster, "backdrop": backdrop, "description": desc, "date": date,
                    "badge": "", "quality": "", "language": "English",
                    "categories": genres, "views": 0,
                    "links": []
                }
                
                if m_type == 'tv':
                    seasons = []
                    for s in res.get('seasons', []):
                        s_num = s.get('season_number')
                        if s_num > 0:
                            episodes = []
                            # Fetch Extra Season Details for Episode Posters
                            try:
                                s_res = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{s_num}?api_key={api_key}").json()
                                for e_data in s_res.get('episodes', []):
                                    e_num = e_data.get('episode_number')
                                    e_still = e_data.get('still_path')
                                    # Episode Thumbnail Poster
                                    ep_poster = f"https://image.tmdb.org/t/p/w500{e_still}" if e_still else ""
                                    episodes.append({"episode": e_num, "poster": ep_poster, "links": []})
                            except:
                                episodes = [{"episode": e, "poster": "", "links": []} for e in range(1, s.get('episode_count') + 1)]
                                
                            seasons.append({"season": s_num, "episodes": episodes})
                    new_doc['seasons'] = seasons
                
                inserted_id = movies_col.insert_one(new_doc).inserted_id
                flash(f"TMDB থেকে '{title}' ইমপোর্ট হয়েছে! এখন লিংক বসান।")
                return redirect(f"/admin/edit_movie/{inserted_id}")
            except Exception as e:
                flash(f"Error connecting to TMDB: {str(e)}")
                return redirect(url_for('add_movie'))

        elif action == 'manual_add':
            title = request.form.get('title')
            m_type = request.form.get('type')
            
            link_names = request.form.getlist('link_name[]')
            link_quals = request.form.getlist('link_quality[]')
            link_urls = request.form.getlist('link_url[]')
            links = [{"name": n, "quality": q, "url": u} for n, q, u in zip(link_names, link_quals, link_urls) if n and u]
            
            poster = request.form.get('poster')
            backdrop = request.form.get('backdrop', poster) # fallback
            
            new_doc = {
                "title": title, "type": m_type, "poster": poster, "backdrop": backdrop,
                "badge": request.form.get('badge'), "quality": request.form.get('quality'),
                "language": request.form.get('language'), "description": request.form.get('description'),
                "categories": request.form.getlist('categories'), "views": 0,
                "links": links
            }
            
            if m_type in ['Series', 'Drama']:
                new_doc['seasons'] = [{"season": 1, "episodes": [{"episode": 1, "poster": "", "links": links}]}]
                new_doc['links'] = []
                
            movies_col.insert_one(new_doc)
            flash("ম্যানুয়ালি ডাটা যোগ করা হয়েছে!")
            return redirect(url_for('add_movie'))

    badges = list(options_col.find({"type": "badge"}))
    qualities = list(options_col.find({"type": "quality"}))
    langs = list(options_col.find({"type": "language"}))
    cats = list(options_col.find({"type": "category"}))
    link_names = list(options_col.find({"type": "link_name"}))

    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">মুভি / সিরিজ / ড্রামা এড</h2>

    <!-- TMDB LIVE SEARCH SECTION -->
    <div class="card p-4 mb-4 border-success shadow" style="background:#151b2b;">
        <h4 class="text-success fw-bold mb-3"><i class="fas fa-search"></i> লাইভ TMDB সার্চ ও ইম্পোর্ট</h4>
        <div class="position-relative">
            <input type="text" id="liveSearchInput" class="form-control form-control-lg bg-dark text-white border-success" placeholder="মুভি বা সিরিজের নাম লিখুন...">
            <div id="liveSearchResults" class="list-group position-absolute w-100 shadow-lg" style="z-index: 1000; max-height: 400px; overflow-y: auto; display: none;">
            </div>
        </div>
        <form id="hiddenImportForm" method="POST" style="display:none;">
            <input type="hidden" name="action" value="fetch_tmdb">
            <input type="hidden" name="tmdb_id" id="hidden_tmdb_id">
            <input type="hidden" name="fetch_type" id="hidden_fetch_type">
        </form>
    </div>

    <!-- TMDB MANUAL ID IMPORT -->
    <div class="card p-4 mb-4 border-info shadow">
        <h4 class="text-info fw-bold mb-3"><i class="fas fa-hashtag"></i> TMDB ID দিয়ে ইম্পোর্ট</h4>
        <form method="POST" class="row align-items-end">
            <input type="hidden" name="action" value="fetch_tmdb">
            <div class="col-md-5 mb-2">
                <label>TMDB ID</label>
                <input type="text" name="tmdb_id" class="form-control" required placeholder="Ex: 299534">
            </div>
            <div class="col-md-4 mb-2">
                <label>Type</label>
                <select name="fetch_type" class="form-select">
                    <option value="movie">Movie</option>
                    <option value="tv">TV Series / Drama</option>
                </select>
            </div>
            <div class="col-md-3 mb-2">
                <button type="submit" class="btn btn-info w-100 fw-bold text-dark"><i class="fas fa-cloud-download-alt"></i> Fetch Data</button>
            </div>
        </form>
    </div>

    <!-- MANUAL POST ADD -->
    <div class="card p-4 shadow">
        <h4 class="text-warning fw-bold mb-3"><i class="fas fa-edit"></i> Manual Publish</h4>
        <form method="POST">
            <input type="hidden" name="action" value="manual_add">
            <div class="row">
                <div class="col-md-6 mb-3"><label>Title</label><input type="text" name="title" class="form-control" required></div>
                <div class="col-md-3 mb-3">
                    <label>Type</label>
                    <select name="type" class="form-select">
                        <option value="Movie">Movie</option><option value="Series">Series</option><option value="Drama">Drama</option>
                    </select>
                </div>
                <div class="col-md-3 mb-3"><label>Badge</label><select name="badge" class="form-select"><option value="">No Badge</option>{% for b in badges %}<option value="{{b.value}}">{{b.value}}</option>{% endfor %}</select></div>
                
                <div class="col-md-6 mb-3"><label>Poster URL (Portrait)</label><input type="url" name="poster" class="form-control" required></div>
                <div class="col-md-6 mb-3"><label>Backdrop URL (Landscape)</label><input type="url" name="backdrop" class="form-control" placeholder="Optional (Fallback to Poster)"></div>
                
                <div class="col-md-6 mb-3"><label>Quality</label><select name="quality" class="form-select"><option value="">Select..</option>{% for q in qualities %}<option value="{{q.value}}">{{q.value}}</option>{% endfor %}</select></div>
                <div class="col-md-6 mb-3"><label>Language</label><select name="language" class="form-select"><option value="">Select..</option>{% for l in langs %}<option value="{{l.value}}">{{l.value}}</option>{% endfor %}</select></div>
                
                <div class="col-12 mb-3">
                    <label>Categories</label><br>
                    {% for c in cats %}
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="checkbox" name="categories" value="{{ c.value }}">
                            <label class="form-check-label">{{ c.value }}</label>
                        </div>
                    {% endfor %}
                </div>
                <div class="col-12 mb-3"><label>Description</label><textarea name="description" class="form-control" rows="3"></textarea></div>
            </div>
            
            <h5 class="mt-3 border-bottom border-secondary pb-2">Download Links (Unlimited)</h5>
            <div id="linkContainer">
                <div class="input-group mb-2 mt-2">
                    <select name="link_name[]" class="form-select" required>
                        <option value="">Select Name...</option>
                        {% for lnk in link_names %}<option value="{{ lnk.value }}">{{ lnk.value }}</option>{% endfor %}
                    </select>
                    <select name="link_quality[]" class="form-select">
                        <option value="">Quality...</option>
                        {% for q in qualities %}<option value="{{ q.value }}">{{ q.value }}</option>{% endfor %}
                    </select>
                    <input type="url" name="link_url[]" class="form-control" placeholder="URL Link">
                    <button type="button" class="btn btn-success" onclick="addLinkField('linkContainer', 'link_name[]', 'link_quality[]', 'link_url[]')"><i class="fas fa-plus"></i></button>
                </div>
            </div>
            <button type="submit" class="btn btn-primary w-100 mt-4 fw-bold fs-5">Publish Manual Post</button>
        </form>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', """
    <script>
        const linkNameOpts = `<option value="">Select Name...</option>{% for lnk in link_names %}<option value="{{ lnk.value }}">{{ lnk.value }}</option>{% endfor %}`;
        const qualOpts = `<option value="">Quality...</option>{% for q in qualities %}<option value="{{ q.value }}">{{ q.value }}</option>{% endfor %}`;

        function addLinkField(containerId, nameAttr, qualAttr, urlAttr) {
            let div = document.createElement('div');
            div.className = "input-group mb-2 mt-2";
            div.innerHTML = `
                <select name="${nameAttr}" class="form-select" required>${linkNameOpts}</select>
                <select name="${qualAttr}" class="form-select">${qualOpts}</select>
                <input type="url" name="${urlAttr}" class="form-control" placeholder="URL" required>
                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
            document.getElementById(containerId).appendChild(div);
        }

        const searchInput = document.getElementById('liveSearchInput');
        const searchResults = document.getElementById('liveSearchResults');
        
        let timeout = null;
        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            const query = this.value;
            if(query.length < 2) {
                searchResults.style.display = 'none';
                return;
            }
            timeout = setTimeout(() => {
                fetch(`/admin/tmdb_search?q=${query}`)
                .then(res => res.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    if(data.length > 0) {
                        data.forEach(item => {
                            const btn = document.createElement('button');
                            btn.className = "list-group-item list-group-item-action d-flex align-items-center bg-dark text-white border-secondary";
                            btn.innerHTML = `
                                <img src="${item.poster}" alt="poster" width="40" class="me-3 rounded">
                                <div>
                                    <h6 class="mb-0 fw-bold">${item.title} <span class="badge bg-secondary ms-2">${item.type.toUpperCase()}</span></h6>
                                    <small class="text-muted">${item.date || 'N/A'}</small>
                                </div>
                                <span class="ms-auto btn btn-sm btn-success fw-bold">Import</span>
                            `;
                            btn.onclick = () => {
                                document.getElementById('hidden_tmdb_id').value = item.id;
                                document.getElementById('hidden_fetch_type').value = item.type;
                                document.getElementById('hiddenImportForm').submit();
                            };
                            searchResults.appendChild(btn);
                        });
                        searchResults.style.display = 'block';
                    } else {
                        searchResults.innerHTML = '<div class="list-group-item bg-dark text-white border-secondary">কোনো রেজাল্ট পাওয়া যায়নি! API Key চেক করুন।</div>';
                        searchResults.style.display = 'block';
                    }
                });
            }, 500);
        });
        
        document.addEventListener('click', function(e) {
            if(e.target !== searchInput && !searchResults.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });
    </script>
    """)
    return render_template_string(html, badges=badges, qualities=qualities, langs=langs, cats=cats, link_names=link_names, db=db)

@app.route('/admin/edit_movie/<id>', methods=['GET', 'POST'])
@login_required
def edit_movie(id):
    movie = movies_col.find_one({"_id": ObjectId(id)})
    
    if request.method == 'POST':
        clear_cache() # Clear cache on edit
        update_data = {
            "title": request.form.get('title'),
            "poster": request.form.get('poster'),
            "backdrop": request.form.get('backdrop'),
            "badge": request.form.get('badge'),
            "quality": request.form.get('quality'),
            "language": request.form.get('language'),
            "description": request.form.get('description'),
            "categories": request.form.getlist('categories')
        }
        
        if movie['type'] == 'Movie':
            l_names = request.form.getlist('link_name[]')
            l_quals = request.form.getlist('link_quality[]')
            l_urls = request.form.getlist('link_url[]')
            update_data['links'] = [{"name": n, "quality": q, "url": u} for n, q, u in zip(l_names, l_quals, l_urls) if n and u]
        else:
            seasons = movie.get('seasons', [])
            for s in seasons:
                for ep in s['episodes']:
                    # Update Episode Poster manually if changed
                    ep['poster'] = request.form.get(f"ep_poster_S{s['season']}_E{ep['episode']}", "")
                    
                    l_names = request.form.getlist(f"link_name_S{s['season']}_E{ep['episode']}[]")
                    l_quals = request.form.getlist(f"link_quality_S{s['season']}_E{ep['episode']}[]")
                    l_urls = request.form.getlist(f"link_url_S{s['season']}_E{ep['episode']}[]")
                    ep['links'] = [{"name": n, "quality": q, "url": u} for n, q, u in zip(l_names, l_quals, l_urls) if n and u]
            update_data['seasons'] = seasons
            
        movies_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash("আপডেট সফলভাবে সেভ হয়েছে!")
        return redirect(f"/admin/edit_movie/{id}")

    badges = list(options_col.find({"type": "badge"}))
    qualities = list(options_col.find({"type": "quality"}))
    langs = list(options_col.find({"type": "language"}))
    cats = list(options_col.find({"type": "category"}))
    link_names = list(options_col.find({"type": "link_name"}))

    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-warning border-4 ps-2 mb-4">Edit: <span class="text-primary">{{ m.title }}</span></h2>
    
    <div class="card p-4">
        <form method="POST">
            <div class="row">
                <div class="col-md-12 mb-3"><label>Title</label><input type="text" name="title" class="form-control" value="{{ m.title }}"></div>
                <div class="col-md-6 mb-3"><label>Poster URL (Portrait)</label><input type="text" name="poster" class="form-control" value="{{ m.poster }}"></div>
                <div class="col-md-6 mb-3"><label>Backdrop URL (Landscape)</label><input type="text" name="backdrop" class="form-control" value="{{ m.backdrop | default(m.poster) }}"></div>
                
                <div class="col-4 mb-3"><label>Badge</label><select name="badge" class="form-select"><option value="">No Badge</option>{% for b in badges %}<option value="{{b.value}}" {% if m.badge==b.value %}selected{% endif %}>{{b.value}}</option>{% endfor %}</select></div>
                <div class="col-4 mb-3"><label>Quality</label><select name="quality" class="form-select"><option value="">Select..</option>{% for q in qualities %}<option value="{{q.value}}" {% if m.quality==q.value %}selected{% endif %}>{{q.value}}</option>{% endfor %}</select></div>
                <div class="col-4 mb-3"><label>Language</label><select name="language" class="form-select"><option value="">Select..</option>{% for l in langs %}<option value="{{l.value}}" {% if m.language==l.value %}selected{% endif %}>{{l.value}}</option>{% endfor %}</select></div>
                
                <div class="col-12 mb-3">
                    <label>Categories</label><br>
                    {% for c in cats %}
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="checkbox" name="categories" value="{{ c.value }}" {% if m.categories and c.value in m.categories %}checked{% endif %}>
                            <label class="form-check-label">{{ c.value }}</label>
                        </div>
                    {% endfor %}
                </div>
                <div class="col-12 mb-3"><label>Description</label><textarea name="description" class="form-control" rows="4">{{ m.description }}</textarea></div>
            </div>
            
            <hr class="border-secondary my-4">
            
            {% if m.type == 'Movie' %}
                <h4 class="mb-3 text-info fw-bold">Download Links</h4>
                <div id="movieLinks">
                    {% for link in m.links %}
                    <div class="input-group mb-2">
                        <select name="link_name[]" class="form-select" required>
                            <option value="">Select Name...</option>
                            {% for lnk in link_names %}<option value="{{lnk.value}}" {% if link.name == lnk.value %}selected{% endif %}>{{lnk.value}}</option>{% endfor %}
                        </select>
                        <select name="link_quality[]" class="form-select">
                            <option value="">Quality...</option>
                            {% for q in qualities %}<option value="{{q.value}}" {% if link.quality == q.value %}selected{% endif %}>{{q.value}}</option>{% endfor %}
                        </select>
                        <input type="url" name="link_url[]" class="form-control" value="{{ link.url }}" required>
                        <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                    </div>
                    {% endfor %}
                </div>
                <button type="button" class="btn btn-success btn-sm mb-3 mt-2" onclick="addLinkField('movieLinks', 'link_name[]', 'link_quality[]', 'link_url[]')"><i class="fas fa-plus"></i> Add Link</button>
            {% else %}
                <h4 class="mb-3 text-info fw-bold">Seasons & Episodes Links</h4>
                <div class="accordion text-dark" id="adminSeasons">
                    {% for s in m.seasons %}
                    <div class="accordion-item mb-2 border-0 bg-transparent">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed bg-dark text-white border border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#col_S{{ s.season }}">
                                Season {{ "%02d"|format(s.season|int) }}
                            </button>
                        </h2>
                        <div id="col_S{{ s.season }}" class="accordion-collapse collapse" data-bs-parent="#adminSeasons">
                            <div class="accordion-body bg-black text-white rounded border border-secondary mt-1">
                                {% for ep in s.episodes %}
                                    <div class="mb-3 p-3 border border-secondary rounded" style="background:#151b2b;">
                                        <h5 class="text-warning">Episode {{ "%02d"|format(ep.episode|int) }}</h5>
                                        
                                        <!-- Editable Episode Poster Field -->
                                        <input type="text" name="ep_poster_S{{ s.season }}_E{{ ep.episode }}" class="form-control form-control-sm mb-3" value="{{ ep.poster | default('') }}" placeholder="Episode Thumbnail URL (Optional)">
                                        
                                        <div id="links_S{{ s.season }}_E{{ ep.episode }}">
                                            {% for link in ep.links %}
                                            <div class="input-group mb-2 mt-2">
                                                <select name="link_name_S{{ s.season }}_E{{ ep.episode }}[]" class="form-select" required>
                                                    <option value="">Select Name...</option>
                                                    {% for lnk in link_names %}<option value="{{lnk.value}}" {% if link.name == lnk.value %}selected{% endif %}>{{lnk.value}}</option>{% endfor %}
                                                </select>
                                                <select name="link_quality_S{{ s.season }}_E{{ ep.episode }}[]" class="form-select">
                                                    <option value="">Quality...</option>
                                                    {% for q in qualities %}<option value="{{q.value}}" {% if link.quality == q.value %}selected{% endif %}>{{q.value}}</option>{% endfor %}
                                                </select>
                                                <input type="url" name="link_url_S{{ s.season }}_E{{ ep.episode }}[]" class="form-control" value="{{ link.url }}" required>
                                                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                                            </div>
                                            {% endfor %}
                                        </div>
                                        <button type="button" class="btn btn-outline-success btn-sm mt-2" onclick="addLinkField('links_S{{ s.season }}_E{{ ep.episode }}', 'link_name_S{{ s.season }}_E{{ ep.episode }}[]', 'link_quality_S{{ s.season }}_E{{ ep.episode }}[]', 'link_url_S{{ s.season }}_E{{ ep.episode }}[]')"><i class="fas fa-plus"></i> Add Link</button>
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% endif %}
            
            <button type="submit" class="btn btn-primary w-100 fw-bold fs-5 mt-4">Save All Changes</button>
        </form>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', """
    <script>
        const linkNameOpts = `<option value="">Select Name...</option>{% for lnk in link_names %}<option value="{{ lnk.value }}">{{ lnk.value }}</option>{% endfor %}`;
        const qualOpts = `<option value="">Quality...</option>{% for q in qualities %}<option value="{{ q.value }}">{{ q.value }}</option>{% endfor %}`;

        function addLinkField(containerId, nameAttr, qualAttr, urlAttr) {
            let div = document.createElement('div');
            div.className = "input-group mb-2 mt-2";
            div.innerHTML = `
                <select name="${nameAttr}" class="form-select" required>${linkNameOpts}</select>
                <select name="${qualAttr}" class="form-select">${qualOpts}</select>
                <input type="url" name="${urlAttr}" class="form-control" placeholder="URL" required>
                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
            document.getElementById(containerId).appendChild(div);
        }
    </script>
    """)
    return render_template_string(html, m=movie, badges=badges, qualities=qualities, langs=langs, cats=cats, link_names=link_names, db=db)

@app.route('/admin/all_movies')
@login_required
def all_movies():
    movies = list(movies_col.find().sort('_id', -1))
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">লিস্ট ও ডিলেট ম্যানেজমেন্ট</h2>
    <div class="card p-4 shadow">
        <div class="d-flex flex-wrap justify-content-between mb-3 gap-2">
            <button class="btn btn-danger fw-bold" onclick="deleteSelected()"><i class="fas fa-trash"></i> Delete Selected</button>
            <input type="text" id="searchInput" class="form-control" style="max-width:300px;" placeholder="Search by name..." onkeyup="filterTable()">
        </div>
        <div class="table-responsive">
            <table class="table table-dark table-hover border-secondary align-middle" id="movieTable">
                <thead>
                    <tr class="text-info">
                        <th><input type="checkbox" class="form-check-input" onclick="toggleAll(this)"> All</th>
                        <th>Poster</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Views</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for m in movies %}
                    <tr>
                        <td><input type="checkbox" class="form-check-input movie-checkbox" value="{{ m._id }}"></td>
                        <td><img src="{{ m.poster }}" width="50" height="70" class="rounded" style="object-fit:cover;"></td>
                        <td class="fw-bold">{{ m.title }}</td>
                        <td><span class="badge bg-secondary">{{ m.type }}</span></td>
                        <td>{{ m.views | default(0) }}</td>
                        <td>
                            <a href="/admin/edit_movie/{{ m._id }}" class="btn btn-sm btn-primary"><i class="fas fa-edit"></i> Edit</a>
                            <a href="/admin/delete_movie/{{ m._id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Are you sure?')"><i class="fas fa-trash"></i></a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="mt-2">
            <button class="btn btn-danger fw-bold" onclick="deleteSelected()"><i class="fas fa-trash"></i> Delete Selected (Bottom)</button>
        </div>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', """
    <script>
        function filterTable() {
            let input = document.getElementById("searchInput").value.toLowerCase();
            let rows = document.querySelectorAll("#movieTable tbody tr");
            rows.forEach(row => { row.style.display = row.innerText.toLowerCase().includes(input) ? "" : "none"; });
        }
        function toggleAll(source) {
            document.querySelectorAll('.movie-checkbox').forEach(cb => cb.checked = source.checked);
        }
        function deleteSelected() {
            let selected = [];
            document.querySelectorAll('.movie-checkbox:checked').forEach(cb => selected.push(cb.value));
            if(selected.length > 0 && confirm("নির্বাচিত মুভিগুলো ডিলেট করতে চান?")) {
                fetch('/admin/delete_multiple', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ids: selected}) })
                .then(() => window.location.reload());
            } else if (selected.length === 0) { alert("কোনো মুভি সিলেক্ট করা হয়নি!"); }
        }
    </script>
    """)
    return render_template_string(html, movies=movies)

@app.route('/admin/delete_movie/<id>')
@login_required
def delete_movie(id):
    clear_cache()
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('all_movies'))

@app.route('/admin/delete_multiple', methods=['POST'])
@login_required
def delete_multiple():
    clear_cache()
    data = request.json
    ids = [ObjectId(i) for i in data.get('ids', [])]
    movies_col.delete_many({"_id": {"$in": ids}})
    return jsonify({"status": "success"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
