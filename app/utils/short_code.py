import string
import random
from app.models import URL


class ShortCodeGenerator:
    """Generate short codes for URLs using Base62 encoding."""
    
    # Base62 character set (alphanumeric)
    CHARSET = string.ascii_letters + string.digits  # a-zA-Z0-9
    
    @staticmethod
    def encode_base62(num):
        """Convert a number to base62 string."""
        if num == 0:
            return ShortCodeGenerator.CHARSET[0]
        
        base62 = []
        base = len(ShortCodeGenerator.CHARSET)
        
        while num:
            num, rem = divmod(num, base)
            base62.append(ShortCodeGenerator.CHARSET[rem])
        
        return ''.join(reversed(base62))
    
    @staticmethod
    def decode_base62(code):
        """Convert a base62 string back to number."""
        base = len(ShortCodeGenerator.CHARSET)
        num = 0
        
        for char in code:
            num = num * base + ShortCodeGenerator.CHARSET.index(char)
        
        return num
    
    @staticmethod
    def generate_from_id(id_num, min_length=6):
        """Generate short code from database ID."""
        code = ShortCodeGenerator.encode_base62(id_num)
        
        # Pad with leading characters if needed
        if len(code) < min_length:
            code = code.zfill(min_length)
        
        return code
    
    @staticmethod
    def generate_random(length=6, max_attempts=10):
        """Generate random short code and check for uniqueness."""
        for _ in range(max_attempts):
            code = ''.join(random.choices(ShortCodeGenerator.CHARSET, k=length))
            
            # Check if code already exists
            if not URL.query.filter_by(short_code=code).first():
                return code
        
        # If we couldn't find a unique code, increase length
        return ShortCodeGenerator.generate_random(length + 1, max_attempts)
    
    @staticmethod
    def is_valid_custom_code(code):
        """Validate custom short code."""
        if not code:
            return False
        
        # Check if code contains only alphanumeric and hyphens/underscores
        allowed_chars = string.ascii_letters + string.digits + '-_'
        
        if not all(c in allowed_chars for c in code):
            return False
        
        # Check length constraints
        from flask import current_app
        min_len = current_app.config.get('CUSTOM_ALIAS_MIN_LENGTH', 3)
        max_len = current_app.config.get('CUSTOM_ALIAS_MAX_LENGTH', 20)
        
        if not (min_len <= len(code) <= max_len):
            return False
        
        return True
