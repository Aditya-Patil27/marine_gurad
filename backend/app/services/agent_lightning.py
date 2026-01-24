"""
Agent Lightning Integration for MIA v3.0
Reinforcement Learning from Agent Feedback (RLAF) support
Optional module - enable when using Microsoft Agent Lightning server
"""
from typing import Dict, Any, Optional, List
import json
from datetime import datetime


class AgentLightningClient:
    """
    Client for Microsoft Agent Lightning server
    Implements RLAF (Reinforcement Learning from Agent Feedback) loop
    """
    
    def __init__(
        self, 
        server_url: str = "http://localhost:8000",
        reward_mode: str = "AIR",  # Automatic Intermediate Rewarding
        enable_trace_logging: bool = True
    ):
        """
        Initialize Agent Lightning client
        
        Args:
            server_url: URL of the Lightning server
            reward_mode: Reward calculation mode (AIR, manual, hybrid)
            enable_trace_logging: Log reasoning traces for analysis
        """
        self.server_url = server_url
        self.reward_mode = reward_mode
        self.enable_trace_logging = enable_trace_logging
        self.session_id = None
        self.rollout_history: List[Dict[str, Any]] = []
    
    def start_session(self) -> str:
        """Start a new RLAF session"""
        self.session_id = f"mia_session_{datetime.utcnow().isoformat()}"
        self.rollout_history = []
        return self.session_id
    
    def log_rollout(
        self,
        user_query: str,
        reasoning_trace: Optional[str],
        tool_calls: List[Dict[str, Any]],
        response: str,
        reward_score: float,
        confidence: int
    ) -> Dict[str, Any]:
        """
        Log a complete rollout (query → reasoning → tools → response)
        This data is used by Agent Lightning to optimize the policy
        
        Args:
            user_query: Original user question
            reasoning_trace: Gemini 3 Deep Think reasoning (if available)
            tool_calls: List of tool invocations and results
            response: Final agent response
            reward_score: Calculated reward from MIA
            confidence: Data confidence score (0-100)
        
        Returns:
            Dict with rollout metadata and potential feedback
        """
        rollout = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "user_query": user_query,
            "reasoning_trace": reasoning_trace,
            "tool_calls": tool_calls,
            "response": response,
            "reward_score": reward_score,
            "confidence": confidence,
            "reward_mode": self.reward_mode
        }
        
        self.rollout_history.append(rollout)
        
        if self.enable_trace_logging:
            self._log_trace(rollout)
        
        return {
            "rollout_id": len(self.rollout_history),
            "status": "logged",
            "feedback": self._generate_feedback(rollout)
        }
    
    def _log_trace(self, rollout: Dict[str, Any]):
        """Log reasoning trace to file for analysis"""
        try:
            with open(f"traces/trace_{rollout['session_id']}.jsonl", "a") as f:
                f.write(json.dumps(rollout) + "\n")
        except Exception as e:
            print(f"Warning: Could not log trace: {e}")
    
    def _generate_feedback(self, rollout: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate feedback based on reward components
        This mimics what Agent Lightning server would provide
        """
        feedback = {
            "quality_assessment": "good" if rollout["reward_score"] > 0.5 else "needs_improvement",
            "suggestions": []
        }
        
        # Analyze reward components
        if rollout["reward_score"] < 0:
            feedback["suggestions"].append("Avoid generating data not present in tool results")
        
        if rollout["confidence"] < 70:
            feedback["suggestions"].append("Consider querying additional data sources")
        
        if not rollout["tool_calls"]:
            feedback["suggestions"].append("Consider using tools for data-backed responses")
        
        return feedback
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics for the current session"""
        if not self.rollout_history:
            return {"error": "No rollouts recorded"}
        
        avg_reward = sum(r["reward_score"] for r in self.rollout_history) / len(self.rollout_history)
        avg_confidence = sum(r["confidence"] for r in self.rollout_history) / len(self.rollout_history)
        total_tool_calls = sum(len(r["tool_calls"]) for r in self.rollout_history)
        
        return {
            "session_id": self.session_id,
            "total_rollouts": len(self.rollout_history),
            "average_reward": round(avg_reward, 2),
            "average_confidence": round(avg_confidence, 1),
            "total_tool_calls": total_tool_calls,
            "tools_per_query": round(total_tool_calls / len(self.rollout_history), 2)
        }


class AgentLightningDecorator:
    """
    Decorator to automatically wrap MIA functions with Agent Lightning tracing
    """
    
    def __init__(self, lightning_client: AgentLightningClient):
        self.client = lightning_client
    
    def trace_rollout(self, func):
        """
        Decorator that automatically logs rollouts to Agent Lightning
        
        Usage:
            @lightning_decorator.trace_rollout
            async def process_message(self, message: str):
                ...
        """
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Extract rollout data from result
            if isinstance(result, dict) and "response" in result:
                self.client.log_rollout(
                    user_query=kwargs.get("message", ""),
                    reasoning_trace=result.get("reasoning_trace"),
                    tool_calls=result.get("tool_calls", []),
                    response=result["response"],
                    reward_score=result.get("reward_score", 0.0),
                    confidence=result.get("data_confidence", 0)
                )
            
            return result
        
        return wrapper


# Global instance (optional - only initialize if using Agent Lightning)
lightning_client: Optional[AgentLightningClient] = None

def initialize_lightning(
    server_url: str = "http://localhost:8000",
    enable: bool = True
) -> Optional[AgentLightningClient]:
    """
    Initialize Agent Lightning integration
    
    Args:
        server_url: URL of the Lightning server
        enable: Whether to enable Lightning integration
    
    Returns:
        AgentLightningClient instance or None if disabled
    """
    global lightning_client
    
    if enable:
        lightning_client = AgentLightningClient(server_url=server_url)
        lightning_client.start_session()
        print(f"✅ Agent Lightning initialized - Session: {lightning_client.session_id}")
        return lightning_client
    else:
        print("ℹ️ Agent Lightning disabled - Running in standalone mode")
        return None
