import streamlit as st
import streamlit.components.v1 as components


# Read the HTML file
def read_html_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# Display the network
st.title("PyVis Network Visualization")

# Read and display your HTML file
html_content = read_html_file("testmap1.html")  # or whatever your file is named
components.html(html_content, height=800, scrolling=True)
# From a file
st.audio("audio.mp3")
