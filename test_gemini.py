"""
Test script for Google Gemini 2.5 Flash Image integration
This script tests the Gemini API connection and basic functionality
"""

import os
import base64
import io
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test basic Gemini API connection"""
    try:
        from google import genai
        
        # Check if API key is set
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return False
        
        # Initialize client
        client = genai.Client(api_key=api_key)
        print("✅ Gemini client initialized successfully")
        
        # Test basic text generation
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents="Generate a simple test image of a red circle"
        )
        
        print("✅ Basic Gemini API call successful")
        return True
        
    except Exception as e:
        print(f"❌ Gemini connection failed: {e}")
        return False

def test_image_generation():
    """Test image generation with Gemini"""
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found")
            return False
        
        client = genai.Client(api_key=api_key)
        
        # Create a simple test prompt
        prompt = "Generate a simple fashion product image: a white t-shirt on a clean background"
        
        print("🔄 Testing image generation...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=prompt
        )
        
        # Check if image was generated
        image_generated = False
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                # Save the generated image
                img = Image.open(io.BytesIO(part.inline_data.data))
                img.save("test_generated_image.png")
                print(f"✅ Image generated successfully: {img.size}")
                image_generated = True
                break
        
        if not image_generated:
            print("❌ No image was generated")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Image generation test failed: {e}")
        return False

def test_multi_image_input():
    """Test Gemini with multiple image inputs (simulating try-on)"""
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found")
            return False
        
        client = genai.Client(api_key=api_key)
        
        # Create test images
        # Test image 1: Simple colored rectangle (simulating user photo)
        user_img = Image.new('RGB', (200, 300), color='lightblue')
        user_img.save("test_user.png")
        
        # Test image 2: Another colored rectangle (simulating product)
        product_img = Image.new('RGB', (150, 200), color='red')
        product_img.save("test_product.png")
        
        # Convert images to base64
        user_buffer = io.BytesIO()
        user_img.save(user_buffer, format='PNG')
        user_data = base64.b64encode(user_buffer.getvalue()).decode()
        
        product_buffer = io.BytesIO()
        product_img.save(product_buffer, format='PNG')
        product_data = base64.b64encode(product_buffer.getvalue()).decode()
        
        print("🔄 Testing multi-image input...")
        
        # Create try-on prompt
        prompt = """
        Create a realistic virtual try-on image.
        
        Instructions:
        1. The first image shows a person (blue rectangle represents user)
        2. The second image shows a clothing item (red rectangle represents product)
        3. Generate a realistic image where the person is wearing the clothing item
        4. Maintain natural proportions and realistic appearance
        
        Return only the generated image with no text or watermarks.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": user_data
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": product_data
                            }
                        }
                    ]
                }
            ]
        )
        
        # Check for generated image
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img = Image.open(io.BytesIO(part.inline_data.data))
                img.save("test_tryon_result.png")
                print(f"✅ Multi-image try-on test successful: {img.size}")
                return True
        
        print("❌ No image generated in multi-image test")
        return False
        
    except Exception as e:
        print(f"❌ Multi-image test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Google Gemini 2.5 Flash Image Integration")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("\n1. Testing basic connection...")
    connection_ok = test_gemini_connection()
    
    if not connection_ok:
        print("\n❌ Basic connection failed. Please check your GEMINI_API_KEY")
        return
    
    # Test 2: Simple image generation
    print("\n2. Testing simple image generation...")
    simple_gen_ok = test_image_generation()
    
    # Test 3: Multi-image input (try-on simulation)
    print("\n3. Testing multi-image input (try-on simulation)...")
    multi_img_ok = test_multi_image_input()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Basic Connection: {'PASS' if connection_ok else 'FAIL'}")
    print(f"✅ Simple Image Generation: {'PASS' if simple_gen_ok else 'FAIL'}")
    print(f"✅ Multi-Image Try-On: {'PASS' if multi_img_ok else 'FAIL'}")
    
    if connection_ok and simple_gen_ok and multi_img_ok:
        print("\n🎉 All tests passed! Gemini integration is working correctly.")
        print("You can now use the Flask server with full AI-powered try-on functionality.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("The Flask server will fall back to demo mode if Gemini is not available.")

if __name__ == "__main__":
    main() 