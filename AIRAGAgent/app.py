# app.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from AIRAGAgent.agent.supervisor_agent import SupervisorAgent

st.title("自动化办公助手（多智能体协同）")
st.divider()

if "agent" not in st.session_state:
    st.session_state["agent"] = SupervisorAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    thinking_placeholder = st.empty()
    output_placeholder = st.empty()

    with st.spinner("思考中..."):
        chat_history = st.session_state["message"][:-1]
        res_stream = st.session_state["agent"].execute_stream(prompt, chat_history)

        thinking_lines = []
        output_lines = []

        for chunk in res_stream:
            if isinstance(chunk, dict):
                chunk_type = chunk["type"]
                if chunk_type in ("thinking", "supervisor_thinking"):
                    thinking_lines.append(chunk["content"])
                    thinking_placeholder.text("\n".join(thinking_lines))
                elif chunk_type in ("thinking_end", "supervisor_action"):
                    thinking_lines.append(chunk["content"])
                    thinking_placeholder.text("\n".join(thinking_lines))
                elif chunk_type == "output":
                    output_lines.append(chunk["content"])
                    output_placeholder.markdown("".join(output_lines))
            else:
                output_lines.append(chunk)
                output_placeholder.markdown("".join(output_lines))

    thinking_placeholder.empty()
    final_output = "".join(output_lines)
    st.session_state["message"].append({"role": "assistant", "content": final_output})
