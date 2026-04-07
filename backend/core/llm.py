# import asyncio
# import json
# import logging
# from typing import Optional, Dict, Any, AsyncGenerator
# import aiohttp
# from core.config import settings

# logger = logging.getLogger(__name__)

# class LLMService:
#     def __init__(self):
#         self.model = settings.LLM_MODEL
#         self.base_url = settings.LLM_BASE_URL
#         self.temperature = settings.LLM_TEMPERATURE
#         self.max_tokens = settings.LLM_MAX_TOKENS
        
#     async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
#         """Make async HTTP request to Ollama API"""
#         url = f"{self.base_url}/api/{endpoint}"
        
#         async with aiohttp.ClientSession() as session:
#             try:
#                 async with session.post(url, json=data) as response:
#                     if response.status == 200:
#                         return await response.json()
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"Ollama API error {response.status}: {error_text}")
#             except aiohttp.ClientError as e:
#                 raise Exception(f"Connection error to Ollama: {str(e)}")

#     async def generate_response(self, 
#                               prompt: str, 
#                               system_prompt: Optional[str] = None,
#                               temperature: Optional[float] = None,
#                               max_tokens: Optional[int] = None) -> str:
#         """Generate a single response from the LLM"""
        
#         # Prepare the prompt
#         messages = []
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": prompt})
        
#         # Prepare request data
#         data = {
#             "model": self.model,
#             "messages": messages,
#             "stream": False,
#             "options": {
#                 "temperature": temperature or self.temperature,
#                 "num_predict": max_tokens or self.max_tokens
#             }
#         }
        
#         try:
#             response = await self._make_request("chat", data)
#             return response.get("message", {}).get("content", "")
#         except Exception as e:
#             logger.error(f"Error generating LLM response: {str(e)}")
#             raise Exception(f"Failed to generate response: {str(e)}")

#     async def generate_stream(self, 
#                             prompt: str, 
#                             system_prompt: Optional[str] = None,
#                             temperature: Optional[float] = None,
#                             max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
#         """Generate streaming response from the LLM"""
        
#         # Prepare the prompt
#         messages = []
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": prompt})
        
#         # Prepare request data
#         data = {
#             "model": self.model,
#             "messages": messages,
#             "stream": True,
#             "options": {
#                 "temperature": temperature or self.temperature,
#                 "num_predict": max_tokens or self.max_tokens
#             }
#         }
        
#         url = f"{self.base_url}/api/chat"
        
#         async with aiohttp.ClientSession() as session:
#             try:
#                 async with session.post(url, json=data) as response:
#                     if response.status != 200:
#                         error_text = await response.text()
#                         raise Exception(f"Ollama API error {response.status}: {error_text}")
                    
#                     async for line in response.content:
#                         if line:
#                             try:
#                                 chunk = json.loads(line.decode('utf-8'))
#                                 if 'message' in chunk and 'content' in chunk['message']:
#                                     content = chunk['message']['content']
#                                     if content:
#                                         yield content
                                
#                                 # Check if this is the last chunk
#                                 if chunk.get('done', False):
#                                     break
#                             except json.JSONDecodeError:
#                                 continue
                                
#             except aiohttp.ClientError as e:
#                 logger.error(f"Streaming error: {str(e)}")
#                 raise Exception(f"Failed to stream response: {str(e)}")

#     async def summarize_text(self, text: str, max_length: int = 200) -> str:
#         """Summarize a piece of text"""
#         system_prompt = f"""You are a helpful assistant that creates concise summaries. 
#         Summarize the following text in no more than {max_length} words. 
#         Focus on the key points and main ideas."""
        
#         return await self.generate_response(text, system_prompt=system_prompt)

#     async def answer_question(self, question: str, context: str) -> str:
#         """Answer a question based on provided context"""
#         system_prompt = """You are a helpful AI assistant. Answer the user's question based on the provided context. 
#         If the answer cannot be found in the context, say so clearly. Be accurate and concise."""
        
#         prompt = f"""Context: {context}

# Question: {question}

# Answer:"""
        
#         return await self.generate_response(prompt, system_prompt=system_prompt)

#     async def check_model_availability(self) -> bool:
#         """Check if the specified model is available"""
#         try:
#             data = {"name": self.model}
#             response = await self._make_request("show", data)
#             return True
#         except Exception as e:
#             logger.error(f"Model {self.model} not available: {str(e)}")
#             return False

# # Global LLM service instance
# llm_service = LLMService()


