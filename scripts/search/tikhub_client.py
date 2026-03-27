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
import re
import time
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_OUTPUT_PATH = os.getenv("DEFAULT_OUTPUT_PATH", "outputs/KOL达人评分最终报告.xlsx")
api_key = os.getenv("TIKHUB_API_KEY")


def extract_hashtags(desc: str) -> List[str]:
    """
    从视频描述中提取话题标签

    Args:
        desc: 视频描述文本

    Returns:
        话题标签列表（不含#号）
    """
    if not desc:
        return []
    hashtags = re.findall(r'#(\w+)', desc)
    return hashtags


def get_challenges(item: Dict) -> List[str]:
    """
    从视频项中提取关联的话题/挑战标签

    Args:
        item: 原始视频数据项

    Returns:
        话题标签列表（列表小写）
    """
    challenges = []
    text_extras = item.get("text_extra", []) or []

    for extra in text_extras:
        hashtag = extra.get("hashtag_name", "") or extra.get("hashtag", "")
        if hashtag and hashtag not in challenges:
            challenges.append(hashtag.lower())

    return challenges


def get_content_topics(videos: List[Dict]) -> Dict[str, int]:
    """
    从视频列表中统计内容话题分布

    优先使用官方 challenges 标签，次用 desc 中的 hashtag

    Args:
        videos: 视频列表

    Returns:
        话题频次字典，按频次降序排列
    """
    topic_counter = {}
    for video in videos:
        item = video.get("_raw_item", {})

        if item:
            challenges = get_challenges(item)
            for tag in challenges:
                topic_counter[tag] = topic_counter.get(tag, 0) + 2

        desc = video.get("desc", "")
        hashtags = extract_hashtags(desc)
        for tag in hashtags:
            tag_lower = tag.lower()
            if tag_lower not in topic_counter:
                topic_counter[tag_lower] = topic_counter.get(tag_lower, 0) + 1

    return dict(sorted(topic_counter.items(), key=lambda x: x[1], reverse=True))


