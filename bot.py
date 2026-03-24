#!/usr/bin/env python3
"""
Telegram Bot - 基于 python-telegram-bot 库
Bot Token: 从环境变量 TELEGRAM_BOT_TOKEN 读取，或使用 .env 文件配置
"""

import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bot Token
# ---------------------------------------------------------------------------
TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "7999315279:AAE-nz7z-PuDnJQv9hO74WrPCPhtVXINhFk",
)


# ---------------------------------------------------------------------------
# 命令处理器
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 命令"""
    user = update.effective_user
    await update.message.reply_html(
        f"你好 {user.mention_html()} ！👋\n\n"
        f"我是你的 Telegram Bot，很高兴为你服务！\n\n"
        f"可用命令：\n"
        f"/start - 开始使用\n"
        f"/help  - 获取帮助\n"
        f"/info  - 查看 Bot 信息\n"
        f"/echo  - 回声测试（/echo 你好）\n"
        f"/ping  - 检测 Bot 是否在线\n",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /help 命令"""
    help_text = (
        "📖 <b>帮助信息</b>\n\n"
        "/start - 开始使用 Bot\n"
        "/help  - 显示此帮助信息\n"
        "/info  - 查看 Bot 信息\n"
        "/echo &lt;文字&gt; - Bot 会原样回复你的文字\n"
        "/ping  - 检测 Bot 是否在线\n\n"
        "你也可以直接发送任意消息，Bot 会回复你！"
    )
    await update.message.reply_html(help_text)


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /info 命令"""
    bot = context.bot
    bot_info = await bot.get_me()
    info_text = (
        f"🤖 <b>Bot 信息</b>\n\n"
        f"名称：{bot_info.first_name}\n"
        f"用户名：@{bot_info.username}\n"
        f"Bot ID：{bot_info.id}\n"
        f"支持内联模式：{bot_info.supports_inline_queries}\n"
    )
    await update.message.reply_html(info_text)


async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /echo 命令 - 回声"""
    if context.args:
        text = " ".join(context.args)
        await update.message.reply_text(f"🔊 {text}")
    else:
        await update.message.reply_text("请在 /echo 后面输入要回声的文字，例如：/echo 你好")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /ping 命令"""
    await update.message.reply_text("🏓 Pong! Bot 运行正常！")


# ---------------------------------------------------------------------------
# 消息处理器
# ---------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理普通文本消息"""
    user = update.effective_user
    text = update.message.text
    logger.info("收到来自 %s 的消息: %s", user.first_name, text)

    reply = (
        f"你好 {user.first_name}！你发送了：\n\n"
        f"「{text}」\n\n"
        f"输入 /help 查看可用命令。"
    )
    await update.message.reply_text(reply)


# ---------------------------------------------------------------------------
# 错误处理器
# ---------------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理错误"""
    logger.error("Update %s caused error: %s", update, context.error)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def main() -> None:
    """启动 Bot"""
    if not TOKEN:
        logger.error("未设置 TELEGRAM_BOT_TOKEN 环境变量！")
        return

    logger.info("正在启动 Telegram Bot ...")

    # 创建 Application
    application = Application.builder().token(TOKEN).build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("echo", echo_command))
    application.add_handler(CommandHandler("ping", ping_command))

    # 注册消息处理器（处理非命令的文本消息）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 注册错误处理器
    application.add_error_handler(error_handler)

    # 启动 Bot (使用 polling 模式)
    logger.info("Bot 已启动，正在监听消息 ...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
