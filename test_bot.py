#!/usr/bin/env python3
"""
快速测试脚本 - 验证 Bot Token 有效并且可以正常连接 Telegram API
"""
import asyncio
import os

from telegram import Bot

TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "7999315279:AAE-nz7z-PuDnJQv9hO74WrPCPhtVXINhFk",
)


async def test_connection():
    """测试与 Telegram API 的连接"""
    bot = Bot(token=TOKEN)

    # 获取 Bot 信息
    me = await bot.get_me()
    print(f"✅ Bot 连接成功!")
    print(f"   名称: {me.first_name}")
    print(f"   用户名: @{me.username}")
    print(f"   Bot ID: {me.id}")
    print(f"   可加入群组: {me.can_join_groups}")
    print()

    # 获取 webhook 信息
    webhook_info = await bot.get_webhook_info()
    print(f"📡 Webhook 状态:")
    print(f"   URL: {webhook_info.url or '(未设置 - 使用 polling 模式)'}")
    print(f"   待处理更新数: {webhook_info.pending_update_count}")
    print()

    print("🎉 一切就绪！你可以运行 `python3 bot.py` 来启动 Bot。")
    print(f"   然后在 Telegram 中搜索 @{me.username} 开始聊天。")


if __name__ == "__main__":
    asyncio.run(test_connection())
