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
            projection_years INTEGER DEFAULT 5,
            initial_debt REAL DEFAULT 0,
            monthly_debt_payment REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Migrations: Add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE scenarios ADD COLUMN projection_years INTEGER DEFAULT 5")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scenarios ADD COLUMN initial_debt REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scenarios ADD COLUMN monthly_debt_payment REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
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
        return f"Welcome back, {user[1]}!", {"id": user[0], "username": user[1]}
    else:
        return "Invalid username or password.", None

# --- Financial Roast Logic ---
def generate_roast(savings, income, burn, debt, debt_payment):
    disposable = income - burn - debt_payment
    savings_rate = (disposable / income) * 100 if income > 0 else 0
    
    if burn + debt_payment > income:
        return "📉 **ROAST:** You are literally burning more cash than you make! Stop buying $7 iced lattes and $30 DoorDash orders. You are sprinting towards bankruptcy!"
    elif debt > 0 and debt_payment < (debt * 0.05):
        return "💳 **ROAST:** That debt is going to bury you bro. You're barely paying off the interest. Stop pretending you have money and pay that off!"
    elif savings_rate < 10:
        return "😬 **ROAST:** A savings rate of less than 10%? You are one flat tire away from financial ruin. Time to cancel some subscriptions."
    elif savings_rate > 50:
        return "👑 **VIBE CHECK:** Saving over 50% of your income?! Absolute legend. You have monk-like discipline. Future millionaire vibes right here."
    else:
        return "👌 **VIBE CHECK:** You're doing okay. Not terrible, but not amazing. Keep grinding and try to bump that savings rate up!"

# --- Forecasting Logic ---
def simulate_growth(current_savings, monthly_income, monthly_burn_rate, initial_debt, monthly_debt_payment, risk_tolerance, years):
    months = int(years * 12)
    
    monthly_savings = monthly_income - monthly_burn_rate - monthly_debt_payment
    
    inflation_rate_annual = 0.025
    inflation_rate_monthly = inflation_rate_annual / 12
    
    risk_profiles = {
        "Low (Conservative)": {"return": 0.04, "volatility": 0.05},
        "Medium (Balanced)": {"return": 0.07, "volatility": 0.12},
        "High (Aggressive)": {"return": 0.11, "volatility": 0.20},
        "Degen (Crypto/Options)": {"return": 0.25, "volatility": 0.60}
    }
    
    profile = risk_profiles.get(risk_tolerance, risk_profiles["Medium (Balanced)"])
    mu = profile["return"] / 12  
    sigma = profile["volatility"] / np.sqrt(12) 
    
    dates = pd.date_range(start=datetime.datetime.now(), periods=months, freq='ME')
    
    seed = int(current_savings + monthly_income + years) % 10000
    np.random.seed(seed)
    
    # Net worth includes savings minus debt
    curr_debt = initial_debt
    
    expected_path = []
    optimistic_path = []
    pessimistic_path = []
    
    curr_exp_savings = current_savings
    curr_opt_savings = current_savings
    curr_pess_savings = current_savings
    
    for _ in range(months):
        # Pay down debt logic (approximate 5% annual interest on debt)
        if curr_debt > 0:
            curr_debt = curr_debt * (1 + (0.05/12)) - monthly_debt_payment
            if curr_debt < 0:
                curr_debt = 0
                
        real_mu = mu - inflation_rate_monthly
        
        market_return_exp = real_mu
        market_return_opt = real_mu + (sigma * 1.0)
        market_return_pess = real_mu - (sigma * 1.0)
        
        curr_exp_savings = (curr_exp_savings + monthly_savings) * (1 + market_return_exp)
        curr_opt_savings = (curr_opt_savings + monthly_savings) * (1 + market_return_opt)
        curr_pess_savings = (curr_pess_savings + monthly_savings) * (1 + market_return_pess)
        
        # Net worth = savings - remaining debt
        expected_path.append(curr_exp_savings - curr_debt)
        optimistic_path.append(curr_opt_savings - curr_debt)
        pessimistic_path.append(curr_pess_savings - curr_debt)
        
    df = pd.DataFrame({
        "Date": dates,
        "Expected (Real $)": expected_path,
        "Optimistic (Real $)": optimistic_path,
        "Pessimistic (Real $)": pessimistic_path
    })
    
    df_melted = df.melt(id_vars=["Date"], value_vars=["Expected (Real $)", "Optimistic (Real $)", "Pessimistic (Real $)"], 
                        var_name="Scenario", value_name="Net Worth ($)")
    
    total_contributed = current_savings + (monthly_savings * months)
    
    roast_msg = generate_roast(current_savings, monthly_income, monthly_burn_rate, initial_debt, monthly_debt_payment)
    
    return df_melted, round(expected_path[-1], 2), round(total_contributed, 2), roast_msg

