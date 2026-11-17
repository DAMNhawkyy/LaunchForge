"""Pydantic models = validation rules (Python's version of the Zod schemas)."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

# A required, trimmed, non-empty string
Str = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class IdeaIn(BaseModel):
    idea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1000)]


class Persona(BaseModel):
    name: Str
    description: Str
    needs: list[Str] = Field(min_length=1)


class MvpFeature(BaseModel):
    name: Str
    description: Str
    priority: Literal["High", "Medium", "Low"]


class Competitor(BaseModel):
    competitor: Str
    strengths: list[Str] = Field(min_length=1)
    weaknesses: list[Str] = Field(min_length=1)
    differentiation: Str


class CostItem(BaseModel):
    item: Str
    estimatedCost: Str
    description: Str


class LaunchPhase(BaseModel):
    phase: Str
    tasks: list[Str] = Field(min_length=1)


class Risk(BaseModel):
    risk: Str
    severity: Literal["Low", "Medium", "High"]
    mitigation: Str


class GeneratedPlan(BaseModel):
    """The structure the AI must return. Field names match the original project."""

    startupName: Str
    alternativeNames: list[Str] = Field(min_length=1, max_length=8)
    tagline: Str
    category: Str
    elevatorPitch: Str
    problemStatement: Str
    proposedSolution: Str
    targetAudience: list[Str] = Field(min_length=1)
    userPersonas: list[Persona] = Field(min_length=1)
    uniqueSellingProposition: Str
    mvpFeatures: list[MvpFeature] = Field(min_length=1)
    businessModel: Str
    pricingStrategy: list[Str] = Field(min_length=1)
    competitorAnalysis: list[Competitor] = Field(min_length=1)
    estimatedStartupCosts: list[CostItem] = Field(min_length=1)
    launchPlan: list[LaunchPhase] = Field(min_length=1)
    risks: list[Risk] = Field(min_length=1)
    assumptions: list[Str] = Field(min_length=1)
    disclaimer: Str


class SaveStartupIn(BaseModel):
    original_idea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1000)]
    plan_json: str  # JSON text coming from the form; re-validated as GeneratedPlan
    is_public: bool = False


class RegisterIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, to_lower=True, max_length=255,
            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        ),
    ]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
