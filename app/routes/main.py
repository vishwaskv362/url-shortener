from flask import render_template, redirect, request, flash, url_for
from app.routes import main_bp
from app.services.url_service import URLService


@main_bp.route('/')
def index():
    """Home page with URL shortening form."""
    return render_template('index.html')


@main_bp.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect short code to original URL."""
    success, result = URLService.get_original_url(short_code)
    
    if not success:
        return render_template('error.html', message=result), 404
    
    # Track the click
    URLService.track_click(result, request)
    
    # Redirect to original URL
    return redirect(result.original_url, code=302)


@main_bp.route('/dashboard')
def dashboard():
    """Display dashboard with all shortened URLs."""
    page = request.args.get('page', 1, type=int)
    success, result = URLService.get_all_urls(page=page, per_page=20)
    
    if not success:
        return render_template('error.html', message=result), 500
    
    return render_template('dashboard.html', data=result)


@main_bp.route('/stats/<short_code>')
def url_stats(short_code):
    """Display statistics for a shortened URL."""
    success, result = URLService.get_url_stats(short_code)
    
    if not success:
        return render_template('error.html', message=result), 404
    
    return render_template('stats.html', stats=result)
