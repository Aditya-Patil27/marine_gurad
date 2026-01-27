"""
Marine Intelligence Assistant (MIA) - Chatbot Service
High-precision analytical agent for maritime data analysis using Google Gemini
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import google.generativeai as genai
from sqlmodel import Session, select
from app.config import settings
from app.models.vessel import VesselTrack
from app.models.pollution import PollutionEvent
from app.models.mpa import MarineProtectedArea
from app.database import SessionLocal


class MarineIntelligenceAssistant:
    """MIA - Marine Intelligence Assistant with Google Gemini"""

    def __init__(self):
        self._model = None
        self._configured = False
        self.tools = self._define_tools()

    def _ensure_configured(self):
        """Lazily configure Gemini API to avoid startup crashes if key is missing"""
        if self._configured:
            return

        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY must be set to use the MIA chatbot. "
                "Please configure it in your .env file."
            )

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            system_instruction=self._build_system_prompt()
        )
        self._configured = True

    @property
    def model(self):
        """Get the Gemini model, configuring on first access"""
        self._ensure_configured()
        return self._model

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

    def _define_tools(self) -> List[Any]:
        """Define Gemini function calling tools"""
        return [
            genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(
                        name="query_vessel_intel",
                        description="Get vessel AIS data and positions",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "mmsi": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "vessel_type": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "timeframe": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER)
                            }
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="query_pollution_data",
                        description="Retrieve pollution events",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "indicator": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "severity": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "timeframe": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER)
                            }
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="get_mpa_compliance",
                        description="Get Marine Protected Area data",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "mpa_name": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "metric_type": genai.protos.Schema(type=genai.protos.Type.STRING)
                            }
                        )
                    )
                ]
            )
        ]

    async def process_message(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process user message with conversation memory"""
        try:
            # Convert conversation history to Gemini format
            gemini_history = []
            if conversation_history:
                for entry in conversation_history:
                    role = "user" if entry.get("role") == "user" else "model"
                    gemini_history.append({
                        "role": role,
                        "parts": [{"text": entry.get("content", "")}]
                    })

            # Start chat with history to preserve context
            chat = self.model.start_chat(history=gemini_history)
            response = chat.send_message(message, tools=self.tools)

            # Check for function calls
            function_calls = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_calls.append({'name': fc.name, 'args': dict(fc.args)})

            if not function_calls:
                return {
                    "response": response.text,
                    "tool_calls": [],
                    "data_confidence": 100,
                    "sources": ["MIA Knowledge Base"]
                }

            # Execute tools
            tool_results = []
            for fc in function_calls:
                result = await self._execute_tool(fc['name'], fc['args'])
                tool_results.append({"name": fc['name'], "arguments": fc['args'], "result": result})

            # Get final response
            function_responses = [
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=r['name'],
                        response={"result": r['result']}
                    )
                )
                for r in tool_results
            ]

            final_response = chat.send_message(genai.protos.Content(parts=function_responses))

            return {
                "response": final_response.text,
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
        """Execute tool"""
        if function_name == "query_vessel_intel":
            return await self._query_vessel_intel(**arguments)
        elif function_name == "query_pollution_data":
            return await self._query_pollution_data(**arguments)
        elif function_name == "get_mpa_compliance":
            return await self._get_mpa_compliance(**arguments)
        return {"error": f"Unknown function: {function_name}"}

    async def _query_vessel_intel(self, mmsi=None, vessel_type=None, timeframe="current", limit=50):
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
                query = query.where(VesselTrack.vessel_type == vessel_type)

            # Add timeframe filter
            if timeframe == "current":
                query = query.where(VesselTrack.timestamp > datetime.utcnow() - timedelta(hours=24))
            elif timeframe == "week":
                query = query.where(VesselTrack.timestamp > datetime.utcnow() - timedelta(days=7))

            query = query.limit(limit)
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

    async def _query_pollution_data(self, indicator="all", severity=None, timeframe="current", limit=50):
        """Query pollution using SessionLocal for proper session management"""
        db = SessionLocal()
        try:
            query = select(PollutionEvent)

            if indicator != "all":
                query = query.where(PollutionEvent.type == indicator)

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

            query = query.limit(limit)
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

    async def _get_mpa_compliance(self, mpa_name=None, metric_type="all"):
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
