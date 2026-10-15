from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, session
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import os

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

# Initialize default settings and admin credentials
if not settings_col.find_one({"type": "general"}):
    settings_col.insert_one({
        "type": "general",
        "ad_status": "off",
        "ad_code": "",
        "direct_link": "",
        "notice": "Welcome to our Premium Movie Site!",
        "popup_notice": "Join our Telegram Group!",
        "telegram_link": "https://t.me/yourchannel",
        "tmdb_api_key": "",
        "admin_user": "admin",
        "admin_pass": "admin"
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DooPlay Pro - Movie Site</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #0b0f19; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar { background-color: #151b2b; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .search-bar { max-width: 400px; width: 100%; }
        
        .movie-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; padding: 20px 0; }
        @media (min-width: 768px) { .movie-grid { grid-template-columns: repeat(4, 1fr); } }
        
        .movie-card { background: #1e2738; border-radius: 8px; overflow: hidden; position: relative; transition: transform 0.3s ease, box-shadow 0.3s ease; border: 1px solid #2d3748; }
        .movie-card:hover { transform: scale(1.03); box-shadow: 0 8px 15px rgba(0,123,255,0.3); }
        .movie-poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
        
        .movie-badge { position: absolute; top: 10px; right: 10px; background: #e50914; color: #fff; padding: 4px 10px; font-size: 11px; border-radius: 4px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.5); z-index: 2;}
        .movie-quality { position: absolute; top: 10px; left: 10px; background: #007bff; color: #fff; padding: 4px 10px; font-size: 11px; border-radius: 4px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.5); z-index: 2;}
        .movie-views { position: absolute; bottom: 65px; left: 10px; background: rgba(0,0,0,0.7); color: #fff; padding: 2px 8px; font-size: 11px; border-radius: 4px; z-index: 2; }
        
        .movie-info { padding: 12px; text-align: center; }
        .movie-title { font-size: 15px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #e2e8f0; }
        
        .btn-horizontal-scroll { display: flex; overflow-x: auto; gap: 10px; padding-bottom: 12px; white-space: nowrap; align-items: center; }
        .btn-horizontal-scroll::-webkit-scrollbar { height: 8px; }
        .btn-horizontal-scroll::-webkit-scrollbar-thumb { background-color: #007bff; border-radius: 10px; }
        .btn-horizontal-scroll::-webkit-scrollbar-track { background: #151b2b; }
        .custom-dl-btn { min-width: 140px; text-align: center; font-weight: bold; border-radius: 25px; transition: 0.3s; }
        .custom-dl-btn:hover { transform: translateY(-2px); }

        .telegram-float { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background-color: #0088cc; color: #FFF; border-radius: 50%; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; font-size: 30px; text-decoration: none; transition: 0.3s;}
        .telegram-float:hover { transform: scale(1.1); background-color: #0077b3; color: white; }
        
        .accordion-button { background-color: #1e2738; color: white; font-weight: bold; }
        .accordion-button:not(.collapsed) { background-color: #007bff; color: white; }
        .accordion-body { background-color: #0b0f19; border: 1px solid #1e2738; }
        .ep-box { background: #151b2b; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #007bff; }
        
        .cat-scroll { display: flex; overflow-x: auto; gap: 10px; padding: 10px 0; }
        .cat-scroll::-webkit-scrollbar { display: none; }
        .cat-badge { background: #1e2738; color: #fff; padding: 5px 15px; border-radius: 20px; text-decoration: none; font-size: 13px; border: 1px solid #2d3748;}
        .cat-badge:hover { background: #007bff; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark sticky-top">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/"><i class="fas fa-play text-primary"></i> DooPlay</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navMenu">
                <form action="/search" method="GET" class="d-flex mx-auto search-bar mt-3 mt-lg-0">
                    <input class="form-control me-2 bg-dark text-white border-secondary" type="search" name="q" placeholder="Search Movies, Series..." required>
                    <button class="btn btn-primary" type="submit"><i class="fas fa-search"></i></button>
                </form>
                <ul class="navbar-nav ms-auto mt-3 mt-lg-0">
                    <li class="nav-item"><a class="nav-link text-white" href="/admin"><i class="fas fa-user-shield text-warning"></i> Admin</a></li>
                </ul>
            </div>
        </div>
    </nav>
    
    {% set settings = db.settings.find_one({"type": "general"}) %}
    
    <div class="container mt-3">
        {% if settings.notice %}<div class="alert alert-info text-center shadow-sm" style="background:#1e2738; color:#fff; border:none;"><i class="fas fa-bell text-warning"></i> {{ settings.notice }}</div>{% endif %}
        {% if settings.ad_code %}<div class="text-center mb-3">{{ settings.ad_code | safe }}</div>{% endif %}
    </div>

    <!-- Error Fixed Here -->
    <div class="container">
        <!-- CONTENT_BLOCK -->
    </div>

    {% if settings.telegram_link %}
        <a href="{{ settings.telegram_link }}" target="_blank" class="telegram-float"><i class="fab fa-telegram-plane"></i></a>
    {% endif %}
    
    {% if settings.popup_notice %}
    <div class="modal fade" id="popupModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="background:#151b2b; color:#fff; border: 1px solid #007bff;">
                <div class="modal-header border-0">
                    <h5 class="modal-title text-warning"><i class="fas fa-bullhorn"></i> Notice</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <p>{{ settings.popup_notice }}</p>
                    {% if settings.telegram_link %}
                        <a href="{{ settings.telegram_link }}" target="_blank" class="btn btn-primary rounded-pill px-4 mt-2"><i class="fab fa-telegram"></i> Join Now</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    {% endif %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        {% if settings.popup_notice %}
        window.onload = () => {
            if(!sessionStorage.getItem('popupShown')) {
                new bootstrap.Modal(document.getElementById('popupModal')).show();
                sessionStorage.setItem('popupShown', 'true');
            }
        };
        {% endif %}

        const adStatus = "{{ settings.ad_status }}";
        const directLink = "{{ settings.direct_link }}";
        function checkAd(event, url) {
            if(adStatus === 'on' && directLink) {
                event.preventDefault();
                window.open(directLink, '_blank');
                setTimeout(() => { window.location.href = url; }, 1000);
            }
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - DooPlay Pro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #0b0f19; color: #fff; font-family: 'Segoe UI', sans-serif; }
        .sidebar { min-height: 100vh; background-color: #151b2b; padding-top: 20px; border-right: 1px solid #2d3748; }
        .sidebar a { color: #8c98a4; text-decoration: none; padding: 15px 20px; display: block; font-weight: 500; transition: 0.3s; font-size: 15px; }
        .sidebar a:hover, .sidebar a.active { background-color: #1e2738; color: #007bff; border-left: 4px solid #007bff; }
        .content { padding: 30px; }
        .card { background-color: #151b2b; border: 1px solid #2d3748; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
        .form-control, .form-select { background-color: #0b0f19; border: 1px solid #2d3748; color: #fff; }
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
                
                <!-- Error Fixed Here -->
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
    movies = list(movies_col.find().sort('_id', -1).limit(40))
    categories = list(options_col.find({"type": "category"}))
    
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <div class="cat-scroll mb-3">
        <a href="/" class="cat-badge bg-primary text-white">All</a>
        {% for c in categories %}
            <a href="/category/{{ c.value }}" class="cat-badge">{{ c.value }}</a>
        {% endfor %}
    </div>

    <h4 class="mb-3 border-start border-primary border-4 ps-2 fw-bold text-uppercase">Latest Updates</h4>
    <div class="movie-grid">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none">
            <div class="movie-card">
                {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                {% if m.quality %}<span class="movie-quality">{{ m.quality }}</span>{% endif %}
                <span class="movie-views"><i class="fas fa-eye"></i> {{ m.views | default(0) }}</span>
                <img src="{{ m.poster }}" alt="{{ m.title }}" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                    <small class="text-muted">{{ m.type }} {% if m.language %}• {{ m.language }}{% endif %}</small>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    {% if not movies %}
        <div class="alert alert-secondary text-center mt-5">কোনো মুভি পাওয়া যায়নি!</div>
    {% endif %}
    """)
    return render_template_string(html, movies=movies, categories=categories, db=db)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    movies = list(movies_col.find({"title": {"$regex": query, "$options": "i"}}).sort('_id', -1))
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h4 class="mb-3 border-start border-primary border-4 ps-2">Search Results for: <span class="text-warning">{{ query }}</span></h4>
    <div class="movie-grid">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="text-decoration-none">
            <div class="movie-card">
                {% if m.badge %}<span class="movie-badge">{{ m.badge }}</span>{% endif %}
                <img src="{{ m.poster }}" class="movie-poster">
                <div class="movie-info">
                    <div class="movie-title">{{ m.title }}</div>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    {% if not movies %}<h5 class="text-center text-muted mt-5">No results found!</h5>{% endif %}
    """)
    return render_template_string(html, movies=movies, query=query, db=db)

@app.route('/category/<cat_name>')
def category_filter(cat_name):
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
        <a href="/movie/{{ m._id }}" class="text-decoration-none">
            <div class="movie-card"><img src="{{ m.poster }}" class="movie-poster"><div class="movie-info"><div class="movie-title">{{ m.title }}</div></div></div>
        </a>
        {% endfor %}
    </div>
    """)
    return render_template_string(html, movies=movies, cat_name=cat_name, categories=categories, db=db)

@app.route('/movie/<id>')
def movie_details(id):
    movies_col.update_one({"_id": ObjectId(id)}, {"$inc": {"views": 1}})
    movie = movies_col.find_one({"_id": ObjectId(id)})
    
    html = FRONTEND_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <div class="row mt-4">
        <div class="col-md-3 col-lg-3 text-center mb-4">
            <div class="position-relative d-inline-block w-100">
                <img src="{{ m.poster }}" class="img-fluid rounded shadow-lg w-100 border border-secondary" alt="Poster" style="max-height: 450px; object-fit: cover;">
                {% if m.badge %}<span class="movie-badge" style="font-size: 14px; padding: 5px 15px;">{{ m.badge }}</span>{% endif %}
            </div>
            <div class="mt-3 text-muted"><i class="fas fa-eye text-primary"></i> Total Views: {{ m.views }}</div>
        </div>
        
        <div class="col-md-9 col-lg-9">
            <h1 class="fw-bold text-white mb-3">{{ m.title }}</h1>
            <div class="mb-3 d-flex flex-wrap gap-2">
                <span class="badge bg-danger fs-6"><i class="fas fa-video"></i> {{ m.type }}</span>
                {% if m.quality %}<span class="badge bg-primary fs-6">{{ m.quality }}</span>{% endif %}
                {% if m.language %}<span class="badge bg-success fs-6"><i class="fas fa-language"></i> {{ m.language }}</span>{% endif %}
                {% for cat in m.categories %}
                    <span class="badge bg-secondary fs-6">{{ cat }}</span>
                {% endfor %}
            </div>
            
            <p class="text-light" style="font-size: 15px; line-height: 1.6; opacity: 0.9;">{{ m.description }}</p>
            <hr class="border-secondary">
            
            {% if m.type == 'Movie' %}
                <h4 class="mb-3 fw-bold border-start border-warning border-4 ps-2">Download & Watch Links</h4>
                <div class="btn-horizontal-scroll">
                    {% if m.links %}
                        {% for link in m.links %}
                        <a href="{{ link.url }}" onclick="checkAd(event, '{{ link.url }}')" class="btn btn-outline-info custom-dl-btn">
                            {% if 'online' in link.name.lower() or 'watch' in link.name.lower() %}<i class="fas fa-play-circle"></i>
                            {% elif 'telegram' in link.name.lower() %}<i class="fab fa-telegram"></i>
                            {% else %}<i class="fas fa-download"></i>{% endif %}
                            {{ link.name }}
                        </a>
                        {% endfor %}
                    {% else %}
                        <div class="alert alert-secondary w-100">No links available yet.</div>
                    {% endif %}
                </div>
            {% else %}
                <h4 class="mb-3 fw-bold border-start border-warning border-4 ps-2">Seasons & Episodes</h4>
                <div class="accordion shadow-sm" id="seasonsAccordion">
                    {% for s in m.seasons %}
                    <div class="accordion-item mb-2 border-0 bg-transparent">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed rounded" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS{{ s.season }}">
                                <i class="fas fa-folder-open me-2 text-warning"></i> Season {{ s.season }}
                            </button>
                        </h2>
                        <div id="collapseS{{ s.season }}" class="accordion-collapse collapse mt-1" data-bs-parent="#seasonsAccordion">
                            <div class="accordion-body rounded">
                                {% for ep in s.episodes %}
                                    <div class="ep-box">
                                        <h6 class="text-white fw-bold mb-2">Episode {{ ep.episode }}</h6>
                                        <div class="btn-horizontal-scroll pb-0">
                                            {% if ep.links %}
                                                {% for link in ep.links %}
                                                <a href="{{ link.url }}" onclick="checkAd(event, '{{ link.url }}')" class="btn btn-outline-primary btn-sm custom-dl-btn">
                                                    {{ link.name }}
                                                </a>
                                                {% endfor %}
                                            {% else %}
                                                <span class="text-muted small">No links available.</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    </div>
    """)
    return render_template_string(html, m=movie, db=db)

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
    <!DOCTYPE html><html data-bs-theme="dark"><head><title>Admin Login</title>
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
        settings_col.update_one({"type": "general"}, {"$set": {
            "ad_status": request.form.get('ad_status'),
            "direct_link": request.form.get('direct_link'),
            "ad_code": request.form.get('ad_code'),
            "telegram_link": request.form.get('telegram_link'),
            "notice": request.form.get('notice'),
            "popup_notice": request.form.get('popup_notice'),
            "tmdb_api_key": request.form.get('tmdb_api_key'),
            "admin_user": request.form.get('admin_user'),
            "admin_pass": request.form.get('admin_pass')
        }})
        flash("সেটিংস সফলভাবে আপডেট হয়েছে!")
        return redirect(url_for('admin_settings'))
    
    s = settings_col.find_one({"type": "general"})
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">সেটিংস ও এডস প্যানেল</h2>
    <form method="POST" class="card p-4">
        <h5 class="text-warning border-bottom border-secondary pb-2"><i class="fas fa-shield-alt"></i> Security / API</h5>
        <div class="row mb-4">
            <div class="col-md-4 mb-2"><label>Admin Username</label><input type="text" name="admin_user" class="form-control" value="{{ s.admin_user }}" required></div>
            <div class="col-md-4 mb-2"><label>Admin Password</label><input type="text" name="admin_pass" class="form-control" value="{{ s.admin_pass }}" required></div>
            <div class="col-md-4 mb-2"><label>TMDB API Key</label><input type="text" name="tmdb_api_key" class="form-control" value="{{ s.tmdb_api_key }}"></div>
        </div>

        <h5 class="text-info border-bottom border-secondary pb-2"><i class="fas fa-ad"></i> Ads & Links</h5>
        <div class="row mb-4">
            <div class="col-md-4 mb-2">
                <label>Direct Ad Link Status</label>
                <select name="ad_status" class="form-select">
                    <option value="on" {% if s.ad_status == 'on' %}selected{% endif %}>ON (চালু)</option>
                    <option value="off" {% if s.ad_status == 'off' %}selected{% endif %}>OFF (বন্ধ)</option>
                </select>
            </div>
            <div class="col-md-8 mb-2"><label>Direct Ad Link URL</label><input type="text" name="direct_link" class="form-control" value="{{ s.direct_link }}"></div>
            <div class="col-12 mb-2"><label>Banner Ad Code (HTML)</label><textarea name="ad_code" class="form-control" rows="3">{{ s.ad_code }}</textarea></div>
        </div>

        <h5 class="text-success border-bottom border-secondary pb-2"><i class="fas fa-bullhorn"></i> Notice & Telegram</h5>
        <div class="row mb-4">
            <div class="col-md-12 mb-2"><label>Telegram Link</label><input type="text" name="telegram_link" class="form-control" value="{{ s.telegram_link }}"></div>
            <div class="col-md-6 mb-2"><label>General Notice (Top bar)</label><input type="text" name="notice" class="form-control" value="{{ s.notice }}"></div>
            <div class="col-md-6 mb-2"><label>Popup Notice Modal</label><input type="text" name="popup_notice" class="form-control" value="{{ s.popup_notice }}"></div>
        </div>
        <button type="submit" class="btn btn-primary fw-bold px-5">Save All Settings</button>
    </form>
    """).replace('<!-- SCRIPTS_BLOCK -->', "")
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
    
    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">ক্যাটাগরি, ব্যাজ, কোয়ালিটি ও ভাষা</h2>
    <div class="card p-4">
        <form method="POST" class="d-flex gap-2 mb-4">
            <select name="type" class="form-select w-25">
                <option value="category">Category (Action..)</option>
                <option value="badge">Badge (CAM, HD..)</option>
                <option value="quality">Quality (1080p..)</option>
                <option value="language">Language (Hindi..)</option>
            </select>
            <input type="text" name="value" class="form-control w-50" placeholder="নাম লিখুন..." required>
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
        </div>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', "")
    return render_template_string(html, badges=badges, qualities=qualities, langs=langs, cats=cats)

@app.route('/admin/del_opt/<id>')
@login_required
def del_opt(id):
    options_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin_options'))

@app.route('/admin/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    settings = settings_col.find_one({"type": "general"})
    
    if request.method == 'POST':
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
                poster = f"https://image.tmdb.org/t/p/w500{res.get('poster_path')}" if res.get('poster_path') else ""
                desc = res.get('overview', '')
                
                genres = [g['name'] for g in res.get('genres', [])]
                for g in genres:
                    if not options_col.find_one({"type": "category", "value": g}):
                        options_col.insert_one({"type": "category", "value": g})
                
                new_doc = {
                    "title": title, "type": "Movie" if m_type == 'movie' else "Series",
                    "poster": poster, "description": desc,
                    "badge": "", "quality": "", "language": "English",
                    "categories": genres, "views": 0,
                    "links": []
                }
                
                if m_type == 'tv':
                    seasons = []
                    for s in res.get('seasons', []):
                        s_num = s.get('season_number')
                        if s_num > 0:
                            episodes = [{"episode": e, "links": []} for e in range(1, s.get('episode_count') + 1)]
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
            link_urls = request.form.getlist('link_url[]')
            links = [{"name": n, "url": u} for n, u in zip(link_names, link_urls) if n and u]
            
            new_doc = {
                "title": title, "type": m_type, "poster": request.form.get('poster'),
                "badge": request.form.get('badge'), "quality": request.form.get('quality'),
                "language": request.form.get('language'), "description": request.form.get('description'),
                "categories": request.form.getlist('categories'), "views": 0,
                "links": links
            }
            
            if m_type in ['Series', 'Drama']:
                new_doc['seasons'] = [{"season": 1, "episodes": [{"episode": 1, "links": links}]}]
                new_doc['links'] = []
                
            movies_col.insert_one(new_doc)
            flash("ম্যানুয়ালি ডাটা যোগ করা হয়েছে!")
            return redirect(url_for('add_movie'))

    badges = list(options_col.find({"type": "badge"}))
    qualities = list(options_col.find({"type": "quality"}))
    langs = list(options_col.find({"type": "language"}))
    cats = list(options_col.find({"type": "category"}))

    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-primary border-4 ps-2 mb-4">মুভি / সিরিজ / ড্রামা এড</h2>
    
    <div class="card p-4 mb-4 border-info shadow">
        <h4 class="text-info fw-bold mb-3"><i class="fas fa-magic"></i> ১ ক্লিকে Auto TMDB Import</h4>
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
                
                <div class="col-md-12 mb-3"><label>Poster URL</label><input type="url" name="poster" class="form-control" required></div>
                
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
                <div class="input-group mb-2">
                    <input type="text" name="link_name[]" class="form-control" placeholder="Name (Watch Online, Download 1080p, Telegram..)">
                    <input type="url" name="link_url[]" class="form-control" placeholder="URL Link">
                    <button type="button" class="btn btn-success" onclick="addLinkField('linkContainer', 'link_name[]', 'link_url[]')"><i class="fas fa-plus"></i></button>
                </div>
            </div>
            <button type="submit" class="btn btn-primary w-100 mt-4 fw-bold fs-5">Publish Manual Post</button>
        </form>
    </div>
    """).replace('<!-- SCRIPTS_BLOCK -->', """
    <script>
        function addLinkField(containerId, nameAttr, urlAttr) {
            let div = document.createElement('div');
            div.className = "input-group mb-2";
            div.innerHTML = `<input type="text" name="${nameAttr}" class="form-control" placeholder="Button Name">
                             <input type="url" name="${urlAttr}" class="form-control" placeholder="URL">
                             <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
            document.getElementById(containerId).appendChild(div);
        }
    </script>
    """)
    return render_template_string(html, badges=badges, qualities=qualities, langs=langs, cats=cats)


@app.route('/admin/edit_movie/<id>', methods=['GET', 'POST'])
@login_required
def edit_movie(id):
    movie = movies_col.find_one({"_id": ObjectId(id)})
    
    if request.method == 'POST':
        update_data = {
            "title": request.form.get('title'),
            "poster": request.form.get('poster'),
            "badge": request.form.get('badge'),
            "quality": request.form.get('quality'),
            "language": request.form.get('language'),
            "description": request.form.get('description'),
            "categories": request.form.getlist('categories')
        }
        
        if movie['type'] == 'Movie':
            l_names = request.form.getlist('link_name[]')
            l_urls = request.form.getlist('link_url[]')
            update_data['links'] = [{"name": n, "url": u} for n, u in zip(l_names, l_urls) if n and u]
        else:
            seasons = movie.get('seasons', [])
            for s in seasons:
                for ep in s['episodes']:
                    l_names = request.form.getlist(f"link_name_S{s['season']}_E{ep['episode']}[]")
                    l_urls = request.form.getlist(f"link_url_S{s['season']}_E{ep['episode']}[]")
                    ep['links'] = [{"name": n, "url": u} for n, u in zip(l_names, l_urls) if n and u]
            update_data['seasons'] = seasons
            
        movies_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        flash("আপডেট সফলভাবে সেভ হয়েছে!")
        return redirect(f"/admin/edit_movie/{id}")

    badges = list(options_col.find({"type": "badge"}))
    qualities = list(options_col.find({"type": "quality"}))
    langs = list(options_col.find({"type": "language"}))
    cats = list(options_col.find({"type": "category"}))

    html = ADMIN_HTML.replace('<!-- CONTENT_BLOCK -->', """
    <h2 class="fw-bold border-start border-warning border-4 ps-2 mb-4">Edit: <span class="text-primary">{{ m.title }}</span></h2>
    <div class="card p-4">
        <form method="POST">
            <div class="row">
                <div class="col-md-12 mb-3"><label>Title</label><input type="text" name="title" class="form-control" value="{{ m.title }}"></div>
                <div class="col-md-12 mb-3"><label>Poster URL</label><input type="text" name="poster" class="form-control" value="{{ m.poster }}"></div>
                
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
                        <input type="text" name="link_name[]" class="form-control" value="{{ link.name }}">
                        <input type="url" name="link_url[]" class="form-control" value="{{ link.url }}">
                        <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                    </div>
                    {% endfor %}
                </div>
                <button type="button" class="btn btn-success btn-sm mb-3" onclick="addLinkField('movieLinks', 'link_name[]', 'link_url[]')"><i class="fas fa-plus"></i> Add Link</button>
            {% else %}
                <h4 class="mb-3 text-info fw-bold">Seasons & Episodes Links</h4>
                <div class="accordion text-dark" id="adminSeasons">
                    {% for s in m.seasons %}
                    <div class="accordion-item mb-2 border-0 bg-transparent">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed bg-dark text-white border border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#col_S{{ s.season }}">
                                Season {{ s.season }}
                            </button>
                        </h2>
                        <div id="col_S{{ s.season }}" class="accordion-collapse collapse" data-bs-parent="#adminSeasons">
                            <div class="accordion-body bg-black text-white rounded border border-secondary mt-1">
                                {% for ep in s.episodes %}
                                    <div class="mb-3 p-3 border border-secondary rounded" style="background:#151b2b;">
                                        <h5 class="text-warning">Episode {{ ep.episode }}</h5>
                                        <div id="links_S{{ s.season }}_E{{ ep.episode }}">
                                            {% for link in ep.links %}
                                            <div class="input-group mb-2">
                                                <input type="text" name="link_name_S{{ s.season }}_E{{ ep.episode }}[]" class="form-control" value="{{ link.name }}">
                                                <input type="url" name="link_url_S{{ s.season }}_E{{ ep.episode }}[]" class="form-control" value="{{ link.url }}">
                                                <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                                            </div>
                                            {% endfor %}
                                        </div>
                                        <button type="button" class="btn btn-outline-success btn-sm mt-2" onclick="addLinkField('links_S{{ s.season }}_E{{ ep.episode }}', 'link_name_S{{ s.season }}_E{{ ep.episode }}[]', 'link_url_S{{ s.season }}_E{{ ep.episode }}[]')"><i class="fas fa-plus"></i> Add Link</button>
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
        function addLinkField(containerId, nameAttr, urlAttr) {
            let div = document.createElement('div');
            div.className = "input-group mb-2 mt-2";
            div.innerHTML = `<input type="text" name="${nameAttr}" class="form-control" placeholder="Button Name">
                             <input type="url" name="${urlAttr}" class="form-control" placeholder="URL">
                             <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
            document.getElementById(containerId).appendChild(div);
        }
    </script>
    """)
    return render_template_string(html, m=movie, badges=badges, qualities=qualities, langs=langs, cats=cats)

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
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('all_movies'))

@app.route('/admin/delete_multiple', methods=['POST'])
@login_required
def delete_multiple():
    data = request.json
    ids = [ObjectId(i) for i in data.get('ids', [])]
    movies_col.delete_many({"_id": {"$in": ids}})
    return jsonify({"status": "success"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
