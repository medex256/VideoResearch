/**
 * Shared video player functionality for all video viewing pages
 * 
 * Usage:
 * initVideoPlayer({
 *   apiEndpoint: '/api/videos',             // API endpoint to fetch videos
 *   roundNumber: 1,                         // Round number (1 or 2)
 *   endpointUrl: '/end_video_viewing_1',    // URL to navigate to when finished
 *   categories: ['category1', 'category2']  // Selected categories
 * });
 */
function initVideoPlayer(options) {
    // Default options
    const config = {
        apiEndpoint: '/api/videos',
        roundNumber: 1,
        endpointUrl: '/',
        categories: [],
        ...options
    };

    // Global state variables
    const selectedCategories = config.categories;
    let videos = [];
    let currentIndex = 0;
    let watchStartTime = null;
    let watchTime = 0;
    let isPlaying = false;
    let videoElement = null;
    let playPauseBtn = null;
    let currentPosition = 0;  // Track current playback position for better seek handling
    let lastRecordedPosition = 0;  // Track the last recorded position for seek detection

    // Initialize the page
    document.addEventListener('DOMContentLoaded', function() {
        // Get UI elements
        const likeBtn = document.getElementById('likeBtn');
        const dislikeBtn = document.getElementById('dislikeBtn');
        const starBtn = document.getElementById('starBtn');
        const commentForm = document.getElementById('commentForm');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        playPauseBtn = document.getElementById('playPauseBtn');
        
        // Fetch videos
        fetchVideos();
        
        // Set up event listeners
        nextBtn.addEventListener('click', handleNextButtonClick);
        prevBtn.addEventListener('click', handlePrevButtonClick);
        commentForm.addEventListener('submit', handleCommentSubmit);
        likeBtn.addEventListener('click', () => handleReaction('like', likeBtn));
        dislikeBtn.addEventListener('click', () => handleReaction('dislike', dislikeBtn));
        starBtn.addEventListener('click', () => handleReaction('star', starBtn));
        
        // Set up page unload handler
        window.addEventListener('beforeunload', saveWatchTimeBeforeUnload);
    });

    // Fetch videos from server
    function fetchVideos() {
        if (config.preloadedVideos && config.preloadedVideos.length > 0) {
            videos = config.preloadedVideos;
            console.log('Using preloaded videos:', videos);
            
            if (videos.length > 0) {
                showVideo(0);
                updateProgress();
            } else {
                document.getElementById('videoContainer').innerHTML = 
                    '<p>暂无视频可显示。</p>';
                document.getElementById('nextBtn').disabled = true;
            }
            return;
        }
        fetch(`${config.apiEndpoint}?categories=${selectedCategories.join(',')}`)
            .then(response => response.json())
            .then(data => {
                videos = data.videos;
                console.log('Fetched videos:', videos);
                
                if (videos.length > 0) {
                    showVideo(0);
                    updateProgress();
                } else {
                    document.getElementById('videoContainer').innerHTML = 
                        '<p>暂无视频可显示。</p>';
                    document.getElementById('nextBtn').disabled = true;
                }
            })
            .catch(error => {
                console.error('Error fetching videos:', error);
            });
    }

    // Convert Douyin link to local file path
    function getLocalVideoPath(originalLink) {
        let parts = originalLink.split("/");
        let possibleId = parts[parts.length - 1];
        let videoId = possibleId.replace(/\D/g, "");
        return `https://d47xsu9sfg2co.cloudfront.net/videos/${videoId}.mp4`;
    }

    // Main function to display a video
    async function showVideo(index) {
        // 1. Record any current watch time before switching
        await recordCurrentWatchTime();
        // 2. Clean up existing video element
        cleanupVideoElement();
        
        // 3. Get the new video and update display
        const video = videos[index];
        const videoContainer = document.getElementById('videoContainer');
        const localPath = getLocalVideoPath(video.link);
        
        // 4. Create fresh DOM elements
        videoContainer.innerHTML = `
            <video id="videoFrame" controls>
                <source src="${localPath}" type="video/mp4">
                您的浏览器不支持 HTML5 video 标签.
            </video>
            <div class="controls">
                <button id="playPauseBtn" title="播放">
                    <span class="material-icons-outlined">play_arrow</span>
                </button>
            </div>
        `;
        
        // 5. Get references to new elements
        videoElement = document.getElementById('videoFrame');
        playPauseBtn = document.getElementById('playPauseBtn');
        
        // 6. Reset watch time for the new video
        resetWatchTime();
        
        // 7. Set up event handlers for the new video
        setupVideoEventHandlers();
        
        // 8. Update UI state
        updateUIState(index);
    }

    // Record the current watch time for the current video
    async function recordCurrentWatchTime() {
        if (watchStartTime !== null && currentIndex < videos.length) {
            // Get the ID of the current video
            const currentVideoId = videos[currentIndex].id;
            
            // Calculate duration
            const currentTime = Date.now();
            const duration = Math.round(((currentTime - watchStartTime) / 1000) * 100) / 100;
            watchTime += duration;
            
            // Get current playback position if video element exists
            if (videoElement) {
                currentPosition = Math.round(videoElement.currentTime);
            }
            
            // Only record if there is actual watch time
            if (watchTime > 0) {
                try {
                    const response = await fetch('/api/record_watch_time', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            video_id: currentVideoId,
                            watch_duration: watchTime,
                            round_number: config.roundNumber,
                            current_position: currentPosition
                        })
                    });
                    const data = await response.json();
                    console.log('Watch time recorded for video ID:', currentVideoId, 
                                'Duration:', watchTime, 
                                'Position:', currentPosition);
                    
                    // Update last recorded position
                    lastRecordedPosition = currentPosition;
                } catch (error) {
                    console.error('Error recording watch time:', error);
                }
            }
            
            // Reset tracking variables
            watchStartTime = null;
            watchTime = 0;
        }
    }

    // Clean up the current video element
    function cleanupVideoElement() {
        if (videoElement) {
            // Pause the video
            videoElement.pause();
            
            // Remove all event listeners
            videoElement.onloadedmetadata = null;
            videoElement.onplay = null;
            videoElement.onpause = null;
            videoElement.onended = null;
            
            // Reset source and force release of resources
            videoElement.src = '';
            videoElement.load();
            
            // Remove from DOM if needed
            if (videoElement.parentNode) {
                videoElement.parentNode.removeChild(videoElement);
            }
        }
    }

    // Set up event handlers for the new video
    function setupVideoEventHandlers() {
        // Handle video metadata loaded
        videoElement.addEventListener('loadedmetadata', function() {
            // Attempt to play with a small delay to ensure clean transition
            setTimeout(() => {
                this.play()
                    .then(() => {
                        isPlaying = true;
                        playPauseBtn.innerHTML = '<span class="material-icons-outlined">pause</span>';
                        playPauseBtn.setAttribute('title', '暂停');
                    })
                    .catch(e => {
                        console.error("Autoplay prevented:", e);
                        isPlaying = false;
                        playPauseBtn.innerHTML = '<span class="material-icons-outlined">play_arrow</span>';
                        playPauseBtn.setAttribute('title', '播放');
                    });
            }, 100);
        });
        
        // Core video event handlers
        videoElement.addEventListener('play', handlePlay);
        videoElement.addEventListener('pause', handlePause);
        videoElement.addEventListener('ended', handleEnded);
        // Listen for 'seeking' (when user starts skipping)
        videoElement.addEventListener('seeking', function() {
            if (isPlaying && watchStartTime !== null) {
                // Record watch time up to the seeking point
                recordCurrentWatchTime();
            }
        });
        
        // Listen for 'seeked' (when user finishes skipping)
        videoElement.addEventListener('seeked', function() {
            // Get the new position after seeking
            currentPosition = Math.round(videoElement.currentTime);
            
            // If significantly different from last position, consider it a seek
            const seekDistance = Math.abs(currentPosition - lastRecordedPosition);
            if (seekDistance > 2) { // More than 2 seconds difference
                console.log(`Seek detected: ${lastRecordedPosition}s → ${currentPosition}s (${seekDistance}s)`);
                lastRecordedPosition = currentPosition;
            }
            
            // If video is playing, start a new watch time segment
            if (isPlaying) {
                watchStartTime = Date.now();
            }
        });
        
        // Control button
        playPauseBtn.addEventListener('click', togglePlayPause);
    }

    // Update UI state for the new video
    function updateUIState(index) {
        // Update navigation buttons
        document.getElementById('prevBtn').disabled = index === 0;
        
        if (index === videos.length - 1) {
            document.getElementById('nextBtn').textContent = '继续下一步';
        } else {
            document.getElementById('nextBtn').textContent = '下一个';
        }
        
        // Reset reaction buttons
        const likeBtn = document.getElementById('likeBtn');
        const dislikeBtn = document.getElementById('dislikeBtn');
        const starBtn = document.getElementById('starBtn');
        
        likeBtn.classList.remove('like');
        dislikeBtn.classList.remove('dislike');
        starBtn.classList.remove('star');
        likeBtn.querySelector('.material-icons-outlined').textContent = 'thumb_up_off_alt';
        dislikeBtn.querySelector('.material-icons-outlined').textContent = 'thumb_down_off_alt';
        starBtn.querySelector('.material-icons-outlined').textContent = 'star_border';
        
        // Update progress indicator
        updateProgress();
    }

    // Video event handlers
    function handlePlay() {
        isPlaying = true;
        watchStartTime = Date.now();
        // Update current position when play starts
        if (videoElement) {
            currentPosition = Math.round(videoElement.currentTime);
        }
        playPauseBtn.innerHTML = '<span class="material-icons-outlined">pause</span>';
        playPauseBtn.setAttribute('title', '暂停');
    }

    function handlePause() {
        if (isPlaying) {
            // Update current position before recording
            if (videoElement) {
                currentPosition = Math.round(videoElement.currentTime);
            }
            recordCurrentWatchTime();
            isPlaying = false;
            playPauseBtn.innerHTML = '<span class="material-icons-outlined">play_arrow</span>';
            playPauseBtn.setAttribute('title', '播放');
        }
    }

    function handleEnded() {
        //recordCurrentWatchTime();
        isPlaying = false;
        playPauseBtn.innerHTML = '<span class="material-icons-outlined">play_arrow</span>';
        playPauseBtn.setAttribute('title', '播放');
        // Note: We intentionally don't auto-navigate when video ends
    }

    // Toggle Play/Pause
    function togglePlayPause() {
        if (isPlaying) {
            videoElement.pause();
        } else {
            videoElement.play();
        }
    }

    // Handle next button click
    async function handleNextButtonClick() {
        // First, record watch time before changing state
        await recordCurrentWatchTime();
        
        // Then clean up the current video
        cleanupVideoElement();
        
        if (currentIndex >= videos.length - 1) {
            // Final video - handle leaving the page
            await handleFinalVideoNavigation();
        } else {
            // Move to next video
            currentIndex++;
            await showVideo(currentIndex);
        }
    }

    // Handle previous button click
    async function handlePrevButtonClick() {
        if (currentIndex > 0) {
            // First record current watch time
            await recordCurrentWatchTime();
            
            // Then clean up video
            cleanupVideoElement();
            
            currentIndex--;
            await showVideo(currentIndex);
        }
    }

    // Handle final video navigation
    async function handleFinalVideoNavigation() {
        // Capture the current video's ID
        const finalVideoId = videos[currentIndex].id;
        
        // Record any remaining watch time
        if (watchStartTime !== null) {
            try {
                // Calculate final watch time
                const currentTime = Date.now();
                const duration = Math.round(((currentTime - watchStartTime) / 1000) * 100) / 100;
                watchTime += duration;
                
                // Get final position if possible
                if (videoElement) {
                    currentPosition = Math.round(videoElement.currentTime);
                }
                
                // Send watch time data
                const response = await fetch('/api/record_watch_time', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_id: finalVideoId,
                        watch_duration: watchTime,
                        round_number: config.roundNumber,
                        current_position: currentPosition
                    })
                });
                
                const data = await response.json();
                console.log('Final watch time recorded for video ID:', finalVideoId);
                
                // Reset tracking variables
                watchStartTime = null;
                watchTime = 0;
            } catch (error) {
                console.error('Error recording final watch time:', error);
            }
        }
        
        // Stop all media elements on the page
        document.querySelectorAll('video, audio').forEach(media => {
            media.pause();
            media.src = '';
            media.load();
        });
        
        // Navigate to the next page
        window.location.href = config.endpointUrl;
    }

    // Handle page unload (browser close, refresh, etc.)
    function saveWatchTimeBeforeUnload() {
        if (watchStartTime !== null) {
            const videoId = videos[currentIndex].id;
            const currentTime = Date.now();
            const duration = Math.round(((currentTime - watchStartTime) / 1000) * 100) / 100;
            
            // Get the final position if possible
            let finalPosition = currentPosition;
            if (videoElement) {
                finalPosition = Math.round(videoElement.currentTime);
            }
            
            // Use sendBeacon for reliable data transmission during page unload
            navigator.sendBeacon('/api/record_watch_time', JSON.stringify({
                video_id: videoId,
                watch_duration: duration,
                round_number: config.roundNumber,
                current_position: finalPosition
            }));
        }
    }

    // Reset watch time tracking for a new video
    function resetWatchTime() {
        watchStartTime = null;
        watchTime = 0;
        currentPosition = 0;
        lastRecordedPosition = 0;
    }

    // Update progress indicator
    function updateProgress() {
        document.querySelector('.progress-number').textContent = currentIndex + 1;
        document.querySelector('.progress-total').textContent = videos.length;
    }

    // Handle reactions (like, dislike, star)
    function handleReaction(action, button) {
        const iconElement = button.querySelector('.material-icons-outlined');
        const videoId = videos[currentIndex].id;
        
        // Handle reaction based on type
        switch(action) {
            case 'like':
                if (button.classList.contains('like')) {
                    button.classList.remove('like');
                    iconElement.textContent = 'thumb_up_off_alt';
                    sendInteraction(videoId, 'remove_like');
                } else {
                    button.classList.add('like');
                    iconElement.textContent = 'thumb_up';
                    
                    // Remove dislike if present
                    const dislikeBtn = document.getElementById('dislikeBtn');
                    if (dislikeBtn.classList.contains('dislike')) {
                        dislikeBtn.classList.remove('dislike');
                        dislikeBtn.querySelector('.material-icons-outlined').textContent = 'thumb_down_off_alt';
                        sendInteraction(videoId, 'remove_dislike');
                    }
                    
                    sendInteraction(videoId, 'like');
                }
                break;
                
            case 'dislike':
                if (button.classList.contains('dislike')) {
                    button.classList.remove('dislike');
                    iconElement.textContent = 'thumb_down_off_alt';
                    sendInteraction(videoId, 'remove_dislike');
                } else {
                    button.classList.add('dislike');
                    iconElement.textContent = 'thumb_down';
                    
                    // Remove like if present
                    const likeBtn = document.getElementById('likeBtn');
                    if (likeBtn.classList.contains('like')) {
                        likeBtn.classList.remove('like');
                        likeBtn.querySelector('.material-icons-outlined').textContent = 'thumb_up_off_alt';
                        sendInteraction(videoId, 'remove_like');
                    }
                    
                    sendInteraction(videoId, 'dislike');
                }
                break;
                
            case 'star':
                if (button.classList.contains('star')) {
                    button.classList.remove('star');
                    iconElement.textContent = 'star_border';
                    sendInteraction(videoId, 'star_remove');
                } else {
                    button.classList.add('star');
                    iconElement.textContent = 'star';
                    sendInteraction(videoId, 'star');
                }
                break;
        }
    }

    // Handle comment submission
    function handleCommentSubmit(e) {
        e.preventDefault();
        const commentInput = document.getElementById('commentInput');
        const commentText = commentInput.value.trim();
        if (!commentText) return;
        
        const videoId = videos[currentIndex].id;
        
        sendInteraction(videoId, 'comment', commentText)
            .then(response => {
                if (response.success) {
                    commentInput.value = '';
                    alert('评论已提交。');
                } else {
                    alert(response.message || '提交评论失败，请稍后再试。');
                }
            });
    }

    // Send interaction to server
    function sendInteraction(videoId, action, commentText = '') {
        console.log('Sending Interaction:', { video_id: videoId, action, comment: commentText });
        
        return fetch('/api/user_interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: videoId,
                action: action,
                comment: commentText
            })
        })
        .then(res => res.json())
        .catch(error => {
            console.error('Error sending interaction:', error);
            return { success: false, message: '网络错误，请稍后再试。' };
        });
    }
}