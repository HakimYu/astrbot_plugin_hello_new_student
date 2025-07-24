import json
from pathlib import Path
import traceback

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
import astrbot.api.message_components as Comp


@register("astrbot_plugin_hello_new_student", "HakimYu", "一个简单的入群欢迎插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.is_send_welcome = config.get("is_send_welcome", True)
        self.is_at = config.get("is_at", True)
        self.welcome_text = config.get("welcome_text", "欢迎新成员加入！")
        self.welcome_groups = config.get("welcome_groups", [])
        self.monitor_groups = config.get("monitor_groups", [])

    async def _handle_add_group(self, event: AstrMessageEvent, group_id: str):
        """添加欢迎群组到白名单"""
        if group_id in self.welcome_groups:
            yield event.plain_result("该群组已在欢迎列表中")
            return

        self.welcome_groups.append(group_id)
        # 更新配置文件
        config = self.context.get_config()
        config['welcome_groups'] = self.welcome_groups
        config.save_config()

        yield event.plain_result(f"已添加群组 {group_id} 到欢迎列表")

    async def _handle_remove_group(self, event: AstrMessageEvent, group_id: str):
        """从白名单中删除欢迎群组"""
        if group_id not in self.welcome_groups:
            yield event.plain_result("该群组不在欢迎列表中")
            return

        self.welcome_groups.remove(group_id)
        # 更新配置文件
        config = self.context.get_config()
        config['welcome_groups'] = self.welcome_groups
        config.save_config()

        yield event.plain_result(f"已从欢迎列表中删除群组 {group_id}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_group_message(self, event: AstrMessageEvent):
        """处理群消息命令"""
        try:
            # 获取消息内容
            message = event.message_str if hasattr(
                event, "message_str") else None
            if not message:
                return

            # 检查是否在监控群组中
            group_id = event.get_group_id()
            if not group_id or str(group_id) not in self.monitor_groups:
                return

            logger.info(f"收到群消息: {event.message_obj.raw_message}")

            # 处理添加群组命令
            if message.startswith(("add_group", "添加欢迎群")):
                parts = message.split()
                if len(parts) < 2:
                    yield event.plain_result("请提供要添加的群号")
                    return
                group_id = parts[1]
                async for result in self._handle_add_group(event, group_id):
                    yield result
                return

            # 处理删除群组命令
            if message.startswith(("remove_group", "删除欢迎群")):
                parts = message.split()
                if len(parts) < 2:
                    yield event.plain_result("请提供要删除的群号")
                    return
                group_id = parts[1]
                async for result in self._handle_remove_group(event, group_id):
                    yield result
                return

        except Exception as e:
            logger.error(f"处理群消息时出错: {e}")
            logger.error(traceback.format_exc())

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_group_increase(self, event: AstrMessageEvent):
        """处理群成员增加事件"""
        try:
            if not hasattr(event, "message_obj") or not hasattr(event.message_obj, "raw_message"):
                return

            raw_message = event.message_obj.raw_message
            if not raw_message or not isinstance(raw_message, dict):
                return

            # 处理新成员入群事件
            if raw_message.get("post_type") == "notice" and raw_message.get("notice_type") == "group_increase":
                if not self.is_send_welcome:
                    return

                group_id = str(raw_message.get("group_id"))
                if group_id not in self.welcome_groups:
                    return

                user_id = raw_message.get("user_id")
                chain = []

                # 只在开启 @功能 时添加 At 组件
                if self.is_at and user_id:
                    chain.append(Comp.At(qq=user_id))
                    # 在 At 后添加一个空格
                    chain.append(Comp.Plain(" "))

                # 添加欢迎文本
                chain.append(Comp.Plain(self.welcome_text))

                yield event.chain_result(chain)

        except Exception as e:
            logger.error(f"处理群成员增加事件时出错: {e}")
            logger.error(traceback.format_exc())
