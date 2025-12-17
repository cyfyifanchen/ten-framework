#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
from pydantic import BaseModel, Field


class MainControlConfig(BaseModel):
    """Main control configuration for voice-image-kids app"""
    greeting: str = Field(
        default="Hi! I'm your AI art friend! Tell me what you'd like to draw!",
        description="Greeting message when user joins"
    )
