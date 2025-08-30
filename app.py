"""
Flask Server Example for InstaFit Virtual Try-On Extension

This is an example Flask server that demonstrates how to handle requests from the Chrome extension.
Integrated with Google Gemini 2.5 Flash Image for AI-powered virtual try-on.
Includes IP-based rate limiting and bot protection.
"""

from flask import Flask, request, jsonify, Response, render_template, g
from flask_cors import CORS
import base64
import io
from PIL import Image
import logging
import time
import os
from datetime import datetime
import functools
from dotenv import load_dotenv
from config import API_CONFIG, SERVER_CONFIG, LOGGING_CONFIG
from rate_limiter import rate_limit_and_protect, get_rate_limit_info, reset_rate_limit

load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOGGING_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS with specific origins
CORS(app, origins=API_CONFIG['cors_origins'])

# Load API keys from environment
API_KEYS = {
    os.getenv("API_KEY"): "default-user",
    "test-key": "test-user"
}

# Initialize Google Gemini client
try:
    from google import genai
    genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI_AVAILABLE = True
    logger.info("Google Gemini client initialized successfully")
except Exception as e:
    logger.warning(f"Google Gemini not available: {e}")
    GEMINI_AVAILABLE = False
    genai_client = None

def require_api_key(f):
    """Decorator to require API key authentication"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "API key required"}), 401
        
        try:
            api_key = auth_header.replace("Bearer ", "")
        except:
            return jsonify({"error": "Invalid authorization format"}), 401
        
        if api_key not in API_KEYS:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Add user info to request context
        request.user = API_KEYS[api_key]
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/')
def root():
    return render_template('landing.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms-of-service.html')

@app.route('/instafit', methods=['POST'])
@require_api_key
@rate_limit_and_protect
def perform_try_on():
    """
    Perform virtual try-on using user image and product image
    
    This endpoint:
    1. Receives user photo (base64) and product image URL
    2. Downloads the product image
    3. Calls Gemini 2.5 Flash Image for try-on
    4. Returns the result image
    """
    
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_image = data.get('user_image')
        product_image_url = data.get('product_image_url')
        meta = data.get('meta', {})
        
        logger.info(f"Try-on request received from user: {request.user}")
        logger.info(f"Product URL: {product_image_url}")
        logger.info(f"Meta data: {meta}")
        
        # Validate input
        if not user_image:
            return jsonify({"error": "User image is required"}), 400
        
        if not product_image_url:
            return jsonify({"error": "Product image URL is required"}), 400
        
        # Decode user image
        try:
            # Remove data URL prefix if present
            if user_image.startswith('data:image'):
                user_image_data = user_image.split(',')[1]
            else:
                user_image_data = user_image
            
            user_image_bytes = base64.b64decode(user_image_data)
            user_image = Image.open(io.BytesIO(user_image_bytes))
            
            logger.info(f"User image decoded: {user_image.size}")
        except Exception as e:
            logger.error(f"Error decoding user image: {e}")
            return jsonify({"error": "Invalid user image format"}), 400
        
        # Download product image
        try:
            import requests
            response = requests.get(product_image_url, timeout=10)
            response.raise_for_status()
            
            product_image = Image.open(io.BytesIO(response.content))
            logger.info(f"Product image downloaded: {product_image.size}")
        except Exception as e:
            logger.error(f"Error downloading product image: {e}")
            return jsonify({"error": "Failed to download product image"}), 400
        
        # Perform AI try-on using Gemini 2.5 Flash Image
        if GEMINI_AVAILABLE:
            try:
                result_image = perform_gemini_try_on(user_image, product_image, meta)
                model_used = "gemini-2.5-flash-image"
            except Exception as e:
                logger.error(f"Gemini try-on failed: {e}")
                logger.info("Falling back to demo result")
                result_image = create_demo_result(user_image, product_image)
                model_used = "demo-model"
        else:
            logger.info("Gemini not available, using demo result")
            result_image = create_demo_result(user_image, product_image)
            model_used = "demo-model"
        
        # Convert result to base64
        buffer = io.BytesIO()
        result_image.save(buffer, format='PNG')
        result_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        processing_time = time.time() - start_time
        
        logger.info(f"Try-on completed in {processing_time:.2f} seconds using {model_used}")
        
        return jsonify({
            "image_data": result_base64,
            "confidence": 0.85,  # Mock confidence score
            "processing_time": processing_time,
            "metadata": {
                "user_id": request.user,
                "product_url": product_image_url,
                "model_used": model_used,
                "timestamp": datetime.now().isoformat(),
                "image_size": result_image.size
            }
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in try-on: {e}")
        return jsonify({"error": "Internal server error"}), 500

def perform_gemini_try_on(user_image: Image.Image, product_image: Image.Image, meta: dict) -> Image.Image:
    """
    Perform virtual try-on using Google Gemini 2.5 Flash Image
    
    Args:
        user_image: PIL Image of the user
        product_image: PIL Image of the clothing product
        meta: Additional metadata about the request
    
    Returns:
        PIL Image of the try-on result
    """
    
    try:
        # Prepare images for Gemini
        user_image_bytes = io.BytesIO()
        user_image.save(user_image_bytes, format='PNG')
        user_image_data = user_image_bytes.getvalue()
        
        product_image_bytes = io.BytesIO()
        product_image.save(product_image_bytes, format='PNG')
        product_image_data = product_image_bytes.getvalue()
        
        # Create a comprehensive prompt for virtual try-on
        prompt = create_try_on_prompt(meta)
        
        logger.info("Sending request to Gemini 2.5 Flash Image...")
        
        # Call Gemini with both images
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(user_image_data).decode()
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(product_image_data).decode()
                            }
                        }
                    ]
                }
            ]
        )
        
        # Extract the generated image
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                result_image = Image.open(io.BytesIO(part.inline_data.data))
                logger.info(f"Gemini generated image: {result_image.size}")
                return result_image
        
        # If no image was returned, raise an error
        raise Exception("No image generated by Gemini")
        
    except Exception as e:
        logger.error(f"Error in Gemini try-on: {e}")
        raise

def create_try_on_prompt(meta: dict) -> str:
    title   = meta.get("productTitle", "garment")
    size    = meta.get("selectedSize")  or "standard"
    color   = meta.get("selectedColor") or "original"

    return f"""
