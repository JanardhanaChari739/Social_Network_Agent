"""
Problem 1: B2B AI Agent Social Network - Multi-Stage Relevance Routing & Webhook Engine
Asama.ai Engineering Assignment Reference Implementation
"""

import os
import time
import json
import hmac
import hashlib
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl
import numpy as np


# ============================================================================
# 1. PYDANTIC SCHEMAS & API CONTRACTS
# ============================================================================

class AgentRegistrationRequest(BaseModel):
    company_name: str = Field(..., example="PhonePe")
    industry_category: str = Field(..., example="Payments & Fintech")
    webhook_url: str = Field(..., example="https://agent.phonepe.com/v1/network-events")
    interest_manifesto: str = Field(..., example="Interested in e-commerce promotions and food delivery festive discounts.")
    excluded_industries: List[str] = Field(default_factory=list)


class AgentProfile(BaseModel):
    id: UUID
    company_name: str
    industry_category: str
    webhook_url: str
    webhook_secret: str
    interest_manifesto: str
    interest_embedding: List[float]
    trust_score: float = 1.0
    is_active: bool = True
    excluded_industries: List[str] = Field(default_factory=list)


class PostCreateRequest(BaseModel):
    author_agent_id: UUID
    title: str = Field(..., example="Diwali Food Delivery Discount")
    content: str = Field(..., example="Swiggy offering flat 5% off on all delivery orders above ₹300 during Diwali week.")
    expires_at: Optional[datetime] = None


class CommentCreateRequest(BaseModel):
    author_agent_id: UUID
    content: str = Field(..., example="PhonePe will provide extra ₹50 cashback when users pay via PhonePe UPI.")


class MatchedCandidate(BaseModel):
    agent_id: UUID
    company_name: str
    webhook_url: str
    webhook_secret: str
    vector_score: float
    rerank_score: float


# ============================================================================
# 2. SIMULATED EMBEDDING & RERANKING SERVICES
# ============================================================================

class EmbeddingService:
    """Simulates text-embedding-3-small (1536 dims) with deterministic unit normalization."""

    @staticmethod
    def get_embedding(text: str, dim: int = 1536) -> List[float]:
        np.random.seed(abs(hash(text)) % (2**32))
        vec = np.random.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist()


class RerankingService:
    """Simulates Cross-Encoder / Fast LLM Judge scoring joint relevance."""

    @staticmethod
    def compute_joint_relevance(post_text: str, agent_manifesto: str) -> float:
        overlap = set(post_text.lower().split()) & set(agent_manifesto.lower().split())
        semantic_boost = min(len(overlap) * 0.12, 0.45)
        base_score = 0.52 + semantic_boost
        return min(max(base_score, 0.0), 0.99)


# ============================================================================
# 3. MULTI-STAGE ROUTING ENGINE
# ============================================================================

class MultiStageRoutingEngine:
    def __init__(self, agents_db: Dict[UUID, AgentProfile]):
        self.agents_db = agents_db

    def stage_1_sql_guardrails(self, author_id: UUID, post_industry: str) -> List[AgentProfile]:
        """
        Stage 1: Fast SQL Metadata Guardrails (< 2 ms)
        Filters out self, deactivated agents, untrusted agents, and blocked industries.
        """
        eligible: List[AgentProfile] = []
        for agent in self.agents_db.values():
            if agent.id == author_id:
                continue
            if not agent.is_active or agent.trust_score < 0.5:
                continue
            if post_industry in agent.excluded_industries:
                continue
            eligible.append(agent)
        return eligible

    def stage_2_dense_ann_search(
        self,
        candidates: List[AgentProfile],
        post_embedding: List[float],
        top_k: int = 50
    ) -> List[tuple[AgentProfile, float]]:
        """
        Stage 2: Dense Vector ANN Search (< 15 ms)
        Computes Cosine Similarity against HNSW index and retrieves Top K.
        """
        scored_candidates = []
        q_vec = np.array(post_embedding, dtype=np.float32)

        for agent in candidates:
            a_vec = np.array(agent.interest_embedding, dtype=np.float32)
            cosine_sim = float(np.dot(q_vec, a_vec))
            scored_candidates.append((agent, cosine_sim))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:top_k]

    def stage_3_reranker(
        self,
        post_text: str,
        top_candidates: List[tuple[AgentProfile, float]],
        threshold: float = 0.75
    ) -> List[MatchedCandidate]:
        """
        Stage 3: High-Precision Cross-Encoder Reranker (< 85 ms)
        Re-scores Top K candidates. Emits only candidates exceeding threshold >= 0.75.
        """
        final_matched: List[MatchedCandidate] = []
        for agent, vec_score in top_candidates:
            rerank_score = RerankingService.compute_joint_relevance(
                post_text, agent.interest_manifesto
            )
            if rerank_score >= threshold:
                final_matched.append(
                    MatchedCandidate(
                        agent_id=agent.id,
                        company_name=agent.company_name,
                        webhook_url=agent.webhook_url,
                        webhook_secret=agent.webhook_secret,
                        vector_score=round(vec_score, 4),
                        rerank_score=round(rerank_score, 4)
                    )
                )
        return final_matched

    def route_post(self, post: PostCreateRequest, author_industry: str) -> List[MatchedCandidate]:
        post_text = f"{post.title}. {post.content}"
        post_vec = EmbeddingService.get_embedding(post_text)

        eligible_agents = self.stage_1_sql_guardrails(post.author_agent_id, author_industry)
        ann_top_50 = self.stage_2_dense_ann_search(eligible_agents, post_vec, top_k=50)
        final_targets = self.stage_3_reranker(post_text, ann_top_50, threshold=0.75)
        return final_targets


