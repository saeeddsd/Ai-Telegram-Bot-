# ai_handler.py
from openai import OpenAI
import json
from typing import Dict, Tuple, Optional
import time
import logging
import re

from config import (
    OPENAI_API_KEY, OPENAI_BASE_URL, AI_SYSTEM_PROMPT,
    AI_TIMEOUT, AI_MAX_TOKENS, AI_TEMPERATURE, CONVERSATION_CONTEXT_SIZE
)

logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=AI_TIMEOUT,
            max_retries=2
        )
        self.model = None
        self.fallback_responses = [
            "ببخشید، الان نمی‌تونم جواب بدم. یه لحظه دیگه امتحان کن.",
            "یه مشکل کوچیک پیش اومده. می‌تونی سوالت رو دوباره بپرسی؟",
            "متأسفم، الان خیلی شلوغه. چند لحظه دیگه تلاش کن."
        ]
    
    def _get_model(self) -> str:
        if self.model:
            return self.model
            
        for attempt in range(3):
            try:
                models = self.client.models.list()
                priority = ["gpt-5.4-nano", "gpt-5.4-mini", "gpt-4o-mini", "gpt-5", "gpt-4o", "gpt-3.5-turbo"]
                available = [m.id.lower().strip() for m in models.data]
                
                for p in priority:
                    for a in available:
                        # رفع باگ: جلوگیری از انتخاب مدل اشتباه (مثل meta-llama-gpt-4o)
                        if a == p or a.startswith(p + "-"):
                            self.model = a
                            logger.info(f"✅ مدل انتخاب شد: {a}")
                            return a
                
                self.model = available[0] if available else "gpt-3.5-turbo"
                return self.model
            except Exception as e:
                logger.warning(f"⚠️ تلاش {attempt + 1} برای دریافت مدل ناموفق: {e}")
                if attempt < 2: time.sleep(2 ** attempt)
        
        return "gpt-3.5-turbo"

    def process_message(self, user_message: str, user_memories: Dict, 
                       conversation_history: list = None) -> Tuple[str, Optional[Dict]]:
        try:
            memory_str = self._format_memories(user_memories)
            # آی‌دی کاربر اینجا قرار ندارد. فقط حافظه و هیستوری ارسال می‌شود
            system_prompt = AI_SYSTEM_PROMPT.format(user_memories=memory_str)
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                for conv in conversation_history[-CONVERSATION_CONTEXT_SIZE:]:
                    messages.append({"role": "user", "content": conv['user']})
                    messages.append({"role": "assistant", "content": conv['bot']})
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self._get_model(),
                messages=messages,
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_response(response.choices[0].message.content)
            
            if result:
                reply = result.get('reply', self._get_fallback_response())
                memory_updates = result.get('memory_updates', {})
                return reply, memory_updates if memory_updates else None
            else:
                return self._get_fallback_response(), None
            
        except Exception as e:
            logger.error(f"❌ خطای AI: {e}")
            return self._get_fallback_response(), None
    
    def _format_memories(self, memories: Dict) -> str:
        if not memories:
            return "(هیچ اطلاعاتی هنوز ذخیره نشده است)"
        return "\n".join([f"- {k}: {v}" for k, v in memories.items()])
    
    def _parse_response(self, content: str) -> Optional[Dict]:
        if not content:
            return None
            
        content = content.strip()
        # پاکسازی کدهای مارک‌داون احتمالی اطراف JSON
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("⚠️ خطا در پارس JSON، تلاش برای استخراج بلوک...")
            # رفع باگ فاجعه‌بار Regex قبلی: به جای گرفتن فقط ریپلای، کل بلوک JSON استخراج می‌شود
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return None
    
    def _get_fallback_response(self) -> str:
        import random
        return random.choice(self.fallback_responses)
    
    def health_check(self) -> bool:
        try:
            self.client.models.list()
            return True
        except:
            return False