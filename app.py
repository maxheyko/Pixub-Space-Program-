from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import uuid
import time
import websocket
import threading
from urllib.parse import urlencode

app = Flask(__name__)
CORS(app)

COMFYUI_SERVER = "http://127.0.0.1:8188"

class ComfyUIAPI:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        
    def queue_prompt(self, workflow):
        """Queue a prompt to ComfyUI"""
        url = f"{COMFYUI_SERVER}/prompt"
        data = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_image(self, filename, subfolder, type_):
        """Get generated image from ComfyUI"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": type_
        }
        url = f"{COMFYUI_SERVER}/view?" + urlencode(params)
        response = requests.get(url)
        response.raise_for_status()
        return response
    
    def wait_for_completion(self, prompt_id, timeout=900, progress_callback=None):
        """Wait for prompt completion using WebSocket"""
        ws_url = f"ws://127.0.0.1:8188/ws?clientId={self.client_id}"
        
        completion_event = threading.Event()
        error_event = threading.Event()
        error_message = None
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                
                # Handle progress updates
                if data.get("type") == "progress" and progress_callback:
                    progress_data = data.get("data", {})
                    if progress_data.get("prompt_id") == prompt_id:
                        value = progress_data.get("value", 0)
                        max_value = progress_data.get("max", 100)
                        progress_percent = int((value / max_value) * 100) if max_value > 0 else 0
                        progress_callback(progress_percent)
                
                # Handle completion
                if (data.get("type") == "executing" and 
                    data.get("data", {}).get("node") is None and 
                    data.get("data", {}).get("prompt_id") == prompt_id):
                    print(f"Completion detected via WebSocket for prompt {prompt_id}")
                    completion_event.set()
            except Exception as e:
                nonlocal error_message
                error_message = str(e)
                error_event.set()
        
        def on_error(ws, error):
            nonlocal error_message
            error_message = str(error)
            error_event.set()
        
        def on_close(ws, close_status_code, close_msg):
            if not completion_event.is_set():
                error_event.set()
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start WebSocket in a separate thread
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for completion or timeout
        if completion_event.wait(timeout):
            ws.close()
            return True
        elif error_event.wait(0.1):  # Check if error occurred
            ws.close()
            raise Exception(f"WebSocket error: {error_message}")
        else:
            ws.close()
            raise Exception("Timeout waiting for image generation")
    
    def get_history(self, prompt_id):
        """Get generation history for a prompt"""
        url = f"{COMFYUI_SERVER}/history/{prompt_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

# Load workflow templates
with open('workflow.json', 'r') as f:
    workflow_template = json.load(f)

try:
    with open('simple_video_workflow.json', 'r') as f:
        video_workflow_template = json.load(f)
    print("Batch video workflow loaded successfully")
except FileNotFoundError:
    video_workflow_template = None
    print("Video workflow not found - video generation disabled")

# Store progress for active generations
active_generations = {}

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/generate', methods=['POST'])
def generate_image():
    """Generate image endpoint"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        generation_type = data.get('type', 'image')  # 'image' or 'video'
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        if generation_type == 'video' and not video_workflow_template:
            return jsonify({"error": "Video generation not available"}), 400
        
        print(f"Generating {generation_type} for prompt: {prompt}")
        
        # Choose workflow based on type
        if generation_type == 'video':
            workflow = json.loads(json.dumps(video_workflow_template))
            # Enhanced prompt for better frame variation
            video_prompt = f"{prompt}, cinematic, dynamic angles, different perspectives, camera movement, detailed, high quality"
            workflow["6"]["inputs"]["text"] = video_prompt
        else:
            workflow = json.loads(json.dumps(workflow_template))
            workflow["6"]["inputs"]["text"] = prompt
            
        workflow["3"]["inputs"]["seed"] = int(time.time() * 1000000) % 1000000000
        
        comfy_api = ComfyUIAPI()
        
        # Queue the prompt
        queue_result = comfy_api.queue_prompt(workflow)
        prompt_id = queue_result["prompt_id"]
        
        print(f"Prompt queued with ID: {prompt_id}")
        
        # Initialize progress tracking
        active_generations[prompt_id] = {
            "progress": 0, 
            "status": "starting",
            "type": generation_type
        }
        
        def update_progress(percent):
            active_generations[prompt_id]["progress"] = percent
            active_generations[prompt_id]["status"] = f"generating {generation_type} ({percent}%)"
            print(f"Progress: {percent}%")
        
        # Wait for completion with progress tracking
        print(f"Waiting for completion of prompt {prompt_id}")
        comfy_api.wait_for_completion(prompt_id, progress_callback=update_progress)
        print(f"Completion detected for prompt {prompt_id}")
        
        # Get the generated content info
        print(f"Getting history for prompt {prompt_id}")
        history = comfy_api.get_history(prompt_id)
        print(f"History keys: {list(history.keys())}")
        
        if prompt_id not in history:
            raise Exception(f"Prompt {prompt_id} not found in history")
            
        outputs = history[prompt_id]["outputs"]
        print(f"Available outputs: {list(outputs.keys())}")
        
        # For SVD, try different node IDs where SaveImage might be
        save_image_output = None
        for node_id in ["17", "16", "13", "11", "9"]:  # Try different possible SaveImage nodes
            if node_id in outputs and outputs[node_id].get("images"):
                save_image_output = outputs[node_id]
                print(f"Found images in node {node_id}: {len(save_image_output['images'])} images")
                break
        
        if not save_image_output or not save_image_output.get("images"):
            print(f"All outputs: {outputs}")
            raise Exception(f"No {generation_type} generated - no images found in any output node")
        
        if generation_type == 'video':
            # Handle SVD video output
            images = save_image_output["images"]
            print(f"Found {len(images)} images in SVD output")
            
            if len(images) == 1:
                # Single video file from SVD
                content_info = images[0]
                params = {
                    "filename": content_info["filename"],
                    "subfolder": content_info["subfolder"],
                    "type": content_info["type"]
                }
                content_url = f"{COMFYUI_SERVER}/view?" + urlencode(params)
                
                print(f"SVD video generated: {content_info['filename']}")
                
                # Clean up progress tracking
                if prompt_id in active_generations:
                    del active_generations[prompt_id]
                
                return jsonify({
                    "success": True,
                    "imageUrl": content_url,
                    "filename": content_info["filename"],
                    "type": generation_type,
                    "frameCount": 25  # SVD generates 25 frames
                })
            else:
                # Multiple frames - create slideshow
                image_urls = []
                for img_info in images:
                    params = {
                        "filename": img_info["filename"],
                        "subfolder": img_info["subfolder"],
                        "type": img_info["type"]
                    }
                    img_url = f"{COMFYUI_SERVER}/view?" + urlencode(params)
                    image_urls.append(img_url)
                
                print(f"Video batch generated successfully: {len(images)} frames")
                
                # Clean up progress tracking
                if prompt_id in active_generations:
                    del active_generations[prompt_id]
                
                return jsonify({
                    "success": True,
                    "imageUrl": image_urls[0],  # First frame for compatibility
                    "imageUrls": image_urls,    # All frames for video
                    "filename": images[0]["filename"],
                    "type": generation_type,
                    "frameCount": len(images)
                })
        else:
            # Regular image generation
            content_info = save_image_output["images"][0]
            params = {
                "filename": content_info["filename"],
                "subfolder": content_info["subfolder"],
                "type": content_info["type"]
            }
            content_url = f"{COMFYUI_SERVER}/view?" + urlencode(params)
            
            print(f"Image generated successfully: {content_info['filename']}")
            
            # Clean up progress tracking
            if prompt_id in active_generations:
                del active_generations[prompt_id]
            
            return jsonify({
                "success": True,
                "imageUrl": content_url,
                "filename": content_info["filename"],
                "type": generation_type
            })
        
    except Exception as e:
        print(f"Error generating image: {e}")
        # Clean up progress tracking on error
        if 'prompt_id' in locals() and prompt_id in active_generations:
            del active_generations[prompt_id]
        return jsonify({
            "error": str(e),
            "details": "Make sure ComfyUI is running on http://127.0.0.1:8188"
        }), 500

@app.route('/progress/<prompt_id>', methods=['GET'])
def get_progress(prompt_id):
    """Get progress for a specific generation"""
    if prompt_id in active_generations:
        return jsonify(active_generations[prompt_id])
    else:
        return jsonify({"progress": 0, "status": "not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f"{COMFYUI_SERVER}/system_stats", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "ComfyUI is running"})
        else:
            raise Exception("ComfyUI not responding")
    except Exception as e:
        return jsonify({
            "status": "ComfyUI not available",
            "error": str(e)
        }), 503

if __name__ == '__main__':
    print("Starting ComfyUI Web App...")
    print("Make sure ComfyUI is running on http://127.0.0.1:8188")
    app.run(host='0.0.0.0', port=3000, debug=True)