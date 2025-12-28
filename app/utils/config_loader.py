"""
🔧 Configuration Loader with Pydantic Validation
================================================

This module provides typed models and loading functions for the master configuration.
It validates config_master.json on startup and fails fast if the schema is invalid.

Usage:
    from app.utils.config_loader import load_and_validate_config
    config = load_and_validate_config("app/config/config_master.json")
"""

import json
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, validator, ValidationError


class ConstraintConfig(BaseModel):
    """
    Configuration for a single activity constraint.
    
    Constraints define which budget codes/types are allowed for a specific activity.
    """
    budget_code_pattern: Optional[str] = Field(
        default=None, 
        description="SQL LIKE pattern for budget code, e.g., '3%' for capital budgets"
    )
    allowed_budget_types: Optional[List[str]] = Field(
        default=None,
        description="List of allowed budget types: 'expense' or 'capital'"
    )
    cost_center_pattern: Optional[str] = Field(
        default=None,
        description="SQL LIKE pattern for cost center code"
    )
    allowed_cost_centers: Optional[List[int]] = Field(
        default=None,
        description="List of specific cost center IDs allowed"
    )
    constraint_type: str = Field(
        default="INCLUDE",
        description="INCLUDE or EXCLUDE constraint type"
    )
    priority: int = Field(
        default=0,
        description="Higher priority constraints are applied first"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the constraint"
    )
    
    @validator("constraint_type")
    def validate_constraint_type(cls, v: str) -> str:
        if v.upper() not in ("INCLUDE", "EXCLUDE"):
            raise ValueError("constraint_type must be INCLUDE or EXCLUDE")
        return v.upper()
    
    @validator("allowed_budget_types", each_item=True, pre=True)
    def validate_budget_types(cls, v: str) -> str:
        if v is None:
            return v
        valid_types = {"expense", "capital"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid budget type: {v}. Must be 'expense' or 'capital'")
        return v.lower()

    class Config:
        extra = "ignore"


class ActivityConfig(BaseModel):
    """
    Configuration for a subsystem activity.
    
    Activities are specific actions that can be performed within a subsystem.
    """
    code: str = Field(
        ...,
        description="Unique code for the activity, e.g., 'CONTRACT_REGISTER'"
    )
    title: str = Field(
        ...,
        description="Persian title for the activity, e.g., 'ثبت قرارداد'"
    )
    form_type: Optional[str] = Field(
        default=None,
        description="Type of form to display: 'contract', 'payroll', etc."
    )
    frequency: str = Field(
        default="MONTHLY",
        description="Execution frequency: DAILY, MONTHLY, YEARLY"
    )
    requires_file_upload: bool = Field(
        default=False,
        description="Whether this activity requires file attachment"
    )
    external_service_url: Optional[str] = Field(
        default=None,
        description="URL for external API integration (e.g., PMIS)"
    )
    order: int = Field(
        default=0,
        description="Display order within the subsystem"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this activity is currently active"
    )
    constraints: List[ConstraintConfig] = Field(
        default_factory=list,
        description="List of constraints for this activity"
    )
    
    @validator("frequency")
    def validate_frequency(cls, v: str) -> str:
        valid = {"DAILY", "MONTHLY", "YEARLY"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid frequency: {v}. Must be one of: {valid}")
        return v.upper()
    
    @validator("code")
    def validate_code_format(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError("Activity code must be alphanumeric with underscores only")
        return v.upper()

    class Config:
        extra = "ignore"


class SubsystemConfig(BaseModel):
    """
    Configuration for a subsystem (سامانه).
    
    A subsystem is a major functional area like Contracts, Payroll, etc.
    """
    code: str = Field(
        ...,
        description="Unique code for the subsystem, e.g., 'CONTRACTS'"
    )
    title: str = Field(
        ...,
        description="Persian title, e.g., 'سامانه امور قراردادها'"
    )
    icon: Optional[str] = Field(
        default=None,
        description="Icon name for UI display"
    )
    attachment_type: str = Field(
        default="upload",
        description="Attachment type: 'upload', 'api', or 'both'"
    )
    order: int = Field(
        default=0,
        description="Display order in the subsystem list"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this subsystem is currently active"
    )
    activities: List[ActivityConfig] = Field(
        default_factory=list,
        description="List of activities for this subsystem"
    )
    
    @validator("code")
    def validate_code_format(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError("Subsystem code must be alphanumeric with underscores only")
        return v.upper()
    
    @validator("attachment_type")
    def validate_attachment_type(cls, v: str) -> str:
        valid = {"upload", "api", "both"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid attachment_type: {v}. Must be one of: {valid}")
        return v.lower()

    class Config:
        extra = "ignore"


class MasterConfig(BaseModel):
    """
    Root configuration model containing all subsystems.
    
    This is the top-level model validated from config_master.json.
    """
    version: Optional[str] = Field(
        default="1.0.0",
        description="Configuration version"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the configuration"
    )
    subsystems: List[SubsystemConfig] = Field(
        ...,
        description="List of all subsystem configurations"
    )
    
    def get_subsystem(self, code: str) -> Optional[SubsystemConfig]:
        """Get a subsystem by its code."""
        for sub in self.subsystems:
            if sub.code.upper() == code.upper():
                return sub
        return None
    
    def get_activity(self, subsystem_code: str, activity_code: str) -> Optional[ActivityConfig]:
        """Get an activity by subsystem and activity code."""
        subsystem = self.get_subsystem(subsystem_code)
        if subsystem:
            for act in subsystem.activities:
                if act.code.upper() == activity_code.upper():
                    return act
        return None

    class Config:
        extra = "ignore"


class ConfigLoadError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


def load_and_validate_config(config_path: str = "app/config/config_master.json") -> MasterConfig:
    """
    Load and validate the master configuration file.
    
    This function reads the JSON file, validates it against the Pydantic schema,
    and returns a typed MasterConfig object.
    
    Args:
        config_path: Path to the config_master.json file
        
    Returns:
        MasterConfig: Validated configuration object
        
    Raises:
        ConfigLoadError: If the file doesn't exist, can't be parsed, or fails validation
    """
    path = Path(config_path)
    
    # 1. Check file exists
    if not path.exists():
        raise ConfigLoadError(f"❌ Configuration file not found: {path.absolute()}")
    
    # 2. Read and parse JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"❌ Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ConfigLoadError(f"❌ Failed to read configuration file: {e}")
    
    # 3. Validate with Pydantic
    try:
        config = MasterConfig.parse_obj(raw_data)
    except ValidationError as e:
        error_details = "\n".join([
            f"  - {'.'.join(str(x) for x in err['loc'])}: {err['msg']}" 
            for err in e.errors()
        ])
        raise ConfigLoadError(
            f"❌ Configuration validation failed:\n{error_details}"
        )
    
    # 4. Return validated config
    print(f"✅ Configuration loaded successfully: {len(config.subsystems)} subsystems")
    return config


def get_config() -> MasterConfig:
    """
    Get the singleton configuration instance.
    
    This is a convenience function that loads the config once and caches it.
    """
    if not hasattr(get_config, "_instance"):
        get_config._instance = load_and_validate_config()
    return get_config._instance


# --- CLI utility for testing ---
if __name__ == "__main__":
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "app/config/config_master.json"
    
    try:
        config = load_and_validate_config(config_path)
        print(f"\n📋 Configuration Summary:")
        print(f"   Version: {config.version}")
        print(f"   Subsystems: {len(config.subsystems)}")
        
        for sub in config.subsystems:
            print(f"\n   🔹 {sub.code}: {sub.title}")
            print(f"      Activities: {len(sub.activities)}")
            for act in sub.activities:
                constraint_count = len(act.constraints)
                print(f"        - {act.code}: {act.title} ({act.frequency}, {constraint_count} constraints)")
                
    except ConfigLoadError as e:
        print(e)
        sys.exit(1)
