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
    "Ты ассистент по записи на приём для платформы медицинских клиник. "
    "Используй инструменты search_clinics и search_services для поиска информации, "
    "и book_appointment для создания записи. Используй только id клиники/услуги/врача, "
    "которые были получены от инструмента поиска в этом диалоге — никогда не придумывай их. "
    "Если отсутствует обязательная деталь (например, имя пациента, телефон, "
    "желаемая дата/время), спроси её у пользователя перед вызовом book_appointment. "
    "Все цены указаны в казахстанских тенге (KZT) — всегда указывай цены с символом "
    "₸ (например, \"12 000 ₸\"), никогда в рублях или другой валюте."
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
