"""LLM operations and health endpoints."""

from fastapi import APIRouter

from app.services.llm_router import local_llm_status

router = APIRouter(prefix="/api/llm", tags=["LLM"])


@router.get("/local-status")
def get_local_llm_status():
    """
    Verify the API container can reach host Ollama and see configured Gemma models.
    """
    return local_llm_status()
