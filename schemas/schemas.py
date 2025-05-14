from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


class AddressInfo(BaseModel):
    hash: str
    is_contract: bool
    is_verified: Optional[bool] = False
    name: Optional[str] = None  # Added field for contract/token name


class FeeInfo(BaseModel):
    type: Literal["actual"]
    value: str  # In Wei


class DecodedParameter(BaseModel):
    name: str
    type: str
    value: str


class DecodedInput(BaseModel):
    method_call: str
    method_id: str
    parameters: List[DecodedParameter]


class Transaction(BaseModel):
    hash: str
    timestamp: datetime
    block_number: int
    status: str
    transaction_types: List[str]
    from_: AddressInfo = Field(..., alias="from")
    # Made this optional for contract creation transactions
    to: Optional[AddressInfo] = None
    method: Optional[str]
    decoded_input: Optional[DecodedInput]
    value: str  # In Wei
    fee: Optional[FeeInfo]
    gas_used: str
    gas_limit: str
    gas_price: str
    exchange_rate: Optional[str]
    historic_exchange_rate: Optional[str]
    token_name: Optional[str] = None  # Added field for token name
    # Added for contract creation
    created_contract: Optional[AddressInfo] = None


class ProcessedTransaction(BaseModel):
    tx_hash: str
    timestamp: datetime
    block_number: int
    status: str
    tx_type: List[str]
    from_address: str
    to_address: str
    from_is_contract: bool
    to_is_contract: bool
    to_is_verified: bool
    from_name: Optional[str]  # Added field for from address name
    to_name: Optional[str]    # Added field for to address name
    token_name: Optional[str]  # Added field for token name
    method: Optional[str]
    token_amount: Optional[float]
    value_wei: int
    value_usd: float
    fee_wei: int
    fee_usd: float
    gas_used: int
    gas_limit: int
    gas_price: int
    gas_efficiency: float

# AI Structured Output:


class ScoringBreakdown(BaseModel):
    criteria: str
    score_delta: float
    reason: str


class WalletMetadata(BaseModel):
    first_seen: datetime
    last_seen: datetime
    age_days: int
    total_transactions: int
    inbound_count: int
    outbound_count: int
    unique_tokens_used: int
    unique_contracts_interacted: int
    uses_only_transfers: bool
    all_contracts_verified: bool
    funded_by_established_wallet: bool
    linked_to_flagged_entity: bool


class ContractUsage(BaseModel):
    single_contract_usage: bool
    unverified_contract_usage: bool


class BehavioralPatterns(BaseModel):
    outbound_only: bool
    transaction_anomalies: List[str]
    contract_usage: ContractUsage


class FraudRiskAnalysis(BaseModel):
    wallet_address: str
    network: str
    analysis_timestamp: datetime
    scoring_breakdown: List[ScoringBreakdown]
    wallet_metadata: WalletMetadata
    behavioral_patterns: BehavioralPatterns
    comments: Optional[List[str]] = []
    final_score: float = Field(..., ge=0, le=100)
    risk_level: str


# Business Proposal Schemas

class SocialMediaLinks(BaseModel):
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    discord: Optional[str] = None
    telegram: Optional[str] = None
    github: Optional[str] = None


class DocumentBase(BaseModel):
    title: str
    type: str
    url: str
    size: str


class DocumentCreate(DocumentBase):
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentResponse(DocumentBase):
    id: str
    proposal_id: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class BusinessProposalBase(BaseModel):
    company_name: str
    logo: Optional[str] = None
    accepted_token: str
    total_pooled: str
    short_description: str
    full_description: str
    business_plan: str
    expected_return: str
    duration: str
    minimum_investment: str
    maximum_investment: str
    # Made optional as it will come from auth token
    proposer_wallet: Optional[str] = None
    deadline: datetime
    status: str = "active"
    current_funding: str = "0"
    target_funding: str
    investor_count: int = 0
    website: Optional[str] = None
    social_media: Optional[SocialMediaLinks] = None
    tags: List[str] = []


class BusinessProposalCreate(BusinessProposalBase):
    proposed_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[DocumentCreate] = []


class BusinessProposalUpdate(BaseModel):
    company_name: Optional[str] = None
    logo: Optional[str] = None
    accepted_token: Optional[str] = None
    total_pooled: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    business_plan: Optional[str] = None
    expected_return: Optional[str] = None
    duration: Optional[str] = None
    minimum_investment: Optional[str] = None
    maximum_investment: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None
    current_funding: Optional[str] = None
    target_funding: Optional[str] = None
    investor_count: Optional[int] = None
    website: Optional[str] = None
    social_media: Optional[SocialMediaLinks] = None
    tags: Optional[List[str]] = None


class BusinessProposalResponse(BusinessProposalBase):
    id: str
    proposed_at: datetime
    documents: List[DocumentResponse]
    wallet_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
