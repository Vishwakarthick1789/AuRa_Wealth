# 🚀 Aura Wealth - Gen Z Financial Forecaster

A modern, AI-driven personal finance and wealth forecasting application. This Micro-SaaS project helps users predict their financial trajectory using a robust simulation engine (Geometric Brownian Motion) with an interactive, sleek UI tailored for Gen Z..

## 🌟 Value Proposition

In an age of financial uncertainty, young adults need intuitive tools to understand how their daily habits (income vs. burn rate) and investment risk profiles affect their long-term wealth. **Aura Wealth** bridges this gap by providing an aesthetic, easy-to-understand dashboard that projects financial growth and allows users to save and iterate on different life scenarios.

## 🏗️ Technical Architecture

- **Frontend**: Built with **Gradio Blocks**, utilizing a highly customized dark/neon CSS theme to provide a modern web app feel.
- **Backend Core**: Pure Python, ensuring lightweight execution and modularity.
- **Database**: **SQLite3** serves as the embedded database for seamless user session management and scenario persistence, requiring no external setup.
- **Data Visualization**: **Pandas** and Gradio's native Vega-Lite wrappers are used for real-time, interactive graphing.

## 🧠 Forecasting Module Logic

The predictive analytics module simulates time-series forecasting using **Geometric Brownian Motion (GBM)**—the industry standard for Monte Carlo retirement simulations—enhanced with a 2.5% annual inflation discount to reflect real purchasing power.

1. **Monthly Base**: Calculates monthly savings (`Income - Burn Rate`).
2. **Risk Profile Mapping**: 
   - Users select a risk tolerance (e.g., Conservative, Balanced, Aggressive, Degen).
   - This selection maps to a predefined expected mean return and volatility/standard deviation.
3. **Simulation Engine**: 
   - Calculates compound growth dynamically over the user-defined timeline (1 to 40 years).
   - Generates three distinct paths: **Expected** (Mean), **Optimistic** (+ Drift), and **Pessimistic** (- Drift) to represent the stochastic nature of markets.
4. **Output**: Returns a melted Pandas DataFrame mapped to an interactive multi-line plot, empowering users to visualize potential upper and lower bounds of their financial future in *real* dollars.

## 🛠️ Setup and Usage Instructions

Setting up the project is fully automated for Windows.

1. **Prerequisites**: Ensure you have Python installed on your system and added to your PATH.
2. **Installation & Launch**:
   - Simply double-click the `start.bat` file in the project directory.
   - The script will automatically:
     - Verify Python installation.
     - Create a sandboxed virtual environment (`venv`).
     - Install all required dependencies from `requirements.txt`.
     - Start the application backend and provide a local URL.
3. **Usage**:
   - Open the provided URL (e.g., `http://127.0.0.1:7860`) in your browser.
   - Register a new account on the "Login / Register" tab.
   - Navigate to the "Dashboard" to tweak your financials and run forecasts.
   - Save compelling scenarios and review them later in the "Saved Scenarios" tab.
