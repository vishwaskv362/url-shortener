from flask import Blueprint, request, jsonify, current_app
from app.services.url_service import URLService
from datetime import datetime

api_bp = Blueprint('api', __name__)


@api_bp.route('/shorten', methods=['POST'])
def shorten_url():
    """
    API endpoint to shorten a URL.
    
    Expected JSON payload:
    {
        "url": "https://example.com/very/long/url",
        "custom_code": "optional-custom-code",  # Optional
        "expires_at": "2024-12-31T23:59:59"     # Optional
    }
    """
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({
            'success': False,
            'error': 'URL is required'
        }), 400
    
    original_url = data.get('url')
    custom_code = data.get('custom_code')
    expires_at_str = data.get('expires_at')
    
    # Parse expiration date if provided
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use ISO 8601 format'
            }), 400
    
    # Create shortened URL
    success, result = URLService.create_short_url(
        original_url=original_url,
        custom_code=custom_code,
        expires_at=expires_at
    )
    
    if not success:
        return jsonify({
            'success': False,
            'error': result
        }), 400
    
    return jsonify({
        'success': True,
        'data': result
    }), 201


@api_bp.route('/urls/<short_code>', methods=['GET'])
def get_url_info(short_code):
    """Get information about a shortened URL."""
    success, result = URLService.get_url_stats(short_code)
    
    if not success:
        return jsonify({
            'success': False,
            'error': result
        }), 404
    
    return jsonify({
        'success': True,
        'data': result
    }), 200


@api_bp.route('/urls/<short_code>', methods=['DELETE'])
def delete_url(short_code):
    """Delete a shortened URL."""
    success, message = URLService.delete_url(short_code)
    
    if not success:
        return jsonify({
            'success': False,
            'error': message
        }), 404
    
    return jsonify({
        'success': True,
        'message': message
    }), 200


@api_bp.route('/urls', methods=['GET'])
def list_urls():
    """Get all shortened URLs with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    
    success, result = URLService.get_all_urls(page=page, per_page=per_page)
    
    if not success:
        return jsonify({
            'success': False,
            'error': result
        }), 500
    
    return jsonify({
        'success': True,
        'data': result
    }), 200


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'url-shortener',
        'version': '1.0.0'
    }), 200
