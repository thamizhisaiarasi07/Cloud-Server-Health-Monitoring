# Cloud-Based Server Health Monitoring System

This project is a local cloud simulation for monitoring multiple simulated servers using Flask, SQLite, and Chart.js. It demonstrates monitoring concepts such as resource tracking, health evaluation, thresholds, alerts, dashboards, history, and failure simulation without requiring external cloud infrastructure or credentials.

## Features

- 5 simulated cloud servers with local private IPs
- CPU, memory, disk, and network monitoring
- Health score evaluation and status classification
- Threshold management stored in SQLite
- Alert generation and resolution workflow
- Failure and recovery simulation
- Search and filtering for servers
- Real-time dashboard refresh via AJAX
- Historical monitoring records and charts
- SQLite-backed persistence

## Project Structure

- app.py — Flask web application
- database.py — SQLite schema and simulation logic
- templates/index.html — dashboard UI
- static/css/style.css — dashboard styling
- static/js/app.js — dashboard behavior and AJAX updates
- server_monitoring.db — SQLite database created on first run

## Prerequisites

- Python 3.10+
- A virtual environment is recommended

## Setup

1. Open a terminal in the project folder.
2. Create and activate a virtual environment if desired.
3. Install dependencies:

   pip install -r requirements.txt

## Run locally

python app.py

Then open:

http://127.0.0.1:5000/

## Notes

This project is intentionally simulation-focused and is designed to run locally on Windows using VS Code.
