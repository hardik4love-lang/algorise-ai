"""initial schema

Revision ID: 0a1e894ceb3b
Revises: 
Create Date: 2026-09-20 18:57:06.121253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0a1e894ceb3b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hero bots table
    op.create_table(
        'hero_bots',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sector', sa.String(64), nullable=False),
        sa.Column('capability', sa.Text, nullable=False),
        sa.Column('tuned_confidence', sa.Float, nullable=False),
        sa.Column('target_latency_ms', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_hero_bots_sector', 'hero_bots', ['sector'])
    op.create_index('ix_hero_bots_name', 'hero_bots', ['name'])

    # Clients table (multi-tenancy)
    op.create_table(
        'clients',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tier', sa.String(32), nullable=False, default='Growth'),
        sa.Column('api_key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('quota_requests', sa.Integer, nullable=False, default=10000),
        sa.Column('quota_used', sa.Integer, nullable=False, default=0),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('settings', postgresql.JSONB, nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_clients_api_key_hash', 'clients', ['api_key_hash'], unique=True)

    # Bot executions table (audit trail)
    op.create_table(
        'bot_executions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('task_id', sa.String(64), nullable=False, index=True),
        sa.Column('bot_id', sa.String(64), sa.ForeignKey('hero_bots.id'), nullable=False),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('input_payload', postgresql.JSONB, nullable=False),
        sa.Column('output_data', postgresql.JSONB, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('reasoning_trace', postgresql.JSONB, nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=False),
        sa.Column('safety_clearance', sa.Boolean, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_bot_executions_client_created', 'bot_executions', ['client_id', 'created_at'])
    op.create_index('ix_bot_executions_bot_created', 'bot_executions', ['bot_id', 'created_at'])

    # Autoflow pipelines
    op.create_table(
        'autoflow_pipelines',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('flow_id', sa.String(128), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('trigger_event', sa.String(128), nullable=False),
        sa.Column('steps', postgresql.JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_autoflow_pipelines_client', 'autoflow_pipelines', ['client_id'])

    # Autoflow executions
    op.create_table(
        'autoflow_executions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('pipeline_id', sa.String(64), sa.ForeignKey('autoflow_pipelines.id'), nullable=False),
        sa.Column('trigger_data', postgresql.JSONB, nullable=False),
        sa.Column('steps_results', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(32), nullable=False, default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
    )
    op.create_index('ix_autoflow_executions_pipeline_started', 'autoflow_executions', ['pipeline_id', 'started_at'])

    # Freelance jobs
    op.create_table(
        'freelance_jobs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('source', sa.String(64), nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('budget_min', sa.Float, nullable=True),
        sa.Column('budget_max', sa.Float, nullable=True),
        sa.Column('client_name', sa.String(255), nullable=True),
        sa.Column('client_rating', sa.Float, nullable=True),
        sa.Column('skills_required', postgresql.JSONB, nullable=True),
        sa.Column('url', sa.String(512), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
    )
    op.create_index('ix_freelance_jobs_category', 'freelance_jobs', ['category'])
    op.create_index('ix_freelance_jobs_source', 'freelance_jobs', ['source'])
    op.create_index('ix_freelance_jobs_posted', 'freelance_jobs', ['posted_at'])

    # Freelance closers
    op.create_table(
        'freelance_closers',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('strategy', sa.Text, nullable=False),
        sa.Column('success_rate', sa.Float, nullable=False, default=0.0),
        sa.Column('total_closes', sa.Integer, nullable=False, default=0),
        sa.Column('avg_response_time_ms', sa.Float, nullable=False, default=0.0),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_freelance_closers_category', 'freelance_closers', ['category'])

    # Job close attempts
    op.create_table(
        'job_close_attempts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('job_id', sa.String(64), sa.ForeignKey('freelance_jobs.id'), nullable=False),
        sa.Column('closer_id', sa.String(64), sa.ForeignKey('freelance_closers.id'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('response', sa.Text, nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_job_close_attempts_job', 'job_close_attempts', ['job_id'])
    op.create_index('ix_job_close_attempts_closer', 'job_close_attempts', ['closer_id'])

    # Real estate leads
    op.create_table(
        'real_estate_leads',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(32), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('buyer_type', sa.String(64), nullable=False),
        sa.Column('budget_max', sa.Float, nullable=False),
        sa.Column('target_locations', postgresql.JSONB, nullable=True),
        sa.Column('timeline_months', sa.Integer, nullable=False),
        sa.Column('preapproved', sa.Boolean, nullable=False, default=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('qualification_score', sa.Float, nullable=True),
        sa.Column('tier', sa.String(32), nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_real_estate_leads_client', 'real_estate_leads', ['client_id'])

    # Outreach messages
    op.create_table(
        'outreach_messages',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('lead_id', sa.String(64), sa.ForeignKey('real_estate_leads.id'), nullable=False),
        sa.Column('channel', sa.String(16), nullable=False),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('status', sa.String(32), nullable=False, default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_outreach_messages_lead', 'outreach_messages', ['lead_id'])

    # Contract explanations
    op.create_table(
        'contract_explanations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('lead_id', sa.String(64), sa.ForeignKey('real_estate_leads.id'), nullable=True),
        sa.Column('draft_text', sa.Text, nullable=False),
        sa.Column('persona', sa.String(64), nullable=False),
        sa.Column('plain_english_summary', sa.Text, nullable=False),
        sa.Column('key_clauses_decoded', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_contract_explanations_lead', 'contract_explanations', ['lead_id'])

    # Telegram users
    op.create_table(
        'telegram_users',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('username', sa.String(128), nullable=True),
        sa.Column('first_name', sa.String(128), nullable=True),
        sa.Column('last_name', sa.String(128), nullable=True),
        sa.Column('language_code', sa.String(16), nullable=True),
        sa.Column('is_bot', sa.Boolean, nullable=False, default=False),
        sa.Column('is_premium', sa.Boolean, nullable=False, default=False),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('clients.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_telegram_users_client', 'telegram_users', ['client_id'])

    # Telegram conversations
    op.create_table(
        'telegram_conversations',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('chat_id', sa.BigInteger, nullable=False, index=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('telegram_users.id'), nullable=False),
        sa.Column('bot_id', sa.String(64), sa.ForeignKey('hero_bots.id'), nullable=True),
        sa.Column('state', sa.String(32), nullable=False, default='active'),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_telegram_conversations_chat', 'telegram_conversations', ['chat_id'])
    op.create_index('ix_telegram_conversations_user', 'telegram_conversations', ['user_id'])

    # Telegram messages
    op.create_table(
        'telegram_messages',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('conversation_id', sa.String(64), sa.ForeignKey('telegram_conversations.id'), nullable=False),
        sa.Column('message_id', sa.BigInteger, nullable=False),
        sa.Column('from_user_id', sa.BigInteger, sa.ForeignKey('telegram_users.id'), nullable=True),
        sa.Column('text', sa.Text, nullable=True),
        sa.Column('direction', sa.String(16), nullable=False),  # inbound, outbound
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_telegram_messages_conversation', 'telegram_messages', ['conversation_id'])
    op.create_index('ix_telegram_messages_created', 'telegram_messages', ['created_at'])

    # Rate limiting
    op.create_table(
        'rate_limit_buckets',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False, unique=True),
        sa.Column('tokens', sa.Float, nullable=False),
        sa.Column('last_refill', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('max_tokens', sa.Float, nullable=False),
        sa.Column('refill_rate', sa.Float, nullable=False),
    )

    # API keys for external services (encrypted)
    op.create_table(
        'external_api_keys',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('client_id', sa.String(64), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('service', sa.String(64), nullable=False),
        sa.Column('key_encrypted', sa.Text, nullable=False),
        sa.Column('key_name', sa.String(128), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_external_api_keys_client', 'external_api_keys', ['client_id'])


def downgrade() -> None:
    op.drop_table('external_api_keys')
    op.drop_table('rate_limit_buckets')
    op.drop_table('telegram_messages')
    op.drop_table('telegram_conversations')
    op.drop_table('telegram_users')
    op.drop_table('contract_explanations')
    op.drop_table('outreach_messages')
    op.drop_table('real_estate_leads')
    op.drop_table('job_close_attempts')
    op.drop_table('freelance_closers')
    op.drop_table('freelance_jobs')
    op.drop_table('autoflow_executions')
    op.drop_table('autoflow_pipelines')
    op.drop_table('bot_executions')
    op.drop_table('clients')
    op.drop_table('hero_bots')