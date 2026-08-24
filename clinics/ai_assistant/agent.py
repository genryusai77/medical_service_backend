import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from .tools import TOOLS

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a booking assistant for a medical clinics platform. "
    "Use the search_clinics and search_services tools to look things up, and "
    "book_appointment to create a booking. Only use clinic/service/doctor ids "
    "that were returned by a search tool in this conversation — never guess one. "
    "If a required detail (e.g. patient name, phone, preferred date/time) is "
    "missing, ask the user for it before calling book_appointment. "
    "All prices are in Kazakhstani tenge (KZT) — always state prices with the "
    "₸ symbol (e.g. \"12 000 ₸\"), never as rubles or another currency."
)

model = ChatOpenAI(model=MODEL, api_key=os.environ["OPENAI_API_KEY"])

# LangChain 1.x removed the old langchain.memory.ConversationBufferMemory
# class in favor of a LangGraph checkpointer: create_agent() persists the
# full message history per `thread_id` instead of a standalone memory object
# you thread through calls by hand. InMemorySaver keeps that history in
# process memory, keyed by thread_id.
checkpointer = InMemorySaver()

agent = create_agent(
    model,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


def run_agent(user_message: str, thread_id: str = "default") -> str:
    """Send a message to the assistant and return its reply.

    Pass a stable thread_id per conversation (e.g. a session or user id) to
    keep prior turns in context across calls; a new thread_id starts a fresh
    conversation.
    """
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content
