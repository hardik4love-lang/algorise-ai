from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def gen_id() -> str:
    return str(uuid4())


class HeroBot(Base):
    __tablename__ = "hero_bots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    capability: Mapped[str] = mapped_column(Text, nullable=False)
    tuned_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    target_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    executions: Mapped[List["BotExecution"]] = relationship(back_populates="bot")
    telegram_conversations: Mapped[List["TelegramConversation"]] = relationship(back_populates="bot")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.id,
            "name": self.name,
            "sector": self.sector,
            "capability": self.capability,
            "tuned_confidence": self.tuned_confidence,
            "target_latency_ms": self.target_latency_ms,
        }


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="Growth")
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    quota_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, default="Surat")
    pin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fb_page_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    fb_page_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fb_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    bot_executions: Mapped[List["BotExecution"]] = relationship(back_populates="client")
    autoflow_pipelines: Mapped[List["AutoflowPipeline"]] = relationship(back_populates="client")
    real_estate_leads: Mapped[List["RealEstateLead"]] = relationship(back_populates="client")
    telegram_users: Mapped[List["TelegramUser"]] = relationship(back_populates="client")
    external_api_keys: Mapped[List["ExternalApiKey"]] = relationship(back_populates="client")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="client")
    leads: Mapped[List["Lead"]] = relationship(back_populates="client")
    facebook_jobs: Mapped[List["FacebookAgentJob"]] = relationship(back_populates="client")


class BotExecution(Base):
    __tablename__ = "bot_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bot_id: Mapped[str] = mapped_column(String(64), ForeignKey("hero_bots.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False)
    input_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasoning_trace: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    safety_clearance: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    bot: Mapped["HeroBot"] = relationship(back_populates="executions")
    client: Mapped["Client"] = relationship(back_populates="bot_executions")


class AutoflowPipeline(Base):
    __tablename__ = "autoflow_pipelines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    flow_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    trigger_event: Mapped[str] = mapped_column(String(128), nullable=False)
    steps: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="autoflow_pipelines")
    executions: Mapped[List["AutoflowExecution"]] = relationship(back_populates="pipeline")


class AutoflowExecution(Base):
    __tablename__ = "autoflow_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    pipeline_id: Mapped[str] = mapped_column(String(64), ForeignKey("autoflow_pipelines.id"), nullable=False)
    trigger_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    steps_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pipeline: Mapped["AutoflowPipeline"] = relationship(back_populates="executions")


class FreelanceJob(Base):
    __tablename__ = "freelance_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skills_required: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    close_attempts: Mapped[List["JobCloseAttempt"]] = relationship(back_populates="job")


class FreelanceCloser(Base):
    __tablename__ = "freelance_closers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_closes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    close_attempts: Mapped[List["JobCloseAttempt"]] = relationship(back_populates="closer")


class JobCloseAttempt(Base):
    __tablename__ = "job_close_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("freelance_jobs.id"), nullable=False, index=True)
    closer_id: Mapped[str] = mapped_column(String(64), ForeignKey("freelance_closers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["FreelanceJob"] = relationship(back_populates="close_attempts")
    closer: Mapped["FreelanceCloser"] = relationship(back_populates="close_attempts")


class RealEstateLead(Base):
    __tablename__ = "real_estate_leads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    budget_max: Mapped[float] = mapped_column(Float, nullable=False)
    target_locations: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    timeline_months: Mapped[int] = mapped_column(Integer, nullable=False)
    preapproved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qualification_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="real_estate_leads")
    outreach_messages: Mapped[List["OutreachMessage"]] = relationship(back_populates="lead")
    contract_explanations: Mapped[List["ContractExplanation"]] = relationship(back_populates="lead")


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    lead_id: Mapped[str] = mapped_column(String(64), ForeignKey("real_estate_leads.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["RealEstateLead"] = relationship(back_populates="outreach_messages")


class ContractExplanation(Base):
    __tablename__ = "contract_explanations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    lead_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("real_estate_leads.id"), nullable=True, index=True)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    persona: Mapped[str] = mapped_column(String(64), nullable=False)
    plain_english_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_clauses_decoded: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped[Optional["RealEstateLead"]] = relationship(back_populates="contract_explanations")


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("clients.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped[Optional["Client"]] = relationship(back_populates="telegram_users")
    conversations: Mapped[List["TelegramConversation"]] = relationship(back_populates="user")
    sent_messages: Mapped[List["TelegramMessage"]] = relationship(back_populates="from_user")


class TelegramConversation(Base):
    __tablename__ = "telegram_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.id"), nullable=False)
    bot_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("hero_bots.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["TelegramUser"] = relationship(back_populates="conversations")
    bot: Mapped[Optional["HeroBot"]] = relationship(back_populates="telegram_conversations")
    messages: Mapped[List["TelegramMessage"]] = relationship(back_populates="conversation")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("telegram_conversations.id"), nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("telegram_users.id"), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound, outbound
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["TelegramConversation"] = relationship(back_populates="messages")
    from_user: Mapped[Optional["TelegramUser"]] = relationship(back_populates="sent_messages")


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    tokens: Mapped[float] = mapped_column(Float, nullable=False)
    last_refill: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    max_tokens: Mapped[float] = mapped_column(Float, nullable=False)
    refill_rate: Mapped[float] = mapped_column(Float, nullable=False)


class ExternalApiKey(Base):
    __tablename__ = "external_api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False)
    key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="external_api_keys")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    plan_tier: Mapped[str] = mapped_column(String(64), nullable=False)  # starter, pro, enterprise
    plan_name: Mapped[str] = mapped_column(String(128), nullable=False)
    monthly_price: Mapped[float] = mapped_column(Float, nullable=False)
    setup_fee: Mapped[float] = mapped_column(Float, nullable=False)
    advance_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_advance")  # active, pending_advance, suspended, cancelled
    billing_cycle: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_billing_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="subscriptions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "plan_tier": self.plan_tier,
            "plan_name": self.plan_name,
            "monthly_price": self.monthly_price,
            "setup_fee": self.setup_fee,
            "advance_amount": self.advance_amount,
            "status": self.status,
            "billing_cycle": self.billing_cycle,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "next_billing_at": self.next_billing_at.isoformat() if self.next_billing_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="facebook_comment")  # facebook_comment, facebook_dm, web_form, manual
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="hot")  # hot, warm, cold, closed
    qualification_score: Mapped[float] = mapped_column(Float, nullable=False, default=85.0)
    intent_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fb_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    fb_comment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="leads")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "source": self.source,
            "status": self.status,
            "qualification_score": self.qualification_score,
            "intent_summary": self.intent_summary,
            "original_message": self.original_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FacebookAgentJob(Base):
    __tablename__ = "facebook_agent_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_id)
    client_id: Mapped[str] = mapped_column(String(64), ForeignKey("clients.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)  # comment_scan, dm_responder, lead_qualification
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")  # pending, running, completed, failed
    comments_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replies_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    log_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="facebook_jobs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "job_type": self.job_type,
            "status": self.status,
            "comments_scanned": self.comments_scanned,
            "replies_sent": self.replies_sent,
            "leads_detected": self.leads_detected,
            "log_summary": self.log_summary,
            "run_at": self.run_at.isoformat() if self.run_at else None,
        }