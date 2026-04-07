"""Base agent class for all LangGraph agents"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, llm=None):
        self.llm = llm
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        pass
