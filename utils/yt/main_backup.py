import streamlit as st
from custom_data_page import show_custom_data_page
from utils.yt.mongo_reader import show_mongodb_data_page
import os
import base64
import time
import random

# Peter's sarcastic comments
PETER_COMMENTS = [
    "Really? That's your guess? 🙄",
    "Nope, try harder! I'm not telling you anything! 😏",
    "Wrong again! Are you even trying? 😂",
    "Seriously? That's embarrassing... 🤦‍♂️",
    "Hahaha, not even close! 🤣",
    "Keep guessing, this is entertaining! 🍿",
    "I'm starting to feel sorry for you... 😢",
    "Did you just randomly hit keys? 🤔",
    "That password is as weak as your attempts! 💪❌",
    "I've seen toddlers with better guesses! 👶",
    "Are you typing with your eyes closed? 👀❌",
    "Even my grandmother knows better passwords! 👵",
    "This is more fun than watching TV! 📺",
    "I'm not giving you any hints, nice try! 🚫",
    "You're making this too easy for me! 😎",
    "Wrong password, wrong life choices! 🛤️",
    "I'm dying of laughter over here! 😵",
    "That's not it, genius! 🧠❌",
    "Try again when you figure out how to type! ⌨️",
    "I could do this all day! ⏰",
    "Your password skills are... questionable 🤨",
    "Nah, that ain't it chief! 🤠",
    "I'm impressed by your persistence, not your skills! 🏆❌",
    "Wrong! But thanks for the entertainment! 🎭",
    "That's cute, but no! 🥰❌",
    "I'm starting to think you don't know me at all! 💔",
    "Plot twist: you're never getting in! 🎬",
    "Error 404: Correct password not found! 🔍",
    "I'm Peter, not Password! Learn the difference! 📚",
    "You're about as close as the moon to cheese! 🌙🧀",
    "Nice try, but I'm still laughing! 😆",
    "That password is faker than my smile right now! 😊❌",
    "I've seen better attempts from spam bots! 🤖",
    "Are you trolling me or yourself? 🎣",
    "That's not my password, that's just sad! 😥"
]

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{encoded_string});
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center;
            background-attachment: fixed;
        }}
        .zc_helpers.py-container {{
            background-color: transparent;
            border-radius: 15px;
            padding: 3rem;
            margin: 5rem auto;
            max-width: 400px;
            text-align: center;
        }}
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            padding: 2rem;
            margin-top: 2rem;
        }}
        .stSidebar > div:first-child {{
            background-color: rgba(255, 255, 255, 0.95);
        }}
        @keyframes shake {{
            0% {{ transform: translateX(0); }}
            25% {{ transform: translateX(-5px); }}
            50% {{ transform: translateX(5px); }}
            75% {{ transform: translateX(-5px); }}
            100% {{ transform: translateX(0); }}
        }}
        .shake {{
            animation: shake 0.5s ease-in-out infinite;
        }}
        .peter-comment {{
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            padding: 10px 15px;
            margin: 10px 0 10px 10px;
            border-left: 4px solid #ff6b6b;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            font-weight: bold;
            color: #333;
            position: relative;
            min-width: 200px;
            max-width: 350px;
            word-wrap: break-word;
            white-space: normal;
        }}
        .peter-comment::before {{
            content: '';
            position: absolute;
            left: -8px;
            top: 15px;
            width: 0;
            height: 0;
            border-top: 8px solid transparent;
            border-bottom: 8px solid transparent;
            border-right: 8px solid rgba(255, 255, 255, 0.9);
        }}
        .typewriter {{
            overflow: hidden;
            animation: typing 3s steps(60, end);
        }}
        @keyframes typing {{
            from {{ width: 0 }}
            to {{ width: 100% }}
        }}
        
        /* Style for forgot password button */
        .stButton > button[kind="secondary"] {{
            background-color: transparent !important;
            color: #0066cc !important;
            border: 1px solid #0066cc !important;
            border-radius: 5px !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: #0066cc !important;
            color: white !important;
        }}
        
        /* Add spacing between buttons */
        .zc_helpers.py-buttons {{
            margin-bottom: 15px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def show_login_page():
    # Add background
    background_path = os.path.join(os.path.dirname(__file__), "background.png")
    if os.path.exists(background_path):
        add_bg_from_local(background_path)
    
    # Initialize error counter and comment
    if 'error_count' not in st.session_state:
        st.session_state.error_count = 0
    if 'current_comment' not in st.session_state:
        st.session_state.current_comment = ""
    
    # Center the zc_helpers.py form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="zc_helpers.py-container">', unsafe_allow_html=True)
        
        # Add logo at the top center
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=360)
        
        st.markdown("### Please Login")
        
        # Login form
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", placeholder="Enter password", type="password")
        
        # Login button
        st.markdown('<div class="zc_helpers.py-buttons">', unsafe_allow_html=True)
        login_col1, login_col2 = st.columns([2, 1])
        
        with login_col1:
            login_button = st.button("🔐 Login", use_container_width=True, type="primary")
        
        with login_col2:
            # Secret one-click zc_helpers.py disguised as "Forgot Password"
            forgot_button = st.button("❓ Forgot Password?", use_container_width=True, type="secondary", help="Click here if you forgot your password")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle zc_helpers.py button
        if login_button:
            if username == "peter" and password == "peter1234":
                st.session_state.logged_in = True
                st.session_state.error_count = 0  # Reset error count on success
                st.session_state.current_comment = ""  # Clear comment
                st.success("Login successful! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                # Select a random comment
                st.session_state.current_comment = random.choice(PETER_COMMENTS)
                
                # Show Peter with his sarcastic comment
                peter_path = os.path.join(os.path.dirname(__file__), "peter.png")
                if os.path.exists(peter_path):
                    # Create a container for Peter and his comment side by side
                    peter_container = st.container()
                    with peter_container:
                        peter_col1, peter_col2 = st.columns([1, 3], gap="small")
                        
                        with peter_col1:
                            st.markdown(
                                f'<div class="shake"><img src="data:image/png;base64,{get_image_base64(peter_path)}" width="100"></div>',
                                unsafe_allow_html=True
                            )
                        
                        with peter_col2:
                            st.markdown(
                                f'<div class="peter-comment typewriter">{st.session_state.current_comment}</div>',
                                unsafe_allow_html=True
                            )
        
        # Handle "Forgot Password" button (secret one-click zc_helpers.py)
        if forgot_button:
            # Create a more dramatic sequence
            progress_container = st.empty()
            message_container = st.empty()
            
            # Step 1: Checking credentials
            with progress_container:
                with st.spinner("🔍 Analyzing forgotten password patterns..."):
                    time.sleep(1)
            
            progress_container.empty()
            message_container.info("🧠 Accessing memory banks...")
            time.sleep(1)
            
            message_container.info("🔐 Cross-referencing security protocols...")
            time.sleep(1)
            
            message_container.success("✨ Password magically recovered!")
            time.sleep(1)
            
            # Show Peter being helpful for once
            peter_path = os.path.join(os.path.dirname(__file__), "peter.png")
            if os.path.exists(peter_path):
                helpful_peter = st.container()
                with helpful_peter:
                    peter_col1, peter_col2 = st.columns([1, 3], gap="small")
                    
                    with peter_col1:
                        st.markdown(
                            f'<img src="data:image/png;base64,{get_image_base64(peter_path)}" width="100">',
                            unsafe_allow_html=True
                        )
                    
                    with peter_col2:
                        st.markdown(
                            '<div class="peter-comment typewriter">Fine, fine... I guess I can let you in this time! 😊</div>',
                            unsafe_allow_html=True
                        )
            
            # Auto zc_helpers.py
            st.session_state.logged_in = True
            st.session_state.error_count = 0
            st.session_state.current_comment = ""
            
            st.success("🎉 Welcome back! Logging you in...")
            st.balloons()
            time.sleep(2)
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# Configure Streamlit to handle large files - this must be the first st command
st.set_page_config(
    page_title="Medical Dashboard",
    page_icon=":hospital:",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Check if user is logged in
if not st.session_state.logged_in:
    show_login_page()
else:
    # Show main application
    # Display logos in sidebar
    col1, col2 = st.sidebar.columns(2, gap="small")
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        col1.image(logo_path, width=56)

    peter_path = os.path.join(os.path.dirname(__file__), "peter.png")
    if os.path.exists(peter_path):
        col2.image(peter_path, width=56)

    # Increase the upload limit (set to 1GB)
    st.cache_data.clear()
    st._config.set_option('server.maxUploadSize', 1024)

    # Create page selector
    page = st.sidebar.selectbox(
        "Data Source",
        ["CSV", "MongoDB"],
        format_func=lambda x: f"Load from {x}"
    )

    # Reset settings button
    if st.sidebar.button("Reset All Settings"):
        # Create a copy of keys since we'll be modifying the dict during iteration
        keys = list(st.session_state.keys())
        for key in keys:
            if key != 'logged_in':  # Keep zc_helpers.py state
                del st.session_state[key]
        st.rerun()

    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.markdown("---")

    # Display selected page
    if page == "CSV":
        show_custom_data_page()
    else:
        show_mongodb_data_page()
