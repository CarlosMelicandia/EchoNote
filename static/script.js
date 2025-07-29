// Common functionality across pages

// default dark theme
const defaultTheme = {
  bgPrimary:   '#212121',
  bgSecondary: '#303030',
  textPrimary: '#ececf1',
  textSecondary:'#ffffff',
  accent:      '#FCFCFD',
  buttonText:  '#36395A',
  borderColor: '#444'
};


// apply theme object to CSS variables
function applyTheme(theme) {
  const root = document.documentElement;
  root.style.setProperty('--bg-primary',   theme.bgPrimary);
  root.style.setProperty('--bg-secondary', theme.bgSecondary);
  root.style.setProperty('--text-primary', theme.textPrimary);
  root.style.setProperty('--text-secondary', theme.textSecondary);
  root.style.setProperty('--accent',       theme.accent);
  root.style.setProperty('--button-text',  theme.buttonText);
  root.style.setProperty('--border-color', theme.borderColor);
}

// load the theme - try server first, then localStorage, then default
async function loadTheme() {
  let theme = defaultTheme;

  if (window.currentUser) {
    try {
      const resp = await fetch('/api/get_theme');
      if (resp.ok) {
        theme = await resp.json();
      } else {
        throw new Error('Server returned ' + resp.status);
      }
    } catch (err) {
      console.warn('Could not fetch theme from server, falling back to localStorage', err);
      const saved = localStorage.getItem('echoNoteTheme');
      if (saved) theme = JSON.parse(saved);
    }
  } else {
    const saved = localStorage.getItem('echoNoteTheme');
    if (saved) theme = JSON.parse(saved);
  }

  applyTheme(theme || defaultTheme);
}

// Nav‐link highlighting
function highlightNav() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('nav a').forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === currentPath);
  });
}

