"""
Market Intelligence 멀티 에이전트 시스템 - 핵심 데이터 모델
모든 에이전트가 공유하는 표준 입출력 스키마
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# 공통 열거형
# ─────────────────────────────────────────────

class AgentPhase(int, Enum):
    PHASE1_COLLECTION = 1   # 데이터 수집
    PHASE2_ANALYSIS   = 2   # 분석 & 심층 리서치
    PHASE3_SYNTHESIS  = 3   # 종합 & 인사이트
    PHASE4_OUTPUT     = 4   # 산출물 & 전달


class AgentStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    SKIPPED    = "skipped"


class QualityLevel(str, Enum):
    PASS    = "pass"
    WARNING = "warning"
    FAIL    = "fail"


# ─────────────────────────────────────────────
# 에이전트 컨텍스트 (에이전트 실행 시 주입)
# ─────────────────────────────────────────────

class ResearchScope(BaseModel):
    """리서치 범위 설정"""
    topic: str = Field(..., description="리서치 주제 (예: 국내 핀테크 시장)")
    industries: List[str] = Field(default_factory=list, description="분석 대상 산업")
    target_companies: List[str] = Field(default_factory=list, description="분석 대상 기업")
    regions: List[str] = Field(default=["KR", "US", "Global"], description="대상 지역")
    date_range_days: int = Field(default=90, ge=7, le=1095, description="데이터 수집 기간 (일, 7~1095)")
    language: str = Field(default="ko", description="주요 언어")
    custom_instructions: Optional[str] = Field(None, description="추가 지시사항")


class AgentContext(BaseModel):
    """에이전트 실행 컨텍스트"""
    session_id: str
    scope: ResearchScope
    previous_results: Dict[str, "AgentOutput"] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# 품질 검증
# ─────────────────────────────────────────────

class QualityCheck(BaseModel):
    criterion: str
    target: str
    actual: str
    level: QualityLevel
    note: Optional[str] = None


class QualityReport(BaseModel):
    overall: QualityLevel
    checks: List[QualityCheck]
    pass_rate: float
    summary: str


# ─────────────────────────────────────────────
# 수집된 원시 데이터
# ─────────────────────────────────────────────

class NewsItem(BaseModel):
    title: str
    summary: str
    source: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    category: Optional[str] = None
    language: str = "ko"


class MarketDataPoint(BaseModel):
    name: str
    metric: str
    value: float
    unit: str
    source: str
    timestamp: Optional[datetime] = None
    change_pct: Optional[float] = None


class RegulatoryItem(BaseModel):
    title: str
    country: str
    authority: str
    category: str
    summary: str
    impact_level: str
    effective_date: Optional[str] = None
    source_url: Optional[str] = None


class CompanyProfile(BaseModel):
    name: str
    country: str
    industry: str
    business_model: Optional[str] = None
    funding_stage: Optional[str] = None
    valuation_usd: Optional[float] = None
    employees: Optional[int] = None
    key_products: List[str] = Field(default_factory=list)
    recent_news: List[str] = Field(default_factory=list)
    source: str


# ─────────────────────────────────────────────
# 에이전트 산출물
# ─────────────────────────────────────────────

class AgentOutput(BaseModel):
    """모든 에이전트의 표준 출력 형식"""
    agent_id: str
    agent_name: str
    phase: AgentPhase
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    summary: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    analysis: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

    quality: Optional[QualityReport] = None

    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    sources_used: List[str] = Field(default_factory=list)
    data_points_collected: int = 0
    tokens_used: int = 0


# ─────────────────────────────────────────────
# 세션 & 오케스트레이터
# ─────────────────────────────────────────────

class SessionStatus(str, Enum):
    CREATED   = "created"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class MISession(BaseModel):
    session_id: str
    scope: ResearchScope
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    agent_results: Dict[str, AgentOutput] = Field(default_factory=dict)

    final_report: Optional[str] = None
    executive_summary: Optional[str] = None
    dashboard_data: Optional[Dict] = None

    current_phase: int = 0
    current_agent: Optional[str] = None
    progress_pct: float = 0.0
    total_tokens_used: int = 0


# ─────────────────────────────────────────────
# WebSocket 메시지
# ─────────────────────────────────────────────

class WSMessageType(str, Enum):
    AGENT_START      = "agent_start"
    AGENT_PROGRESS   = "agent_progress"
    AGENT_COMPLETE   = "agent_complete"
    AGENT_ERROR      = "agent_error"
    PHASE_COMPLETE   = "phase_complete"
    SESSION_COMPLETE = "session_complete"
    SESSION_CANCELLED = "session_cancelled"
    QA_RETRY         = "qa_retry"
    LOG              = "log"


class WSMessage(BaseModel):
    type: WSMessageType
    session_id: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    phase: Optional[int] = None
    progress_pct: Optional[float] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
