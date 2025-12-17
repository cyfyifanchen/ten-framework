#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import json
from ten_runtime import (
    Data,
    TenEnv,
    AsyncTenEnv,
)
from ten_ai_base.const import (
    DATA_OUT_PROPERTY_END_OF_SEGMENT,
    DATA_OUT_PROPERTY_TEXT,
    CONTENT_DATA_OUT_NAME,
    LOG_CATEGORY_KEY_POINT,
    LOG_CATEGORY_VENDOR,
)
from ten_ai_base.types import LLMToolMetadataParameter, LLMToolResultLLMResult
from ten_ai_base.llm_tool import (
    AsyncLLMToolBaseExtension,
    LLMToolMetadata,
    LLMToolResult,
)
from .config import OpenAIGPTImageConfig
from .openai_image_client import (
    OpenAIImageClient,
    ContentPolicyError,
    InvalidAPIKeyError,
    ModelNotFoundError,
)


class OpenAIGPTImageExtension(AsyncLLMToolBaseExtension):
    """
    OpenAI GPT Image 1.5 Extension

    Provides AI image generation using OpenAI's GPT Image 1.5 model
    with fallback to DALL-E 3. Integrates as an LLM tool for
    conversational image creation.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.config: OpenAIGPTImageConfig = None
        self.client: OpenAIImageClient = None

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        """Initialize extension with configuration and client"""
        await super().on_start(ten_env)

        # Load configuration from property.json
        ten_env.log_info("Loading OpenAI GPT Image configuration...")
        config_json_str, _ = await ten_env.get_property_to_json("")
        self.config = OpenAIGPTImageConfig.model_validate_json(config_json_str)

        # Log config (with sensitive data encrypted)
        ten_env.log_info(
            f"Configuration loaded: {self.config.to_str()}",
            category=LOG_CATEGORY_KEY_POINT
        )

        # Validate configuration
        try:
            self.config.validate()
            self.config.update_params()
        except ValueError as e:
            ten_env.log_error(f"Configuration validation failed: {e}")
            raise

        # Initialize OpenAI client
        self.client = OpenAIImageClient(self.config, ten_env)
        ten_env.log_info(
            "OpenAI GPT Image client initialized successfully",
            category=LOG_CATEGORY_KEY_POINT
        )

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        """Cleanup resources"""
        await super().on_stop(ten_env)

        if self.client:
            await self.client.cleanup()
            ten_env.log_info("OpenAI client cleaned up")

    def get_tool_metadata(self, ten_env: TenEnv) -> list[LLMToolMetadata]:
        """Register image generation tool with LLM"""
        return [
            LLMToolMetadata(
                name="generate_image",
                description=(
                    "Generate an image from a text description using AI. "
                    "Creates high-quality, creative images based on detailed prompts. "
                    "Use this when the user asks to create, draw, make, or generate an image."
                ),
                parameters=[
                    LLMToolMetadataParameter(
                        name="prompt",
                        type="string",
                        description=(
                            "Detailed description of the image to generate. "
                            "Include style, subject, mood, colors, and composition. "
                            "Be specific and descriptive for best results. "
                            "Use the same language as the user's request."
                        ),
                        required=True,
                    ),
                    LLMToolMetadataParameter(
                        name="quality",
                        type="string",
                        description=(
                            "Image quality: 'standard' for faster generation, "
                            "'hd' for higher detail (optional, defaults to configured value)"
                        ),
                        required=False,
                    ),
                ],
            )
        ]

    async def send_image(
        self, async_ten_env: AsyncTenEnv, image_url: str
    ) -> None:
        """Send generated image URL to frontend via content_data"""
        async_ten_env.log_info(f"Sending image URL: {image_url}")

        try:
            # Format as JSON matching TEN content_data schema
            payload = json.dumps({
                "data": {
                    "image_url": image_url
                },
                "type": "image_url"
            })

            # Create content_data message
            output_data = Data.create(CONTENT_DATA_OUT_NAME)
            output_data.set_property_string(DATA_OUT_PROPERTY_TEXT, payload)
            output_data.set_property_bool(DATA_OUT_PROPERTY_END_OF_SEGMENT, True)

            # Send asynchronously
            await async_ten_env.send_data(output_data)

            async_ten_env.log_info(
                "Image URL sent successfully",
                category=LOG_CATEGORY_KEY_POINT
            )

        except Exception as err:
            async_ten_env.log_error(
                f"Failed to send image URL: {err}",
                category=LOG_CATEGORY_VENDOR
            )

    async def run_tool(
        self, ten_env: AsyncTenEnv, name: str, args: dict
    ) -> LLMToolResult | None:
        """Execute image generation tool"""
        ten_env.log_info(f"run_tool {name} with args: {args}")

        if name != "generate_image":
            return None

        prompt = args.get("prompt")
        if not prompt or not prompt.strip():
            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": False,
                    "error": "No prompt provided. Please describe what image you want to create."
                }),
            )

        try:
            # Override quality if specified
            quality = args.get("quality", self.config.params.get("quality"))

            # Generate image
            ten_env.log_info(
                f"Generating image with prompt: {prompt[:100]}...",
                category=LOG_CATEGORY_KEY_POINT
            )
            image_url = await self.client.generate_image(
                prompt=prompt,
                quality=quality,
            )

            # Send image to frontend
            await self.send_image(ten_env, image_url)

            # Return success to LLM
            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": True,
                    "image_url": image_url,
                    "message": "Image generated successfully!"
                }),
            )

        except ContentPolicyError as e:
            error_msg = "I can't create that image. Let's try something different!"
            ten_env.log_warn(
                f"Content policy violation: {e}",
                category=LOG_CATEGORY_VENDOR
            )

            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": False,
                    "error": error_msg
                }),
            )

        except InvalidAPIKeyError as e:
            error_msg = "API key is invalid. Please check your configuration."
            ten_env.log_error(
                f"Invalid API key: {e}",
                category=LOG_CATEGORY_VENDOR
            )

            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": False,
                    "error": error_msg
                }),
            )

        except ModelNotFoundError as e:
            # Try fallback model
            fallback_model = self.config.params.get("fallback_model")
            if fallback_model and fallback_model != self.client.current_model:
                ten_env.log_warn(
                    f"Model {self.client.current_model} not available, "
                    f"falling back to {fallback_model}",
                    category=LOG_CATEGORY_KEY_POINT
                )
                try:
                    image_url = await self.client.generate_image(
                        prompt=prompt,
                        quality=quality,
                        model_override=fallback_model
                    )
                    await self.send_image(ten_env, image_url)
                    return LLMToolResultLLMResult(
                        type="llmresult",
                        content=json.dumps({
                            "success": True,
                            "image_url": image_url,
                            "message": f"Image generated with {fallback_model}"
                        }),
                    )
                except Exception as fallback_error:
                    error_msg = "Image generation is temporarily unavailable."
                    ten_env.log_error(
                        f"Fallback also failed: {fallback_error}",
                        category=LOG_CATEGORY_VENDOR
                    )
            else:
                error_msg = "Image generation model is not available."

            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": False,
                    "error": error_msg
                }),
            )

        except Exception as e:
            error_msg = "Something went wrong. Please try again."
            ten_env.log_error(
                f"Image generation failed: {e}",
                category=LOG_CATEGORY_VENDOR
            )

            return LLMToolResultLLMResult(
                type="llmresult",
                content=json.dumps({
                    "success": False,
                    "error": error_msg
                }),
            )