class TikHubClient:
    """TikHub API 客户端"""
    BASE_URL = "https://api.tikhub.io/api/v1"
    PLATFORM_TIKTOK = "tiktok"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 60,
                 max_retries: int = 5):
        """
        初始化客户端

        Args:
            api_key: TikHub API Key，不传则从环境变量 TIKHUB_API_KEY 读取
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("TIKHUB_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 TIKHUB_API_KEY 环境变量或在初始化时传入 api_key")

        self.timeout = timeout
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
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

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
    """
    def general_search(self, keyword: str, offset: int = 0, count: int = 20,
                       sort_type: int = 0, publish_time: int = 0,
                       output_path: str = None) -> Dict:

        获取指定关键词的综合搜索结果

        TikHub API: Get comprehensive search results of specified keywords
        端点: GET /tiktok/app/v3/fetch_general_search_result

        Args:
            keyword: 搜索关键词
            offset: 偏移量，用于翻页
            count: 数量，默认20
            sort_type: 排序类型
                0: 相关度
                1: 最多点赞
            publish_time: 发布时间筛选
                0: 不限制
                1: 最近一天
                7: 最近一周
                30: 最近一个月
                90: 最近三个月
                180: 最近半年
            output_path: Excel文件路径（默认为 DEFAULT_OUTPUT_PATH）

        Returns:
            综合搜索结果列表，包含视频、用户、话题信息

        params = {
            "keyword": keyword,
            "offset": offset,
            "count": count,
            "sort_type": sort_type,
            "publish_time": publish_time,
        }

        result = self._request("GET", "tiktok/app/v3/fetch_general_search_result", params)

        parsed_results = []
        videos = []
        users = []
        challenges = []
        data = result.get("data", {})
        items = data.get("search_item_list", []) or data.get("data", [])

        for item in items:
            aweme_info = item.get("aweme_info", {})
            user_info = item.get("user_info", {})
            challenge_info = item.get("challenge_info", {})

            if aweme_info:
                author = aweme_info.get("author", {})
                stats = aweme_info.get("statistics", {})
                music = aweme_info.get("music", {})
                video = aweme_info.get("video", {})

                video_data = {
                    "type": "video",
                    "video_id": aweme_info.get("aweme_id") or aweme_info.get("id"),
                    "desc": aweme_info.get("desc", ""),
                    "create_time": aweme_info.get("create_time", 0),
                    "author": {
                        "uid": author.get("uid") or author.get("id"),
                        "unique_id": author.get("unique_id", "") or author.get("uniqueId", ""),
                        "nickname": author.get("nickname", ""),
                        "sec_uid": author.get("sec_uid", ""),
                        "signature": author.get("signature", ""),
                        "followers": author.get("follower_count", 0),
                    },
                    "stats": {
                        "play_count": stats.get("play_count", 0),
                        "digg_count": stats.get("digg_count", 0),
                        "comment_count": stats.get("comment_count", 0),
                        "share_count": stats.get("share_count", 0),
                        "collect_count": stats.get("collect_count", 0),
                    },
                    "music": {
                        "title": music.get("title", ""),
                        "author": music.get("author", ""),
                    },
                    "video": {
                        "cover": video.get("cover", {}).get("url_list", [""])[0] if video.get("cover") else "",
                        "duration": video.get("duration", 0),
                    },
                }
                parsed_results.append(video_data)
                videos.append(video_data)

            elif user_info:
                user_data = {
                    "type": "user",
                    "uid": user_info.get("uid") or user_info.get("id"),
                    "unique_id": user_info.get("unique_id", "") or user_info.get("uniqueId", ""),
                    "nickname": user_info.get("nickname", ""),
                    "signature": user_info.get("signature", ""),
                    "sec_uid": user_info.get("sec_uid", ""),
                    "followers": user_info.get("follower_count", 0),
                    "following": user_info.get("following_count", 0),
                    "video_count": user_info.get("video_count", 0),
                    "total_likes": user_info.get("total_favorited", 0) or user_info.get("heart_count", 0),
                    "verified": user_info.get("verified", False),
                }
                parsed_results.append(user_data)
                users.append(user_data)

            elif challenge_info:
                challenge_data = {
                    "type": "hashtag",
                    "challenge_id": challenge_info.get("challenge_id", ""),
                    "title": challenge_info.get("cha_name", "") or challenge_info.get("title", ""),
                    "desc": challenge_info.get("desc", ""),
                    "video_count": challenge_info.get("video_count", 0),
                    "view_count": challenge_info.get("view_count", 0),
                    "user_count": challenge_info.get("user_count", 0),
                    "cover": challenge_info.get("cover", {}).get("url_list", [""])[0] if challenge_info.get("cover") else "",
                }
                parsed_results.append(challenge_data)
                challenges.append(challenge_data)

        if output_path is None:
            output_path = DEFAULT_OUTPUT_PATH

        if users:
            self._save_users_data(users, output_path, mode="append")

        return parsed_results
    """

    """
    def fetch_hashtag_videos(self, ch_id: str, cursor: int = 0, count: int = 20,
                             output_path: str = None) -> Dict:
        
        获取指定话题的作品数据

        TikHub API: Get video list of specified hashtag
        端点: GET /tiktok/app/v3/fetch_hashtag_video_list

        Args:
            ch_id: 话题ID
            cursor: 游标，用于翻页，第一页为0
            count: 数量，默认20
            output_path: Excel文件路径（默认为 DEFAULT_OUTPUT_PATH）

        Returns:
            话题视频列表
        
        params = {
            "ch_id": ch_id,
            "cursor": cursor,
            "count": count,
        }

        result = self._request("GET", "tiktok/app/v3/fetch_hashtag_video_list", params)

        parsed_results = []
        data = result.get("data", {})
        items = data.get("aweme_list", []) or data.get("video_list", []) or data.get("data", [])

        for item in items:
            aweme_info = item.get("aweme_info", {}) or item.get("aweme", {}) or item
            if not aweme_info:
                continue

            author = aweme_info.get("author", {})
            stats = aweme_info.get("statistics", {})

            parsed_results.append({
                "type": "video",
                "video_id": aweme_info.get("aweme_id") or aweme_info.get("id"),
                "desc": aweme_info.get("desc", ""),
                "create_time": aweme_info.get("create_time", 0),
                "author": {
                    "uid": author.get("uid") or author.get("id"),
                    "unique_id": author.get("unique_id", "") or author.get("uniqueId", ""),
                    "nickname": author.get("nickname", ""),
                    "sec_uid": author.get("sec_uid", ""),
                    "signature": author.get("signature", ""),
                    "followers": author.get("follower_count", 0),
                },
                "stats": {
                    "play_count": stats.get("play_count", 0),
                    "digg_count": stats.get("digg_count", 0),
                    "comment_count": stats.get("comment_count", 0),
                    "share_count": stats.get("share_count", 0),
                    "collect_count": stats.get("collect_count", 0),
                },
            })

        if output_path is None:
            output_path = DEFAULT_OUTPUT_PATH

        return parsed_results
    """

    def search_users(self, keyword: str, offset: int = 0, count: int = 20,
                     follower_count: str = None, profile_type: str = None,
                     other_pref: str = None, output_path: str = None) -> Dict:
        """
        获取指定关键词的用户搜索结果

        TikHub API: Get user search results of specified keywords
        端点: GET /tiktok/app/v3/fetch_user_search_result

        Args:
            keyword: 搜索关键词
            offset: 偏移量，用于翻页
            count: 数量，默认20
            follower_count: 根据粉丝数筛选
                None: 不限制
                "ZERO_TO_ONE_K": 0-1K
                "ONE_K_TO_TEN_K": 1K-10K
                "TEN_K_TO_ONE_H_K": 10K-100K
                "ONE_H_K_PLUS": 100K以上
            profile_type: 根据账号类型筛选
                None: 不限制
                "VERIFIED": 认证用户
            other_pref: 其他偏好
                "USERNAME": 根据用户名相关性
            output_path: Excel文件路径（默认为 DEFAULT_OUTPUT_PATH）

        Returns:
            用户搜索结果列表
        """
        params = {
            "keyword": keyword,
            "offset": offset,
            "count": count,
        }
        if follower_count:
            params["user_search_follower_count"] = follower_count
        if profile_type:
            params["user_search_profile_type"] = profile_type
        if other_pref:
            params["user_search_other_pref"] = other_pref

        result = self._request("GET", "tiktok/app/v3/fetch_user_search_result", params)

        all_users = set()
        parsed_results = []
        data = result.get("data", {})
        items = data.get("user_list", []) or data.get("data", [])

        for item in items:
            user_info = item.get("user_info", {}) or item
            if not user_info:
                continue

            sec_uid = user_info.get("sec_uid", "")
            if sec_uid and sec_uid not in all_users:
                all_users.add(sec_uid)
                parsed_results.append({
                    "uid": user_info.get("uid") or user_info.get("id"),
                    "unique_id": user_info.get("unique_id", "") or user_info.get("uniqueId", ""),
                    "nickname": user_info.get("nickname", ""),
                    "signature": user_info.get("signature", ""),
                    "sec_uid": sec_uid,
                    "followers": user_info.get("follower_count", 0),
                    "following": user_info.get("following_count", 0),
                    "video_count": user_info.get("video_count", 0),
                    "total_likes": user_info.get("total_favorited", 0) or user_info.get("heart_count", 0),
                    "verified": user_info.get("verified", False),
                })

        if output_path is None:
            output_path = DEFAULT_OUTPUT_PATH

        output_path = Path(output_path)

        if parsed_results:
            self._save_users_data(parsed_results, output_path, mode="append")

        return parsed_results

    def fetch_similar_user_recommendations(self, sec_uid: str, page_token: str = None,
                                            output_path: str = None) -> List[Dict]:
        """
        获取类似用户推荐

        TikHub API: Get similar user recommendations
        端点: GET /tiktok/app/v3/fetch_similar_user_recommendations

        Args:
            sec_uid: 用户 sec_uid
            page_token: 分页标记，第一次请求时不需要传递，后续请求时传递上一次响应中的 next_page_token 值
            output_path: Excel文件路径

        Returns:
            类似用户推荐列表，包含推荐用户信息
        """
        params = {
            "sec_uid": sec_uid,
        }
        if page_token:
            params["page_token"] = page_token

        result = self._request("GET", "tiktok/app/v3/fetch_similar_user_recommendations", params)

        parsed_results = []
        data = result.get("data", {})
        items = data.get("user_list", []) or data.get("users", []) or data.get("data", [])

        for item in items:
            user_info = item.get("user_info", {}) or item
            if not user_info:
                continue

            parsed_results.append({
                "uid": user_info.get("uid") or user_info.get("id"),
                "unique_id": user_info.get("unique_id", "") or user_info.get("uniqueId", ""),
                "nickname": user_info.get("nickname", ""),
                "signature": user_info.get("signature", ""),
                "sec_uid": user_info.get("sec_uid", ""),
                "followers": user_info.get("follower_count", 0),
                "following": user_info.get("following_count", 0),
                "video_count": user_info.get("video_count", 0),
                "total_likes": user_info.get("total_favorited", 0) or user_info.get("heart_count", 0),
                "verified": user_info.get("verified", False),
            })

        if parsed_results:
            if output_path is None:
                output_path = DEFAULT_OUTPUT_PATH
            self._save_users_data(parsed_results, Path(output_path), mode="append")

        return parsed_results

    def search_videos(self, keyword: str, offset: int = 0, count: int = 20,
                      sort_type: int = 0, publish_time: int = 0, region: str = "US",
                      output_path: str = None) -> Dict:
        """
        获取指定关键词的视频搜索结果

        TikHub API: Get video search results of specified keywords
        端点: GET /tiktok/app/v3/fetch_video_search_result

        Args:
            keyword: 搜索关键词
            offset: 偏移量，用于翻页
            count: 数量，默认20
            sort_type: 排序类型
                0: 相关度
                1: 最多点赞
            publish_time: 发布时间筛选
                0: 不限制
                1: 最近一天
                7: 最近一周
                30: 最近一个月
                90: 最近三个月
                180: 最近半年
            region: 地区，默认US（美国），参考ISO 3166-1 alpha-2国家代码
            output_path: Excel文件路径（默认为 DEFAULT_OUTPUT_PATH）

        Returns:
            视频搜索结果列表
        """
        params = {
            "keyword": keyword,
            "offset": offset,
            "count": count,
            "sort_type": sort_type,
            "publish_time": publish_time,
            "region": region,
        }

        result = self._request("GET", "tiktok/app/v3/fetch_video_search_result", params)

        parsed_results = []
        data = result.get("data", {})
        items = data.get("search_item_list", []) or data.get("data", [])

        for item in items:
            aweme_info = item.get("aweme_info", {}) or item
            if not aweme_info:
                continue

            author = aweme_info.get("author", {})
            stats = aweme_info.get("statistics", {})

            parsed_results.append({
                "type": "video",
                "video_id": aweme_info.get("aweme_id") or aweme_info.get("id"),
                "desc": aweme_info.get("desc", ""),
                "create_time": aweme_info.get("create_time", 0),
                "author": {
                    "uid": author.get("uid") or author.get("id"),
                    "unique_id": author.get("unique_id", "") or author.get("uniqueId", ""),
                    "nickname": author.get("nickname", ""),
                    "sec_uid": author.get("sec_uid", ""),
                    "signature": author.get("signature", ""),
                    "followers": author.get("follower_count", 0),
                },
                "stats": {
                    "play_count": stats.get("play_count", 0),
                    "digg_count": stats.get("digg_count", 0),
                    "comment_count": stats.get("comment_count", 0),
                    "share_count": stats.get("share_count", 0),
                    "collect_count": stats.get("collect_count", 0),
                },
            })

        return parsed_results


    
    """
    def fetch_user_post_v3(self, sec_uid: str = None, unique_id: str = None,
                        max_cursor: int = 0, count: int = 20,
                        sort_type: int = 0) -> Dict:
        
        获取 TikTok 用户的作品列表 (V3 API - 精简数据，更快速)

        TikHub API: Get user homepage video data V3 (simplified data - faster)
        端点: GET /tiktok/app/v3/fetch_user_post_videos_v3

        Args:
            sec_uid: 用户sec_user_id，优先使用sec_user_id获取用户作品数据
            unique_id: 用户unique_id（用户名），如果sec_uid为空则使用unique_id
            max_cursor: 最大游标，用于翻页，第一页为0，第二页为第一次响应中的max_cursor值
            count: 最大数量，建议保持默认值20
            sort_type: 排序类型
                0: 最新
                1: 热门

        Returns:
            解析后的视频信息列表，每个视频包含：
                - id, create_time, desc
                - author: {id, sec_uid, unique_id, nickname, signature}
                - stats: {play_count, digg_count, comment_count, collect_count, share_count}
        
        params = {}
        if sec_uid:
            params["sec_user_id"] = sec_uid
        elif unique_id:
            params["unique_id"] = unique_id
        else:
            raise ValueError("必须提供 sec_uid 或 unique_id")

        params["max_cursor"] = max_cursor
        params["count"] = count
        params["sort_type"] = sort_type

        result = self._request("GET", "tiktok/app/v3/fetch_user_post_videos_v3", params)

        video_data = result.get("data", {})
        items = video_data.get("aweme_list", []) or video_data.get("itemList", []) or video_data.get("items", [])

        parsed_videos = []
        for item in items:
            author = item.get("author", {})
            stats = item.get("statistics", {}) or item.get("stats", {})

            parsed_videos.append({
                "id": item.get("aweme_id") or item.get("id"),
                "create_time": item.get("create_time") or item.get("createTime"),
                "desc": item.get("desc", ""),
                "_raw_item": item,
                "author": {
                    "id": author.get("uid") or author.get("id"),
                    "sec_uid": author.get("sec_uid") or author.get("secUid"),
                    "unique_id": author.get("unique_id") or author.get("uniqueId", ""),
                    "nickname": author.get("nickname", ""),
                    "signature": author.get("signature", ""),
                },
                "stats": {
                    "play_count": stats.get("play_count", 0) or stats.get("playCount", 0),
                    "digg_count": stats.get("digg_count", 0) or stats.get("diggCount", 0),
                    "comment_count": stats.get("comment_count", 0) or stats.get("commentCount", 0),
                    "collect_count": stats.get("collect_count", 0) or stats.get("collectCount", 0),
                    "share_count": stats.get("share_count", 0) or stats.get("shareCount", 0),
                },
            })

        return parsed_videos
    """

    def fetch_user_post_v2(self, sec_uid: str = None, unique_id: str = None,
                           max_cursor: int = 0, count: int = 20,
                           sort_type: int = 0) -> Dict:
        """
        获取 TikTok 用户作品列表 (V2 API - 完整数据)

        TikHub API: Get user homepage video data V2 (full data)
        端点: GET /tiktok/app/v3/fetch_user_post_videos_v2

        注意：V2 API 返回完整数据，包含 text_extra 等字段，可提取更准确的话题标签

        Args:
            sec_uid: 用户sec_user_id，优先使用
            unique_id: 用户unique_id（用户名），如果sec_uid为空则使用
            max_cursor: 最大游标，用于翻页，第一页为0
            count: 最大数量，建议保持默认值20
            sort_type: 排序类型
                0: 最新
                1: 热门

        Returns:
            解析后的视频信息列表，每个视频包含：
                - id, create_time, desc
                - text_extra: 官方话题标签列表
                - author: {id, sec_uid, unique_id, nickname, signature}
                - stats: {play_count, digg_count, comment_count, collect_count, share_count}
        """
        params = {}
        if sec_uid:
            params["sec_user_id"] = sec_uid
        elif unique_id:
            params["unique_id"] = unique_id
        else:
            raise ValueError("必须提供 sec_uid 或 unique_id")

        params["max_cursor"] = max_cursor
        params["count"] = count
        params["sort_type"] = sort_type

        result = self._request("GET", "tiktok/app/v3/fetch_user_post_videos_v2", params)

        video_data = result.get("data", {})
        items = video_data.get("aweme_list", []) or video_data.get("itemList", []) or video_data.get("items", [])

        parsed_videos = []
        for item in items:
            author = item.get("author", {})
            stats = item.get("statistics", {}) or item.get("stats", {})
            text_extra = item.get("text_extra", []) or []

            parsed_videos.append({
                "id": item.get("aweme_id") or item.get("id"),
                "create_time": item.get("create_time") or item.get("createTime"),
                "desc": item.get("desc", ""),
                "text_extra": text_extra,
                "_raw_item": item,
                "author": {
                    "id": author.get("uid") or author.get("id"),
                    "sec_uid": author.get("sec_uid") or author.get("secUid"),
                    "unique_id": author.get("unique_id") or author.get("uniqueId", ""),
                    "nickname": author.get("nickname", ""),
                    "signature": author.get("signature", ""),
                },
                "stats": {
                    "play_count": stats.get("play_count", 0) or stats.get("playCount", 0),
                    "digg_count": stats.get("digg_count", 0) or stats.get("diggCount", 0),
                    "comment_count": stats.get("comment_count", 0) or stats.get("commentCount", 0),
                    "collect_count": stats.get("collect_count", 0) or stats.get("collectCount", 0),
                    "share_count": stats.get("share_count", 0) or stats.get("shareCount", 0),
                },
            })

        return parsed_videos
    
    def fetch_kol_play_data(self, sec_uid: str = None, unique_id: str = None,
                             output_path: str = None) -> Dict:
        """
        获取 KOL 达人的播放数据（最新3个 + 最早2个）并保存到 Excel

        使用 V2 API（精简数据，更快速），不再返回粉丝数和作品数，
        这些数据应在搜索阶段已保存到Excel中。

        Args:
            sec_uid: 用户 sec_user_id（优先）
            unique_id: 用户 unique_id（用户名），如果 sec_uid 为空则使用
            output_path: Excel 文件路径（默认为 DEFAULT_OUTPUT_PATH）

        Returns:
            包含以下字段的字典：
            - 达人昵称, unique_id, signature
            - 播放1-5: 5个视频的播放量
            - 点赞1-5, 评论1-5, 收藏1-5, 分享1-5: 每个视频的互动数据
            - 内容话题: 高频 hashtag 列表
            - sec_uid: 用户ID
        """
        result = self.fetch_user_post_v2(
            sec_uid=sec_uid,
            unique_id=unique_id,
            sort_type=0
        )
        if len(result) < 10:
            return {}

        recent_3 = result[:3]
        oldest_2 = result[-2:]
        all_5 = recent_3 + oldest_2

        first_video = recent_3[0] if recent_3 else {}
        author_info = first_video.get("author", {})

        topic_counter = get_content_topics(result)
        top_topics = list(topic_counter.keys())[:10]
        content_topics = ", ".join(top_topics) if top_topics else ""

        data = {
            "达人昵称": author_info.get("nickname", ""),
            "unique_id": author_info.get("unique_id", ""),
            "signature": author_info.get("signature", ""),
            "内容话题": content_topics,
            "sec_uid": sec_uid or author_info.get("sec_uid", ""),
        }

        for i, video in enumerate(all_5, 1):
            stats = video.get("stats", {})
            data[f"播放{i}"] = stats.get("play_count", 0)
            data[f"点赞{i}"] = stats.get("digg_count", 0)
            data[f"评论{i}"] = stats.get("comment_count", 0)
            data[f"收藏{i}"] = stats.get("collect_count", 0)
            data[f"分享{i}"] = stats.get("share_count", 0)
            data[f"文案{i}"] = video.get("desc", "")[:500]

        if data.get("sec_uid"):
            self.save_kol_to_excel(data, output_path)

        return data   

    def save_kol_to_excel(self, kol_data: Dict, output_path: str = None):
        """
        将 KOL 数据追加或更新到 Excel 文件

        Args:
            kol_data: fetch_kol_play_data 返回的达人数据字典
            output_path: Excel 文件路径（默认为 DEFAULT_OUTPUT_PATH）
        """
        import pandas as pd
        import numpy as np

        if output_path is None:
            output_path = DEFAULT_OUTPUT_PATH

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        required_cols = ["达人昵称", "unique_id", "signature",
                         "播放1", "播放2", "播放3", "播放4", "播放5",
                         "点赞1", "点赞2", "点赞3", "点赞4", "点赞5",
                         "评论1", "评论2", "评论3", "评论4", "评论5",
                         "收藏1", "收藏2", "收藏3", "收藏4", "收藏5",
                         "分享1", "分享2", "分享3", "分享4", "分享5",
                         "文案1", "文案2", "文案3", "文案4", "文案5",
                         "内容话题", "sec_uid", "建联状态", "报价"]

        if output_path.exists():
            df = pd.read_excel(output_path, dtype=str)  # 读取为字符串类型
            # 确保所有必需的列都存在
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
        else:
            df = pd.DataFrame(columns=required_cols)

        sec_uid = kol_data.get("sec_uid", "")
        
        # 检查是否已存在该用户
        if sec_uid and sec_uid in df["sec_uid"].values:
            idx = df[df["sec_uid"] == sec_uid].index[0]
            play_cols = ["播放1", "播放2", "播放3", "播放4", "播放5"]
            has_play_data = all(
                col in df.columns and pd.notna(df.at[idx, col]) and str(df.at[idx, col]) not in ["", "0", "nan"]
                for col in play_cols
            )
            if has_play_data:
                return
            
            # 更新现有行 - 使用重建行的方式避免类型问题
            row_data = df.loc[idx].to_dict()
            row_data["达人昵称"] = str(kol_data.get("达人昵称", row_data.get("达人昵称", "")))
            row_data["unique_id"] = str(kol_data.get("unique_id", row_data.get("unique_id", "")))
            row_data["signature"] = str(kol_data.get("signature", row_data.get("signature", "")))
            row_data["播放1"] = str(int(kol_data.get("播放1", 0) or 0))
            row_data["播放2"] = str(int(kol_data.get("播放2", 0) or 0))
            row_data["播放3"] = str(int(kol_data.get("播放3", 0) or 0))
            row_data["播放4"] = str(int(kol_data.get("播放4", 0) or 0))
            row_data["播放5"] = str(int(kol_data.get("播放5", 0) or 0))
            row_data["点赞1"] = str(int(kol_data.get("点赞1", 0) or 0))
            row_data["点赞2"] = str(int(kol_data.get("点赞2", 0) or 0))
            row_data["点赞3"] = str(int(kol_data.get("点赞3", 0) or 0))
            row_data["点赞4"] = str(int(kol_data.get("点赞4", 0) or 0))
            row_data["点赞5"] = str(int(kol_data.get("点赞5", 0) or 0))
            row_data["评论1"] = str(int(kol_data.get("评论1", 0) or 0))
            row_data["评论2"] = str(int(kol_data.get("评论2", 0) or 0))
            row_data["评论3"] = str(int(kol_data.get("评论3", 0) or 0))
            row_data["评论4"] = str(int(kol_data.get("评论4", 0) or 0))
            row_data["评论5"] = str(int(kol_data.get("评论5", 0) or 0))
            row_data["收藏1"] = str(int(kol_data.get("收藏1", 0) or 0))
            row_data["收藏2"] = str(int(kol_data.get("收藏2", 0) or 0))
            row_data["收藏3"] = str(int(kol_data.get("收藏3", 0) or 0))
            row_data["收藏4"] = str(int(kol_data.get("收藏4", 0) or 0))
            row_data["收藏5"] = str(int(kol_data.get("收藏5", 0) or 0))
            row_data["分享1"] = str(int(kol_data.get("分享1", 0) or 0))
            row_data["分享2"] = str(int(kol_data.get("分享2", 0) or 0))
            row_data["分享3"] = str(int(kol_data.get("分享3", 0) or 0))
            row_data["分享4"] = str(int(kol_data.get("分享4", 0) or 0))
            row_data["分享5"] = str(int(kol_data.get("分享5", 0) or 0))
            row_data["文案1"] = str(kol_data.get("文案1", row_data.get("文案1", "")))[:500]
            row_data["文案2"] = str(kol_data.get("文案2", row_data.get("文案2", "")))[:500]
            row_data["文案3"] = str(kol_data.get("文案3", row_data.get("文案3", "")))[:500]
            row_data["文案4"] = str(kol_data.get("文案4", row_data.get("文案4", "")))[:500]
            row_data["文案5"] = str(kol_data.get("文案5", row_data.get("文案5", "")))[:500]
            row_data["内容话题"] = str(kol_data.get("内容话题", row_data.get("内容话题", "")))
            
            # 重建 DataFrame
            df_list = df.to_dict('records')
            df_list[idx] = row_data
            df = pd.DataFrame(df_list)
            
            df.to_excel(output_path, index=False)
            print(f"已更新 KOL 播放数据: {output_path}")
            return

        # 检查是否已存在该用户
        existing_row = df[df["sec_uid"] == sec_uid] if sec_uid else pd.DataFrame()
        
        # 准备新数据 - 所有值转为字符串或整数避免类型问题
        new_row_data = {
            "达人昵称": str(kol_data.get("达人昵称", "")),
            "unique_id": str(kol_data.get("unique_id", "")),
            "signature": str(kol_data.get("signature", "")),
            "播放1": int(kol_data.get("播放1", 0) or 0),
            "播放2": int(kol_data.get("播放2", 0) or 0),
            "播放3": int(kol_data.get("播放3", 0) or 0),
            "播放4": int(kol_data.get("播放4", 0) or 0),
            "播放5": int(kol_data.get("播放5", 0) or 0),
            "点赞1": int(kol_data.get("点赞1", 0) or 0),
            "点赞2": int(kol_data.get("点赞2", 0) or 0),
            "点赞3": int(kol_data.get("点赞3", 0) or 0),
            "点赞4": int(kol_data.get("点赞4", 0) or 0),
            "点赞5": int(kol_data.get("点赞5", 0) or 0),
            "评论1": int(kol_data.get("评论1", 0) or 0),
            "评论2": int(kol_data.get("评论2", 0) or 0),
            "评论3": int(kol_data.get("评论3", 0) or 0),
            "评论4": int(kol_data.get("评论4", 0) or 0),
            "评论5": int(kol_data.get("评论5", 0) or 0),
            "收藏1": int(kol_data.get("收藏1", 0) or 0),
            "收藏2": int(kol_data.get("收藏2", 0) or 0),
            "收藏3": int(kol_data.get("收藏3", 0) or 0),
            "收藏4": int(kol_data.get("收藏4", 0) or 0),
            "收藏5": int(kol_data.get("收藏5", 0) or 0),
            "分享1": int(kol_data.get("分享1", 0) or 0),
            "分享2": int(kol_data.get("分享2", 0) or 0),
            "分享3": int(kol_data.get("分享3", 0) or 0),
            "分享4": int(kol_data.get("分享4", 0) or 0),
            "分享5": int(kol_data.get("分享5", 0) or 0),
            "文案1": str(kol_data.get("文案1", ""))[:500],
            "文案2": str(kol_data.get("文案2", ""))[:500],
            "文案3": str(kol_data.get("文案3", ""))[:500],
            "文案4": str(kol_data.get("文案4", ""))[:500],
            "文案5": str(kol_data.get("文案5", ""))[:500],
            "内容话题": str(kol_data.get("内容话题", "")),
            "sec_uid": str(sec_uid),
            "建联状态": str(kol_data.get("建联状态", "未建联")),
            "报价": str(kol_data.get("报价", ""))
        }

        df = pd.concat([df, pd.DataFrame([new_row_data])], ignore_index=True)
        df.to_excel(output_path, index=False)
        print(f"已将 KOL 数据追加到 {output_path}")

    def _save_users_data(self, users: List[Dict], output_path: str,
                           mode: str = "append", columns: List[str] = None):
        """保存用户数据"""
        import pandas as pd

        default_columns = ["达人昵称", "unique_id", "signature", "粉丝数", "关注数", "作品数", "获赞数", "sec_uid", "uid", "是否认证"]

        df_data = []
        for u in users:
            df_data.append({
                "达人昵称": u.get("nickname", ""),
                "unique_id": u.get("unique_id", ""),
                "signature": u.get("signature", ""),
                "粉丝数": u.get("followers", 0),
                "关注数": u.get("following", 0),
                "作品数": u.get("video_count", 0),
                "获赞数": u.get("total_likes", 0),
                "sec_uid": u.get("sec_uid", ""),
                "uid": u.get("uid", ""),
                "是否认证": u.get("verified", False),
            })

        if mode == "append" and output_path.exists():
            existing_df = pd.read_excel(output_path)
            if not existing_df.empty and "sec_uid" in existing_df.columns:
                new_df = pd.DataFrame(df_data)
                df = pd.concat([existing_df, new_df], ignore_index=True)
                df = df.drop_duplicates(subset=["sec_uid"], keep="last")
            else:
                df = pd.DataFrame(df_data)
        else:
            df = pd.DataFrame(df_data)

        df.to_excel(output_path, index=False)
        print(f"已保存 {len(df_data)} 条用户数据到 {output_path}")

if __name__ == "__main__":
    client = TikHubClient()

    result = client.fetch_user_post(
        sec_uid="MS4wLjABAAAA4FqTi-up6QWqLJI5Tcnrxvjh2Py7Fs91lqo2JtqjHD5BV00toJMBBlwLWxKsCHdU"
    )
    print(f"获取到 {len(result)} 个视频")
    if result:
        print(f"第一个视频ID: {result[0].get('id')}")
        print(f"第一个视频播放量: {result[0].get('stats', {}).get('play_count', 0)}")
