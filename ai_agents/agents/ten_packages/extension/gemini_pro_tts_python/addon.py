from ten_runtime import Addon, register_addon_as_extension, TenEnv
from .extension import GeminiProTTSExtension


@register_addon_as_extension("gemini_pro_tts_python")
class GeminiProTTSExtensionAddon(Addon):
    def on_create_instance(self, ten_env: TenEnv, name: str, context) -> None:
        ten_env.log_info(f"Creating Gemini Pro TTS extension instance: {name}")
        ten_env.on_create_instance_done(GeminiProTTSExtension(name), context)
