# Save this file as webapp.py in your project's root directory (e.g., /u01/genspark/)
import json
import logging
import os
import glob
from flask import Flask, render_template_string, jsonify, request, url_for
from datetime import datetime

# Configure Flask app
app = Flask(__name__)
RUN_HISTORY_DIR = 'run_history'

# --- HTML Template for the Main Dashboard ---
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oracle Alert Log Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/heroicons/2.0.18/24/outline/hero-icons.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
        .loading-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
</head>
<body class="p-4 sm:p-6 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col sm:flex-row justify-between items-center mb-6 pb-4 border-b border-gray-300">
            <div class="flex items-center space-x-4">
                <div><img src="{{ url_for('static', filename='elsewedy.png') }}" alt="El Sewedy Logo" class="h-16"></div>
                <div>
                    <h1 class="text-3xl font-bold text-gray-800">Oracle Alert Log Dashboard</h1>
                    <p class="text-gray-500">AI-powered analysis of database errors</p>
                </div>
            </div>
            <div class="text-right space-y-2 mt-4 sm:mt-0">
                 <div class="flex items-center justify-end space-x-2 text-sm text-gray-500">
                    <svg id="refresh-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.664 0l3.18-3.185m-3.181 9.348a8.25 8.25 0 00-11.664 0l-3.18 3.185m3.181-9.348l-3.181-3.183a8.25 8.25 0 000-11.664l3.18-3.185" />
                    </svg>
                    <span>Last Updated: <span id="last-updated" class="font-semibold text-gray-700"></span></span>
                 </div>
                 <div id="history-selector-container"></div>
            </div>
        </header>

        <!-- Summary Statistics -->
        <div id="summary-stats" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"></div>
        <!-- Main Content Grid -->
        <main id="dashboard-content" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <!-- Server cards will be dynamically inserted here -->
        </main>
    </div>

    <script>
        function createStatCard(title, value, icon, colorClass) {
            return `<div class="bg-white p-5 rounded-xl shadow flex items-center justify-between"><div><p class="text-sm text-gray-500">${title}</p><p class="text-2xl font-bold text-gray-800">${value}</p></div><div class="p-3 rounded-full ${colorClass}">${icon}</div></div>`;
        }

        async function updateDashboard() {
            const refreshIcon = document.getElementById('refresh-icon');
            refreshIcon.classList.add('loading-spin');

            try {
                // Get the currently selected run file from the dropdown
                const runSelector = document.getElementById('run-selector');
                const selectedRun = runSelector ? runSelector.value : null;
                
                const dataUrl = selectedRun ? `/api/data?run=${selectedRun}` : '/api/data';
                const response = await fetch(dataUrl);
                if (!response.ok) throw new Error('Network response was not ok');
                const data = await response.json();
                
                const contentDiv = document.getElementById('dashboard-content');
                const summaryDiv = document.getElementById('summary-stats');
                contentDiv.innerHTML = '';
                summaryDiv.innerHTML = '';

                document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();

                if (Object.keys(data).length === 0) {
                    contentDiv.innerHTML = '<div class="col-span-full text-center p-10 bg-white rounded-lg shadow-sm"><p class="text-gray-500">No data available. Run the monitor script to generate results.</p></div>';
                    return;
                }

                // Calculate and display summary stats
                const totalServers = Object.keys(data).length;
                let serversWithErrors = 0, totalErrors = 0, criticalErrorCount = 0;
                for (const serverName in data) {
                    const analyses = data[serverName];
                    if (analyses.length > 0) {
                        serversWithErrors++;
                        totalErrors += analyses.length;
                        analyses.forEach(a => { if (a.criticality === 'Critical') criticalErrorCount++; });
                    }
                }
                const serverIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-800"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008z" /></svg>';
                const errorIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-orange-800"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>';
                const totalErrorsIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-yellow-800"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" /></svg>';
                const criticalIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-red-800"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 0v3.75m0-3.75h.008v.008H12v-.008zm0 0H9.75m-5.026 0a4.5 4.5 0 119.052 0 4.5 4.5 0 01-9.052 0z" /></svg>';
                summaryDiv.innerHTML += createStatCard('Total Servers', totalServers, serverIcon, 'bg-blue-200');
                summaryDiv.innerHTML += createStatCard('Servers with Errors', serversWithErrors, errorIcon, 'bg-orange-200');
                summaryDiv.innerHTML += createStatCard('Total New Errors', totalErrors, totalErrorsIcon, 'bg-yellow-200');
                summaryDiv.innerHTML += createStatCard('Critical Errors', criticalErrorCount, criticalIcon, 'bg-red-200');

                // Build server cards
                for (const serverName in data) {
                    const analyses = data[serverName];
                    const hasErrors = analyses.length > 0;
                    const statusColor = hasErrors ? 'red' : 'green';
                    
                    // The server card is now a link to the detail page
                    const serverLink = document.createElement('a');
                    serverLink.href = `/server/${selectedRun}/${encodeURIComponent(serverName)}`;
                    serverLink.className = 'block bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300';
                    
                    let cardHTML = `<div class="p-4 flex justify-between items-center border-b border-gray-200"><div class="flex items-center space-x-3"><span class="flex h-3 w-3 relative"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-${statusColor}-400 opacity-75"></span><span class="relative inline-flex rounded-full h-3 w-3 bg-${statusColor}-500"></span></span><h2 class="text-lg font-semibold text-gray-800">${serverName}</h2></div><span class="text-sm font-medium ${hasErrors ? 'text-red-600' : 'text-green-600'}">${analyses.length} Errors</span></div>`;
                    cardHTML += `<div class="p-4 text-sm text-gray-600">Click to view details and error analysis.</div>`;
                    
                    serverLink.innerHTML = cardHTML;
                    contentDiv.appendChild(serverLink);
                }

            } catch (error) {
                console.error('Failed to fetch dashboard data:', error);
                document.getElementById('dashboard-content').innerHTML = '<div class="col-span-full text-center p-10 bg-red-100 text-red-700 rounded-lg shadow-sm"><p>Error loading dashboard data. Please check console.</p></div>';
            } finally {
                refreshIcon.classList.remove('loading-spin');
            }
        }

        async function initialize() {
            try {
                const response = await fetch('/api/runs');
                const runs = await response.json();
                const container = document.getElementById('history-selector-container');
                if (runs.length > 0) {
                    let options = '';
                    runs.forEach(run => {
                        const displayTime = run.replace('run_', '').replace('.json', '').replace('T', ' ').replaceAll('-',':').split('.')[0];
                        options += `<option value="${run}">${displayTime}</option>`;
                    });
                    container.innerHTML = `<select id="run-selector" class="text-sm border border-gray-300 rounded-md p-1"> ${options} </select>`;
                    document.getElementById('run-selector').addEventListener('change', updateDashboard);
                }
            } catch (error) {
                console.error("Could not load run history:", error);
            }
            await updateDashboard(); 
        }

        setInterval(initialize, 15000);
        document.addEventListener('DOMContentLoaded', initialize);
    </script>