// once the DOM is ready
document.addEventListener('DOMContentLoaded', () => {

//start recording
    const recordButton = document.getElementById('btn-record');
    const stopButton = document.getElementById('btn-stop');
    const saveButton = document.getElementById('btn-save');
    const transcriptArea = document.getElementById('transcript');
        
    let recorder;
    let stream;

// Initialize media recording
    navigator.mediaDevices.getUserMedia({ audio: true }).then(
        mediaStream => {
            stream = mediaStream;
            recorder = new MediaRecorder(stream);
            let chunks = [];

            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/webm'});
                chunks = [];

                const form = new FormData();
                form.append('audio', blob, 'recording.webm')

                try {
                    const res = await fetch('/api/transcribe', { method: 'POST', body: form});
                    const payload = await res.json();
                    if (!res.ok) throw new Error(payload.error || "Transcription failed");
                    transcriptArea.value = payload.transcript;
                } catch (error) {
                    console.error('Error transcribing audio:', error);
                    transcriptArea.value = 'Error transcribing audio. Please try again.';
                }
            };
        }
        ).catch(error => {
            console.error('Error accessing microphone:', error);
            alert('Could not access microphone. Please check permissions.');
        });

        // Record button
        recordButton.addEventListener('click', function() {
            if (recorder && recorder.state === 'inactive') {
                recorder.start();
                recordButton.classList.add('recording');
                stopButton.disabled = false;
            }
        });

        // Stop button
        stopButton.addEventListener('click', function() {
            if (recorder && recorder.state === 'recording') {
                recorder.stop();
                recordButton.classList.remove('recording');
                stopButton.disabled = true;
                
                // Stop all tracks
                if (stream) {
                    stream.getTracks().forEach(track => {
                        if (track.readyState === 'live') {
                            track.stop();
                        }
                    });
                }
                
        // Reinitialize for next recording
        navigator.mediaDevices.getUserMedia({ audio: true }).then(
            mediaStream => {
                stream = mediaStream;
                recorder = new MediaRecorder(stream);
                let chunks = [];

                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.onstop = async () => {
                    const blob = new Blob(chunks, { type: 'audio/webm'});
                    chunks = [];

                    const form = new FormData();
                    form.append('audio', blob, 'recording.webm')

                    try {
                        const res = await fetch('/api/transcribe', { method: 'POST', body: form});
                        const payload = await res.json();
                        if (!res.ok) throw new Error(payload.error || "Transcription failed");
                        transcriptArea.value = payload.transcript;
                        } catch (error) {
                        console.error('Error transcribing audio:', error);
                        transcriptArea.value = 'Error transcribing audio. Please try again.';
                    }
                    };
                }
            ).catch(console.error);
        }
    });  
    
    // Save button
        saveButton.addEventListener('click', async function() {
            const transcript = transcriptArea.value.trim();
            
            if (!transcript) {
                alert('Please record something first.');
                return;
            }
            
            try {
                const response = await fetch('/api/save_task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        transcript: transcript
                    })
                });
                
                if (response.ok) {
                    // Clear the transcript area
                    transcriptArea.value = '';
                    
                    // Refresh the page to show the new task
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to save task');
                }
            } catch (error) {
                console.error('Error saving task:', error);
                alert('Error saving task: ' + error.message);
            }
        });

    loadTheme();
    highlightNav();
  
    
    // Handle keyboard shortcuts that should work across the app
    document.addEventListener('keydown', function(e) {
      // Add any global keyboard shortcuts here
      // For example: Ctrl+S to save, Esc to cancel, etc.
    });

    // Task editing, deletion, and completion functionality
    // Only run this code on pages with task items
    if (document.querySelector('.task-list')) {
        // Task editing
        document.querySelectorAll('.btn-edit').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.getAttribute('data-task-id');
                const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
                const taskContent = taskItem.querySelector('.task-content').textContent.trim();
                
                // Extract task name (remove the "— Due: date" and "(Done)" parts if present)
                let taskName = taskContent;
                if (taskName.includes('—')) {
                    taskName = taskName.split('—')[0].trim();
                }
                if (taskName.includes('(Done)')) {
                    taskName = taskName.replace('(Done)', '').trim();
                }
                
                // Create edit form
                const originalContent = taskItem.innerHTML;
                taskItem.innerHTML = `
                    <div class="task-edit-form">
                        <input type="text" id="edit-task-name" value="${taskName}">
                        <div class="edit-actions">
                            <button class="btn-save">Save</button>
                            <button class="btn-cancel">Cancel</button>
                        </div>
                    </div>
                `;
                
    

                
                // Save button
                taskItem.querySelector('.btn-save').addEventListener('click', async function() {
                    const newName = taskItem.querySelector('#edit-task-name').value.trim();
                    
                    if (!newName) {
                        alert('Task name cannot be empty');
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/api/tasks/${taskId}`, {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                name: newName
                            })
                        });
                        
                        if (response.ok) {
                            // Refresh the page to show updated task
                            window.location.reload();
                        } else {
                            const errorData = await response.json();
                            throw new Error(errorData.error || 'Failed to update task');
                        }
                    } catch (error) {
                        console.error('Error updating task:', error);
                        alert('Error updating task: ' + error.message);
                        // Restore original content
                        taskItem.innerHTML = originalContent;
                    }
                });
                
                // Cancel button
                taskItem.querySelector('.btn-cancel').addEventListener('click', function() {
                    taskItem.innerHTML = originalContent;
                    
                    // Re-attach event listeners to the restored buttons
                    attachTaskButtonListeners();
                });
            });
        });
        
        // Task deletion
        document.querySelectorAll('.btn-delete').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                
                if (confirm('Are you sure you want to delete this task?')) {
                    try {
                        const response = await fetch(`/api/tasks/${taskId}`, {
                            method: 'DELETE'
                        });
                        
                        if (response.ok) {
                            // Remove the task item from the DOM
                            const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
                            taskItem.remove();
                            
                            // If no tasks left, show the "no tasks" message
                            const taskList = document.querySelector('.task-list');
                            if (taskList.querySelectorAll('.task-item').length === 0) {
                                taskList.innerHTML = '<p>No tasks yet. Start recording to create tasks.</p>';
                            }
                        } else {
                            const errorData = await response.json();
                            throw new Error(errorData.error || 'Failed to delete task');
                        }
                    } catch (error) {
                        console.error('Error deleting task:', error);
                        alert('Error deleting task: ' + error.message);
                    }
                }
            });
        });
        
        // Task completion
        document.querySelectorAll('.btn-done').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
                
                try {
                    const response = await fetch(`/api/tasks/${taskId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            completed: true
                        })
                    });
                    
                    if (response.ok) {
                        // Mark as completed visually
                        taskItem.classList.add('completed');
                        
                        // Update the button to show "Undo" instead of "Done"
                        this.innerHTML = '<i class="fa-solid fa-rotate-left"></i>';
                        this.classList.remove('btn-done');
                        this.classList.add('btn-undo');
                        
                        // Add "(Done)" text to the task content if it's not already there
                        const taskContent = taskItem.querySelector('.task-content');
                        if (!taskContent.textContent.includes('(Done)')) {
                            taskContent.textContent = taskContent.textContent + ' (Done)';
                        }
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Failed to mark task as completed');
                    }
                } catch (error) {
                    console.error('Error marking task as completed:', error);
                    alert('Error marking task as completed: ' + error.message);
                }
            });
        });
        
        // Undo completion
        document.querySelectorAll('.btn-undo').forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
                
                try {
                    const response = await fetch(`/api/tasks/${taskId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            completed: false
                        })
                    });
                    
                    if (response.ok) {
                        // Remove completed styling
                        taskItem.classList.remove('completed');
                        
                        // Update the button back to "Done"
                        this.innerHTML = '<i class="fa-solid fa-check"></i>';
                        this.classList.remove('btn-undo');
                        this.classList.add('btn-done');
                        
                        // Remove "(Done)" text from the task content
                        const taskContent = taskItem.querySelector('.task-content');
                        taskContent.textContent = taskContent.textContent.replace(' (Done)', '');
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Failed to mark task as incomplete');
                    }
                } catch (error) {
                    console.error('Error marking task as incomplete:', error);
                    alert('Error marking task as incomplete: ' + error.message);
                }
            });
        });
        
        // Helper function to attach event listeners to task buttons
        function attachTaskButtonListeners() {
            // Re-attach edit button listeners
            document.querySelectorAll('.btn-edit').forEach(button => {
                button.addEventListener('click', function() {
                    // This would be a duplicate of the edit functionality above
                    // In a real implementation, you'd refactor the edit logic into a separate function
                    // and call it here
                });
            });
            
            // Re-attach delete button listeners
            document.querySelectorAll('.btn-delete').forEach(button => {
                button.addEventListener('click', function() {
                    // This would be a duplicate of the delete functionality above
                    // In a real implementation, you'd refactor the delete logic into a separate function
                    // and call it here
                });
            });
            
            // Re-attach done button listeners
            document.querySelectorAll('.btn-done').forEach(button => {
                button.addEventListener('click', function() {
                    // This would be a duplicate of the done functionality above
                    // In a real implementation, you'd refactor the done logic into a separate function
                    // and call it here
                });
            });
            
            // Re-attach undo button listeners
            document.querySelectorAll('.btn-undo').forEach(button => {
                button.addEventListener('click', function() {
                    // This would be a duplicate of the undo functionality above
                    // In a real implementation, you'd refactor the undo logic into a separate function
                    // and call it here
                });
            });
        }
    }
});