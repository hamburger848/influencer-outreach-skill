#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikHub API 客户端
支持 TikTok平台达人数据获取

使用前需要：
1. 注册 TikHub 账号：https://tikhub.io
2. 获取 API Key
3. 设置环境变量 TIKHUB_API_KEY 或在初始化时传入
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass



class TikHubClient:
    """TikHub API 客户端"""
    BASE_URL = "https://api.tikhub.io/api/v1"
    PLATFORM_TIKTOK = "tiktok"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 60, 
                 proxy: Optional[str] = None, max_retries: int = 5):
        """
        初始化客户端
        
        Args:
            api_key: TikHub API Key，不传则从环境变量 TIKHUB_API_KEY 读取
            timeout: 请求超时时间（秒）
            proxy: 代理地址（如 http://127.0.0.1:7890）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("TIKHUB_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 TIKHUB_API_KEY 环境变量或在初始化时传入 api_key")
        
        self.timeout = timeout
        self.proxy = proxy or os.getenv("TIKHUB_PROXY")
        self.max_retries = max_retries
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """创建带重试机制的 Session"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries, # 最大重试次数
            backoff_factor=2, # 重试间隔因子，每次重试间隔增加 2 倍
            status_forcelist=[429, 500, 502, 503, 504], # 重试的 HTTP 状态码
            allowed_methods=["GET", "POST"], # 允许重试的 HTTP 方法
            raise_on_status=False # 不抛出 HTTPError 异常
        )
        adapter = HTTPAdapter(max_retries=retry_strategy) # 创建 HTTPAdapter 实例
        session.mount("https://", adapter) # 挂载 HTTPS 适配器
        session.mount("http://", adapter) # 挂载 HTTP 适配器
        
        if self.proxy:
            session.proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
        
        return session
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 data: Optional[Dict] = None) -> Dict:
        """
        发送 API 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: URL 参数
            data: POST 数据
            
        Returns:
            API 响应数据
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
                else:
                    response = self.session.post(url, headers=headers, json=data, timeout=self.timeout)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    raise ValueError("API Key 无效或已过期")
                elif response.status_code == 402:
                    raise ValueError("账户余额不足，请充值")
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"请求频率超限，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    try:
                        error_detail = response.json()
                        raise ValueError(f"API 请求失败 ({response.status_code}): {error_detail}")
                    except:
                        raise ValueError(f"API 请求失败: {e}")
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_error = e
                wait_time = 2 ** attempt
                print(f"网络错误: {e}，等待 {wait_time} 秒后重试 ({attempt + 1}/{self.max_retries})...")
                time.sleep(wait_time)
                
                # 重新创建 session
                self.session = self._create_session()
                continue
        
        raise ValueError(f"网络请求失败，已重试 {self.max_retries} 次: {last_error}")
    
    # ========== TikTok API ==========
    def search_tiktok_users(self, keyword: str, cursor: int = 0,
                            search_id: str = None, cookie: str = None,
                            parse_result: bool = True) -> Dict:
        """
        搜索 TikTok 用户

        TikHub API: Get user search results of specified keywords
        端点: GET /tiktok/web/fetch_search_user

        Args:
            keyword: 搜索关键词
            cursor: 翻页游标，第一次请求时为0，第二次请求时从上一次请求的返回响应中获取
            search_id: 搜索ID，第一次请求时为空，第二次翻页时需要提供
                       从上一次请求的返回响应中获取: $.data.extra.logid 或 $.data.log_pb.impr_id
            cookie: 用户cookie（可选，如果需要使用自己的账号搜索或遇到接口报错时提供）
            parse_result: 是否解析结果（默认True，返回解析后的用户列表）

        Returns:
            如果 parse_result=True: 用户列表，每个用户包含：
                uid, unique_id, nickname, signature, verified, followers, total_likes, sec_uid
            如果 parse_result=False: 原始API返回结果
        """
        params = {"keyword": keyword}
        if cursor:
            params["cursor"] = cursor
        if search_id:
            params["search_id"] = search_id
        if cookie:
            params["cookie"] = cookie

        result = self._request("GET", "tiktok/web/fetch_search_user", params)

        if not parse_result:
            return result

        users = []
        data = result.get("data", {})
        if isinstance(data, dict):
            user_list = data.get("user_list", [])
            if isinstance(user_list, list):
                for item in user_list:
                    user_info = item.get("user_info", item)
                    users.append({
                        "uid": user_info.get("uid") or user_info.get("id"),
                        "unique_id": user_info.get("unique_id", "") or user_info.get("uniqueId", ""),
                        "nickname": user_info.get("nickname", ""),
                        "signature": user_info.get("signature", ""),
                        "verified": bool(user_info.get("enterprise_verify_reason", "")),
                        "followers": user_info.get("follower_count", 0),
                        "total_likes": user_info.get("total_favorited", 0),
                        "sec_uid": user_info.get("sec_uid", ""),
                    })

        return users
    
    def fetch_user_post(self, sec_uid: str, cursor: int = 0, count: int = 20,
                        cover_format: int = 2, post_item_list_request_type: int = 0,
                        cookie: str = None) -> Dict:
        """
        获取 TikTok 用户的作品列表

        TikHub API: Get user posts
        端点: GET /tiktok/web/fetch_user_post

        Args:
            sec_uid: 用户secUid
            cursor: 翻页游标，第一次请求时为0，翻页时从上一次请求的返回响应中获取
            count: 每页数量，默认为20，不可变更
            cover_format: 封面格式，默认为2，可选值为1或2
            post_item_list_request_type: 排序方式
                0: 默认排序
                1: 热门排序
                2: 最旧排序
            cookie: 用户cookie（可选，用于获取受限制的内容）

        Returns:
            解析后的视频信息列表，每个视频包含：
                - id, create_time, desc, is_ad, is_pinned, original_item, private_item,
                  share_enabled, category_type, is_hd_bitrate, aigc_description
                - author: {id, sec_uid, unique_id, nickname, signature, verified,
                           private_account, avatar_thumb, avatar_medium, avatar_larger}
                - author_stats: {follower_count, following_count, heart_count, digg_count, video_count}
                - stats: {play_count, digg_count, comment_count, collect_count, share_count}
        """
        params = {"secUid": sec_uid}
        if cursor:
            params["cursor"] = cursor
        if count:
            params["count"] = count
        if cover_format:
            params["coverFormat"] = cover_format
        if post_item_list_request_type:
            params["post_item_list_request_type"] = post_item_list_request_type
        if cookie:
            params["cookie"] = cookie

        result = self._request("GET", "tiktok/web/fetch_user_post", params)

        video_data = result.get("data", {})
        items = video_data.get("itemList", [])

        parsed_videos = []
        for item in items:
            author = item.get("author", {})
            stats = item.get("stats", {})
            author_stats = item.get("authorStats", {}) or item.get("authorStatsV2", {})

            parsed_videos.append({
                "id": item.get("id"),
                "create_time": item.get("createTime"),
                "desc": item.get("desc", ""),
                "is_ad": item.get("isAd", False),
                "is_pinned": item.get("isPinnedItem", False),
                "original_item": item.get("originalItem", False),
                "private_item": item.get("privateItem", False),
                "share_enabled": item.get("shareEnabled", False),
                "category_type": item.get("CategoryType"),
                "is_hd_bitrate": item.get("IsHDBitrate", False),
                "aigc_description": item.get("AIGCDescription", ""),
                "author": {
                    "id": author.get("id"),
                    "sec_uid": author.get("secUid"),
                    "unique_id": author.get("uniqueId", ""),
                    "nickname": author.get("nickname", ""),
                    "signature": author.get("signature", ""),
                    "verified": author.get("verified", False),
                    "private_account": author.get("privateAccount", False),
                    "avatar_thumb": author.get("avatarThumb", ""),
                    "avatar_medium": author.get("avatarMedium", ""),
                    "avatar_larger": author.get("avatarLarger", ""),
                },
                "author_stats": {
                    "follower_count": author_stats.get("followerCount", 0),
                    "following_count": author_stats.get("followingCount", 0),
                    "heart_count": author_stats.get("heartCount", 0),
                    "digg_count": author_stats.get("diggCount", 0),
                    "video_count": author_stats.get("videoCount", 0),
                },
                "stats": {
                    "play_count": stats.get("playCount", 0),
                    "digg_count": stats.get("diggCount", 0),
                    "comment_count": stats.get("commentCount", 0),
                    "collect_count": stats.get("collectCount", 0),
                    "share_count": stats.get("shareCount", 0),
                },
            })

        return parsed_videos

    def fetch_kol_play_data(self, sec_uid: str, cookie: str = None) -> Dict:
        """
        获取 KOL 达人的播放数据（最新3个 + 最早2个）

        用于 analyze_kol_data 方法的参数

        Args:
            sec_uid: 用户 secUid
            cookie: 用户cookie（可选，用于获取受限制的内容）

        Returns:
            包含以下字段的字典：
            - 达人昵称, unique_id, signature, 粉丝数, 作品数
            - 播放1-5: 5个视频的播放量
            - 点赞1-5, 评论1-5, 收藏1-5: 每个视频的互动数据
            - 内容匹配度: 默认"待评估"
            - sec_uid: 用户ID
        """
        result = self.fetch_user_post(
            sec_uid=sec_uid,
            post_item_list_request_type=0,
            cookie=cookie
        )
        if len(result) < 10:
            return {}

        recent_3 = result[:3]
        oldest_2 = result[-2:]
        all_5 = recent_3 + oldest_2

        first_video = recent_3[0] if recent_3 else {}
        author_info = first_video.get("author", {})
        author_stats = first_video.get("author_stats", {})

        data = {
            "达人昵称": author_info.get("nickname", ""),
            "unique_id": author_info.get("unique_id", ""),
            "signature": author_info.get("signature", ""),
            "粉丝数": author_stats.get("follower_count", 0),
            "作品数": author_stats.get("video_count", 0),
            "内容匹配度": "待评估",
            "sec_uid": sec_uid,
        }

        for i, video in enumerate(all_5, 1):
            stats = video.get("stats", {})
            data[f"播放{i}"] = stats.get("play_count", 0)
            data[f"点赞{i}"] = stats.get("digg_count", 0)
            data[f"评论{i}"] = stats.get("comment_count", 0)
            data[f"收藏{i}"] = stats.get("collect_count", 0)

        return data

    def save_kol_to_csv(self, kol_data: Dict, csv_path: str = "kol_data.csv"):
        """
        将 KOL 数据保存到 CSV 文件

        Args:
            kol_data: fetch_kol_play_data 返回的达人数据字典
            csv_path: CSV 文件路径
        """
        import os
        import pandas as pd

        required_cols = ["达人昵称", "unique_id", "signature", "粉丝数", "作品数",
                         "播放1", "播放2", "播放3", "播放4", "播放5",
                         "点赞1", "点赞2", "点赞3", "点赞4", "点赞5",
                         "评论1", "评论2", "评论3", "评论4", "评论5",
                         "收藏1", "收藏2", "收藏3", "收藏4", "收藏5",
                         "内容匹配度", "sec_uid", "建联状态", "报价"]

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
        else:
            os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
            df = pd.DataFrame(columns=required_cols)

        sec_uid = kol_data.get("sec_uid", "")
        if sec_uid and sec_uid in df["sec_uid"].values:
            return

        new_row = {
            "达人昵称": kol_data.get("达人昵称", ""),
            "unique_id": kol_data.get("unique_id", ""),
            "signature": kol_data.get("signature", ""),
            "粉丝数": kol_data.get("粉丝数", 0),
            "作品数": kol_data.get("作品数", 0),
            "播放1": kol_data.get("播放1", 0),
            "播放2": kol_data.get("播放2", 0),
            "播放3": kol_data.get("播放3", 0),
            "播放4": kol_data.get("播放4", 0),
            "播放5": kol_data.get("播放5", 0),
            "点赞1": kol_data.get("点赞1", 0),
            "点赞2": kol_data.get("点赞2", 0),
            "点赞3": kol_data.get("点赞3", 0),
            "点赞4": kol_data.get("点赞4", 0),
            "点赞5": kol_data.get("点赞5", 0),
            "评论1": kol_data.get("评论1", 0),
            "评论2": kol_data.get("评论2", 0),
            "评论3": kol_data.get("评论3", 0),
            "评论4": kol_data.get("评论4", 0),
            "评论5": kol_data.get("评论5", 0),
            "收藏1": kol_data.get("收藏1", 0),
            "收藏2": kol_data.get("收藏2", 0),
            "收藏3": kol_data.get("收藏3", 0),
            "收藏4": kol_data.get("收藏4", 0),
            "收藏5": kol_data.get("收藏5", 0),
            "内容匹配度": kol_data.get("内容匹配度", "待评估"),
            "sec_uid": sec_uid,
            "建联状态": "未建联",
            "报价": None,
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    client = TikHubClient()
    
    # 使用你的 TikTok cookie（从浏览器开发者工具获取）
    cookie = "your_tiktok_cookie_here"
    
    result = client.fetch_user_post(
        sec_uid="MS4wLjABAAAA4FqTi-up6QWqLJI5Tcnrxvjh2Py7Fs91lqo2JtqjHD5BV00toJMBBlwLWxKsCHdU",
        cookie=cookie
    )
    print(f"获取到 {len(result)} 个视频")
    if result:
        print(f"第一个视频ID: {result[0].get('id')}")
        print(f"第一个视频播放量: {result[0].get('stats', {}).get('play_count', 0)}")
