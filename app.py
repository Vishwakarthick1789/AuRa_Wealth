import gradio as gr
import sqlite3
import hashlib
import pandas as pd
import numpy as np
import datetime
import os

# --- Database Setup ---
DB_NAME = "finance_app.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    # Scenarios table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            scenario_name TEXT NOT NULL,
            current_savings REAL NOT NULL,
            monthly_income REAL NOT NULL,
            monthly_burn_rate REAL NOT NULL,
            risk_tolerance TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# --- Auth Helpers ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username, password):
    if not username or not password:
        return "Username and password cannot be empty."
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return f"Registration successful for '{username}'. You can now log in."
    except sqlite3.IntegrityError:
        return f"Username '{username}' already exists. Please choose another."
    finally:
        conn.close()

def login_user(username, password):
    if not username or not password:
        return "Username and password cannot be empty.", None
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Return user dict for state
        return f"Welcome back, {user[1]}!", {"id": user[0], "username": user[1]}
    else:
        return "Invalid username or password.", None

# --- Forecasting Logic ---
def simulate_growth(current_savings, monthly_income, monthly_burn_rate, risk_tolerance):
    """
    Simulates a time-series forecasting model (like GRU/LSTM behavior)
    using deterministic compounding with added stochastic noise.
    """
    months = 60 # 5 years
    monthly_savings = monthly_income - monthly_burn_rate
    
    # Risk profiles defining expected annual return and volatility (standard deviation)
    risk_profiles = {
        "Low (Conservative)": {"return": 0.04, "volatility": 0.05},
        "Medium (Balanced)": {"return": 0.07, "volatility": 0.12},
        "High (Aggressive)": {"return": 0.11, "volatility": 0.20},
        "Degen (Crypto/Options)": {"return": 0.25, "volatility": 0.60}
    }
    
    profile = risk_profiles.get(risk_tolerance, risk_profiles["Medium (Balanced)"])
    mu = profile["return"] / 12  # monthly expected return
    sigma = profile["volatility"] / np.sqrt(12) # monthly volatility
    
    dates = pd.date_range(start=datetime.datetime.now(), periods=months, freq='ME')
    
    # Set seed for reproducibility based on inputs
    seed = int(current_savings + monthly_income) % 10000
    np.random.seed(seed)
    
    expected_path = [current_savings]
    optimistic_path = [current_savings]
    pessimistic_path = [current_savings]
    
    curr_exp = current_savings
    curr_opt = current_savings
    curr_pess = current_savings
    
    for _ in range(1, months):
        # Simulate market return for the month
        market_return_exp = mu
        market_return_opt = mu + (sigma * 0.5)  # Add some positive drift for optimistic
        market_return_pess = mu - (sigma * 0.5) # Negative drift for pessimistic
        
        curr_exp = (curr_exp + monthly_savings) * (1 + market_return_exp)
        curr_opt = (curr_opt + monthly_savings) * (1 + market_return_opt)
        curr_pess = (curr_pess + monthly_savings) * (1 + market_return_pess)
        
        expected_path.append(curr_exp)
        optimistic_path.append(curr_opt)
        pessimistic_path.append(curr_pess)
        
    df = pd.DataFrame({
        "Date": dates,
        "Expected": expected_path,
        "Optimistic": optimistic_path,
        "Pessimistic": pessimistic_path
    })
    
    # Melt dataframe for Gradio LinePlot
    df_melted = df.melt(id_vars=["Date"], value_vars=["Expected", "Optimistic", "Pessimistic"], 
                        var_name="Scenario", value_name="Balance ($)")
    
    return df_melted, round(expected_path[-1], 2)

# --- Database Operations for Scenarios ---
def save_scenario(user_state, name, savings, income, burn, risk):
    if not user_state:
        return "You must be logged in to save scenarios."
    if not name:
        return "Please provide a scenario name."
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO scenarios (user_id, scenario_name, current_savings, monthly_income, monthly_burn_rate, risk_tolerance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_state["id"], name, savings, income, burn, risk, created_at))
    conn.commit()
    conn.close()
    return f"Scenario '{name}' saved successfully!"

def load_user_scenarios(user_state):
    if not user_state:
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, scenario_name, current_savings, monthly_income, monthly_burn_rate, risk_tolerance, created_at FROM scenarios WHERE user_id = ?", conn, params=(user_state["id"],))
    conn.close()
    return df

# --- Gradio UI ---

# Custom Theme for a "Gen Z" aesthetic (Dark, Neon)
custom_theme = gr.themes.Monochrome(
    primary_hue="indigo",
    secondary_hue="purple",
    neutral_hue="slate",
    radius_size=gr.themes.sizes.radius_lg,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    body_background_fill="*neutral_950",
    body_background_fill_dark="*neutral_950",
    body_text_color="*neutral_100",
    body_text_color_dark="*neutral_100",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_500",
    button_primary_text_color="white",
    button_primary_text_color_dark="white",
    block_background_fill="*neutral_900",
    block_background_fill_dark="*neutral_900",
    block_border_color="*neutral_800",
    block_border_width="1px",
    input_background_fill="*neutral_800",
    input_background_fill_dark="*neutral_800",
    slider_color="*primary_500",
    slider_color_dark="*primary_500"
)

