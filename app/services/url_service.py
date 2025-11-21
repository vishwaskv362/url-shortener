from app import db
from app.models import URL, Click
from app.utils.short_code import ShortCodeGenerator
from datetime import datetime
import validators
from flask import current_app


class URLService:
    """Business logic for URL shortening operations."""
    
    @staticmethod
    def validate_url(url):
        """Validate if the provided string is a valid URL."""
        if not url or len(url) > current_app.config.get('MAX_URL_LENGTH', 2048):
            return False, "URL is required and must be less than 2048 characters"
        
        if not validators.url(url):
            return False, "Invalid URL format"
        
        return True, "Valid URL"
    
    @staticmethod
    def create_short_url(original_url, custom_code=None, expires_at=None):
        """
        Create a shortened URL.
        
        Args:
            original_url: The original long URL
            custom_code: Optional custom short code
            expires_at: Optional expiration datetime
            
        Returns:
            tuple: (success: bool, result: dict/str)
        """
        # Validate URL
        is_valid, message = URLService.validate_url(original_url)
        if not is_valid:
            return False, message
        
        # Check if URL already exists (return existing short URL)
        # Only if it's not expired and not a custom code request
        if not custom_code:
            existing_url = URL.query.filter_by(original_url=original_url).first()
            if existing_url:
                # Check if it's expired
                if not existing_url.expires_at or existing_url.expires_at > datetime.utcnow():
                    return True, {
                        'url': existing_url.to_dict(),
                        'short_url': f"{current_app.config['BASE_URL']}/{existing_url.short_code}",
                        'message': 'This URL was already shortened. Returning existing short URL.',
                        'already_exists': True
                    }
        
        # Handle custom code
        is_custom = False
        if custom_code:
            # Validate custom code
            if not ShortCodeGenerator.is_valid_custom_code(custom_code):
                return False, "Invalid custom code format"
            
            # Check if custom code already exists
            if URL.query.filter_by(short_code=custom_code).first():
                return False, "Custom code already in use"
            
            short_code = custom_code
            is_custom = True
        else:
            # Generate random short code
            short_code_length = current_app.config.get('SHORT_CODE_LENGTH', 6)
            short_code = ShortCodeGenerator.generate_random(short_code_length)
        
        # Create new URL entry
        new_url = URL(
            original_url=original_url,
            short_code=short_code,
            custom=is_custom,
            expires_at=expires_at
        )
        
        try:
            db.session.add(new_url)
            db.session.commit()
            
            return True, {
                'url': new_url.to_dict(),
                'short_url': f"{current_app.config['BASE_URL']}/{new_url.short_code}",
                'message': 'URL shortened successfully',
                'already_exists': False
            }
        except Exception as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def get_original_url(short_code):
        """
        Retrieve original URL from short code.
        
        Args:
            short_code: The short code to look up
            
        Returns:
            tuple: (success: bool, result: URL object/str)
        """
        url = URL.query.filter_by(short_code=short_code).first()
        
        if not url:
            return False, "Short URL not found"
        
        # Check if URL has expired
        if url.expires_at and url.expires_at < datetime.utcnow():
            return False, "Short URL has expired"
        
        return True, url
    
    @staticmethod
    def track_click(url, request):
        """
        Track a click on a shortened URL.
        
        Args:
            url: URL object
            request: Flask request object
        """
        # Increment click count
        url.click_count += 1
        
        # Create click record
        click = Click(
            url_id=url.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            referer=request.headers.get('Referer', '')
        )
        
        try:
            db.session.add(click)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Don't fail the redirect if analytics fails
            print(f"Failed to track click: {str(e)}")
    
    @staticmethod
    def get_url_stats(short_code):
        """
        Get statistics for a shortened URL.
        
        Args:
            short_code: The short code to get stats for
            
        Returns:
            tuple: (success: bool, result: dict/str)
        """
        url = URL.query.filter_by(short_code=short_code).first()
        
        if not url:
            return False, "Short URL not found"
        
        stats = url.to_dict()
        stats['short_url'] = f"{current_app.config['BASE_URL']}/{url.short_code}"
        stats['total_clicks'] = url.click_count
        stats['recent_clicks'] = [
            click.to_dict() for click in url.clicks.order_by(Click.clicked_at.desc()).limit(10)
        ]
        
        return True, stats
    
    @staticmethod
    def get_all_urls(page=1, per_page=50):
        """
        Get all shortened URLs with pagination.
        
        Args:
            page: Page number (1-indexed)
            per_page: Number of URLs per page
            
        Returns:
            tuple: (success: bool, result: dict/str)
        """
        try:
            pagination = URL.query.order_by(URL.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            urls = []
            for url in pagination.items:
                url_dict = url.to_dict()
                url_dict['short_url'] = f"{current_app.config['BASE_URL']}/{url.short_code}"
                urls.append(url_dict)
            
            return True, {
                'urls': urls,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        except Exception as e:
            return False, f"Error retrieving URLs: {str(e)}"
    
    @staticmethod
    def delete_url(short_code):
        """
        Delete a shortened URL.
        
        Args:
            short_code: The short code to delete
            
        Returns:
            tuple: (success: bool, message: str)
        """
        url = URL.query.filter_by(short_code=short_code).first()
        
        if not url:
            return False, "Short URL not found"
        
        try:
            db.session.delete(url)
            db.session.commit()
            return True, "URL deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
