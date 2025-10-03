// SPARQL Agent Chat UI - Main Application JavaScript

class SPARQLAgentUI {
    constructor() {
        this.currentResults = null;
        this.conversationHistory = [];
        this.isLoading = false;

        this.initializeElements();
        this.bindEvents();
        this.loadHistory();
    }

    initializeElements() {
        // Main elements
        this.chatMessages = document.getElementById('chat-messages');
        this.queryText = document.getElementById('query-text');
        this.sendButton = document.getElementById('send-query');
        this.endpointSelect = document.getElementById('endpoint');
        this.testEndpointButton = document.getElementById('test-endpoint');
        this.endpointStatus = document.getElementById('endpoint-status');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.clearChatButton = document.getElementById('clear-chat');
        this.exportResultsButton = document.getElementById('export-results');
        this.autoExecuteCheckbox = document.getElementById('auto-execute');

        // Modal elements
        this.resultModal = document.getElementById('result-modal');
        this.modalCloseButtons = document.querySelectorAll('.modal-close');
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabPanels = document.querySelectorAll('.tab-panel');
        this.downloadCsvButton = document.getElementById('download-csv');
        this.downloadJsonButton = document.getElementById('download-json');

        // Tab content elements
        this.tableContent = document.getElementById('table-content');
        this.explanationText = document.getElementById('explanation-text');
        this.explanationTab = document.getElementById('explanation-tab');
        this.sparqlCode = document.getElementById('sparql-code');
        this.jsonCode = document.getElementById('json-code');
        this.chartCanvas = document.getElementById('chart-canvas');
        this.vizTab = document.getElementById('viz-tab');
    }

