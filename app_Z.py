import os
import csv
import uuid
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_from_directory
import pandas as pd
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import os
import google.generativeai as genai
import base64
import io
import requests
from rembg import remove, new_session
from api_keys import GEMINI_API_KEY


# Configuration
UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
CSV_FILE = 'submissions.csv'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True) # <--- Add this

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
MY_API_KEY = GEMINI_API_KEY

# --- Backend Logic: Data Management ---

def init_db():
    """Initialize the CSV file if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=[
            'id', 'image_filename', 'anime_name', 'email_id',
            'build_status', 'mail_status', 'timestamp'
        ])
        df.to_csv(CSV_FILE, index=False)

def get_next_id():
    """Calculate the next sequential ID."""
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return 1
        return df['id'].max() + 1
    except:
        return 1

def save_to_csv(filename, anime_name, email):
    """Save the final submission to CSV."""
    new_id = get_next_id()
    new_row = {
        'id': new_id,
        'image_filename': filename,
        'anime_name': anime_name,
        'email_id': email,
        'build_status': 'N',
        'mail_status': 'N',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    df = pd.read_csv(CSV_FILE)
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    return new_id

# --- Backend Logic ---

def bg_rem(in_path, out_path, model="human"):
    """
    removes bg
    :param in_path:
    :param out_path:
    :param model:
    :return:
    """
    if model == "human":
        model_name = "u2net_human_seg"
    else:
        model_name = "isnet-anime"

    session = new_session(model_name)
    in_img = Image.open(in_path)

    output = remove(in_img, session=session)
    output.save(f"{out_path}")
    return True

def generate_anime_image(api_key: MY_API_KEY, input_image_path, prompt):
                              # ,output_path: str = "generated_output.png"):
    """
    Generates a new image based on an input image and a text prompt using Google's Gen AI.

    Args:
        api_key (str): Your Google Generative AI API Key.
        input_image_path (str): Path to the source image file.
        prompt (str): Text description of the desired changes or result.
        output_path (str): Path where the generated image will be saved.
    """

    img = Image.open(input_image_path)
    return img


def process_image_pipeline(image_path, anime_name):
    """Runs the transformation pipeline."""
    try:

        prompt = (f"make this into an anime artwork in {anime_name}'s style, "
                  f"all the lines and brushstroke should match with the anime's, like they are in the {anime_name}, "
                  f"also change their clothes to something that would match the {anime_name}'s world"
                  "This anime artwork should match the facial features and hairs"
                  "The body pose should not change")

        # Open original
        original = Image.open(image_path)

        filename = os.path.basename(image_path)
        # Create new filename (e.g., "photo.png") - Force PNG for transparency
        name_only, _ = os.path.splitext(filename)
        new_filename = f"{name_only}.png"
        # Define full path for saving
        save_path = os.path.join(PROCESSED_FOLDER, new_filename)

        # Step 1: Convert it into anime
        # generate_anime_image(api_key=MY_API_KEY, input_image_path=image_path, prompt=prompt)

        # Step 2: Background Removal
        bg_rem(image_path, save_path, model="anime")

        return new_filename

    except Exception as e:
        print(f"Error processing image: {e}")
        return None


# --- Routes ---

@app.route('/')
def index():
    init_db()
    # Read CSV to show 'History' in the 3rd section
    try:
        history = pd.read_csv(CSV_FILE).tail(5).sort_values(by='id', ascending=False).to_dict(orient='records')
    except:
        history = []
    return render_template_string(HTML_TEMPLATE, history=history)

@app.route('/upload_and_preview', methods=['POST'])
def upload_and_preview():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    anime_name = request.form.get('anime_name')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        # Save Original
        # filename = f"{uuid.uuid4().hex}_{file.filename}"
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Run Pipeline
        processed_filename = process_image_pipeline(filepath, anime_name)

        if processed_filename:
            return jsonify({
                'status': 'success',
                'original_file': filename,
                'processed_file': processed_filename,
                'anime_name': anime_name
            })
        else:
            return jsonify({'error': 'Processing failed'}), 500

@app.route('/submit_final', methods=['POST'])
def submit_final():
    try:
        data = request.json
        filename = data.get('processed_file')
        anime_name = data.get('anime_name')
        email = data.get('email')

        if not all([filename, anime_name, email]):
            return jsonify({'error': 'Missing data'}), 400

        # Save to CSV
        record_id = save_to_csv(filename, anime_name, email)

        return jsonify({'status': 'success', 'id': int(record_id)})

    except Exception as e:
        # This will print the EXACT error to your terminal so you can see it
        print("------------------------------------------------")
        print("ERROR IN SUBMIT FINAL:", str(e))
        print("------------------------------------------------")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """API endpoint to get the latest history data for the refresh button."""
    try:
        if os.path.exists(CSV_FILE):
            # Read CSV to get latest updates on build_status/mail_status
            history = pd.read_csv(CSV_FILE).tail(5).sort_values(by='id', ascending=False).to_dict(orient='records')
            return jsonify(history)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Frontend Template (HTML/Tailwind/JS) ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chibi-Chitra</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        body { font-family: 'Poppins', sans-serif; }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-100 h-screen overflow-hidden flex flex-col">

    <!-- Header -->
    <header class="bg-indigo-600 text-white p-4 shadow-md z-10">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold"><i class="fa-solid fa-wand-magic-sparkles"></i> Chibi-Chitra </h1>
            <p class="text-sm opacity-80">Convert yourself into your favorite character</p>
        </div>
    </header>

    <!-- Main Content Grid -->
    <div class="flex-1 grid grid-cols-1 md:grid-cols-3 gap-0 divide-x divide-gray-300 overflow-hidden">

        <!-- SECTION 1: INPUT -->
        <div class="p-8 bg-white overflow-y-auto">
            <div class="max-w-md mx-auto">
                <h2 class="text-xl font-bold text-gray-800 mb-6 border-b pb-2">1. Upload Details</h2>

                <form id="uploadForm" class="space-y-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Your Photo</label>
                        <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-indigo-500 transition cursor-pointer relative" id="dropzone">
                            <div class="space-y-1 text-center">
                                <i class="fa-solid fa-cloud-arrow-up text-gray-400 text-3xl"></i>
                                <div class="flex text-sm text-gray-600">
                                    <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-indigo-600 hover:text-indigo-500 focus-within:outline-none">
                                        <span>Upload a file</span>
                                        <input id="file-upload" name="image" type="file" class="sr-only" accept="image/*" required onchange="previewInput(this)">
                                    </label>
                                </div>
                                <p class="text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
                            </div>
                        </div>
                        <!-- Mini preview of selected file - CONTAINED -->
                        <div class="mt-4 bg-gray-50 rounded-lg border border-gray-200 hidden h-64 flex items-center justify-center" id="inputPreviewContainer">
                            <img id="inputPreview" class="w-full h-full object-contain rounded-lg">
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700">Anime Style</label>
                        <input type="text" name="anime_name" id="anime_name" required 
                            class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" 
                            placeholder="e.g. Naruto, Attack on Titan, Cyberpunk">
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700">Email Address</label>
                        <input type="email" name="email" id="email" required 
                            class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" 
                            placeholder="you@example.com">
                    </div>

                    <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition">
                        <span id="genBtnText">Generate Preview</span>
                        <div id="genLoader" class="loader ml-2 hidden" style="width: 20px; height: 20px; border-width: 2px;"></div>
                    </button>
                </form>
            </div>
        </div>

        <!-- SECTION 2: PREVIEW & ACTION -->
        <div class="p-8 bg-gray-50 overflow-y-auto flex flex-col items-center justify-start relative">
            <h2 class="text-xl font-bold text-gray-800 mb-6 border-b pb-2 w-full">2. Review & Refine</h2>

            <div id="placeholder-state" class="text-center mt-20 text-gray-400">
                <i class="fa-solid fa-image text-6xl mb-4"></i>
                <p>Upload details in Section 1 to see the magic here.</p>
            </div>

            <!-- Preview Container - CONTAINED -->
            <div id="result-container" class="hidden w-full max-w-md flex flex-col items-center">
                <div class="relative w-full h-96 bg-gray-200 rounded-lg shadow-lg overflow-hidden border-4 border-white mb-6 group flex items-center justify-center">
                    <img id="processedImage" src="" alt="Generated Anime" class="w-full h-full object-contain">
                    <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 text-center opacity-0 group-hover:opacity-100 transition">
                        Background Removed + Style Applied
                    </div>
                </div>

                <div class="flex space-x-4 w-full">
                    <button onclick="regenerate()" class="flex-1 py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none transition">
                        <i class="fa-solid fa-rotate-right mr-2"></i> Refresh/Retry
                    </button>
                    <button onclick="submitFinal()" class="flex-1 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none transition">
                        <i class="fa-solid fa-cube mr-2"></i> Submit for 3D
                    </button>
                </div>
            </div>
        </div>

        <!-- SECTION 3: STATUS / HISTORY -->
        <div class="p-8 bg-white overflow-y-auto">
            <div class="flex justify-between items-center mb-6 border-b pb-2">
                <h2 class="text-xl font-bold text-gray-800">3. Status Queue</h2>
                <!-- Refresh Button -->
                <button onclick="refreshStatus()" class="text-indigo-600 hover:text-indigo-800 text-sm font-semibold focus:outline-none flex items-center gap-2">
                    <i class="fa-solid fa-arrows-rotate" id="refreshIcon"></i> Refresh Status
                </button>
            </div>

            <div id="success-message" class="hidden mb-6 bg-green-50 border-l-4 border-green-400 p-4">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fa-solid fa-check-circle text-green-400"></i>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm text-green-700">
                            Success! Your ID is <span id="new-id" class="font-bold"></span>. <br>
                            Your character is queued for 3D generation. Check your email.
                        </p>
                    </div>
                </div>
            </div>

            <div class="bg-indigo-50 rounded-lg p-4 mb-4 shadow-sm">
                <div class="flex justify-between items-center mb-2">
                    <h3 class="font-semibold text-indigo-900">Live Queue</h3>
                    <span class="text-xs text-indigo-500">Updates from CSV</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full text-xs">
                        <thead class="bg-indigo-100">
                            <tr>
                                <th class="px-2 py-2 text-left text-indigo-800 rounded-tl-md">ID</th>
                                <th class="px-2 py-2 text-left text-indigo-800">Anime</th>
                                <th class="px-2 py-2 text-left text-indigo-800">Build</th>
                                <th class="px-2 py-2 text-left text-indigo-800 rounded-tr-md">Mail</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-indigo-200 bg-white" id="statusTableBody">
                            {% for row in history %}
                            <tr>
                                <td class="px-2 py-2 font-mono font-medium text-indigo-600">#{{ row.id }}</td>
                                <td class="px-2 py-2 text-gray-700">{{ row.anime_name }}</td>
                                <td class="px-2 py-2">
                                    <span class="px-2 py-1 rounded-full text-[10px] font-bold 
                                        {% if row.build_status == 'Y' %}bg-green-100 text-green-800{% else %}bg-yellow-100 text-yellow-800{% endif %}">
                                        {{ row.build_status }}
                                    </span>
                                </td>
                                <td class="px-2 py-2">
                                    <span class="px-2 py-1 rounded-full text-[10px] font-bold 
                                        {% if row.mail_status == 'Y' %}bg-green-100 text-green-800{% else %}bg-yellow-100 text-yellow-800{% endif %}">
                                        {{ row.mail_status }}
                                    </span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <p class="text-xs text-gray-500 mt-2 text-center">Showing last 5 submissions</p>
            </div>
        </div>

    </div>

    <!-- JavaScript Logic -->
    <script>
        // Global state to hold current processed data before final submission
        let currentData = {
            processed_file: null,
            anime_name: null,
            email: null
        };

        function previewInput(input) {
            if (input.files && input.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.getElementById('inputPreview');
                    img.src = e.target.result;
                    document.getElementById('inputPreviewContainer').classList.remove('hidden');
                }
                reader.readAsDataURL(input.files[0]);
            }
        }

        async function refreshStatus() {
            const icon = document.getElementById('refreshIcon');
            icon.classList.add('fa-spin');

            try {
                // Add timestamp to avoid caching
                const response = await fetch('/api/history?t=' + new Date().getTime());
                const data = await response.json();

                const tbody = document.getElementById('statusTableBody');
                tbody.innerHTML = ''; // Clear current rows

                data.forEach(row => {
                    const tr = document.createElement('tr');

                    // Logic to color badges
                    const buildClass = row.build_status === 'Y' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';
                    const mailClass = row.mail_status === 'Y' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';

                    tr.innerHTML = `
                        <td class="px-2 py-2 font-mono font-medium text-indigo-600">#${row.id}</td>
                        <td class="px-2 py-2 text-gray-700">${row.anime_name}</td>
                        <td class="px-2 py-2">
                            <span class="px-2 py-1 rounded-full text-[10px] font-bold ${buildClass}">${row.build_status}</span>
                        </td>
                        <td class="px-2 py-2">
                            <span class="px-2 py-1 rounded-full text-[10px] font-bold ${mailClass}">${row.mail_status}</span>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

            } catch (error) {
                console.error('Error fetching history:', error);
            } finally {
                setTimeout(() => icon.classList.remove('fa-spin'), 500);
            }
        }

        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            // UI Loading State
            const btnText = document.getElementById('genBtnText');
            const loader = document.getElementById('genLoader');
            btnText.textContent = "Processing...";
            loader.classList.remove('hidden');

            const formData = new FormData(this);

            try {
                const response = await fetch('/upload_and_preview', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();

                if (result.status === 'success') {
                    // Update View
                    document.getElementById('placeholder-state').classList.add('hidden');
                    const resContainer = document.getElementById('result-container');
                    resContainer.classList.remove('hidden');

                    const img = document.getElementById('processedImage');
                    
                    // Add timestamp to prevent browser caching of same filename
                    // img.src = '/static/uploads/' + result.processed_file + '?t=' + new Date().getTime();
                    // --- CHANGED LINE BELOW ---
                    // Point to /static/processed/ and use the filename returned by backend
                    img.src = '/static/processed/' + result.processed_file + '?t=' + new Date().getTime(); 
                    // --------------------------


                    // Store state for final submission
                    currentData.processed_file = result.processed_file;
                    currentData.anime_name = result.anime_name;
                    currentData.email = document.getElementById('email').value;

                } else {
                
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred during processing.');
            } finally {
                btnText.textContent = "Generate Preview";
                loader.classList.add('hidden');
            }
        });

        function regenerate() {
            // Trigger the form submit again to "regenerate"
            document.getElementById('uploadForm').requestSubmit();
        }

        async function submitFinal() {
            if(!currentData.processed_file) return;

            try {
                const response = await fetch('/submit_final', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentData)
                });
                const result = await response.json();

                if(result.status === 'success') {
                    document.getElementById('new-id').textContent = '#' + result.id;
                    document.getElementById('success-message').classList.remove('hidden');
                    document.getElementById('result-container').classList.add('hidden');
                    document.getElementById('placeholder-state').classList.remove('hidden');
                    document.getElementById('placeholder-state').innerHTML = '<i class="fa-solid fa-check text-green-500 text-6xl mb-4"></i><p>Submitted successfully!</p>';

                    // Reset form
                    document.getElementById('uploadForm').reset();
                    document.getElementById('inputPreviewContainer').classList.add('hidden');

                    // Refresh status table immediately
                    refreshStatus();
                } else {
                    alert("Submission failed");
                }
            } catch (err) {
                alert("Network error");
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    # app.run(debug=True)
    # app.run(port=5000, debug=True)
    app.run(host='0.0.0.0', port=8080, debug=True)