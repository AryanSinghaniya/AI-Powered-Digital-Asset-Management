document.addEventListener('DOMContentLoaded', () => {
    const folderPath = document.getElementById('folderPath');
    const indexBtn = document.getElementById('indexBtn');
    const statusLabel = document.getElementById('statusLabel');
    const progressFill = document.getElementById('progressFill');
    const statsText = document.getElementById('statsText');
    
    const searchQuery = document.getElementById('searchQuery');
    const searchBtn = document.getElementById('searchBtn');
    const filters = document.querySelectorAll('.type-filter');
    const resultsGrid = document.getElementById('resultsGrid');
    
    const foldersList = document.getElementById('foldersList');
    const resetBtn = document.getElementById('resetBtn');

    let statusInterval = null;
    
    async function fetchFolders() {
        try {
            const res = await fetch('/api/folders');
            if (res.ok) {
                const data = await res.json();
                if (data.folders && data.folders.length > 0) {
                    let html = '<strong>Indexed Folders:</strong><ul>';
                    data.folders.forEach(f => {
                        html += `<li>${f.path} (${f.count} files)</li>`;
                    });
                    html += '</ul>';
                    foldersList.innerHTML = html;
                } else {
                    foldersList.innerHTML = '<strong>Indexed Folders:</strong> <span>None</span>';
                }
            }
        } catch(e) { console.error("Failed to fetch folders", e); }
    }
    
    // Fetch folders on load
    fetchFolders();
    
    resetBtn.addEventListener('click', async () => {
        if (!confirm("Are you sure you want to completely clear the entire index? This cannot be undone.")) return;
        try {
            const res = await fetch('/api/reset', { method: 'POST' });
            if (res.ok) {
                alert("Index completely reset.");
                fetchFolders();
                resultsGrid.innerHTML = '';
            } else {
                alert("Failed to reset index.");
            }
        } catch(e) {
            console.error(e);
            alert("Failed to reset index.");
        }
    });

    // Indexing
    indexBtn.addEventListener('click', async () => {
        const path = folderPath.value.trim();
        if(!path) return alert("Please enter a folder path");

        try {
            const res = await fetch('/api/index', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_path: path })
            });
            
            if (!res.ok) {
                const data = await res.json();
                return alert(`Error: ${data.detail || 'Failed to start indexing'}`);
            }
            
            startStatusPolling();
        } catch(e) {
            console.error(e);
            alert("Failed to start indexing");
        }
    });

    // Polling Status
    function startStatusPolling() {
        if(statusInterval) clearInterval(statusInterval);
        statusLabel.textContent = "Processing...";
        statusInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                statsText.textContent = `Total: ${data.total} | Done: ${data.done} | Pending: ${data.pending} | Failed: ${data.failed}`;
                
                const processingOrPending = data.pending + data.processing;
                if(data.total > 0) {
                    const percent = (data.done / data.total) * 100;
                    progressFill.style.width = `${percent}%`;
                }

                if(processingOrPending === 0 && data.total > 0) {
                    clearInterval(statusInterval);
                    statusLabel.textContent = "Idle";
                    progressFill.style.width = `100%`;
                    fetchFolders();
                }
            } catch(e) {
                console.error(e);
            }
        }, 2000);
    }
    
    startStatusPolling();

    // Searching
    searchBtn.addEventListener('click', doSearch);
    searchQuery.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') doSearch();
    });

    async function doSearch() {
        const query = searchQuery.value.trim();
        if(!query) return;

        const selectedTypes = Array.from(filters)
            .filter(f => f.checked)
            .map(f => f.value);

        searchBtn.textContent = "Searching...";
        searchBtn.disabled = true;

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    file_types: selectedTypes.length > 0 ? selectedTypes : null,
                    limit: 100
                })
            });
            const data = await res.json();
            renderResults(data);
        } catch(e) {
            console.error(e);
            alert("Search failed");
        } finally {
            searchBtn.textContent = "Search";
            searchBtn.disabled = false;
        }
    }

    function renderResults(results) {
        resultsGrid.innerHTML = '';
        if(results.length === 0) {
            resultsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No results found for your query. Try something else!</div>';
            return;
        }

        results.forEach(res => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            let previewHtml = '';
            const fileUrl = `/api/file?path=${encodeURIComponent(res.filepath)}`;
            
            if(res.type === 'image') {
                previewHtml = `<img src="${fileUrl}" alt="preview">`;
            } else if(res.type === 'video') {
                // Videos play on hover
                previewHtml = `<video src="${fileUrl}#t=0.1" preload="metadata" muted loop onmouseover="this.play()" onmouseout="this.pause()"></video>`;
            } else if(res.type === 'pdf') {
                previewHtml = `<div class="pdf-icon">📄</div>`;
            }

            card.innerHTML = `
                <div class="preview-container">
                    <span class="type-badge">${res.type}</span>
                    ${previewHtml}
                </div>
                <div class="card-info">
                    <div class="filename" title="${res.filename}">${res.filename}</div>
                    <div class="file-meta">
                        <span>${res.formatted_size || 'Unknown Size'}</span>
                        <span class="score">${(res.score * 100).toFixed(1)}% Match</span>
                    </div>
                    <button class="action-btn" onclick="openFile('${res.filepath.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">Open File Location</button>
                </div>
            `;
            resultsGrid.appendChild(card);
        });
    }

    window.openFile = async (filepath) => {
        try {
            // Attempt to copy to clipboard as a fallback
            try {
                await navigator.clipboard.writeText(filepath);
                alert("File path copied to clipboard:\n" + filepath + "\n\n(Attempting to open in Explorer...)");
            } catch (err) {
                alert("File path:\n" + filepath);
            }
            
            await fetch('/api/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filepath: filepath })
            });
        } catch(e) {
            console.error("Failed to open file", e);
        }
    }
});
