from astrbot.api.all import *
from astrbot.api.message_components import *
import aiohttp
import asyncio
import time
from typing import Dict, Optional

# 用于跟踪每个用户的状态，防止超时或重复请求
USER_STATES: Dict[str, Optional[float]] = {}

# 注册插件命令，版本号等信息
@register("sauceno_search", "Hazellol", "sauceno搜图", "1.0.0")
class SauceNAOSearch(Star):
    
    # 初始化，获取配置文件中的 API Key
    def __init__(self, context: Context, config: dict):
        super().__init__(context)  # 调用父类初始化
        self.config = config
        self.api_key = config.get("saucenao_api", "")  # 获取配置中的API Key
    
    # 处理"搜图"命令
    @command("搜图")
    async def search_image(self, event: AstrMessageEvent):
        '''sauceno搜图'''
        user_id = event.get_sender_id()  # 获取用户ID
        USER_STATES[user_id] = time.time()  # 记录用户请求的时间
        yield event.plain_result("杂鱼~请发送你要查找的图片")  # 提示用户发送图片
        await asyncio.sleep(30)  # 等待30秒
        # 如果超时，删除用户状态并通知用户
        if user_id in USER_STATES:
            del USER_STATES[user_id]
            yield event.plain_result("搜索超时了哦，杂鱼~")

    # 处理所有消息类型的事件
    @event_message_type(EventMessageType.ALL)
    async def handle_image(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()  # 获取发送者的ID
        if user_id not in USER_STATES:  # 如果用户没有发起请求，跳过
            return
        
        # 检查消息中是否包含图片
        images = [c for c in event.message_obj.message if isinstance(c, Image)]
        if not images:  # 如果没有图片，跳过
            return
        
        # 删除用户状态，表示用户已提交图片
        del USER_STATES[user_id]
        
        # 如果未配置API Key，提醒用户
        if not self.api_key:
            yield event.plain_result("请先配置SauceNAO API Key")
            return
        
        # 使用第一张图片进行搜索
        image_url = images[0].url
        
        try:
            # 使用aiohttp进行异步请求
            async with aiohttp.ClientSession() as session:
                # 构造API请求的参数
                params = {
                    "url": image_url,
                    "output_type": 2,
                    "api_key": self.api_key,
                    "numres": 5  # 获取前5个结果
                }
                
                # 调用SauceNAO API进行图片搜索
                async with session.get("https://saucenao.com/search.php", params=params) as resp:
                    data = await resp.json()  # 解析返回的JSON数据
                
                results = data.get("results", [])  # 获取搜索结果
                if not results:  # 如果没有结果，返回提示
                    yield event.plain_result("没有找到匹配的结果哦，杂鱼~")
                    return
                
                # 根据相似度对结果进行排序，选择前5个最相似的结果
                sorted_results = sorted(
                    results,
                    key=lambda x: float(x["header"]["similarity"]),
                    reverse=True
                )[:5]
                
                # 创建消息列表，用于存储搜索结果
                msg_list = [Plain("搜索结果（可能性从高到低）：\n")]
                
                # 遍历前5个排序结果，构建显示信息
                for idx, result in enumerate(sorted_results, 1):
                    header = result["header"]
                    data = result["data"]
                    
                    similarity = header["similarity"]  # 获取相似度
                    thumbnail = header.get("thumbnail", "")  # 获取缩略图URL
                    author = data.get("member_name") or data.get("creator") or "未知作者"  # 获取作者
                    source = data.get("ext_urls", ["无原链接"])[0] if data.get("ext_urls") else "无原链接"  # 获取原图链接
                    
                    # 添加结果到消息列表
                    msg_list.append(Plain(f"\n#{idx} 可能性：{similarity}%\n"))
                    msg_list.append(Plain(f"作者：{author}\n"))
                    msg_list.append(Plain(f"原图：{source}\n"))
                    
                    if thumbnail:  # 如果有缩略图，添加图片到消息列表
                        msg_list.append(Image.fromURL(thumbnail))  # 从缩略图URL生成图片组件
                
                # 发送最终的结果，直接传递消息列表
                yield event.chain_result(msg_list)
                
        except Exception as e:  # 捕获异常并返回错误信息
            print(f"SauceNAO搜索失败: {str(e)}")
            yield event.plain_result("搜索失败了哦，杂鱼程序员又写bug了！")
