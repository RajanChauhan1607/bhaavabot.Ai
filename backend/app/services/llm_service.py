import os
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.models.schemas import (
    StructuredCompanionResponse,
    ChatMessage,
    ResponseStrategy,
    ConversationState,
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
)
from app.prompts.empathy_companion import compose_prompt, build_system_prompt
from app.services.context_builder import ContextBuilder, build_conversation_state
from app.services.response_planner import plan_response, DEFAULT_STRATEGY, get_intent_description
from app.services.output_validator import (
    validate_and_repair_output,
    validate_output,
    get_deterministic_safe_fallback,
)

logger = logging.getLogger("bhaavabot.llm")

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        user_message: str,
        detected_emotion: str,
        pacing: str,
        communication_style: str,
        response_plan: Optional[ResponseStrategy] = None,
        safety_level: str = "NORMAL"
    ) -> StructuredCompanionResponse:
        pass

class GeminiProvider(BaseLLMProvider):
    """Integrates Gemini using Google GenAI SDK with multi-model fallback and structured output validation."""
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key
        self.model_name = model_name or "gemini-3.6-flash"
        self.client = None
        if api_key and os.getenv("TESTING") != "1" and not os.getenv("PYTEST_CURRENT_TEST"):
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                logger.info(f"Initialized GeminiProvider with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}")

    async def generate_response(
        self,
        prompt: str,
        user_message: str,
        detected_emotion: str,
        pacing: str,
        communication_style: str,
        response_plan: Optional[ResponseStrategy] = None,
        safety_level: str = "NORMAL"
    ) -> StructuredCompanionResponse:
        if not self.client:
            raise RuntimeError("Gemini client is not initialized or API key is missing.")

        active_strategy = response_plan or ResponseStrategy(
            objective=PlanObjective.LISTEN,
            tone=communication_style,
            pacing=pacing,
            validation_level=ValidationLevel.HIGH,
            solution_mode=SolutionMode.OFF,
            information_density=InformationDensity.MODERATE
        )

        try:
            # Candidate models with automatic multi-model fallback resilience
            candidate_models = [self.model_name] + [
                m for m in ["gemini-3.6-flash", "gemini-3-flash-preview", "gemini-flash-latest"]
                if m != self.model_name
            ]
            response = None
            last_err = None
            for model_id in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "temperature": 0.7,
                        }
                    )
                    if response and response.text:
                        self.model_name = model_id
                        break
                except Exception as m_err:
                    last_err = m_err
                    logger.warning(f"Error calling {model_id}: {m_err}. Trying next candidate model...")

            if not response or not response.text:
                raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")

            raw_text = response.text.strip()
            
            # Step 1: Validate generated output
            is_valid, reason, structured = validate_output(
                raw_text=raw_text,
                strategy=active_strategy,
                detected_emotion=detected_emotion,
                emotion_confidence=0.85,
                emotion_intensity=0.5,
                safety_level=safety_level
            )
            if is_valid and structured is not None:
                return structured

            # Step 2: If invalid, attempt at most ONE controlled repair
            logger.warning(f"Output validation failed ({reason}). Attempting at most ONE controlled repair.")
            repair_prompt = f"""Your previous response was rejected by safety validation for reason: {reason}.
Please regenerate the empathetic response in valid JSON matching:
{{
  "message": "<safe empathetic message strictly matching the objective>",
  "needs_follow_up": false,
  "suggested_action": null
}}
CRITICAL RULES:
- Do NOT diagnose any condition.
- Do NOT pretend to be a doctor, therapist, or clinician.
- Do NOT give medication or dosage instructions.
- Do NOT foster emotional dependency.
- Do NOT give false guarantees.
- Strictly adhere to objective: {active_strategy.objective.value}

Original user message: "{user_message}"
"""
            try:
                repair_res = self.client.models.generate_content(
                    model=self.model_name,
                    contents=repair_prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.5,
                    }
                )
                repaired_text = repair_res.text.strip() if repair_res.text else ""
                repaired_is_valid, _, repaired_structured = validate_output(
                    raw_text=repaired_text,
                    strategy=active_strategy,
                    detected_emotion=detected_emotion,
                    emotion_confidence=0.85,
                    emotion_intensity=0.5,
                    safety_level=safety_level
                )
                if repaired_is_valid and repaired_structured is not None:
                    logger.info("Controlled repair successful.")
                    return repaired_structured
            except Exception as repair_err:
                logger.warning(f"Controlled repair attempt encountered an error: {repair_err}")

            # Step 3: If repair failed or re-validation failed, return deterministic safe fallback
            logger.warning("Repair unsuccessful. Returning deterministic safe fallback.")
            return get_deterministic_safe_fallback(
                strategy=active_strategy,
                detected_emotion=detected_emotion,
                safety_level=safety_level,
                emotion_confidence=0.85,
                emotion_intensity=0.5
            )
        except Exception as e:
            logger.error(f"Error during Gemini generation: {e}")
            raise e