    bindEvents() {
        // Send query
        this.sendButton.addEventListener('click', () => this.sendQuery());
        this.queryText.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendQuery();
            }
        });

        // Auto-resize textarea
        this.queryText.addEventListener('input', () => {
            this.queryText.style.height = 'auto';
            this.queryText.style.height = Math.min(this.queryText.scrollHeight, 120) + 'px';
        });

        // Test endpoint
        this.testEndpointButton.addEventListener('click', () => this.testEndpoint());

        // Clear chat
        this.clearChatButton.addEventListener('click', () => this.clearChat());

        // Export results
        this.exportResultsButton.addEventListener('click', () => this.showResultModal());

        // Example queries
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('example-btn')) {
                const query = e.target.dataset.query;
                this.queryText.value = query;
                this.queryText.focus();
            }
        });

        // Modal events
        this.modalCloseButtons.forEach(button => {
            button.addEventListener('click', () => this.hideResultModal());
        });

        this.resultModal.addEventListener('click', (e) => {
            if (e.target === this.resultModal) {
                this.hideResultModal();
            }
        });

        // Tab switching
        this.tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Download buttons
        this.downloadCsvButton.addEventListener('click', () => this.downloadResults('csv'));
        this.downloadJsonButton.addEventListener('click', () => this.downloadResults('json'));

        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.resultModal.classList.contains('hidden')) {
                this.hideResultModal();
            }
        });
    }

    async sendQuery() {
        const query = this.queryText.value.trim();
        if (!query || this.isLoading) return;

        const endpoint = this.endpointSelect.value;

        // Add user message
        this.addMessage('user', query);
        this.queryText.value = '';
        this.queryText.style.height = 'auto';

        // Show loading
        this.setLoading(true);

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    endpoint: endpoint
                })
            });

            const data = await response.json();

            if (data.success) {
                this.handleQuerySuccess(data);
            } else {
                this.handleQueryError(data.error, data.sparql_query);
            }

        } catch (error) {
            console.error('Query error:', error);
            this.addMessage('assistant', `Network error: ${error.message}`, true);
        }

        this.setLoading(false);
    }

    handleQuerySuccess(data) {
        this.currentResults = data;

        // Create success message with explanation
        let message = `✅ Found ${data.result_count} results in ${data.execution_time}ms`;

        // Add natural language explanation if available
        if (data.explanation) {
            message += `\n\n**Explanation:**\n${data.explanation}`;
        }

        this.addMessage('assistant', message);

        // Enable export button
        this.exportResultsButton.disabled = false;

        // Show results modal if auto-execute is enabled
        if (this.autoExecuteCheckbox.checked) {
            setTimeout(() => this.showResultModal(), 500);
        }
    }

    handleQueryError(error, sparqlQuery = null) {
        let message = `❌ Error: ${error}`;

        if (sparqlQuery) {
            message += `\n\nGenerated SPARQL:\n\`\`\`sparql\n${sparqlQuery}\n\`\`\``;
        }

        this.addMessage('assistant', message, true);
    }

    addMessage(role, content, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}${isError ? ' error' : ''}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Handle markdown-style code blocks
        let formattedContent = content;
        formattedContent = formattedContent.replace(/```(\w+)?\n([\s\S]*?)```/g,
            (match, lang, code) => {
                return `<pre><code class="language-${lang || 'text'}">${this.escapeHtml(code.trim())}</code></pre>`;
            }
        );

        // Handle inline code
        formattedContent = formattedContent.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Handle line breaks
        formattedContent = formattedContent.replace(/\n/g, '<br>');

        contentDiv.innerHTML = formattedContent;
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        // Highlight code if present
        Prism.highlightAllUnder(contentDiv);

        // Store in history
        this.conversationHistory.push({
            role,
            content,
            timestamp: new Date().toISOString(),
            isError
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatExplanation(explanation) {
        // Handle markdown-style formatting
        let formatted = explanation;

        // Handle bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Handle line breaks
        formatted = formatted.replace(/\n\n/g, '</p><p>');
        formatted = formatted.replace(/\n/g, '<br>');

        // Handle bullet points
        formatted = formatted.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
        formatted = formatted.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

        // Handle numbered lists
        formatted = formatted.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
        formatted = formatted.replace(/(<li>.*<\/li>)/gs, (match) => {
            if (!match.includes('<ul>')) {
                return '<ol>' + match + '</ol>';
            }
            return match;
        });

        // Wrap in paragraphs if not already wrapped
        if (!formatted.includes('<p>') && !formatted.includes('<ul>') && !formatted.includes('<ol>')) {
            formatted = '<p>' + formatted + '</p>';
        }

        return formatted;
    }

    async testEndpoint() {
        const endpoint = this.endpointSelect.value;

        this.endpointStatus.textContent = 'Testing endpoint...';
        this.endpointStatus.className = 'endpoint-status testing';

        try {
            const response = await fetch('/api/endpoints/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ endpoint })
            });

            const data = await response.json();

            if (data.accessible) {
                this.endpointStatus.textContent = `✅ Connected (${data.response_time}ms)`;
                this.endpointStatus.className = 'endpoint-status success';
            } else {
                this.endpointStatus.textContent = `❌ Failed: ${data.error || 'Unknown error'}`;
                this.endpointStatus.className = 'endpoint-status error';
            }

        } catch (error) {
            this.endpointStatus.textContent = `❌ Network error: ${error.message}`;
            this.endpointStatus.className = 'endpoint-status error';
        }
    }

    async clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) {
            return;
        }

        try {
            await fetch('/api/clear', { method: 'POST' });

            // Clear UI
            this.chatMessages.innerHTML = `
                <div class="message system-message">
                    <div class="message-content">
                        <p>👋 Welcome to the SPARQL Agent! Type a natural language query to get started.</p>
                        <div class="example-queries">
                            <h4>Example queries:</h4>
                            <ul>
                                <li><button class="example-btn" data-query="Find 10 people born in Paris">Find 10 people born in Paris</button></li>
                                <li><button class="example-btn" data-query="Show me proteins involved in diabetes">Show me proteins involved in diabetes</button></li>
                                <li><button class="example-btn" data-query="List countries with their capitals">List countries with their capitals</button></li>
                                <li><button class="example-btn" data-query="Find ontology terms related to cancer">Find ontology terms related to cancer</button></li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;

            this.conversationHistory = [];
            this.currentResults = null;
            this.exportResultsButton.disabled = true;

        } catch (error) {
            console.error('Clear chat error:', error);
            alert('Failed to clear chat history');
        }
    }

    async loadHistory() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();

            // Restore conversation history
            if (data.history && data.history.length > 1) {  // More than just system message
                this.chatMessages.innerHTML = ''; // Clear welcome message

                data.history.forEach(message => {
                    if (message.role !== 'system') {
                        this.addMessage(message.role, message.content, message.metadata?.error);
                    }
                });
            }

        } catch (error) {
            console.error('Load history error:', error);
        }
    }

    showResultModal() {
        if (!this.currentResults) return;

        this.populateModalContent();
        this.resultModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    hideResultModal() {
        this.resultModal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    populateModalContent() {
        const data = this.currentResults;

        // Populate table
        this.populateTable(data.results);

        // Populate SPARQL
        this.sparqlCode.textContent = data.sparql_query;
        Prism.highlightElement(this.sparqlCode);

        // Populate explanation
        if (data.explanation) {
            this.explanationText.innerHTML = this.formatExplanation(data.explanation);
            this.explanationTab.style.display = 'block';
        } else {
            this.explanationTab.style.display = 'none';
        }

        // Populate JSON
        this.jsonCode.textContent = JSON.stringify(data, null, 2);
        Prism.highlightElement(this.jsonCode);

        // Show/hide visualization tab
        if (data.visualization) {
            this.vizTab.style.display = 'block';
            this.populateVisualization(data);
        } else {
            this.vizTab.style.display = 'none';
        }

        // Switch to table tab by default
        this.switchTab('table');
    }

    populateTable(results) {
        if (!results || results.length === 0) {
            this.tableContent.innerHTML = '<p>No results found.</p>';
            return;
        }

        // Create summary
        const summary = document.createElement('div');
        summary.className = 'result-summary';
        summary.innerHTML = `
            <span class="summary-text">Query Results</span>
            <span class="summary-stats">${results.length} rows</span>
        `;

        // Get all unique keys
        const allKeys = new Set();
        results.forEach(row => {
            Object.keys(row).forEach(key => allKeys.add(key));
        });
        const columns = Array.from(allKeys);

        // Create table
        const table = document.createElement('table');
        table.className = 'results-table';

        // Create header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create body
        const tbody = document.createElement('tbody');
        results.forEach(row => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row[col] || '';

                // Check if it's a URL
                if (value.startsWith('http://') || value.startsWith('https://')) {
                    const link = document.createElement('a');
                    link.href = value;
                    link.textContent = value;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    td.appendChild(link);
                } else {
                    td.textContent = value;
                }

                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        this.tableContent.innerHTML = '';
        this.tableContent.appendChild(summary);
        this.tableContent.appendChild(table);
    }

    populateVisualization(data) {
        // Simple bar chart example using Chart.js
        // This would be enhanced based on the visualization suggestion from the backend

        const ctx = this.chartCanvas.getContext('2d');

        // Clear any existing chart
        if (window.sparqlChart) {
            window.sparqlChart.destroy();
        }

        // Simple example: count of results per variable
        const results = data.results;
        if (!results || results.length === 0) return;

        // Get first column for labels and count occurrences
        const firstCol = Object.keys(results[0])[0];
        if (!firstCol) return;

        const counts = {};
        results.forEach(row => {
            const value = row[firstCol];
            counts[value] = (counts[value] || 0) + 1;
        });

        const labels = Object.keys(counts).slice(0, 20); // Limit to 20 for readability
        const values = labels.map(label => counts[label]);

        window.sparqlChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: `Count by ${firstCol}`,
                    data: values,
                    backgroundColor: 'rgba(102, 126, 234, 0.6)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        this.tabButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });

        // Update tab panels
        this.tabPanels.forEach(panel => {
            panel.classList.remove('active');
        });

        const targetPanel = document.getElementById(`${tabName}-content`);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }
    }

    downloadResults(format) {
        if (!this.currentResults) return;

        let content, filename, mimeType;

        if (format === 'csv') {
            content = this.convertToCSV(this.currentResults.results);
            filename = 'sparql-results.csv';
            mimeType = 'text/csv';
        } else if (format === 'json') {
            content = JSON.stringify(this.currentResults, null, 2);
            filename = 'sparql-results.json';
            mimeType = 'application/json';
        }

        this.downloadFile(content, filename, mimeType);
    }

    convertToCSV(results) {
        if (!results || results.length === 0) return '';

        // Get all unique keys
        const allKeys = new Set();
        results.forEach(row => {
            Object.keys(row).forEach(key => allKeys.add(key));
        });
        const columns = Array.from(allKeys);

        // Create CSV content
        let csv = columns.join(',') + '\n';

        results.forEach(row => {
            const values = columns.map(col => {
                const value = row[col] || '';
                // Escape quotes and wrap in quotes if necessary
                return `"${value.replace(/"/g, '""')}"`;
            });
            csv += values.join(',') + '\n';
        });

        return csv;
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.queryText.disabled = loading;

        if (loading) {
            this.loadingOverlay.classList.remove('hidden');
        } else {
            this.loadingOverlay.classList.add('hidden');
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sparqlAgentUI = new SPARQLAgentUI();
});