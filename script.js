class ComfyUIClient {
    constructor() {
        this.serverUrl = 'http://localhost:3000';
        this.init();
    }

    init() {
        this.customPrompt = document.getElementById('customPrompt');
        this.habitatType = document.getElementById('habitatType');
        this.generateBtn = document.getElementById('generateBtn');
        this.status = document.getElementById('status');
        this.imageContainer = document.getElementById('imageContainer');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.timer = document.getElementById('timer');
        this.genTypeRadios = document.querySelectorAll('input[name="genType"]');
        
        this.startTime = null;
        this.timerInterval = null;
        
        // Add event listeners for generation type change
        this.genTypeRadios.forEach(radio => {
            radio.addEventListener('change', () => this.updateGenerateButton());
        });
        
        this.updateGenerateButton();

        this.generateBtn.addEventListener('click', () => this.generateImage());
        this.customPrompt.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.generateImage();
            }
        });
    }

    async generateImage() {
        const generationType = document.querySelector('input[name="genType"]:checked').value;
        const prompt = this.buildHabitatPrompt();

        if (!prompt) {
            this.showStatus('Please configure habitat parameters or add custom requirements', 'error');
            return;
        }

        this.setLoading(true);
        this.showProgress(0);
        this.startTimer();
        this.showStatus(`Starting ${generationType} generation...`, 'loading');

        try {
            // Start the generation request (don't await yet)
            const generatePromise = fetch(`${this.serverUrl}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    prompt: prompt,
                    type: generationType 
                })
            });

            // Start progress polling after a short delay
            setTimeout(() => this.pollProgress(), 1000);

            const response = await generatePromise;

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.imageUrl) {
                this.showProgress(100);
                this.displayContent(data.imageUrl, data.type || 'image', data);
                const frameText = data.frameCount ? ` (${data.frameCount} frames)` : '';
                this.showStatus(`${data.type || 'Image'} generated successfully!${frameText}`, 'success');
            } else {
                throw new Error(data.error || `Failed to generate ${generationType}`);
            }

        } catch (error) {
            console.error('Error generating image:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
            this.stopTimer();
            this.hideProgress();
        }
    }

    displayContent(contentUrl, type = 'image', data = null) {
        if (type === 'video') {
            if (data && data.imageUrls) {
                // Create animated slideshow from batch images
                this.createVideoSlideshow(data.imageUrls);
            } else {
                // Display true video from SVD
                this.displayTrueVideo(contentUrl, data);
            }
        } else {
            this.imageContainer.innerHTML = `
                <img src="${contentUrl}" alt="Generated ${type}" class="generated-image">
            `;
        }
    }

    displayTrueVideo(videoUrl, data) {
        const frameCount = data && data.frameCount ? data.frameCount : 25;
        this.imageContainer.innerHTML = `
            <div class="true-video-container">
                <video controls autoplay loop class="generated-video">
                    <source src="${videoUrl}" type="video/mp4">
                    <source src="${videoUrl}" type="video/webm">
                    Your browser does not support the video tag.
                </video>
                <div class="video-info">
                    <span class="video-details">SVD Video • ${frameCount} frames • 6 FPS</span>
                </div>
            </div>
        `;
    }

    createVideoSlideshow(imageUrls) {
        this.imageContainer.innerHTML = `
            <div class="video-slideshow">
                <div class="slideshow-container">
                    <img src="${imageUrls[0]}" alt="Generated video frame" class="generated-image slideshow-image current">
                    <img src="${imageUrls[1] || imageUrls[0]}" alt="Generated video frame" class="generated-image slideshow-image next">
                </div>
                <div class="video-controls">
                    <button class="play-pause-btn">⏸️</button>
                    <span class="frame-info">Frame 1 of ${imageUrls.length}</span>
                </div>
            </div>
        `;

        const currentImg = this.imageContainer.querySelector('.slideshow-image.current');
        const nextImg = this.imageContainer.querySelector('.slideshow-image.next');
        const playPauseBtn = this.imageContainer.querySelector('.play-pause-btn');
        const frameInfo = this.imageContainer.querySelector('.frame-info');
        
        let currentFrame = 0;
        let isPlaying = true;
        let intervalId;

        const fadeTransition = () => {
            nextImg.style.opacity = '0';
            nextImg.style.transition = 'opacity 1.5s ease-in-out';
            
            setTimeout(() => {
                nextImg.style.opacity = '1';
            }, 50);
        };

        const updateFrame = () => {
            const nextFrame = (currentFrame + 1) % imageUrls.length;
            
            // Preload next image
            nextImg.src = imageUrls[nextFrame];
            
            // Apply fade transition
            fadeTransition();
            
            // Update frame info
            frameInfo.textContent = `Frame ${nextFrame + 1} of ${imageUrls.length}`;
            
            // After transition, swap the images
            setTimeout(() => {
                currentImg.src = imageUrls[nextFrame];
                nextImg.style.opacity = '0';
                nextImg.style.transition = '';
                currentFrame = nextFrame;
            }, 1600); // Wait for fade to complete
        };

        const startAnimation = () => {
            intervalId = setInterval(updateFrame, 5000); // 5 seconds between transitions
        };

        const stopAnimation = () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        };

        playPauseBtn.addEventListener('click', () => {
            if (isPlaying) {
                stopAnimation();
                playPauseBtn.textContent = '▶️';
                isPlaying = false;
            } else {
                startAnimation();
                playPauseBtn.textContent = '⏸️';
                isPlaying = true;
            }
        });

        // Start animation
        startAnimation();
    }

    showStatus(message, type = 'info') {
        this.status.textContent = message;
        this.status.className = `mission-status ${type}`;

        if (type === 'loading') {
            this.status.innerHTML = `🔧 ${message}`;
        }
    }

    setLoading(isLoading) {
        this.generateBtn.disabled = isLoading;
        if (!isLoading) {
            this.updateGenerateButton();
        } else {
            const type = document.querySelector('input[name="genType"]:checked').value;
            this.generateBtn.textContent = `Generating ${type}...`;
        }
    }

    updateGenerateButton() {
        const selectedType = document.querySelector('input[name="genType"]:checked').value;
        const btnText = selectedType === 'video' ? '🎬 Generate 360° Tour' : '📸 Generate Static View';
        this.generateBtn.innerHTML = `<span class="btn-icon">🛠️</span>${btnText}`;
    }

    buildHabitatPrompt() {
        const habitatType = this.habitatType.value;
        const customPrompt = this.customPrompt.value.trim();
        
        // Habitat type descriptions
        const habitatDescriptions = {
            'surface': 'futuristic planetary surface base with landing pads and surface equipment',
            'orbital': 'advanced orbital space station with docking ports and solar arrays',
            'deep-space': 'deep space outpost with advanced propulsion and long-range communications',
            'lunar': 'lunar colony with regolith protection and Earth-view windows',
            'mars': 'Mars settlement with atmospheric processors and red Martian landscape'
        };
        
        let basePrompt = `${habitatDescriptions[habitatType]}`;
        
        // Add custom requirements if provided
        if (customPrompt) {
            basePrompt += `, ${customPrompt}`;
        } else {
            // Add default features if no custom prompt
            basePrompt += ', with life support systems, crew quarters, and advanced technology';
        }
        
        // Add quality and style modifiers (simplified for faster generation)
        basePrompt += ', detailed, cinematic, sci-fi, realistic';
        
        return basePrompt;
    }

    showProgress(percent) {
        this.progressContainer.style.display = 'block';
        this.progressFill.style.width = `${percent}%`;
        this.progressText.textContent = `${percent}%`;
    }

    hideProgress() {
        this.progressContainer.style.display = 'none';
        this.progressFill.style.width = '0%';
        this.progressText.textContent = '0%';
        this.timer.textContent = '00:00';
    }

    async pollProgress() {
        // This is a simple approach - in a real app you'd track the prompt_id
        // For now, we'll just simulate progress updates
        let progress = 0;
        const interval = setInterval(() => {
            if (!this.generateBtn.disabled) {
                clearInterval(interval);
                return;
            }
            
            progress += Math.random() * 10;
            if (progress > 95) progress = 95; // Don't go to 100% until actually done
            
            this.showProgress(Math.floor(progress));
            const type = document.querySelector('input[name="genType"]:checked').value;
            this.showStatus(`Generating ${type}... ${Math.floor(progress)}%`, 'loading');
        }, 1000);
    }

    startTimer() {
        this.startTime = Date.now();
        this.updateTimer();
        this.timerInterval = setInterval(() => this.updateTimer(), 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimer() {
        if (!this.startTime) return;
        
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        const formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        this.timer.textContent = formattedTime;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ComfyUIClient();
});