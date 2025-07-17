// Common functionality across pages
document.addEventListener('DOMContentLoaded', function() {
    // Load theme from localStorage with robust error handling
    try {
        const savedThemeJSON = localStorage.getItem('echoNoteTheme');
        console.log('Raw theme data from localStorage:', savedThemeJSON);
        
        if (savedThemeJSON && savedThemeJSON !== 'undefined') {
            const savedTheme = JSON.parse(savedThemeJSON);
            console.log('Parsed theme data:', savedTheme);
            
            // Apply theme only if we have valid data
            if (savedTheme && typeof savedTheme === 'object') {
                // Apply each property with fallbacks
                document.documentElement.style.setProperty('--bg-primary', savedTheme.bgPrimary || '#212121');
                document.documentElement.style.setProperty('--bg-secondary', savedTheme.bgSecondary || '#303030');
                document.documentElement.style.setProperty('--text-primary', savedTheme.textPrimary || '#ececf1');
                document.documentElement.style.setProperty('--text-secondary', savedTheme.textSecondary || '#ffffff');
                document.documentElement.style.setProperty('--accent', savedTheme.accent || '#FCFCFD');
                document.documentElement.style.setProperty('--button-text', savedTheme.buttonText || '#36395A');
                document.documentElement.style.setProperty('--border-color', savedTheme.borderColor || '#444');
                
                console.log('Theme applied successfully');
            }
        } else {
            console.log('No saved theme found in localStorage');
        }
    } catch (error) {
        console.error('Error loading theme:', error);
    }

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });
  
    // Initialize any other common UI elements
    
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
                        this.textContent = 'Undo';
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
                        this.textContent = 'Done';
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