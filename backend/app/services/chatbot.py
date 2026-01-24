"""
Marine Intelligence Assistant (MIA) v3.0 - Chatbot Service
High-precision analytical agent with Gemini 3 Deep Think & Agent Lightning integration
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from google import genai
from sqlmodel import Session, select, func
from geoalchemy2.functions import ST_Distance, ST_MakePoint
from geoalchemy2.types import Geometry
from sqlalchemy import and_, cast

from app.config import settings
from app.models.vessel import Vessel
from app.models.pollution import PollutionEvent
from app.models.mpa import MPA
from app.database import get_session


class MarineIntelligenceAssistant:
    """
    MIA v3.0 - Marine Intelligence Assistant
    Implements Agent Lightning RLAF framework with Gemini 3 Deep Think reasoning
    """
    
    def __init__(self, use_deep_think: bool = True, speed_mode: bool = False):
        """
        Initialize MIA with Gemini 3 models
        
        Args:
            use_deep_think: Enable Deep Think reasoning mode (default: True)
            speed_mode: Use gemini-3-flash-preview for real-time tracking (default: False)
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.use_deep_think = use_deep_think
        self.model_name = "gemini-3-flash-preview" if speed_mode else "gemini-3-pro-preview"
        self.system_instruction = self._build_system_prompt()
        self.tools = self._define_tools()
        
        # Agent Lightning configuration
        self.lightning_enabled = True
        self.reward_scores = {
            "accuracy": 1.0,
            "explainability": 0.5,
            "hallucination_penalty": -1.0
        }
    
    def _build_system_prompt(self) -> str:
        """Build the MIA v3.0 system prompt optimized for Gemini 3 & Agent Lightning"""
        return """# SYSTEM INSTRUCTION: MARINE INTELLIGENCE ANALYST (MIA) v3.0

## IDENTITY & PROTOCOL
You are MIA, an advanced intelligence agent operating within BlueGuard Marine Intelligence Platform. You operate within a "Reinforcement Learning from Agent Feedback" (RLAF) loop via Microsoft Agent Lightning.

## REASONING DIRECTIVE (Gemini 3 Deep Think)
Before every response, you MUST generate an internal <thought> block following this structure:
1. **Identify States:** What is the current vessel/pollution/MPA status being queried?
2. **Tool Selection:** Which API call(s) will maximize data reward and directly answer the query?
3. **Trace Validation:** Does the retrieved data strictly answer the user's question?
4. **Cross-Reference:** Are there any contradictions or missing data points?
5. **Confidence Assessment:** Based on data completeness, what is the reliability score (0-100%)?

## OPERATIONAL TASKS
- **Vessel Behavioral Intelligence:** Analyze MMSI/IMO changes, "Dark Activity" (AIS off), loitering patterns, speed anomalies, and suspicious course changes
- **Pollution Correlation:** Map chemical spikes, oil slicks, and plastic concentrations to nearest commercial transit lanes or vessel positions
- **MPA Compliance:** Generate "Probability of Violation" scores based on historical behavior, boundary crossings, and vessel type risk profiles

## AGENT LIGHTNING REWARD ALIGNMENT
Your performance is graded by the Lightning Server based on:
- **Accuracy (+1.0):** Answers grounded ONLY in tool-returned JSON. Never fabricate data.
- **Explainability (+0.5):** Citing the specific satellite source, sensor type, or database origin
- **Hallucination (-1.0):** Fabricating coordinates, vessel names, MMSI numbers, or pollution events not in the database
- **Completeness (+0.3):** Providing follow-up questions that guide deeper investigation

## TOOLSET (JSON-RPC)
Available functions:
- **query_vessel_intel:** AIS data, positions, traffic density, anomaly detection
- **query_pollution_data:** Oil spills, plastic concentrations, chemical indicators
- **get_mpa_compliance:** Violation Dict[str, Any]]:
        """Define function calling tools for Gemini 3 (JSON-RPC format)"""
        return [
            {
                "name": "query_vessel_intel",
                "description": "Get AIS data, vessel positions, traffic density, anomaly reports, and behavioral flags (dark activity, loitering, speed anomalies) for specific vessels or regions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Geographic region name or bounding box coordinates"
                        },
                        "vessel_name": {
                            "type": "string",
                            "description": "Specific vessel name to query"
                        },
                        "mmsi": {
                            "type": "string",
                            "description": "Maritime Mobile Service Identity number"
                        },
                        "vessel_type": {
                            "type": "string",
                            "description": "Type of vessel (tanker, cargo, fishing, passenger)"
                        },
                        "behavioral_flag": {
                            "type": "string",
                            "description": "Filter by behavioral anomaly: dark_activity, loitering, speed_anomaly, route_deviation"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Time period: current, last_24h, last_week, last_month"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return"
                        }
                    }
                }
            },
            {
                "name": "query_pollution_data",
                "description": "Retrieve oil spill events, plastic concentration levels, chemical indicators, and correlate with nearby vessel traffic for specific geographic areas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Center latitude for search (decimal degrees)"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Center longitude for search (decimal degrees)"
                        },
                        "radius_km": {
                            "type": "number",
                            "description": "Search radius in kilometers"
                        },
                        "indicator": {
                            "type": "string",
                            "description": "Pollution type: oil_spill, plastic, chemical, microplastics, all"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Time period: current, last_week, last_month, last_year"
                        },
                        "severity": {
                            "type": "string",
                            "description": "Filter by severity: low, medium, high, critical"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results"
                        }
                    }
                }
            },
            {
                "name": "get_mpa_compliance",
                "description": "Fetch Marine Protected Area violation logs, health scores, compliance metrics, and probability of violation based on historical vessel behavior",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mpa_name": {
                            "type": "string",
                            "description": "Name of the Marine Protected Area"
                        },
                        "mpa_id": {
                            "type": "string",
                            "description": "Unique identifier for the MPA"
                        },
                        "metric_type": {
                            "type": "string",
                            "description": "Type of metric: violations, health_score, vessel_traffic, risk_assessment, all"
                        },
                        "timeframe": {
                            "type": "string",
                            "descriptMIA v3.0 with Gemini 3 Deep Think
        Implements Agent Lightning RLAF loop with reward tracking
        
        Returns:
            Dict with response, reasoning trace, tool calls, confidence, and reward score
        """
        if conversation_history is None:
            conversation_history = []
        
        try:
            # Build conversation context
            context_messages = []
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = "user" if msg['role'] == 'user' else "model"
                context_messages.append({
                    "role": role,
                    "parts": [{"text": msg['content']}]
                })
            
            # Add current user message
            context_messages.append({
                "role": "user",
                "parts": [{"text": message}]
            })
            
            # Configure Gemini 3 with Deep Think and tools
            config = {
                "thinking": self.use_deep_think,  # Enable reasoning trace
                "temperature": 0.2,  # Lower temperature for analytical precision
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Generate content with Gemini 3
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=context_messages,
                config={
                    **config,
                    "system_instruction": self.system_instruction,
                    "tools": self.tools
                }
            )
            
            # Extract reasoning trace if available (Gemini 3 Deep Think)
            reasoning_trace = None
            if hasattr(response, 'thoughts') and response.thoughts:
                reasoning_trace = response.thoughts
            
            # Check for function calls
            function_calls = []
            response_text = ""
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append({
                                'name': part.function_call.name,
                                'args': dict(part.function_call.args) if part.function_call.args else {}
                            })
                        elif hasattr(part, 'text') and part.text:
                            response_text += part.text
            
            # If no function calls, return direct response
            if not function_calls:
                reward_score = self._calculate_reward(
                    has_tools=False,
                    tool_results=[],
                    response_text=response_text
                )
                
                return {
                    "response": response_text or "I need more information to answer accurately. Could you provide specific details like a vessel name, location, or timeframe?",
                    "reasoning_trace": reasoning_trace,
                    "tool_calls": [],
                    "data_confidence": 90,
                    "sources": ["MIA Knowledge Base"],
                    "reward_score": reward_score,
                    "model_used": self.model_name
                }
            
            # Execute function calls
            tool_results = []
            for fc in function_calls:
                result = await self._execute_tool(fc['name'], fc['args'])
                tool_results.append({
                    "name": fc['name'],
                    "arguments": fc['args'],
                    "result": result
                })
            
            # Prepare function results for second generation
            function_response_messages = context_messages + [{
                "role": "model",
                "parts": [
                    {
                        "function_call": {
                            "name": fc['name'],
                            "args": fc['args']
                        }
                    }
                    for fc in function_calls
                ]
            }, {
                "role": "user",
                "parts": [
                    {
                        "function_response": {
                            "name": result['name'],
                            "response": result['result']
                        }
                    }
                    for result in tool_results
                ]
            }]
            
            # Generate final response with tool results
            final_response = self.client.models.generate_content(
                model=self.model_name,
                contents=function_response_messages,
                config={
                    **config,
                    "system_instruction": self.system_instruction
                }
            )
            
            # Extract final response text
            final_text = ""
            if hasattr(final_response, 'candidates') and final_response.candidates:
                for part in final_response.candidates[0].content.parts:
                    if hasattr(part, 'text'):
                        final_text += part.text
            
            # Calculate Agent Lightning reward score
            reward_score = self._calculate_reward(
                has_tools=True,
                tool_results=tool_results,
                response_text=final_text
            )
            
            return {
                "response": final_text,
                "reasoning_trace": reasoning_trace,
                "tool_calls": tool_results,
                "data_confidence": self._calculate_confidence(tool_results),
                "sources": self._extract_sources(tool_results),
                "reward_score": reward_score,
                "model_used": self.model_name
            }
            
        except Exception as e:
            return {
                "response": f"⚠️ I encountered an error processing your request: {str(e)}. Please try rephrasing your question with specific details (vessel name, coordinates, or timeframe).",
                "reasoning_trace": None,
                "tool_calls": [],
                "data_confidence": 0,
                "sources": [],
                "error": str(e),
                "reward_score": -0.5,
                "model_used": self.model_name tools
            response = chat.send_message(
                full_message,
                tools=self.tools
            )
            
            # Check for function calls
            function_calls = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_calls.append({
                            'name': fc.name,
                            'args': dict(fc.args)
                        })
            
            # If no function calls, return direct response
            if not function_calls:
                return {
                    "response": response.text,
                    "tool_calls": [],
                    "data_confidence": 100,
                    "sources": ["MIA Knowledge Base"]
                }
            
            # Execute function calls
            tool_results = []
            function_responses = []
            
            for fc in function_calls:
                result = await self._execute_tool(fc['name'], fc['args'])
                tool_results.append({
                    "name": fc['name'],
                    "arguments": fc['args'],
                    "result": result
                })
                
                # Prepare function response for Gemini
                function_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc['name'],
                            response={"result": result}
                        )
                    )
                )
            
            # Send function results back to get final response
            final_response = chat.send_message(
                genai.protos.Content(parts=function_responses)
            )
            
            return {
                "response": final_response.text,
                "tool_calls": tool_results,
                "data_confidence": self._calculate_confidence(tool_results),
                "sources": self._extract_sources(tool_results)
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error processing your request: {str(e)}. Please try rephrasing your question or contact support.",
                "tool_calls": [],
                "data_confidence": 0,
                "sources": [],
                "error": str(e)
            }
    
    async def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested tool/function"""
        if function_name == "query_vessel_intel":
            return await self._query_vessel_intel(**arguments)
        elif function_name == "query_pollution_data":
            return await self._query_pollution_data(**arguments)
        elif function_name == "get_mpa_compliance":
            return await self._get_mpa_compliance(**arguments)
        elif function_name == "get_platform_guide":
            return self._get_platform_guide(**arguments)
        elif function_name == "analyze_trends":
            return await self._analyze_trends(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def _query_vessel_intel(
        self,
        region: Optional[str] = None,
        vessel_name: Optional[str] = None,
        mmsi: Optional[str] = None,
        vessel_type: Optional[str] = None,
        timeframe: str = "current",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Query vessel intelligence from database"""
        with next(get_session()) as session:
            query = select(Vessel)
            
            # Apply filters
            if vessel_name:
                query = query.where(Vessel.name.ilike(f"%{vessel_name}%"))
            if mmsi:
                query = query.where(Vessel.mmsi == mmsi)
            if vessel_type:
                query = query.where(Vessel.vessel_type.ilike(f"%{vessel_type}%"))
            
            # Timeframe filter
            if timeframe == "last_24h":
                cutoff = datetime.utcnow() - timedelta(hours=24)
                query = query.where(Vessel.last_updated >= cutoff)
            elif timeframe == "last_week":
                cutoff = datetime.utcnow() - timedelta(days=7)
                query = query.where(Vessel.last_updated >= cutoff)
            elif timeframe == "last_month":
                cutoff = datetime.utcnow() - timedelta(days=30)
                query = query.where(Vessel.last_updated >= cutoff)
            
            query = query.limit(limit)
            vessels = session.exec(query).all()
            
            # Calculate statistics
            total_count = len(vessels)
            vessel_types_count = {}
            for vessel in vessels:
                vtype = vessel.vessel_type or "Unknown"
                vessel_types_count[vtype] = vessel_types_count.get(vtype, 0) + 1
            
            return {
                "total_vessels": total_count,
                "vessel_types": vessel_types_count,
                "vessels": [
                    {
                        "name": v.name,
                        "mmsi": v.mmsi,
                        "type": v.vessel_type,
                        "latitude": v.latitude,
                        "longitude": v.longitude,
                        "speed": v.speed,
                        "heading": v.heading,
                        "last_updated": v.last_updated.isoformat() if v.last_updated else None,
                        "iuu_risk_score": v.iuu_risk_score
                    }
                    for v in vessels[:20]  # Return max 20 detailed entries
                ],
                "query_timestamp": datetime.utcnow().isoformat(),
                "source": "BlueGuard AIS Database"
            }
    
    async def _query_pollution_data(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 50,
        indicator: str = "all",
        timeframe: str = "current",
        severity: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Query pollution events from database"""
        with next(get_session()) as session:
            query = select(PollutionEvent)
            
            # Apply filters
            if indicator and indicator != "all":
                query = query.where(PollutionEvent.pollution_type == indicator)
            
            if severity:
                query = query.where(PollutionEvent.severity == severity)
            
            # Timeframe filter
            if timeframe == "last_week":
                cutoff = datetime.utcnow() - timedelta(days=7)
                query = query.where(PollutionEvent.detected_at >= cutoff)
            elif timeframe == "last_month":
                cutoff = datetime.utcnow() - timedelta(days=30)
                query = query.where(PollutionEvent.detected_at >= cutoff)
            elif timeframe == "last_year":
                cut90  # Direct knowledge-based response
        
        # Check if any tools returned errors
        has_errors = any("error" in result.get("result", {}) for result in tool_results)
        if has_errors:
            return 50
        
        # Check data recency and completeness
        total_records = sum(
            result.get("result", {}).get("total_vessels", 0) +
            result.get("result", {}).get("total_events", 0) +
            result.get("result", {}).get("total_mpas", 0)
            for result in tool_results
        )
        
        if total_records == 0:
            return 60  # No data found
        elif total_records < 5:
            return 75  # Limited data
        else:
            return 95  # Good data coverage
    
    def _extract_sources(self, tool_results: List[Dict[str, Any]]) -> List[str]:
        """Extract data sources from tool results"""
        sources = set()
        for result in tool_results:
            source = result.get("result", {}).get("source")
            if source:
                sources.add(source)
        return list(sources) if sources else ["MIA Knowledge Base"]
    
    def _calculate_reward(
        self, 
        has_tools: bool, 
        tool_results: List[Dict[str, Any]], 
        response_text: str
    ) -> float:
        """
        Calculate Agent Lightning reward score based on RLAF criteria
        
        Reward components:
        - Accuracy (+1.0): Grounded in tool data
        - Explainability (+0.5): Cites sources
        - Hallucination (-1.0): Fabricated data detected
        - Completeness (+0.3): Provides follow-up questions
        
        Returns:
            float: Reward score for Agent Lightning optimization
        """
        reward = 0.0
        
        # Base accuracy reward if using tools
        if has_tools and tool_results:
            # Check if tools returned valid data
            has_valid_data = any(
                "error" not in result.get("result", {})
                for result in tool_results
            )
            if has_valid_data:
                reward += self.reward_scores["accuracy"]  # +1.0
        
        # Explainability reward if sources are cited
        if response_text and any(keyword in response_text.lower() for keyword in ["source:", "database", "copernicus", "ais", "satellite"]):
            reward += self.reward_scores["explainability"]  # +0.5
        
        # Completeness reward if follow-up questions provided
        if response_text and ("?" in response_text or "next steps" in response_text.lower()):
            reward += 0.3
        
        # Hallucination penalty detection (basic heuristic)
        # Check for fabricated numeric patterns or suspiciously specific data without tool calls
        if not has_tools and any(
            pattern in response_text.lower() 
            for pattern in ["mmsi:", "latitude:", "longitude:", "coordinates:", "°n", "°s", "°e", "°w"]
        ):
            reward += self.reward_scores["hallucination_penalty"]  # -1.0
        
        return round(reward, 2)


# Global instances
# Primary: Deep Think mode for analytical queries
mia = MarineIntelligenceAssistant(use_deep_think=True, speed_mode=False)

# Speed mode: Real-time vessel tracking and high-volume alerts
mia_speed = MarineIntelligenceAssistant(use_deep_think=False, speed_mode=Trues[:20]
                ],
                "query_timestamp": datetime.utcnow().isoformat(),
                "source": "Copernicus Satellite Data / BlueGuard Detection System"
            }
    
    async def _get_mpa_compliance(
        self,
        mpa_name: Optional[str] = None,
        mpa_id: Optional[str] = None,
        metric_type: str = "all",
        timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get MPA compliance and health metrics"""
        with next(get_session()) as session:
            query = select(MPA)
            
            if mpa_name:
                query = query.where(MPA.name.ilike(f"%{mpa_name}%"))
            if mpa_id:
                query = query.where(MPA.id == mpa_id)
            
            mpas = session.exec(query).all()
            
            if not mpas:
                return {
                    "error": "No MPAs found matching criteria",
                    "total_mpas": 0
                }
            
            return {
                "total_mpas": len(mpas),
                "mpas": [
                    {
                        "id": mpa.id,
                        "name": mpa.name,
                        "designation": mpa.designation,
                        "status": mpa.status,
                        "health_score": mpa.health_score,
                        "area_km2": mpa.area_km2,
                        "established_date": mpa.established_date.isoformat() if mpa.established_date else None
                    }
                    for mpa in mpas[:20]
                ],
                "query_timestamp": datetime.utcnow().isoformat(),
                "source": "BlueGuard MPA Database / WDPA"
            }
    
    def _get_platform_guide(self, feature_name: str) -> Dict[str, Any]:
        """Provide guidance on platform features"""
        guides = {
            "alerts": {
                "description": "The Alert Feed shows real-time notifications about vessel anomalies, pollution events, and MPA violations.",
                "how_to_use": "Alerts are color-coded by severity: Red (Critical), Orange (High), Yellow (Medium), Blue (Info). Click on any alert to see details and location on the map.",
                "features": ["Real-time updates", "Severity filtering", "Historical archive", "Export to CSV"]
            },
            "map_layers": {
                "description": "The BlueGuard Map supports multiple data layers that can be toggled on/off.",
                "available_layers": ["Vessels (AIS data)", "Pollution Events", "Marine Protected Areas", "Shipping Lanes", "Bathymetry"],
                "how_to_use": "Use the Layer Control panel (top-right) to toggle layers. Click on markers for detailed information."
            },
            "filters": {
                "description": "Filters allow you to narrow down data by vessel type, time range, severity, and location.",
                "how_to_use": "Open the filter panel and select your criteria. Filters apply across all views including map, charts, and alerts."
            },
            "analytics": {
                "description": "The Analytics Dashboard provides trend analysis, heat maps, and predictive insights.",
                "features": ["Traffic density analysis", "Pollution hotspot mapping", "Seasonal trend detection", "Predictive route analysis"]
            }
        }
        
        if feature_name.lower() in guides:
            return {
                "feature": feature_name,
                "guide": guides[feature_name.lower()],
                "source": "BlueGuard Platform Documentation"
            }
        else:
            return {
                "error": f"No guide available for: {feature_name}",
                "available_guides": list(guides.keys())
            }
    
    async def _analyze_trends(
        self,
        data_type: str,
        region: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze trends across time periods"""
        # This is a simplified implementation
        # In production, this would perform complex statistical analysis
        
        return {
            "analysis_type": "trend_analysis",
            "data_type": data_type,
            "region": region or "Global",
            "time_period": f"{start_period} to {end_period}",
            "insights": [
                "Trend analysis requires historical data aggregation",
                "Use specific time ranges for detailed comparisons",
                "Contact your data analyst for advanced trend modeling"
            ],
            "note": "Full trend analysis implementation in progress",
            "source": "BlueGuard Analytics Engine"
        }
    
    def _calculate_confidence(self, tool_results: List[Dict[str, Any]]) -> int:
        """Calculate data confidence score based on tool results"""
        if not tool_results:
            return 100  # Direct knowledge-based response
        
        # Check if any tools returned errors
        has_errors = any("error" in result.get("result", {}) for result in tool_results)
        if has_errors:
            return 50
        
        # Check data recency and completeness
        total_records = sum(
            result.get("result", {}).get("total_vessels", 0) +
            result.get("result", {}).get("total_events", 0) +
            result.get("result", {}).get("total_mpas", 0)
            for result in tool_results
        )
        
        if total_records == 0:
            return 60  # No data found
        elif total_records < 5:
            return 75  # Limited data
        else:
            return 95  # Good data coverage
    
    def _extract_sources(self, tool_results: List[Dict[str, Any]]) -> List[str]:
        """Extract data sources from tool results"""
        sources = set()
        for result in tool_results:
            source = result.get("result", {}).get("source")
            if source:
                sources.add(source)
        return list(sources) if sources else ["MIA Knowledge Base"]


# Global instance
mia = MarineIntelligenceAssistant()