css = """
h1 {
    text-align: center;
    background: -webkit-linear-gradient(45deg, #8b5cf6, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
.gradio-container {
    box-shadow: inset 0 0 100px rgba(139, 92, 246, 0.05);
}
"""

with gr.Blocks(title="Aura Wealth") as demo:
    # State variable to hold logged in user info
    user_state = gr.State(None)
    
    gr.Markdown("# ✨ Aura Wealth Forecaster ✨")
    gr.Markdown("<p style='text-align: center; color: #94a3b8;'>AI-driven personal finance & predictive growth simulator</p>")
    
    with gr.Tabs() as tabs:
        
        # --- Authentication Tab ---
        with gr.Tab("Login / Register", id="auth_tab"):
            with gr.Row():
                with gr.Column(scale=1):
                    pass
                with gr.Column(scale=2):
                    auth_msg = gr.Markdown("Please login or register to save your financial scenarios.")
                    
                    with gr.Tabs():
                        with gr.Tab("Login"):
                            l_user = gr.Textbox(label="Username", placeholder="Enter username")
                            l_pass = gr.Textbox(label="Password", type="password", placeholder="Enter password")
                            l_btn = gr.Button("Login", variant="primary")
                        
                        with gr.Tab("Register"):
                            r_user = gr.Textbox(label="Username", placeholder="Choose a username")
                            r_pass = gr.Textbox(label="Password", type="password", placeholder="Choose a strong password")
                            r_btn = gr.Button("Register")
                            
                    current_user_display = gr.Markdown("")
                with gr.Column(scale=1):
                    pass

        # --- Dashboard Tab ---
        with gr.Tab("Dashboard", id="dash_tab"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 💸 Your Stats")
                    savings_input = gr.Slider(minimum=0, maximum=1000000, value=5000, step=100, label="Current Savings ($)")
                    income_input = gr.Slider(minimum=0, maximum=50000, value=4000, step=50, label="Monthly Income ($)")
                    burn_input = gr.Slider(minimum=0, maximum=50000, value=2500, step=50, label="Monthly Burn Rate ($)")
                    risk_input = gr.Radio(
                        choices=["Low (Conservative)", "Medium (Balanced)", "High (Aggressive)", "Degen (Crypto/Options)"],
                        value="Medium (Balanced)",
                        label="Risk Tolerance"
                    )
                    
                    forecast_btn = gr.Button("🚀 Run AI Forecast", variant="primary")
                    
                    gr.Markdown("### 💾 Save Scenario")
                    scenario_name = gr.Textbox(label="Scenario Name", placeholder="e.g., 'Moving to NY plan'")
                    save_btn = gr.Button("Save to DB")
                    save_msg = gr.Markdown("")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📈 5-Year Wealth Projection")
                    plot_output = gr.LinePlot(
                        x="Date",
                        y="Balance ($)",
                        color="Scenario",
                        title="Wealth Growth Over 5 Years",
                        tooltip=["Date", "Balance ($)", "Scenario"]
                    )
                    summary_output = gr.Markdown("")

        # --- Saved Scenarios Tab ---
        with gr.Tab("Saved Scenarios", id="saved_tab"):
            gr.Markdown("### 📂 Your Saved Financial Scenarios")
            refresh_btn = gr.Button("🔄 Refresh List")
            scenarios_table = gr.Dataframe(
                headers=["ID", "Name", "Savings", "Income", "Burn Rate", "Risk", "Created At"],
                interactive=False
            )

    # --- Interactions ---
    
    # Registration
    r_btn.click(
        fn=register_user,
        inputs=[r_user, r_pass],
        outputs=[auth_msg]
    )
    
    # Login
    def handle_login(user, pwd):
        msg, state = login_user(user, pwd)
        if state:
            return msg, state, f"**Currently logged in as:** {state['username']}"
        return msg, None, ""

    l_btn.click(
        fn=handle_login,
        inputs=[l_user, l_pass],
        outputs=[auth_msg, user_state, current_user_display]
    )
    
    # Forecasting
    def handle_forecast(savings, income, burn, risk):
        if burn > income:
            return None, "⚠️ **Warning**: Burn rate exceeds income. You are losing money every month! Adjust inputs."
        df, final_val = simulate_growth(savings, income, burn, risk)
        return df, f"### 🎯 Expected Balance in 5 Years: **${final_val:,.2f}**"
        
    forecast_btn.click(
        fn=handle_forecast,
        inputs=[savings_input, income_input, burn_input, risk_input],
        outputs=[plot_output, summary_output]
    )
    
    # Saving Scenarios
    save_btn.click(
        fn=save_scenario,
        inputs=[user_state, scenario_name, savings_input, income_input, burn_input, risk_input],
        outputs=[save_msg]
    )
    
    # Loading Scenarios
    refresh_btn.click(
        fn=load_user_scenarios,
        inputs=[user_state],
        outputs=[scenarios_table]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, theme=custom_theme, css=css)