class RuleBasedEmpatheticProvider(BaseLLMProvider):
    """
    High-fidelity offline / fallback empathetic response generator.
    Prioritizes explicit user requests (recommendations, actionable advice, explanations)
    before generic conversational reflections.
    """
    async def generate_response(
        self,
        prompt: str,
        user_message: str,
        detected_emotion: str,
        pacing: str,
        communication_style: str,
        response_plan: Optional[ResponseStrategy] = None,
        safety_level: str = "NORMAL"
    ) -> StructuredCompanionResponse:
        active_strategy = response_plan or ResponseStrategy(
            objective=PlanObjective.LISTEN,
            tone=communication_style,
            pacing=pacing,
            validation_level=ValidationLevel.HIGH,
            solution_mode=SolutionMode.OFF,
            information_density=InformationDensity.MODERATE
        )

        effective_pacing = active_strategy.pacing
        effective_tone = active_strategy.tone
        msg_lower = user_message.lower()

        suggested_action = None

        # 1. Recommendations (Media, Audio, Music, Reading)
        if (
            any(w in msg_lower for w in ["listen", "music", "song", "podcast", "sound", "track", "ambient", "audio", "playlist", "read", "book", "suggest"])
            and active_strategy.objective in (PlanObjective.CALMING_SUPPORT, PlanObjective.INFORMATIONAL_SUPPORT, PlanObjective.REFLECT, PlanObjective.PROVIDE_GUIDANCE)
        ):
            reply = (
                "Here are three calming options to help you settle and reset:\n\n"
                "1. 'Weightless' by Marconi Union — ambient soundscape shown to significantly lower heart rate and cortisol.\n"
                "2. Gentle Lo-Fi Instrumental (e.g., Chillhop or Lofi Girl) — steady, soft rhythms that calm the mind without distracting lyrics.\n"
                "3. Natural Rainfall & Ocean Sounds — soothing ambient pink noise to ease mental tension and quiet busy thoughts.\n\n"
                "Would you like gentle ambient music or natural rainfall sounds?"
            )
            suggested_action = "recommend_media"

        # 2. Practical Guidance & Actionable Advice
        elif active_strategy.objective == PlanObjective.PROVIDE_GUIDANCE or any(w in msg_lower for w in ["practical advice", "actionable steps", "step by step", "break this freeze", "what should i do"]):
            if any(w in msg_lower for w in ["procrastinat", "focus", "freeze", "work", "study", "start"]):
                reply = (
                    "Here is a concrete 3-step action plan to break through the freeze and get started:\n\n"
                    "1. The 5-Minute Micro-Step: Choose the smallest possible piece of the task and commit to working on it for just 5 minutes with zero expectation of perfection.\n"
                    "2. Lower Cognitive Friction: Close all unrelated browser tabs and put your phone in another room to give your brain quiet focus.\n"
                    "3. Make an Imperfect First Pass: Give yourself permission to write a rough, messy draft. Editing something messy is always easier than facing a blank page."
                )
            else:
                reply = (
                    "Here are clear, actionable steps you can take right now:\n\n"
                    "1. Define the Immediate Priority: Identify the single most important next step, setting everything else aside for the next hour.\n"
                    "2. Break it Down: Divide that step into 2 or 3 tiny, bite-sized actions that each take under ten minutes.\n"
                    "3. Take the First Micro-Action: Focus purely on starting the first piece without worrying about the final outcome."
                )
            suggested_action = None

        # 3. Informational Support / Factual Explanations
        elif active_strategy.objective == PlanObjective.INFORMATIONAL_SUPPORT or any(w in msg_lower for w in ["what is", "can you explain", "explain to me"]):
            if "4-7-8" in msg_lower or "breathing" in msg_lower:
                reply = (
                    "4-7-8 breathing is an evidence-backed breathwork exercise that stimulates the parasympathetic nervous system:\n\n"
                    "1. Inhale quietly through your nose for 4 seconds.\n"
                    "2. Hold your breath gently for 7 seconds.\n"
                    "3. Exhale completely through your mouth with a soft whoosh for 8 seconds.\n\n"
                    "Repeating this 4 times helps decrease heart rate and reduce physical arousal."
                )
                suggested_action = "offer_breathing"
            elif any(w in msg_lower for w in ["mindfulness", "cbt", "grounding"]):
                reply = (
                    "Mindfulness is the practice of maintaining moment-by-moment awareness of our thoughts, feelings, bodily sensations, and surrounding environment with acceptance and without judgment. "
                    "It helps interrupt automatic worry loops by anchoring your focus back to tangible present reality."
                )
                suggested_action = None
            else:
                reply = (
                    "Here is clear context on that: understanding how your thoughts, nervous system, and emotional states interact is one of the most reliable ways to regain calm and focus. "
                    "When we name what we are experiencing, it shifts brain activity from reactive panic to intentional problem solving."
                )
                suggested_action = None

        # 4. Calming Support (Guided Breathing / Grounding)
        elif active_strategy.objective == PlanObjective.CALMING_SUPPORT:
            reply = (
                "Let's take a gentle pause to reset your nervous system together:\n\n"
                "1. Place one hand on your chest and one on your abdomen.\n"
                "2. Inhale slowly through your nose for 4 seconds, feeling your belly expand.\n"
                "3. Exhale smoothly through your mouth for 6 seconds.\n\n"
                "Would you like to try a quick 1-minute guided breathing rhythm together?"
            )
            suggested_action = "offer_breathing"

        # 5. Reflection
        elif active_strategy.objective == PlanObjective.REFLECT:
            reply = (
                "Taking a moment to pause and reflect can bring clarity to what you're carrying. "
                "A helpful prompt to consider: What is one thing currently within your control today, and what is one thing you can give yourself permission to set down?"
            )
            suggested_action = "recommend_media"

        # 6. Explicit Venting / Pure Listening (Solution mode OFF or objective LISTEN)
        elif active_strategy.solution_mode == SolutionMode.OFF or active_strategy.objective == PlanObjective.LISTEN:
            if detected_emotion in ["anxiety", "fear"]:
                reply = "I hear how heavy and unsettling this anxiety feels. You don't have to carry every worry at once. I'm right here listening."
            elif detected_emotion in ["stress"]:
                reply = "It sounds like you have been carrying far too much for too long. You can let it all out here—I'm here to listen without judgment."
            elif detected_emotion in ["loneliness", "sadness"]:
                reply = "Feeling lonely or down takes real courage to put into words. I'm right here with you. Take all the time you need."
            elif detected_emotion in ["anger", "frustration"]:
                reply = "It makes complete sense that you're feeling so frustrated. It's completely valid to feel this way. I'm listening."
            else:
                reply = "I'm right here listening. Take all the time and space you need to share what's on your mind."

        # 7. Emotion-specific conversational responses
        elif detected_emotion in ["anxiety", "fear"]:
            if effective_tone == "direct":
                reply = "Anxiety is physically exhausting. Let's ground right now: unclench your hands and take one long, slow exhalation. What is one tangible thing you can pause right now?"
            elif effective_tone == "patient_supportive":
                reply = "It makes complete sense that you're feeling so uneasy right now. Let's take this very slowly, one small breath at a time. Would you like to tell me what part feels heaviest?"
            else:
                reply = "I hear how heavy and unsettling this anxiety feels. You don't have to carry every worry at once. Let's take a slow breath together. Would it help to talk through what feels heaviest?"

        elif detected_emotion in ["stress"]:
            if effective_tone == "direct":
                reply = "You are carrying an overload of demands. Let's separate what must be done today from what can wait. What is the single biggest stressor on your plate?"
            else:
                reply = "It sounds like you have been carrying far too much for too long. Your mind and body deserve a pause. What is one small thing we could take off your shoulders for the next hour?"

        elif detected_emotion in ["loneliness", "sadness"]:
            if effective_tone == "direct":
                reply = "Feeling isolated and down takes real energy. I am here to listen objectively. What has brought this sadness to the surface today?"
            elif effective_tone == "patient_supportive":
                reply = "Feeling lonely or sad can feel like a quiet ache that nobody else notices. You are not alone in this room right now. Take all the time you need to put it into words."
            else:
                reply = "That sounds so deeply tender and heavy to bear. It takes courage to acknowledge these feelings. I'm right here with you—what has been taking up space in your thoughts?"

        elif detected_emotion in ["anger", "frustration"]:
            if effective_tone == "direct":
                reply = "Frustration is valid data about an unmet need or boundary crossed. Let's unpack the root issue directly: what crossed the line?"
            else:
                reply = "That sounds genuinely maddening, and it makes complete sense that your frustration is running high. I'm in your corner—vent as much as you need."

        elif detected_emotion in ["happiness", "excitement"]:
            reply = "I'm genuinely glad to feel this lightness in your day. Celebrating moments of joy and relief matters so much. Tell me all about it!"

        else:
            if effective_tone == "direct":
                reply = "I am listening. Feel free to lay out what is happening, and we can look at it clearly together."
            else:
                reply = "I am here with you. Whatever has been unfolding, you don't have to navigate it in silence. What is sitting with you most right now?"

        # Validate through output validator for consistency
        _, structured = validate_and_repair_output(
            raw_text=json.dumps({"message": reply, "needs_follow_up": False, "suggested_action": suggested_action}),
            strategy=active_strategy,
            detected_emotion=detected_emotion,
            emotion_confidence=0.85,
            emotion_intensity=0.5,
            safety_level=safety_level
        )
        return structured