"""Centralized LLM service with OpenAI/Ollama toggle support"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import aiohttp
from langchain_ollama import OllamaLLM, ChatOllama
from langchain_openai import ChatOpenAI
from core.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM service supporting both Ollama and OpenAI
    Automatically switches based on settings.LLM_PROVIDER
    """
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
        # Initialize based on provider
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "":
                raise ValueError("OPENAI_API_KEY not set in environment")
            
            self.model = settings.OPENAI_MODEL
            self.llm = ChatOpenAI(
                model=self.model,
                api_key=settings.OPENAI_API_KEY,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=settings.LLM_TIMEOUT
            )
            logger.info(f"✅ LLMService initialized with OpenAI: {self.model}")
            
        elif self.provider == "ollama":
            self.model = settings.LLM_MODEL
            self.base_url = settings.LLM_BASE_URL
            self.llm = ChatOllama(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature,
            )
            logger.info(f"✅ LLMService initialized with Ollama: {self.model}")
            
        else:
            raise ValueError(f"Invalid LLM_PROVIDER: {self.provider}. Must be 'ollama' or 'openai'")
    
    
    async def _make_request_ollama(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to Ollama API (backward compatibility)"""
        url = f"{self.base_url}/api/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error {response.status}: {error_text}")
            except aiohttp.ClientError as e:
                raise Exception(f"Connection error to Ollama: {str(e)}")


    async def generate_response(self, 
                              prompt: str, 
                              system_prompt: Optional[str] = None,
                              temperature: Optional[float] = None,
                              max_tokens: Optional[int] = None) -> str:
        """
        Generate a single response from the LLM
        Works with both OpenAI and Ollama
        """
        
        # Use custom temperature/max_tokens if provided
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        try:
            if self.provider == "openai":
                # ✅ OpenAI path using LangChain
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Temporarily override settings if custom values provided
                if temperature or max_tokens:
                    temp_llm = ChatOpenAI(
                        model=self.model,
                        api_key=settings.OPENAI_API_KEY,
                        temperature=temp,
                        max_tokens=max_tok,
                        timeout=settings.LLM_TIMEOUT
                    )
                    response = await temp_llm.ainvoke(messages)
                else:
                    response = await self.llm.ainvoke(messages)
                
                return response.content
                
            else:  # ollama
                # ✅ Ollama path - keep existing logic
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                data = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temp,
                        "num_predict": max_tok
                    }
                }
                
                response = await self._make_request_ollama("chat", data)
                return response.get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Error generating LLM response ({self.provider}): {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")


    async def generate_stream(self, 
                            prompt: str, 
                            system_prompt: Optional[str] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from the LLM
        Works with both OpenAI and Ollama
        """
        
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            if self.provider == "openai":
                # ✅ OpenAI streaming
                if temperature or max_tokens:
                    temp_llm = ChatOpenAI(
                        model=self.model,
                        api_key=settings.OPENAI_API_KEY,
                        temperature=temp,
                        max_tokens=max_tok,
                        timeout=settings.LLM_TIMEOUT,
                        streaming=True
                    )
                    stream = temp_llm.astream(messages)
                else:
                    # Need to recreate with streaming=True
                    streaming_llm = ChatOpenAI(
                        model=self.model,
                        api_key=settings.OPENAI_API_KEY,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        timeout=settings.LLM_TIMEOUT,
                        streaming=True
                    )
                    stream = streaming_llm.astream(messages)
                
                async for chunk in stream:
                    if chunk.content:
                        yield chunk.content
                        
            else:  # ollama
                # ✅ Ollama streaming - keep existing logic
                data = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temp,
                        "num_predict": max_tok
                    }
                }
                
                url = f"{self.base_url}/api/chat"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Ollama API error {response.status}: {error_text}")
                        
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line.decode('utf-8'))
                                    if 'message' in chunk and 'content' in chunk['message']:
                                        content = chunk['message']['content']
                                        if content:
                                            yield content
                                    
                                    if chunk.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                                    
        except Exception as e:
            logger.error(f"Streaming error ({self.provider}): {str(e)}")
            raise Exception(f"Failed to stream response: {str(e)}")


    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize a piece of text"""
        system_prompt = f"""You are a helpful assistant that creates concise summaries. 
        Summarize the following text in no more than {max_length} words. 
        Focus on the key points and main ideas."""
        
        return await self.generate_response(text, system_prompt=system_prompt)


    async def answer_question(self, question: str, context: str) -> str:
        """Answer a question based on provided context"""
        system_prompt = """You are a helpful AI assistant. Answer the user's question based on the provided context. 
        If the answer cannot be found in the context, say so clearly. Be accurate and concise."""
        
        prompt = f"""Context: {context}

Question: {question}

Answer:"""
        
        return await self.generate_response(prompt, system_prompt=system_prompt)


    async def check_model_availability(self) -> bool:
        """Check if the specified model is available"""
        try:
            if self.provider == "openai":
                # ✅ For OpenAI, try a simple test request
                test_response = await self.generate_response(
                    "Say 'OK'", 
                    max_tokens=5
                )
                return True
                
            else:  # ollama
                # ✅ Keep existing Ollama check
                data = {"name": self.model}
                response = await self._make_request_ollama("show", data)
                return True
                
        except Exception as e:
            logger.error(f"Model {self.model} ({self.provider}) not available: {str(e)}")
            return False


# ✅ FACTORY FUNCTIONS for backward compatibility

def get_llm(use_chat_model: bool = True):
    """
    Get synchronous LLM instance (for upload.py, non-async contexts)
    
    Args:
        use_chat_model: Not used for OpenAI (always chat), 
                       For Ollama: True=ChatOllama, False=OllamaLLM
    
    Returns:
        LLM instance ready for .invoke()
    """
    try:
        if settings.LLM_PROVIDER.lower() == "openai":
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT
            )
            logger.info(f"✅ get_llm() created: OpenAI ({settings.OPENAI_MODEL})")
            return llm
            
        elif settings.LLM_PROVIDER.lower() == "ollama":
            if use_chat_model:
                llm = ChatOllama(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_BASE_URL,
                    temperature=settings.LLM_TEMPERATURE,
                )
            else:
                llm = OllamaLLM(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_BASE_URL,
                    temperature=settings.LLM_TEMPERATURE,
                )
            logger.info(f"✅ get_llm() created: Ollama ({settings.LLM_MODEL})")
            return llm
            
        else:
            raise ValueError(f"Invalid LLM_PROVIDER: {settings.LLM_PROVIDER}")
            
    except Exception as e:
        logger.error(f"❌ Failed to create LLM: {e}")
        raise


def get_llm_async():
    """
    Get async LLM service instance (for response_agent.py)
    Returns the full LLMService class with async methods
    """
    return LLMService()


# ✅ Global LLM service instance (backward compatibility)
llm_service = LLMService()


# ✅ Export commonly used functions
__all__ = [
    'LLMService',
    'llm_service',
    'get_llm',
    'get_llm_async'
]
