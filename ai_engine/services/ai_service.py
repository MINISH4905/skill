import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from services.memory_service import memory_service
from services.task_templates import build_task
from services.hash_service import generate_task_hash

logger = logging.getLogger("SkillForge-AI")

# Lazy optional transformer (non-blocking when unused)
_tokenizer = None
_model = None
_device = None


def _lazy_model():
    global _tokenizer, _model, _device
    if _model is not None:
        return _tokenizer, _model, _device
    if os.getenv("SKILLFORGE_DISABLE_LLM", "").lower() in ("1", "true", "yes"):
        return None, None, None
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        name = os.getenv("SKILLFORGE_MODEL_NAME", "google/flan-t5-small")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading %s onto %s (lazy)...", name, device)
        tok = AutoTokenizer.from_pretrained(name)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(name).to(device)
        _tokenizer, _model, _device = tok, mdl, device
        return _tokenizer, _model, _device
    except Exception as e:
        logger.warning("LLM lazy init skipped: %s", e)
        return None, None, None


async def _generate_flavor_sentence(prompt: str, temperature: float) -> str:
    tok, mdl, device = _lazy_model()
    if not mdl:
        return ""

    def _run():
        import torch

        inputs = tok(prompt, return_tensors="pt", max_length=256, truncation=True).to(device)
        out = mdl.generate(
            **inputs,
            max_length=128,
            temperature=max(0.1, min(1.5, temperature)),
            do_sample=True,
        )
        return tok.decode(out[0], skip_special_tokens=True)

    return await asyncio.to_thread(_run)


class AIService:
    async def generate_task(
        self,
        *,
        tier: str,
        topic: str,
        level: int,
        domain: str,
        target_difficulty: int,
        season_id: int,
        seed: Optional[int] = None,
        temperature: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Production path: seed-based templates + memory de-duplication + optional LLM flavor text.
        """
        max_attempts = 7
        attempt = 0
        effective_seed = seed

        while attempt < max_attempts:
            base = build_task(
                domain=domain,
                tier=tier,
                level=level,
                season_id=season_id,
                target_difficulty=target_difficulty,
                seed=effective_seed,
            )

            desc = base["description"]
            title = base["title"]

            flavor_prompt = (
                f"Rewrite in one sentence a coding challenge context for {domain} about: {title}. "
                f"No JSON, no code, plain English only."
            )
            flavor = await _generate_flavor_sentence(flavor_prompt, temperature + attempt * 0.05)
            if flavor:
                desc = f"{desc}\n\nContext: {flavor.strip()}"

            content_hash = generate_task_hash(title, desc, base["starter_code"])

            task_data: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": desc,
                "starter_code": base["starter_code"],
                "test_cases": base["test_cases"],
                "difficulty_score": int(base["difficulty_score"]),
                "hints": base.get("hints", []),
                "explanation": base.get("explanation", ""),
                "type": base.get("type", "code_complete"),
                "solution": base.get("solution", ""),
                "domain": domain.lower().strip(),
                "content_hash": content_hash,
            }

            if memory_service.is_scenario_unique(desc):
                memory_service.add_scenario({**task_data, "problem": desc})
                logger.info(
                    "[%s] Generated task '%s' (L%s, attempt %s)",
                    domain.upper(),
                    title,
                    level,
                    attempt + 1,
                )
                return task_data

            attempt += 1
            # Perturb seed / noise so the next template differs
            effective_seed = (effective_seed or (season_id * 100_000 + level * 13)) + 17 * attempt

        # Should be rare: return last built task even if fuzzy collision (hash still unique per Django)
        memory_service.add_scenario({**task_data, "problem": desc})
        return task_data


ai_service = AIService()