class LLMService:
    """Orchestrates LLM providers with automatic fallback resilience and Phase 2 Prompt Composer."""
    def __init__(self):
        self.gemini_provider = GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
        self.fallback_provider = RuleBasedEmpatheticProvider()

    async def generate_reply(
        self,
        user_message: str,
        profile_type: str = "PROFILE_A",
        communication_style: str = "warm",
        preferred_pacing: str = "normal",
        emotional_style: str = "responsive",
        cognitive_style: str = "collaborative",
        current_emotion: str = "neutral",
        emotion_intensity: float = 0.5,
        safety_level: str = "NORMAL",
        user_theme: str = "General Support",
        user_preferences: str = "Default",
        recent_messages: Optional[List[ChatMessage]] = None,
        response_plan: Optional[ResponseStrategy] = None,
        conversation_state: Optional[ConversationState] = None
    ) -> StructuredCompanionResponse:
        # Determine effective strategy
        strategy = response_plan or plan_response(
            user_message=user_message,
            safety_level=safety_level,
            detected_emotion=current_emotion,
            emotion_intensity=emotion_intensity,
            user_theme=user_theme
        )

        # Determine effective conversational state
        state = conversation_state or build_conversation_state(
            current_emotion=current_emotion,
            emotion_intensity=emotion_intensity,
            emotion_confidence=0.8,
            safety_level=safety_level,
            current_intent=get_intent_description(user_message, user_theme),
            strategy=strategy,
            recent_messages=recent_messages
        )

        # Build bounded history with ContextBuilder (never sends unlimited DB records)
        history_text = ContextBuilder.format_recent_history(recent_messages)
        profile_meta = f"Profile Type: {profile_type}"
        prefs_text = str(user_preferences)

        # Phase 2: Modular Prompt Composer
        prompt = compose_prompt(
            user_message=user_message,
            strategy=strategy,
            state=state,
            recent_history_text=history_text,
            user_preferences_text=prefs_text,
            profile_metadata_text=profile_meta
        )

        # Try Gemini first if API key is provided and not in offline testing mode
        if (
            settings.GEMINI_API_KEY
            and self.gemini_provider.client
            and os.getenv("TESTING") != "1"
            and not os.getenv("PYTEST_CURRENT_TEST")
        ):
            try:
                return await self.gemini_provider.generate_response(
                    prompt=prompt,
                    user_message=user_message,
                    detected_emotion=current_emotion,
                    pacing=strategy.pacing,
                    communication_style=strategy.tone,
                    response_plan=strategy,
                    safety_level=safety_level
                )
            except Exception as e:
                logger.warning(f"Gemini generation failed, falling back to rule-based engine: {e}")

        # Graceful fallback provider
        return await self.fallback_provider.generate_response(
            prompt=prompt,
            user_message=user_message,
            detected_emotion=current_emotion,
            pacing=strategy.pacing,
            communication_style=strategy.tone,
            response_plan=strategy,
            safety_level=safety_level
        )

llm_service = LLMService()
