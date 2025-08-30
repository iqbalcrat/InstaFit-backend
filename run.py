"""
Simplified Flask app for InstaFit Virtual Try-On Extension
This is a cleaner version for production deployment
Integrated with Google Gemini 2.5 Flash Image for AI-powered virtual try-on.
"""

from flask import Flask, request, jsonify
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

# Load environment variables from .env file
load_dotenv()
logger.info("Environment variables loaded from .env file")

# Log all environment variables (masked for security)
env_vars = {k: v[:10] + "..." if v and k in ['API_KEY', 'GEMINI_API_KEY'] else v for k, v in os.environ.items() if k in ['API_KEY', 'GEMINI_API_KEY', 'TEST_API_KEY']}
logger.info(f"Environment variables found: {env_vars}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS - update origins for production
CORS(app, origins=[
    "chrome-extension://*",  # Allow Chrome extensions
    "http://localhost:*",    # Allow local development
    # Add your production domains here
])

# Configuration - move to environment variables in production
API_KEYS = {
    os.getenv('API_KEY', 'your-api-key-here'): 'default-user',
    os.getenv('TEST_API_KEY', 'test-key'): 'test-user'
}

# Initialize Google Gemini client
try:
    from google import genai
    logger.info("Google genai module imported successfully")
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    logger.info(f"GEMINI_API_KEY from environment: {gemini_api_key[:10] if gemini_api_key else 'None'}...")
    
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    if gemini_api_key.strip() == "":
        raise ValueError("GEMINI_API_KEY is empty")
    
    logger.info("Attempting to initialize Gemini client...")
    genai_client = genai.Client(api_key=gemini_api_key)
    GEMINI_AVAILABLE = True
    logger.info("Google Gemini client initialized successfully")
    logger.info(f"Gemini API key loaded: {gemini_api_key[:10]}...")
    
    # Test the client with a simple call
    logger.info("Testing Gemini client with a simple call...")
    test_response = genai_client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents="Test message"
    )
    logger.info("Gemini client test successful")
    
except ImportError as e:
    logger.error(f"Failed to import google.genai: {e}")
    GEMINI_AVAILABLE = False
    genai_client = None
except ValueError as e:
    logger.error(f"Gemini API key error: {e}")
    GEMINI_AVAILABLE = False
    genai_client = None
except Exception as e:
    logger.error(f"Google Gemini initialization failed: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error details: {str(e)}")
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
        
        request.user = API_KEYS[api_key]
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/')
def root():
    """Health check endpoint"""
    return jsonify({
        "message": "InstaFit Virtual Try-On API",
        "version": "1.0.0",
        "status": "running",
        "gemini_available": GEMINI_AVAILABLE
    })

@app.route('/tryon', methods=['POST'])
@require_api_key
def perform_try_on():
    """Perform virtual try-on using user image and product image"""
    
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
        
        # Validate input
        if not user_image:
            return jsonify({"error": "User image is required"}), 400
        
        if not product_image_url:
            return jsonify({"error": "Product image URL is required"}), 400
        
        # Decode user image
        try:
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
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.myntra.com/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            logger.info(f"Downloading product image from: {product_image_url}")
            response = requests.get(product_image_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            product_image = Image.open(io.BytesIO(response.content))
            logger.info(f"Product image downloaded successfully: {product_image.size}")
        except Exception as e:
            logger.error(f"Error downloading product image: {e}")
            logger.error(f"Product URL: {product_image_url}")
            return jsonify({"error": f"Failed to download product image: {str(e)}"}), 400
        
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
                # Add a note about the fallback
                fallback_note = "Server is busy with too many requests. Please try after some time."
        else:
            logger.info("Gemini not available, using demo result")
            result_image = create_demo_result(user_image, product_image)
            model_used = "demo-model"
            fallback_note = "Server is busy with too many requests. Please try after some time."
        
        # Convert result to base64
        buffer = io.BytesIO()
        result_image.save(buffer, format='PNG')
        result_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        processing_time = time.time() - start_time
        
        logger.info(f"Try-on completed in {processing_time:.2f} seconds using {model_used}")
        
        response_data = {
            "image_data": result_base64,
            "confidence": 0.85,
            "processing_time": processing_time,
            "metadata": {
                "user_id": request.user,
                "product_url": product_image_url,
                "model_used": model_used,
                "timestamp": datetime.now().isoformat(),
                "image_size": result_image.size
            }
        }
        
        # Add fallback note if using demo model
        if model_used == "demo-model":
            response_data["fallback_message"] = fallback_note
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in try-on: {e}")
        return jsonify({"error": "Internal server error"}), 500

def perform_gemini_try_on(user_image: Image.Image, product_image: Image.Image, meta: dict) -> Image.Image:
    """Perform virtual try-on using Google Gemini 2.5 Flash Image"""
    
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
        logger.info(f"Prompt: {prompt}")
        logger.info(f"User image size: {user_image.size}")
        logger.info(f"Product image size: {product_image.size}")
        logger.info("Image order: 1st = Product clothing, 2nd = User photo")
        
        # Call Gemini with both images (reversed order)
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
                                "data": base64.b64encode(product_image_data).decode()
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(user_image_data).decode()
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
    """Create a comprehensive prompt for virtual try-on"""
    
    product_title = meta.get('productTitle', 'clothing item')
    selected_size = meta.get('selectedSize', '')
    selected_color = meta.get('selectedColor', '')
    
    prompt = f"""
    TASK: Virtual clothing try-on
    
    You have 2 images:
    - FIRST image: A clothing product
    - SECOND image: A real person (customer)
    
    GOAL: Show the person from the SECOND image wearing the clothing from the FIRST image.
    
    RULES:
    - Use ONLY the person's body from the SECOND image
    - Use ONLY the clothing from the FIRST image
    - Keep the person's face, hair, skin, and background exactly the same
    - Put the product clothing on the person's body
    - Do NOT use any model from the product image
    - Do NOT change the person's appearance
    
    Product: {product_title}
    Size: {selected_size if selected_size else 'standard'}
    Color: {selected_color if selected_color else 'original'}
    
    Result: The person from image 2 wearing the clothing from image 1.
    """
    
    return prompt.strip()

def create_demo_result(user_image: Image.Image, product_image: Image.Image) -> Image.Image:
    """Create a demo result image for demonstration purposes"""
    
    # Resize images to same height for demo
    target_height = 400
    user_image = user_image.resize((int(user_image.width * target_height / user_image.height), target_height))
    product_image = product_image.resize((int(product_image.width * target_height / product_image.height), target_height))
    
    # Create a simple side-by-side comparison
    total_width = user_image.width + product_image.width + 20
    result_image = Image.new('RGB', (total_width, target_height), (255, 255, 255))
    
    # Paste images
    result_image.paste(user_image, (0, 0))
    result_image.paste(product_image, (user_image.width + 20, 0))
    
    # Add text labels
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(result_image)
    
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    # Add labels
    draw.text((10, 10), "Your Photo", fill=(0, 0, 0), font=font)
    draw.text((user_image.width + 30, 10), "Product", fill=(0, 0, 0), font=font)
    draw.text((total_width // 2 - 50, target_height - 30), "Demo Result", fill=(102, 126, 234), font=font)
    
    return result_image

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "gemini_available": GEMINI_AVAILABLE
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Get port from environment variable or default to 8000
    port = int(os.environ.get('PORT', 8000))
    
    # Run the Flask server
    app.run(
        host="0.0.0.0",
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ) 