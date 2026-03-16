import streamlit as st
from xai_sdk import Client
from xai_sdk.chat import user, system

# Ensure prompt exists in session state
if 'prompt' not in st.session_state:
    st.session_state.prompt = ""

# Ensure messages list exists for rolling chat display
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Load API key - try Streamlit secrets first (secrets.toml), then fall back to .env
try:
    GROK_API_KEY = st.secrets["GROK_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ API key not found! Please set GROK_API_KEY in `.streamlit/secrets.toml` (preferred) or `.env` file.")
    st.stop()

# Initialize client
client = Client(
    api_key=GROK_API_KEY,
    timeout=3600, # Override default timeout with longer timeout for reasoning models
)

# Functions

def update_beliefs_text():
    new_mode = st.session_state.mode_slider
    with open("Beliefs/" + new_mode + ".txt", 'r', encoding='utf-8') as file:
        st.session_state.beliefs = file.read()

def update_slider_text(name, key):
    new_slider_value = st.session_state[key + "_slider"]
    with open("SliderPrompts/" + name + "/" + str(new_slider_value) + ".txt", 'r', encoding='utf-8') as file:
        new_text = file.read()
        st.session_state[key + "_edited"] = new_text
        st.session_state[key + "_edit_textarea"] = new_text

def reset_session():
    # Resset Messages   
    st.session_state.messages = []
    st.session_state.chat = None
    
    # Resset Sliders
    st.session_state.mode_slider = "Right"
    for key in ["participation", "expression", "reason", "listening", "selfint", "disagreement", "abrasiveness", "persuadability"]:
        st.session_state[f"{key}_slider"] = 3
        st.session_state[f"{key}_toggle"] = True
        st.session_state[f"{key}_edit"] = False
        st.session_state[f"{key}_edited"] = None
        if f"{key}_edit_textarea" in st.session_state:
            st.session_state[f"{key}_edit_textarea"] = ""
            
    # Resset Buttons
    st.session_state.edit_beliefs = False
    st.session_state.edit_prompt = False
    st.session_state.edited_beliefs = None
    st.session_state.edited_prompt_template = None
    if "beliefs" in st.session_state:
        st.session_state["beliefs"] = ""

def create_slider(name, key, row):
    if f"{key}_edit" not in st.session_state:
        st.session_state[f"{key}_edit"] = False
    if f"{key}_edited" not in st.session_state:
        st.session_state[f"{key}_edited"] = None
    rows[row].write(name)
    s_col1, s_col2, s_col3 = rows[row].columns([.5, 3, .5])
    with s_col1:
        s_toggle = st.toggle("toggle", label_visibility="collapsed", value=True, key=f"{key}_toggle")
    with s_col2:
        s = st.slider('Slider Mode', 1, 5, 3, label_visibility="collapsed", disabled=not s_toggle, key=f"{key}_slider", on_change=update_slider_text, args=(name, key))
    with s_col3:
        if st.button("Edit", key=f"{key}_edit_btn", disabled=not s_toggle):
            st.session_state[f"{key}_edit"] = not st.session_state[f"{key}_edit"]
    if st.session_state[f"{key}_edit"]:
        if st.session_state[f"{key}_edited"] is None:
            with open(f"SliderPrompts/{name}/{s}.txt", 'r', encoding='utf-8') as file:
                st.session_state[f"{key}_edited"] = file.read()
        s_edited = rows[row].text_area("Edit", st.session_state[f"{key}_edited"], height='content', disabled=not s_toggle, key=f"{key}_edit_textarea")
        if s_edited != st.session_state[f"{key}_edited"]:
            st.session_state[f"{key}_edited"] = s_edited

st.markdown("# Welcome to the SAIL Lab!")
st.markdown("Are you ready to build democratic skills?")

# Add CSS to gray out disabled sliders
st.markdown("""
<style>
    div[data-baseweb="slider"] input[disabled] {
        opacity: 0.5;
    }
    .stSlider > div > div[data-baseweb="slider"] {
        opacity: 0.5;
    }
    .stSlider[data-disabled="true"] > div > div[data-baseweb="slider"] {
        opacity: 0.5;
    }
</style>
""", unsafe_allow_html=True)

