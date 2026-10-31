"""塔罗牌占卜插件(QQ 官方 Bot 版)。

改自 MinatoAquaCrews/nonebot_plugin_tarot(MIT)。

命令:
- 占卜: 随机牌阵抽多张, 文本 + 横向拼图(单条合成图, 规避官方被动消息 5 条限制)
- 塔罗牌: 单张抽牌回应

官方群聊需 @机器人 触发; C2C 直接发送。均为被动回复, 不占主动消息额度。
"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Event
from nonebot.adapters.qq import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata

from .data_source import tarot_manager

__version__ = "1.0.0"

__plugin_meta__ = PluginMetadata(
    name="塔罗牌",
    description="塔罗牌！魔法占卜🔮(QQ 官方 Bot 版, 牌图内置)",
    usage=(
        "占卜 —— 随机牌阵占卜(文本+拼图)\n"
        "塔罗牌 —— 单张抽牌回应\n"
        "官方群聊请 @机器人 触发"
    ),
    type="application",
    homepage="https://github.com/MinatoAquaCrews/nonebot_plugin_tarot",
    supported_adapters={"QQ"},
)

divine = on_command("占卜", priority=7, block=True)
tarot = on_command("塔罗牌", priority=7, block=True)


async def _send_result(matcher: Matcher, event: Event, text: str, image: bytes | None) -> None:
    """先发文本, 再发图(两条被动回复, 稳于图文同条)。无图时只发文本。"""
    await matcher.send(text)
    if image is None:
        return
    try:
        await matcher.finish(Message([MessageSegment.file_image(image, file_name="tarot.png")]))
    except Exception as exc:
        # 富媒体上传失败不影响文字结果
        from nonebot.log import logger

        logger.warning(f"塔罗牌图片上传失败: {exc}")


@divine.handle()
async def handle_divine(matcher: Matcher, event: Event) -> None:
    arg = event.get_plaintext()
    if "帮助" in arg[-2:]:
        await matcher.finish(__plugin_meta__.usage)
    text, image = await tarot_manager.draw_formation()
    await _send_result(matcher, event, text, image)


@tarot.handle()
async def handle_tarot(matcher: Matcher, event: Event) -> None:
    arg = event.get_plaintext()
    if "帮助" in arg[-2:]:
        await matcher.finish(__plugin_meta__.usage)
    text, image = await tarot_manager.draw_single()
    await _send_result(matcher, event, text, image)
