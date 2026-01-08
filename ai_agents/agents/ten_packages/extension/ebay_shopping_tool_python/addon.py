#
# eBay Shopping Tool Extension for TEN Framework
# Copyright (c) 2024 Agora IO. All rights reserved.
#
from ten_runtime import (
    Addon,
    register_addon_as_extension,
    TenEnv,
)


@register_addon_as_extension("ebay_shopping_tool_python")
class EbayShoppingToolExtensionAddon(Addon):

    def on_create_instance(self, ten_env: TenEnv, name: str, context) -> None:
        from .extension import EbayShoppingToolExtension

        ten_env.log_info("EbayShoppingToolExtensionAddon on_create_instance")
        ten_env.on_create_instance_done(EbayShoppingToolExtension(name), context)