# Reset button
if st.button("Reset"):
    reset_session()

# Input
# Sliders
row1 = st.columns([2.5,1])

mode = row1[0].select_slider(
    'Pick a Mode:', 
    ['Left', 'Lean-Left', 'Center', 'Lean-Right', 'Right'], 
    value="Right",
    key="mode_slider",
    on_change=update_beliefs_text
)

# Session state for edit beliefs
if "edit_beliefs" not in st.session_state:
    st.session_state.edit_beliefs = False
if "edited_beliefs" not in st.session_state:
    st.session_state.edited_beliefs = None

# Edit Beliefs button and text area
beliefs = None
if row1[1].button("Edit Beliefs"):
    st.session_state.edit_beliefs = not st.session_state.edit_beliefs
if st.session_state.edit_beliefs:
    if st.session_state.edited_beliefs is None:
        with open(f"Beliefs/{mode}.txt", 'r', encoding='utf-8') as file:
            st.session_state.edited_beliefs = file.read()
    beliefs = st.text_area("Edit Beliefs", st.session_state.edited_beliefs, height=200, key="beliefs")
    if beliefs != st.session_state.edited_beliefs:
        st.session_state.edited_beliefs = beliefs

# Sliders with toggles
st.markdown("### Conversation Parameters")

# Containers
rows = []
for i in range(8):
    rows.append(st.container())
        
create_slider("Participation", "participation", 0)
create_slider("Expression", "expression", 1)
create_slider("Reason-Giving", "reason", 2)
create_slider("Listening", "listening", 3)
create_slider("Self-Interrogation", "selfint", 4)
create_slider("Disagreement", "disagreement", 5)
create_slider("Abrasiveness", "abrasiveness", 6)
create_slider("Persuadability", "persuadability", 7)

