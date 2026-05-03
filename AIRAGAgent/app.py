# app.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from AIRAGAgent.agent.react_agent import ReactAgent

st.title("自动化办公助手")
st.divider()

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []
    thinking_placeholder = st.empty()
    output_placeholder = st.empty()

    with st.spinner("思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        thinking_lines = []
        output_lines = []

        for chunk in res_stream:
            if isinstance(chunk, dict):
                if chunk["type"] == "thinking":
                    thinking_lines.append(chunk["content"])
                    thinking_placeholder.text("\n".join(thinking_lines))
                elif chunk["type"] == "thinking_end":
                    thinking_placeholder.empty()
                elif chunk["type"] == "output":
                    output_lines.append(chunk["content"])
                    output_placeholder.markdown("".join(output_lines))
            else:
                output_lines.append(chunk)
                output_placeholder.markdown("".join(output_lines))

    thinking_placeholder.empty()
    final_output = "".join(output_lines)
    st.session_state["message"].append({"role": "assistant", "content": final_output})
