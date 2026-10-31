"""塔罗牌数据与渲染(QQ 官方 Bot 版)。

改自 MinatoAquaCrews/nonebot_plugin_tarot(MIT), 主要变化:
- tarot.json 内置, 不再运行时从 GitHub 更新
- 图片资源本地内置(BilibiliTarot 主题), 不再在线拉取
- 多张牌拼成一张合成图, 规避官方 Bot 被动消息 5 分钟/5 条限制
  (原版逐张发送 + OB11 合并转发在官方通道均不可用)
- 发送层与适配器解耦, 只产出 (文本, 图片bytes), 由 __init__ 决定怎么发
"""

from __future__ import annotations

import json
import random
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

#: 内置资源: 牌阵与 78 张牌的文本数据
JSON_PATH = Path(__file__).parent / "tarot.json"
#: 卡图目录(按 type 分子目录, 文件名 = json 的 pic 字段)
RESOURCE_DIR = Path(__file__).parent / "resource" / "BilibiliTarot"
#: 合成图上标注牌名用的字体(思源黑体, 与 xibao 同源)
FONT_PATH = Path(__file__).parent / "SourceHanSansSC-Regular.otf"

#: 合成图参数: 单张目标高度 / 间距 / 标注区高度
_CARD_TARGET_H = 560
_PAD = 24
_LABEL_H = 64
_BG_COLOR = (248, 244, 235)
_LABEL_COLOR = (70, 55, 40)


class TarotManager:
    """塔罗牌抽取与合成图渲染。"""

    def __init__(self) -> None:
        with JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.cards: dict[str, dict] = data["cards"]
        self.formations: dict[str, dict] = data["formations"]

    # ------------------------------------------------------------------ 抽牌

    def _pick_cards(self, num: int) -> list[dict]:
        return random.sample(list(self.cards.values()), num)

    def _load_card_image(self, card: dict) -> Image.Image | None:
        """按 json 的 pic 字段在本地资源目录找卡图; 找不到返回 None(纯文字退化)。"""
        img_dir = RESOURCE_DIR / str(card.get("type") or "")
        if not img_dir.is_dir():
            return None
        for p in img_dir.glob(str(card.get("pic") or "\0") + ".*"):
            try:
                return Image.open(p).convert("RGB")
            except OSError:
                continue
        return None

    def _flip(self, card: dict) -> bool:
        """随机正/逆位: True=正位。"""
        return random.random() < 0.5

    # ------------------------------------------------------------------ 占卜入口

    async def draw_single(self) -> tuple[str, bytes | None]:
        """单张抽牌(塔罗牌命令): 返回 (文本, 卡图bytes 或 None)。"""
        card = self._pick_cards(1)[0]
        up = self._flip(card)
        meaning = card["meaning"]["up" if up else "down"]
        pos = "正位" if up else "逆位"
        text = f"回应是「{card['name_cn']}{pos}」({card['name_en']})\n{meaning}"
        img = self._load_card_image(card)
        if img is not None and not up:
            img = img.rotate(180)
        return text, self._img_bytes(img) if img is not None else None

    async def draw_formation(self) -> tuple[str, bytes | None]:
        """牌阵占卜(占卜命令): 随机牌阵抽 N 张, 文本 + 横向拼图。"""
        formation_name = random.choice(list(self.formations))
        formation = self.formations[formation_name]
        cards_num: int = formation["cards_num"]
        is_cut: bool = formation["is_cut"]
        representations = random.choice(formation["representations"])

        cards = self._pick_cards(cards_num)
        lines = [f"启用「{formation_name}」，正在洗牌中……"]
        composed: list[tuple[Image.Image, str]] = []
        for i, card in enumerate(cards):
            up = self._flip(card)
            meaning = card["meaning"]["up" if up else "down"]
            pos = "正位" if up else "逆位"
            label = str(representations[i]) if i < len(representations) else f"第{i + 1}张"
            if is_cut and i == cards_num - 1:
                header = f"切牌「{label}」"
            else:
                header = f"第{i + 1}张「{label}」"
            lines.append(f"{header}：{card['name_cn']}{pos} —— {meaning}")

            img = self._load_card_image(card)
            if img is not None:
                if not up:
                    img = img.rotate(180)
                composed.append((img, f"{card['name_cn']}{pos}"))

        return "\n".join(lines), self._compose(composed) if composed else None

    # ------------------------------------------------------------------ 渲染

    @staticmethod
    def _img_bytes(img: Image.Image) -> bytes:
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _compose(self, cards: list[tuple[Image.Image, str]]) -> bytes:
        """把多张牌横向拼成一张图, 底部标注牌名与正逆位。"""
        font: ImageFont.FreeTypeFont | None = None
        if FONT_PATH.exists():
            try:
                font = ImageFont.truetype(str(FONT_PATH), 36)
            except OSError:
                font = None

        scaled: list[tuple[Image.Image, str]] = []
        for img, label in cards:
            w = max(1, int(img.width * _CARD_TARGET_H / img.height))
            scaled.append((img.resize((w, _CARD_TARGET_H)), label))

        total_w = sum(img.width for img, _ in scaled) + _PAD * (len(scaled) + 1)
        total_h = _PAD * 2 + _CARD_TARGET_H + _LABEL_H
        canvas = Image.new("RGB", (total_w, total_h), _BG_COLOR)
        draw = ImageDraw.Draw(canvas)

        x = _PAD
        for img, label in scaled:
            canvas.paste(img, (x, _PAD))
            if font is not None:
                draw.text(
                    (x + img.width // 2, _PAD + _CARD_TARGET_H + 10),
                    label,
                    fill=_LABEL_COLOR,
                    font=font,
                    anchor="ma",
                )
            x += img.width + _PAD

        return self._img_bytes(canvas)


tarot_manager = TarotManager()