# --- Database Operations for Scenarios ---
def save_scenario(user_state, name, savings, income, burn, debt, debt_payment, risk, years):
    if not user_state:
        return "You must be logged in to save scenarios."
    if not name:
        return "Please provide a scenario name."
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO scenarios (user_id, scenario_name, current_savings, monthly_income, monthly_burn_rate, risk_tolerance, created_at, projection_years, initial_debt, monthly_debt_payment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_state["id"], name, savings, income, burn, risk, created_at, years, debt, debt_payment))
    conn.commit()
    conn.close()
    return f"Scenario '{name}' saved successfully!"

def load_user_scenarios(user_state):
    if not user_state:
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, scenario_name, current_savings, monthly_income, monthly_burn_rate, initial_debt, monthly_debt_payment, risk_tolerance, projection_years, created_at FROM scenarios WHERE user_id = ?", conn, params=(user_state["id"],))
    conn.close()
    return df

# Helper to map dataframe row to gradio components
def select_scenario(evt: gr.SelectData, user_state):
    if not user_state:
        return [gr.update()]*7
    
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM scenarios WHERE user_id = ?", conn, params=(user_state["id"],))
    conn.close()
    
    if evt.index[0] < len(df):
        row = df.iloc[evt.index[0]]
        return (
            row["current_savings"],
            row["monthly_income"],
            row["monthly_burn_rate"],
            row["initial_debt"],
            row["monthly_debt_payment"],
            row["risk_tolerance"],
            row["projection_years"]
        )
    return [gr.update()]*7

# --- Gradio UI ---
custom_theme = gr.themes.Monochrome(
    primary_hue="indigo",
    secondary_hue="purple",
    neutral_hue="slate",
    radius_size=gr.themes.sizes.radius_lg,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    body_background_fill="*neutral_950",
    body_text_color="*neutral_100",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_500",
    button_primary_text_color="white",
    block_background_fill="*neutral_900",
    block_border_color="*neutral_800",
    input_background_fill="*neutral_800",
    slider_color="*primary_500"
)

css = """
h1 {
    text-align: center;
    background: -webkit-linear-gradient(45deg, #8b5cf6, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
.roast-box {
    padding: 15px;
    border-radius: 10px;
    background: #1e1b4b;
    border: 2px solid #6366f1;
    margin-top: 20px;
}
"""

