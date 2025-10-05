# Pixub Space Program

This project is a web application featuring a user interface for generative AI tasks. The backend is powered by **ComfyUI**, enabling the flexible setup and execution of complex workflows for image and video generation.

**A live demonstration of the project is available here: [https://nova.delightex.com/shared/hnlmtp](https://nova.delightex.com/shared/hnlmtp)**

## 🚀 Key Features

* **Web Interface**: A simple and intuitive interface for interacting with the models.
* **Image Generation**: Supports workflows for image-to-image transformations (img2img).
* **Video Generation**: Basic capabilities for creating videos based on specified parameters.
* **Flexible Workflows**: Utilizes `.json` files to define and switch between different generation pipelines.

## 🛠️ Tech Stack

* **Backend**: Python, ComfyUI
* **Frontend**: HTML, CSS, JavaScript

## ⚙️ Project Structure

* `app.py`: The main server file that runs the application.
* `/ComfyUI`: Directory containing the ComfyUI core.
* `index.html`, `style.css`, `script.js`: Files responsible for the user interface.
* `*.workflow.json`: Workflow definition files for ComfyUI.
* `requirements.txt`: A list of required Python libraries.

## 🏁 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/maxheyko/Pixub-Space-Program-.git](https://github.com/maxheyko/Pixub-Space-Program-.git)
    cd Pixub-Space-Program-
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```

4.  Open your browser and navigate to the address shown in the console (usually `http://127.0.0.1:8188` or another port).