def get_parameter_text(name, key):
    if not st.session_state.get(f"{key}_toggle", True):
        return None
        
    edited_text = st.session_state.get(f"{key}_edited")
    if edited_text is not None:
        return edited_text.strip()
    else:
        slider_val = st.session_state.get(f"{key}_slider", 3)
        try:
            with open(f"SliderPrompts/{name}/{slider_val}.txt", 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            return ""

# Function to generate the prompt for Edit Prompt view (keeps {beliefs} as placeholder)
def generate_prompt_for_edit(mode, prompt_template_edited=None):
    """Generate the prompt with all slider values filled in, but keep {beliefs} as placeholder."""
    # Load prompt template
    if prompt_template_edited:
        expression_template = prompt_template_edited
    else:
        with open("Prompt/expresivness.txt", 'r', encoding='utf-8') as file:
            expression_template = file.read()
    
    # Keep beliefs as placeholder
    beliefs = "{beliefs}"
    
    # Load slider/text values from session state
    participation_text = get_parameter_text("Participation", "participation")
    expression_text = get_parameter_text("Expression", "expression")
    reason_text = get_parameter_text("Reason-Giving", "reason")
    listening_text = get_parameter_text("Listening", "listening")
    selfint_text = get_parameter_text("Self-Interrogation", "selfint")
    disagreement_text = get_parameter_text("Disagreement", "disagreement")
    abrasiveness_text = get_parameter_text("Abrasiveness", "abrasiveness")
    persuadability_text = get_parameter_text("Persuadability", "persuadability")
    
    # Format the prompt with all placeholders replaced (except beliefs stays as {beliefs})
    full_prompt = expression_template.format(
        beliefs=beliefs,
        participation=(f"Participation: {participation_text}\n" if participation_text is not None else ""),
        expression=(f"Expression: {expression_text}\n" if expression_text is not None else ""),
        reason_giving=(f"Reason-Giving: {reason_text}\n" if reason_text is not None else ""),
        listening=(f"Listening: {listening_text}\n" if listening_text is not None else ""),
        self_interrogation=(f"Self-Interrogation: {selfint_text}\n" if selfint_text is not None else ""),
        disagreement=(f"Disagreement: {disagreement_text}\n" if disagreement_text is not None else ""),
        abrasiveness=(f"Abrasiveness: {abrasiveness_text}\n" if abrasiveness_text is not None else ""),
        persuadability=(f"Persuadability: {persuadability_text}\n" if persuadability_text is not None else ""),
    )
    
    return full_prompt

# Function to generate the full formatted prompt for Play button (includes actual beliefs)
def generate_full_prompt(mode, beliefs_edited=None, prompt_template_edited=None):
    """Generate the full prompt with all placeholders replaced, including beliefs."""
    # Load prompt template
    if prompt_template_edited:
        expression_template = prompt_template_edited
    else:
        with open("Prompt/expresivness.txt", 'r', encoding='utf-8') as file:
            expression_template = file.read()
    
    # Load beliefs
    if beliefs_edited:
        beliefs = beliefs_edited
    else:
        with open(f"Beliefs/{mode}.txt", 'r', encoding='utf-8') as file:
            beliefs = file.read()
    
    # Load slider/text values from session state
    participation_text = get_parameter_text("Participation", "participation")
    expression_text = get_parameter_text("Expression", "expression")
    reason_text = get_parameter_text("Reason-Giving", "reason")
    listening_text = get_parameter_text("Listening", "listening")
    selfint_text = get_parameter_text("Self-Interrogation", "selfint")
    disagreement_text = get_parameter_text("Disagreement", "disagreement")
    abrasiveness_text = get_parameter_text("Abrasiveness", "abrasiveness")
    persuadability_text = get_parameter_text("Persuadability", "persuadability")
    
    # Format the prompt with all placeholders replaced
    full_prompt = expression_template.format(
        beliefs=beliefs,
        participation=(f"Participation: {participation_text}\n" if participation_text is not None else ""),
        expression=(f"Expression: {expression_text}\n" if expression_text is not None else ""),
        reason_giving=(f"Reason-Giving: {reason_text}\n" if reason_text is not None else ""),
        listening=(f"Listening: {listening_text}\n" if listening_text is not None else ""),
        self_interrogation=(f"Self-Interrogation: {selfint_text}\n" if selfint_text is not None else ""),
        disagreement=(f"Disagreement: {disagreement_text}\n" if disagreement_text is not None else ""),
        abrasiveness=(f"Abrasiveness: {abrasiveness_text}\n" if abrasiveness_text is not None else ""),
        persuadability=(f"Persuadability: {persuadability_text}\n" if persuadability_text is not None else ""),
    )
    
    return full_prompt

# Session state for edit prompt
if "edit_prompt" not in st.session_state:
    st.session_state.edit_prompt = False
if "edited_prompt_template" not in st.session_state:
    st.session_state.edited_prompt_template = None

# Edit Prompt button and text area - shows fully formatted prompt
if st.button("Edit Prompt"):
    st.session_state.edit_prompt = not st.session_state.edit_prompt
    # Reset edited prompt when toggling to show fresh generated version
    if st.session_state.edit_prompt:
        st.session_state.edited_prompt_template = None

if st.session_state.edit_prompt:
    # Always generate fresh prompt from current sliders to show live updates
    # Keep {beliefs} as placeholder since there's a separate Edit Beliefs button
    # Use edited template if user has edited it
    current_full_prompt = generate_prompt_for_edit(mode, st.session_state.edited_prompt_template)
    
    # Create a hash of current slider states to detect changes
    hash_parts = [mode]
    for key in ["participation", "expression", "reason", "listening", "selfint", "disagreement", "abrasiveness", "persuadability"]:
        hash_parts.append(str(st.session_state.get(f"{key}_slider", 3)))
        hash_parts.append(str(st.session_state.get(f"{key}_toggle", True)))
        hash_parts.append(str(st.session_state.get(f"{key}_edited", "")))
    slider_hash = "_".join(hash_parts)
    
    # Check if sliders changed
    if "last_slider_hash" not in st.session_state:
        st.session_state.last_slider_hash = ""
    
    # If sliders changed, always show the new generated prompt (updates live)
    # Use slider hash in key to force Streamlit to update the text area
    if slider_hash != st.session_state.last_slider_hash:
        st.session_state.last_slider_hash = slider_hash
        # Clear any previous edits when sliders change (to show live updates)
        # User can still edit after sliders change
        st.session_state.edited_prompt_template = None
    
    # Always show current generated prompt (updates with sliders)
    # If user edits, we'll save it, but next slider change will show new generated version
    display_value = current_full_prompt
    
    # Use slider hash in key so the widget updates when sliders change
    prompt_key = f"edit_prompt_text_{slider_hash}"
    
    prompt = st.text_area("Edit Prompt (Fully Formatted - Updates as Sliders Change)", 
                          display_value, height=400, key=prompt_key)
    
    # Save user's edits if they modified the prompt from the generated version
    if prompt != current_full_prompt:
        st.session_state.edited_prompt_template = prompt
    else:
        # If it matches current generated, clear edited version
        st.session_state.edited_prompt_template = None

left, middle, right = st.columns([1.75,1,1])
play = middle.button("Play")

if play:
    # Use the generate_full_prompt function to get the final prompt
    # If user edited the prompt, use that; otherwise generate from current sliders
    if st.session_state.edited_prompt_template:
        # User edited the prompt (may still have {beliefs} placeholder), format it with beliefs
        expression_template = st.session_state.edited_prompt_template
        # Load beliefs
        if st.session_state.edited_beliefs:
            beliefs = st.session_state.edited_beliefs
        else:
            with open(f"Beliefs/{mode}.txt", 'r', encoding='utf-8') as file:
                beliefs = file.read()
        
        # Format the edited prompt with beliefs (and any other placeholders)
        # Need to load slider/text values to format properly
        participation_text = get_parameter_text("Participation", "participation")
        expression_text = get_parameter_text("Expression", "expression")
        reason_text = get_parameter_text("Reason-Giving", "reason")
        listening_text = get_parameter_text("Listening", "listening")
        selfint_text = get_parameter_text("Self-Interrogation", "selfint")
        disagreement_text = get_parameter_text("Disagreement", "disagreement")
        abrasiveness_text = get_parameter_text("Abrasiveness", "abrasiveness")
        persuadability_text = get_parameter_text("Persuadability", "persuadability")
        
        st.session_state.prompt = expression_template.format(
            beliefs=beliefs,
            participation=(f"Participation: {participation_text}\n" if participation_text is not None else ""),
            expression=(f"Expression: {expression_text}\n" if expression_text is not None else ""),
            reason_giving=(f"Reason-Giving: {reason_text}\n" if reason_text is not None else ""),
            listening=(f"Listening: {listening_text}\n" if listening_text is not None else ""),
            self_interrogation=(f"Self-Interrogation: {selfint_text}\n" if selfint_text is not None else ""),
            disagreement=(f"Disagreement: {disagreement_text}\n" if disagreement_text is not None else ""),
            abrasiveness=(f"Abrasiveness: {abrasiveness_text}\n" if abrasiveness_text is not None else ""),
            persuadability=(f"Persuadability: {persuadability_text}\n" if persuadability_text is not None else ""),
        )
    else:
        # Generate from current slider values and edited beliefs if any (include beliefs for final prompt)
        st.session_state.prompt = generate_full_prompt(mode, st.session_state.edited_beliefs, None)

    st.write("Session Ready!")

    # Initialize conversation with system prompt both in the chat client and in local messages
    st.session_state.chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        messages=[system(st.session_state.prompt)]
    )

# Chat (only show after user hits Play)
if 'chat' in st.session_state:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{'role': 'assistant', 'content': "Hello."}]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        st.session_state.chat.append(user(prompt))
        aiResponce = st.session_state.chat.sample()
        st.session_state.chat.append(aiResponce)
        response = f"Robert: {aiResponce.content}"
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})