with gr.Blocks(title="Aura Wealth", theme=custom_theme, css=css) as demo:
    user_state = gr.State(None)
    
    gr.Markdown("# ✨ Aura Wealth Forecaster ✨")
    gr.Markdown("<p style='text-align: center; color: #94a3b8;'>Realistic AI-driven personal finance & predictive growth simulator</p>")
    
    with gr.Tabs() as tabs:
        
        # --- Authentication Tab ---
        with gr.Tab("Login / Register", id="auth_tab"):
            with gr.Row():
                with gr.Column(scale=1): pass
                with gr.Column(scale=2):
                    auth_msg = gr.Markdown("Please login or register to save your financial scenarios.")
                    with gr.Tabs():
                        with gr.Tab("Login"):
                            l_user = gr.Textbox(label="Username")
                            l_pass = gr.Textbox(label="Password", type="password")
                            l_btn = gr.Button("Login", variant="primary")
                        with gr.Tab("Register"):
                            r_user = gr.Textbox(label="Username")
                            r_pass = gr.Textbox(label="Password", type="password")
                            r_btn = gr.Button("Register")
                    current_user_display = gr.Markdown("")
                with gr.Column(scale=1): pass

        # --- Dashboard Tab ---
        with gr.Tab("Dashboard", id="dash_tab"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 💸 Assets & Income")
                    savings_input = gr.Slider(minimum=0, maximum=1000000, value=5000, step=100, label="Current Savings ($)")
                    income_input = gr.Slider(minimum=0, maximum=50000, value=4000, step=50, label="Monthly Income ($)")
                    
                    gr.Markdown("### 💳 Expenses & Debt")
                    burn_input = gr.Slider(minimum=0, maximum=50000, value=2500, step=50, label="Monthly Expenses (Rent, Food, etc) ($)")
                    debt_input = gr.Slider(minimum=0, maximum=500000, value=0, step=500, label="Initial Total Debt ($)")
                    debt_payment_input = gr.Slider(minimum=0, maximum=10000, value=0, step=50, label="Monthly Debt Payment ($)")
                    
                    gr.Markdown("### ⚙️ Simulation Parameters")
                    years_input = gr.Slider(minimum=1, maximum=40, value=5, step=1, label="Projection Horizon (Years)")
                    risk_input = gr.Radio(
                        choices=["Low (Conservative)", "Medium (Balanced)", "High (Aggressive)", "Degen (Crypto/Options)"],
                        value="Medium (Balanced)",
                        label="Investment Risk Tolerance"
                    )
                    
                    forecast_btn = gr.Button("🚀 Run AI Forecast", variant="primary")
                    
                    gr.Markdown("### 💾 Save Scenario")
                    scenario_name = gr.Textbox(label="Scenario Name", placeholder="e.g., 'Aggressive Debt Payoff'")
                    save_btn = gr.Button("Save to DB")
                    save_msg = gr.Markdown("")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📈 Net Worth Projection (Inflation Adjusted)")
                    plot_output = gr.LinePlot(
                        x="Date",
                        y="Net Worth ($)",
                        color="Scenario",
                        title="Real Net Worth Growth (Assets minus Debt, Adjusted for 2.5% Annual Inflation)",
                        tooltip=["Date", "Net Worth ($)", "Scenario"]
                    )
                    summary_output = gr.Markdown("")
                    roast_output = gr.Markdown(elem_classes="roast-box")

        # --- Saved Scenarios Tab ---
        with gr.Tab("Saved Scenarios", id="saved_tab"):
            gr.Markdown("### 📂 Your Saved Financial Scenarios")
            gr.Markdown("**Tip:** Click on any row to instantly load that scenario back into your Dashboard!")
            refresh_btn = gr.Button("🔄 Refresh List")
            scenarios_table = gr.Dataframe(
                headers=["ID", "Name", "Savings", "Income", "Burn Rate", "Initial Debt", "Debt Payment", "Risk", "Years", "Created At"],
                interactive=False
            )
            
    gr.Markdown("---")
    gr.Markdown("<p style='text-align: center; color: #64748b; font-size: 0.8rem;'><b>Disclaimer:</b> Projections are generated using a Geometric Brownian Motion model. Debt assumes a generic 5% APR.</p>")

    # --- Interactions ---
    r_btn.click(fn=register_user, inputs=[r_user, r_pass], outputs=[auth_msg])
    
    def handle_login(user, pwd):
        msg, state = login_user(user, pwd)
        if state:
            return msg, state, f"**Currently logged in as:** {state['username']}"
        return msg, None, ""

    l_btn.click(fn=handle_login, inputs=[l_user, l_pass], outputs=[auth_msg, user_state, current_user_display])
    
    def handle_forecast(savings, income, burn, debt, debt_payment, risk, years):
        df, final_val, total_contrib, roast = simulate_growth(savings, income, burn, debt, debt_payment, risk, years)
        summary = f"### 🎯 Expected Real Net Worth in {years} Years: **${final_val:,.2f}**\\n*(Total Cash Contributed to Investments: ${total_contrib:,.2f})*"
        return df, summary, roast
        
    forecast_btn.click(
        fn=handle_forecast,
        inputs=[savings_input, income_input, burn_input, debt_input, debt_payment_input, risk_input, years_input],
        outputs=[plot_output, summary_output, roast_output]
    )
    
    save_btn.click(
        fn=save_scenario,
        inputs=[user_state, scenario_name, savings_input, income_input, burn_input, debt_input, debt_payment_input, risk_input, years_input],
        outputs=[save_msg]
    )
    
    refresh_btn.click(fn=load_user_scenarios, inputs=[user_state], outputs=[scenarios_table])
    
    # Event Listener to load scenario when clicked
    scenarios_table.select(
        fn=select_scenario,
        inputs=[user_state],
        outputs=[savings_input, income_input, burn_input, debt_input, debt_payment_input, risk_input, years_input]
    ).then(
        fn=lambda: gr.Tabs(selected="dash_tab"),
        outputs=[tabs]
    ).then(
        fn=handle_forecast,
        inputs=[savings_input, income_input, burn_input, debt_input, debt_payment_input, risk_input, years_input],
        outputs=[plot_output, summary_output, roast_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, theme=custom_theme, css=css)