ROLE: You are an expert fashion compositor specializing in photorealistic virtual try-on.

INPUTS (order matters):
• Image A = PERSON photo (this is the only person to use; preserve their identity, pose, orientation, and background).
• Image B = PRODUCT photo (extract only the garment/clothing item from this image).

TASK:
Dress the person from Image A in the garment from Image B, producing a seamless, photorealistic try-on result.

CRITICAL RULES:
1. PERSON PRESERVATION:
   - Use only the person from Image A (face, hair, skin tone, body proportions, pose, and background).
   - If the person is facing sideways, angled, or partially turned, adapt the garment naturally to that orientation.
   - Do not copy or include any part of the body, face, hair, or background from Image B.

2. GARMENT PRESERVATION:
   - Transfer the entire garment from Image B exactly, including its true color, shade, fabric texture, weave, patterns, logos, and decorative details.
   - No color adjustments, artistic filters, or fabric simplifications.
   - Preserve all stitching, zippers, buttons, prints, and logos.

3. FITTING REQUIREMENTS:
   - Fit the garment naturally to the person’s current orientation and pose (front, side, angled).
   - Ensure correct placement of necklines, collars, sleeves, hems, and closures.
   - Add realistic shadows, folds, and occlusions where the garment meets the body (e.g., under arms, around hair, or when arms are bent).

4. QUALITY & INTEGRITY:
   - Maintain the original background and lighting from Image A.
   - Avoid floating clothes, duplicated limbs, distorted faces, or mismatched body proportions.
   - Output one single high-quality, photorealistic image of the person wearing the garment.
   - No extra people, no background changes, no added text, logos, or watermarks.

PRODUCT DETAILS:
• Item: {title}
• Size: {size}
• Color: {color}

OUTPUT:
Return only one high-quality image of the person from Image A realistically wearing the garment from Image B, adapted correctly even if the person is looking sideways or angled.
"""

def create_demo_result(user_image: Image.Image, product_image: Image.Image) -> Image.Image:
    """
    Create a demo result image for demonstration purposes.
    Used when Gemini is not available or fails.
    """
    
    # Resize images to same height for demo
    target_height = 400
    user_image = user_image.resize((int(user_image.width * target_height / user_image.height), target_height))
    product_image = product_image.resize((int(product_image.width * target_height / product_image.height), target_height))
    
    # Create a simple side-by-side comparison
    total_width = user_image.width + product_image.width + 20  # 20px gap
    result_image = Image.new('RGB', (total_width, target_height), (255, 255, 255))
    
    # Paste images
    result_image.paste(user_image, (0, 0))
    result_image.paste(product_image, (user_image.width + 20, 0))
    
    # Add text labels
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(result_image)
    
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    # Add labels
    draw.text((10, 10), "Your Photo", fill=(0, 0, 0), font=font)
    draw.text((user_image.width + 30, 10), "Product", fill=(0, 0, 0), font=font)
    draw.text((total_width // 2 - 50, target_height - 30), "Demo Result", fill=(102, 126, 234), font=font)
    
    return result_image

@app.route('/health')
@rate_limit_and_protect
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "gemini_available": GEMINI_AVAILABLE,
        "rate_limit_info": getattr(g, 'rate_limit_info', None)
    })

@app.route('/rate-limit/status')
@rate_limit_and_protect
def rate_limit_status():
    """Get current rate limit status for the requesting IP"""
    client_ip = getattr(g, 'client_ip', request.remote_addr)
    return jsonify({
        "client_ip": client_ip,
        "rate_limit_info": get_rate_limit_info(client_ip),
        "limits": {
            "per_minute": API_CONFIG.get('rate_limit_config', {}).get('requests_per_minute', 3),
            "per_hour": API_CONFIG.get('rate_limit_config', {}).get('requests_per_hour', 15),
            "per_day": API_CONFIG.get('rate_limit_config', {}).get('requests_per_day', 30)
        }
    })

@app.route('/rate-limit/reset/<ip_address>')
def admin_reset_rate_limit(ip_address):
    """Admin endpoint to reset rate limit for a specific IP"""
    # In production, you should add proper admin authentication here
    if reset_rate_limit(ip_address):
        return jsonify({
            "success": True,
            "message": f"Rate limit reset for IP: {ip_address}"
        })
    else:
        return jsonify({
            "success": False,
            "message": f"No rate limit data found for IP: {ip_address}"
        }), 404

@app.route('/api-keys')
def list_api_keys():
    """List available API keys (for development only)"""
    return jsonify({
        "available_keys": list(API_KEYS.keys()),
        "note": "This endpoint should be removed in production"
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Run the Flask server
    app.run(
        host=SERVER_CONFIG['host'],
        port=SERVER_CONFIG['port'],
        debug=SERVER_CONFIG['debug'],
        threaded=SERVER_CONFIG['threaded']
    ) 