</body>
</html>
"""

# --- HTML Template for the Server Detail Page ---
SERVER_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Details for {{ server_name }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
        .criticality-Critical { border-left-color: #ef4444; }
        .criticality-High { border-left-color: #f97316; }
        .criticality-Medium { border-left-color: #f59e0b; }
        .criticality-Low { border-left-color: #84cc16; }
        .criticality-Informational { border-left-color: #3b82f6; }
    </style>
</head>
<body class="p-4 sm:p-6 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex justify-between items-center mb-6 pb-4 border-b border-gray-300">
            <div>
                <h1 class="text-3xl font-bold text-gray-800">Server Details: <span class="text-blue-600">{{ server_name }}</span></h1>
                <p class="text-gray-500">Run from: {{ run_timestamp }}</p>
            </div>
            <a href="/" class="text-blue-600 hover:underline flex items-center space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" /></svg>
                <span>Back to Dashboard</span>
            </a>
        </header>

        <!-- Content: Charts and Errors -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Chart Section -->
            <div class="lg:col-span-1 bg-white p-6 rounded-xl shadow-md">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">Error Criticality Breakdown</h2>
                <canvas id="criticalityChart"></canvas>
            </div>

            <!-- Error Details Section -->
            <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow-md">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">Error Details ({{ analyses|length }})</h2>
                <div id="error-list" class="space-y-4">
                    <!-- Error cards will be inserted here -->
                </div>
            </div>
        </div>
    </div>

    <script>
        const analyses = {{ analyses|tojson }};
        const chartData = {{ chart_data|tojson }};

        function createAnalysisCard(analysis) {
            const criticalityColors = {'Critical': 'text-red-600', 'High': 'text-orange-600', 'Medium': 'text-amber-600', 'Low': 'text-lime-600', 'Informational': 'text-blue-600'};
            const textColor = criticalityColors[analysis.criticality] || 'text-gray-700';
            return `<div class="bg-gray-50 p-4 rounded-lg border-l-4 criticality-${analysis.criticality}"><p class="text-sm text-gray-600 font-mono break-all mb-3">${analysis.error_line}</p><div class="space-y-2 text-sm"><p><strong>Explanation:</strong> ${analysis.explanation}</p><p><strong>Action:</strong> ${analysis.recommended_action}</p><div class="flex justify-between items-center pt-2"><span class="inline-block bg-gray-200 rounded-full px-3 py-1 text-xs font-semibold text-gray-700">Criticality: <span class="font-bold ${textColor}">${analysis.criticality}</span></span><span class="text-xs text-gray-400">${new Date(analysis.timestamp).toLocaleString()}</span></div></div></div>`;
        }

        document.addEventListener('DOMContentLoaded', () => {
            // Populate error list
            const errorListDiv = document.getElementById('error-list');
            if (analyses.length > 0) {
                errorListDiv.innerHTML = analyses.map(createAnalysisCard).join('');
            } else {
                errorListDiv.innerHTML = '<p class="text-gray-500">No errors to display for this server.</p>';
            }

            // Create the chart
            const ctx = document.getElementById('criticalityChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Error Count',
                        data: chartData.data,
                        backgroundColor: [
                            '#ef4444', // Critical
                            '#f97316', // High
                            '#f59e0b', // Medium
                            '#84cc16', // Low
                            '#3b82f6'  // Informational
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: false,
                            text: 'Error Criticality'
                        }
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

# --- API Endpoints ---
@app.route('/api/runs')
def get_runs():
    """Returns a list of the last 20 available run files."""
    try:
        if not os.path.exists(RUN_HISTORY_DIR): return jsonify([])
        run_files = sorted(glob.glob(os.path.join(RUN_HISTORY_DIR, 'run_*.json')), reverse=True)
        return jsonify([os.path.basename(f) for f in run_files[:20]])
    except Exception as e:
        logging.error(f"Error listing run history: {e}")
        return jsonify({"error": "Could not list run history."}), 500

@app.route('/api/data')
def get_data():
    """Reads and returns the content of a specific run's JSON file."""
    run_file = request.args.get('run')
    try:
        if not run_file:
            all_runs = sorted(glob.glob(os.path.join(RUN_HISTORY_DIR, 'run_*.json')), reverse=True)
            if not all_runs: return jsonify({})
            file_path = all_runs[0]
        else:
            if '..' in run_file or not run_file.startswith('run_') or not run_file.endswith('.json'):
                return jsonify({"error": "Invalid filename."}), 400
            file_path = os.path.join(RUN_HISTORY_DIR, run_file)
        with open(file_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({})
    except Exception as e:
        logging.error(f"Error reading data file: {e}")
        return jsonify({"error": "Could not read data file."}), 500

# --- NEW ROUTE for Server Detail Page ---
@app.route('/server/<run_file>/<server_name>')
def server_details(run_file, server_name):
    """Renders the detail page for a specific server from a specific run."""
    try:
        # Security check on filename
        if '..' in run_file or not run_file.startswith('run_') or not run_file.endswith('.json'):
            return "Invalid run file specified", 400
        
        file_path = os.path.join(RUN_HISTORY_DIR, run_file)
        with open(file_path, 'r') as f:
            all_data = json.load(f)
        
        server_data = all_data.get(server_name, [])
        
        # Prepare data for the chart
        criticality_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Informational': 0}
        for analysis in server_data:
            if analysis['criticality'] in criticality_counts:
                criticality_counts[analysis['criticality']] += 1
        
        chart_data = {
            "labels": list(criticality_counts.keys()),
            "data": list(criticality_counts.values())
        }

        # Format timestamp for display
        run_timestamp = run_file.replace('run_', '').replace('.json', '').replace('T', ' ').replace('-', ':', 2)

        return render_template_string(
            SERVER_DETAIL_TEMPLATE, 
            server_name=server_name, 
            analyses=server_data,
            chart_data=chart_data,
            run_timestamp=run_timestamp
        )
    except FileNotFoundError:
        return "Run data not found.", 404
    except Exception as e:
        logging.error(f"Error rendering server detail page: {e}")
        return "An error occurred.", 500

# --- Main Route to Render the Dashboard ---
@app.route('/')
def dashboard():
    """Renders the main HTML dashboard page."""
    return render_template_string(DASHBOARD_TEMPLATE)

# --- Main execution ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- HTTPS Configuration ---
    # For HTTPS, you need a certificate and a private key.
    # Place your certificate files in the same directory as this script.
    # RENAME these files to match your certificate and key files.
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    
    ssl_context = None
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = (cert_file, key_file)
        print(f"INFO: Found certificate files. Starting server with HTTPS on https://0.0.0.0:5001")
    else:
        print(f"WARNING: Certificate files not found. Starting server with HTTP on http://0.0.0.0:5001")
        print(f"WARNING: To enable HTTPS, create '{cert_file}' and '{key_file}' in the project directory.")

    # Run the Flask app.
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context=ssl_context)

