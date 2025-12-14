from ten_runtime import Addon, register_addon_as_extension, TenEnv
from .extension import GeminiFlashTTSExtension


@register_addon_as_extension("gemini_flash_tts_python")
class GeminiFlashTTSExtensionAddon(Addon):
    def on_create_instance(self, ten_env: TenEnv, name: str, context) -> None:
        ten_env.log_info(
            f"Creating Gemini Flash TTS extension instance: {name}"
        )
        ten_env.on_create_instance_done(GeminiFlashTTSExtension(name), context)
