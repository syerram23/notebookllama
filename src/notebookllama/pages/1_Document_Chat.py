import streamlit as st
import asyncio

from llama_index.tools.mcp import BasicMCPClient

MCP_CLIENT = BasicMCPClient(command_or_url="http://localhost:8000/mcp")


async def chat(inpt: str):
    result = await MCP_CLIENT.call_tool(
        tool_name="query_index_tool", arguments={"question": inpt}
    )
    return result.content[0].text


def sync_chat(inpt: str):
    return asyncio.run(chat(inpt))


# Chat Interface
st.set_page_config(page_title="NotebookLlaMa - Document Chat", page_icon="🗣")

st.sidebar.header("Document Chat🗣")
st.sidebar.info("To switch to the Home page, select it from above!🔺")
st.markdown("---")
st.markdown("## NotebookLlaMa - Document Chat🗣")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "sources" in message:
            # Display the main response
            st.markdown(message["content"])
            # Add toggle for sources
            with st.expander("Sources"):
                st.markdown(message["sources"])
        else:
            st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question about your document"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = sync_chat(prompt)

                # Split response and sources if they exist
                # Assuming your response format includes sources somehow
                # You might need to modify this based on your actual response format
                if "## Sources" in response:
                    parts = response.split("## Sources", 1)
                    main_response = parts[0].strip()
                    sources = "## Sources" + parts[1].strip()
                else:
                    main_response = response
                    sources = None

                st.markdown(main_response)

                # Add toggle for sources if they exist
                if sources:
                    with st.expander("Sources"):
                        st.markdown(sources)
                    # Add to history with sources
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": main_response,
                            "sources": sources,
                        }
                    )
                else:
                    # Add to history without sources
                    st.session_state.messages.append(
                        {"role": "assistant", "content": main_response}
                    )

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.markdown(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
