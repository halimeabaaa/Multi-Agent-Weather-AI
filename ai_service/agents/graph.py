# ai_service/agents/graph.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .weather import weather_agent_node
from .health import health_agent_node
from .summary import summary_agent_node

# Grafiği (Workflow) başlatıyoruz
workflow = StateGraph(AgentState)

# Düğümleri (Node) tanımlıyoruz
workflow.add_node("weather_agent", weather_agent_node)
workflow.add_node("health_agent", health_agent_node)
workflow.add_node("summary_agent", summary_agent_node)

# Ajanların çalışma sırasını çiziyoruz
workflow.set_entry_point("weather_agent")
workflow.add_edge("weather_agent", "health_agent")
workflow.add_edge("health_agent", "summary_agent")
workflow.add_edge("summary_agent", END)

# Grafiği dışarıdan çağrılabilir hale getirmek için derliyoruz
agent_chain = workflow.compile()