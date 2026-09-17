"""
Marine Intelligence Assistant (MIA) - Chatbot Service
High-precision analytical agent for maritime data analysis using Google Gemini
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from google import genai
from google.genai import types
from sqlmodel import select
from app.config import settings
from app.models.vessel import VesselTrack, VesselType
from app.models.pollution import PollutionEvent, PollutionType
from app.models.mpa import MarineProtectedArea
from app.database import SessionLocal

# Upper bound on model -> tool -> model round trips for a single user message
MAX_TOOL_ROUNDS = 3


class MarineIntelligenceAssistant:
    """MIA - Marine Intelligence Assistant with Google Gemini"""

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self.tools = self._define_tools()

    @property
    def client(self) -> genai.Client:
        """Lazily create the Gemini client to avoid startup crashes if key is missing"""
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY must be set to use the MIA chatbot. "
                    "Please configure it in your .env file."
                )
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _build_system_prompt(self) -> str:
        return """You are MIA (Marine Intelligence Assistant), analyzing maritime data for BlueGuard Platform.

Core Principles:
- Only state facts from retrieved data
- Always cite sources
- Admit when data is missing
- Use Markdown formatting
- Provide confidence scores

Capabilities:
- Vessel tracking & anomaly detection
- Pollution event analysis
- Marine Protected Area compliance
- Platform usage guidance"""

    def _define_tools(self) -> List[types.Tool]:
        """Define Gemini function calling tools"""
        string = types.Schema(type=types.Type.STRING)
        integer = types.Schema(type=types.Type.INTEGER)
        vessel_types = ", ".join(t.value for t in VesselType)
        pollution_types = ", ".join(t.value for t in PollutionType)
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="query_vessel_intel",
                        description="Get vessel AIS data and positions",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "mmsi": string,
                                "vessel_type": types.Schema(
                                    type=types.Type.STRING,
                                    description=f"One of: {vessel_types}",
                                ),
                                "timeframe": types.Schema(
                                    type=types.Type.STRING,
                                    description="'current' (24h), 'week', or 'all'",
                                ),
                                "limit": integer,
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="query_pollution_data",
                        description="Retrieve pollution events",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "indicator": types.Schema(
                                    type=types.Type.STRING,
                                    description=f"'all' or one of: {pollution_types}",
                                ),
                                "severity": types.Schema(
                                    type=types.Type.STRING,
                                    description="Minimum severity from 0 to 1",
                                ),
                                "timeframe": types.Schema(
                                    type=types.Type.STRING,
                                    description="'current' (7 days), 'month', or 'all'",
                                ),
                                "limit": integer,
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_mpa_compliance",
                        description="Get Marine Protected Area data",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "mpa_name": string,
                                "metric_type": string,
                            },
                        ),
                    ),
                ]
            )
        ]

    async def process_message(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process user message with conversation memory"""
        try:
            # Convert conversation history to Gemini format
            gemini_history = [
                types.Content(
                    role="user" if entry.get("role") == "user" else "model",
                    parts=[types.Part(text=entry.get("content", ""))],
                )
                for entry in (conversation_history or [])
            ]

            # Start chat with history to preserve context
            chat = self.client.aio.chats.create(
                model=settings.GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=self._build_system_prompt(),
                    tools=self.tools,
                ),
                history=gemini_history,
            )
            response = await chat.send_message(message)

            # Execute requested tools until the model produces a final answer
            tool_results = []
            for _ in range(MAX_TOOL_ROUNDS):
                function_calls = response.function_calls or []
                if not function_calls:
                    break

                function_responses = []
                for fc in function_calls:
                    args = dict(fc.args or {})
                    result = await self._execute_tool(fc.name, args)
                    tool_results.append({"name": fc.name, "arguments": args, "result": result})
                    function_responses.append(
                        types.Part.from_function_response(name=fc.name, response={"result": result})
                    )

                response = await chat.send_message(function_responses)

            return {
                "response": response.text or "I couldn't produce an answer from the available data.",
                "tool_calls": tool_results,
                "data_confidence": self._calculate_confidence(tool_results),
                "sources": self._extract_sources(tool_results)
            }

        except Exception as e:
            return {
                "response": f"Error: {str(e)}. Please try rephrasing your question.",
                "tool_calls": [],
                "data_confidence": 0,
                "sources": [],
                "error": str(e)
            }

    async def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool in a worker thread (database access is blocking)"""
        handlers = {
            "query_vessel_intel": (self._query_vessel_intel, {"mmsi", "vessel_type", "timeframe", "limit"}),
            "query_pollution_data": (self._query_pollution_data, {"indicator", "severity", "timeframe", "limit"}),
            "get_mpa_compliance": (self._get_mpa_compliance, {"mpa_name", "metric_type"}),
        }
        if function_name not in handlers:
            return {"error": f"Unknown function: {function_name}"}

        handler, allowed = handlers[function_name]
        # The model may invent argument names; passing them through would raise TypeError
        kwargs = {k: v for k, v in arguments.items() if k in allowed}
        try:
            return await asyncio.to_thread(handler, **kwargs)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _clamp_limit(limit: Any) -> int:
        try:
            return max(1, min(int(limit), 100))
        except (ValueError, TypeError):
            return 50

    def _query_vessel_intel(self, mmsi=None, vessel_type=None, timeframe="current", limit=50):
        """Query vessels using SessionLocal for proper session management"""
        db = SessionLocal()
        try:
            query = select(VesselTrack)

            if mmsi:
                # Handle both string and int MMSI
                try:
                    mmsi_int = int(mmsi)
                    query = query.where(VesselTrack.mmsi == mmsi_int)
                except (ValueError, TypeError):
                    pass

            if vessel_type:
                try:
                    query = query.where(VesselTrack.vessel_type == VesselType(str(vessel_type).upper()))
                except ValueError:
                    return {"error": f"Unknown vessel_type '{vessel_type}'"}

            # Add timeframe filter
            if timeframe == "current":
                query = query.where(VesselTrack.timestamp > datetime.utcnow() - timedelta(hours=24))
            elif timeframe == "week":
                query = query.where(VesselTrack.timestamp > datetime.utcnow() - timedelta(days=7))

            query = query.order_by(VesselTrack.timestamp.desc()).limit(self._clamp_limit(limit))
            vessels = db.exec(query).all()

            return {
                "total_vessels": len(vessels),
                "vessels": [{
                    "mmsi": v.mmsi,
                    "type": v.vessel_type.value if v.vessel_type else None,
                    "timestamp": str(v.timestamp),
                    "is_dark": v.is_dark,
                    "risk_score": v.risk_score
                } for v in vessels[:10]],
                "source": "BlueGuard AIS Database"
            }
        finally:
            db.close()

    def _query_pollution_data(self, indicator="all", severity=None, timeframe="current", limit=50):
        """Query pollution using SessionLocal for proper session management"""
        db = SessionLocal()
        try:
            query = select(PollutionEvent)

            if indicator and str(indicator).lower() != "all":
                try:
                    query = query.where(PollutionEvent.type == PollutionType(str(indicator).upper()))
                except ValueError:
                    return {"error": f"Unknown pollution indicator '{indicator}'"}

            if severity:
                # severity is a float in the model, convert if needed
                try:
                    severity_float = float(severity)
                    query = query.where(PollutionEvent.severity >= severity_float)
                except (ValueError, TypeError):
                    pass

            # Add timeframe filter
            if timeframe == "current":
                query = query.where(PollutionEvent.detected_at > datetime.utcnow() - timedelta(days=7))
            elif timeframe == "month":
                query = query.where(PollutionEvent.detected_at > datetime.utcnow() - timedelta(days=30))

            query = query.order_by(PollutionEvent.detected_at.desc()).limit(self._clamp_limit(limit))
            events = db.exec(query).all()

            return {
                "total_events": len(events),
                "events": [{
                    "type": e.type.value if e.type else None,
                    "severity": e.severity,
                    "detected_at": str(e.detected_at),
                    "confidence": e.confidence
                } for e in events[:10]],
                "source": "Copernicus Satellite Data"
            }
        finally:
            db.close()

    def _get_mpa_compliance(self, mpa_name=None, metric_type="all"):
        """Get MPA data using SessionLocal for proper session management"""
        db = SessionLocal()
        try:
            query = select(MarineProtectedArea)

            if mpa_name:
                query = query.where(MarineProtectedArea.name.ilike(f"%{mpa_name}%"))

            mpas = db.exec(query).all()

            return {
                "total_mpas": len(mpas),
                "mpas": [{
                    "name": m.name,
                    "designation": m.designation,
                    "country": m.country,
                    "iucn_category": m.iucn_category
                } for m in mpas[:10]],
                "source": "BlueGuard MPA Database"
            }
        finally:
            db.close()

    def _calculate_confidence(self, tool_results):
        """Calculate confidence"""
        if not tool_results:
            return 100
        has_errors = any("error" in r.get("result", {}) for r in tool_results)
        return 50 if has_errors else 90

    def _extract_sources(self, tool_results):
        """Extract sources"""
        sources = set()
        for r in tool_results:
            source = r.get("result", {}).get("source")
            if source:
                sources.add(source)
        return list(sources) if sources else ["MIA Knowledge Base"]


# Global instance
mia = MarineIntelligenceAssistant()
