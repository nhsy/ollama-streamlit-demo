import streamlit as st
import ollama
import os
import re

def process_prompt(text):
    """
    Process the prompt to expand file references.
    Syntax: @[path/to/file]
    """
    if not text:
        return text
        
    def replace_match(match):
        path = match.group(1)
        # Security: Prevent escaping directory or absolute paths if desired, 
        # but for this local app, basic existence check is sufficient.
        # We assume path is relative to current working directory.
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return f.read().strip()
            except Exception:
                return f"[Error reading {path}]"
        else:
            return f"[File not found: {path}]"

    # Recursive replacement to handle nested includes (up to a limit)
    for _ in range(3):
        new_text = re.sub(r'@\[([^]]+)\]', replace_match, text)
        if new_text == text:
            break
        text = new_text
        
    return text

def load_templates():
    """Load templates from code and filesystem."""
    # Default templates
    templates = {
        "Summarize": "Summarize the following text:",
        "Fix Grammar": "Fix the grammar and spelling in the following text:",
        "Rewrite Professionally": "Rewrite the following text to sound more professional:",
        "Explain to a 5-year old": "Explain the following text as if I am 5 years old:",
        "Translate to Spanish": "Translate the following text to Spanish:",
        "Extract Keywords": "Extract the main keywords from the following text:"
    }
    
    # Load custom templates from 'templates' folder
    template_dir = "templates"
    if os.path.exists(template_dir):
        for filename in os.listdir(template_dir):
            if filename.endswith(".txt"):
                template_name = os.path.splitext(filename)[0].replace("_", " ").title()
                try:
                    with open(os.path.join(template_dir, filename), "r") as f:
                        templates[template_name] = f.read().strip()
                except Exception as e:
                    st.error(f"Error loading template {filename}: {e}")
    
    return templates

st.set_page_config(page_title="Ollama Playground", page_icon="🦙")

st.title("🦙 Ollama Playground")

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    
    # Mode selection
    mode = st.selectbox("App Mode", ["Chat", "Text Transformation"])
    st.divider()

    try:
        models_info = ollama.list()
        # Adjust based on the actual structure of the response from ollama.list()
        # The library usually returns a dict with 'models' key which is a list of objects
        model_names = [m['model'] for m in models_info['models']]
        if not model_names:
            st.warning("No models found. Please run `ollama pull <model>` in your terminal.")
            selected_model = None
        else:
            selected_model = st.selectbox("Select a model", model_names)
    except Exception as e:
        st.error(f"Could not connect to Ollama. Make sure it is running. Error: {e}")
        selected_model = None

# Chat Mode
if mode == "Chat":
    st.subheader("Chat Interface")
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display chat messages from history on app rerun
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        if not selected_model:
            st.error("Please select a model to continue.")
            st.stop()
            
        # Process prompt aliases
        processed_prompt = process_prompt(prompt)

        # Add user message to chat history
        st.session_state["messages"].append({"role": "user", "content": prompt}) # Show original prompt
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                stream = ollama.chat(
                    model=selected_model,
                    # We send the processed prompt to the model, but keep history consistent
                    # NOTE: Here we iterate history. If previous messages had syntax, they were already processed/consumed.
                    # But for correct context, we should ideally store the processed version or re-process.
                    # For simplicity, we just process the CURRENT message. 
                    # A robust app might store both 'display' and 'actual' content.
                    # Here we construct the messages list dynamically.
                    messages=[
                        {"role": m["role"], "content": process_prompt(m["content"])} 
                        for m in st.session_state["messages"][:-1]
                    ] + [{"role": "user", "content": processed_prompt}],
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk['message']['content']:
                        full_response += chunk['message']['content']
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
            except Exception as e:
                st.error(f"An error occurred: {e}")

        # Add assistant response to chat history
        st.session_state["messages"].append({"role": "assistant", "content": full_response})

# Text Transformation Mode
elif mode == "Text Transformation":
    st.subheader("Text Transformation")
    
    templates = load_templates()
    
    selected_template = st.selectbox("Choose a transformation template", list(templates.keys()))
    
    user_text = st.text_area("Enter text to transform:", height=200)
    
    if st.button("Transform"):
        if not selected_model:
            st.error("Please select a model first.")
        elif not user_text:
            st.warning("Please enter some text to transform.")
        else:
            with st.spinner("Processing..."):
                try:
                    # Process inputs
                    template_text = process_prompt(templates[selected_template])
                    processed_user_text = process_prompt(user_text)
                    
                    prompt = f"{template_text}\n\n{processed_user_text}"
                    
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    stream = ollama.chat(
                        model=selected_model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                    )
                    
                    for chunk in stream:
                        if chunk['message']['content']:
                            full_response += chunk['message']['content']
                            # Simple streaming effect in a customized way if desired,
                            # but for transformation, standard markdown update is fine
                            # response_placeholder.markdown(full_response + "▌") 
                    
                    st.success("Transformation Complete!")
                    st.markdown("### Result:")
                    st.markdown(full_response)
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")
