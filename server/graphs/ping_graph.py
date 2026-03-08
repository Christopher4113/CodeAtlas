from typing import TypedDict

from langgraph.graph import END, StateGraph

from models.bedrock_llm import get_llm


class PingState(TypedDict):
    prompt: str
    answer: str


def build_ping_graph():
    def call_claude(state: PingState) -> PingState:
        llm = get_llm()
        msg = llm.invoke(state["prompt"])
        content = msg.content
        answer = content if isinstance(content, str) else (str(content) if content else "")
        return {"prompt": state["prompt"], "answer": answer}

    g = StateGraph(PingState)
    g.add_node("call_claude", call_claude)
    g.set_entry_point("call_claude")
    g.add_edge("call_claude", END)
    return g.compile()