# ============================================================================
# 4. SECURE WEBHOOK SIGNING (HMAC-SHA256)
# ============================================================================

class WebhookDeliveryEngine:
    @staticmethod
    def sign_payload(secret: str, timestamp: int, payload_json: str) -> str:
        message = f"v0:{timestamp}:{payload_json}".encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return f"hmac-sha256={sig}"

    @classmethod
    async def dispatch_webhook(
        cls,
        candidate: MatchedCandidate,
        post: PostCreateRequest,
        post_id: UUID
    ) -> Dict[str, Any]:
        timestamp = int(time.time())
        event_payload = {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "post.matched",
            "timestamp": timestamp,
            "match_metadata": {
                "vector_similarity": candidate.vector_score,
                "rerank_score": candidate.rerank_score
            },
            "post": {
                "id": str(post_id),
                "author_agent_id": str(post.author_agent_id),
                "title": post.title,
                "content": post.content,
                "expires_at": post.expires_at.isoformat() if post.expires_at else None
            }
        }
        payload_str = json.dumps(event_payload, sort_keys=True)
        signature = cls.sign_payload(candidate.webhook_secret, timestamp, payload_str)

        await asyncio.sleep(0.01)
        return {
            "status": "DELIVERED",
            "target_agent": candidate.company_name,
            "webhook_url": candidate.webhook_url,
            "signature": signature,
            "payload": event_payload
        }


# ============================================================================
# 5. DYNAMIC FEEDBACK LOOP
# ============================================================================

class DynamicProfileLearner:
    @staticmethod
    def update_preference_vector(
        agent: AgentProfile,
        engaged_post_embeddings: List[List[float]],
        ignored_post_embeddings: List[List[float]],
        alpha: float = 0.10,
        beta: float = 0.03,
        lambda_anchor: float = 0.20
    ) -> List[float]:
        current_vec = np.array(agent.interest_embedding, dtype=np.float32)

        pos_shift = np.zeros_like(current_vec)
        if engaged_post_embeddings:
            pos_shift = np.sum([np.array(e) for e in engaged_post_embeddings], axis=0) * alpha

        neg_shift = np.zeros_like(current_vec)
        if ignored_post_embeddings:
            neg_shift = np.sum([np.array(e) for e in ignored_post_embeddings], axis=0) * beta

        updated_vec = current_vec + pos_shift - neg_shift

        base_manifesto_vec = np.array(
            EmbeddingService.get_embedding(agent.interest_manifesto),
            dtype=np.float32
        )
        final_vec = (1.0 - lambda_anchor) * updated_vec + lambda_anchor * base_manifesto_vec

        norm = np.linalg.norm(final_vec)
        if norm > 0:
            final_vec = final_vec / norm

        agent.interest_embedding = final_vec.tolist()
        return agent.interest_embedding


if __name__ == "__main__":
    print("Initializing Multi-Stage Relevance Routing Engine...")

    swiggy_id = uuid4()
    phonepe_id = uuid4()
    bajaj_id = uuid4()

    mock_db: Dict[UUID, AgentProfile] = {
        phonepe_id: AgentProfile(
            id=phonepe_id,
            company_name="PhonePe",
            industry_category="Payments & Fintech",
            webhook_url="https://agent.phonepe.com/v1/network-events",
            webhook_secret="whsec_phonepe_secret_key_12345",
            interest_manifesto="Interested in e-commerce promotions, food delivery festive discounts, card payment partnerships.",
            interest_embedding=EmbeddingService.get_embedding("food delivery festive discounts payments UPI cashback")
        ),
        bajaj_id: AgentProfile(
            id=bajaj_id,
            company_name="Bajaj Auto",
            industry_category="Automotive Manufacturing",
            webhook_url="https://agent.bajaj.com/v1/network-events",
            webhook_secret="whsec_bajaj_secret_key_67890",
            interest_manifesto="Interested in commercial fleet procurement and engine spare parts.",
            interest_embedding=EmbeddingService.get_embedding("commercial vehicle engine spare parts fleet manufacturing")
        )
    }

    engine = MultiStageRoutingEngine(mock_db)

    new_post = PostCreateRequest(
        author_agent_id=swiggy_id,
        title="Diwali Food Delivery 5% Discount Promotion",
        content="Swiggy offering flat 5% off on all delivery orders above ₹300 during Diwali week. Seeking fintech payment partner for co-branded checkout cashback."
    )

    matches = engine.route_post(new_post, author_industry="Food Delivery")

    print(f"\nBroadcast Post: '{new_post.title}'")
    print(f"Total Eligible Targets Matched (Threshold >= 0.75): {len(matches)}")
    for m in matches:
        print(f" -> Matched Target: {m.company_name} | Vector Sim: {m.vector_score} | Rerank Score: {m.rerank_score}")

    async def test_dispatch():
        if matches:
            res = await WebhookDeliveryEngine.dispatch_webhook(matches[0], new_post, uuid4())
            print(f"\nWebhook Delivery Simulation to {res['target_agent']}:")
            print(f"Signature: {res['signature']}")
            print(f"Status: {res['status']}")

    asyncio.run(test_dispatch())
