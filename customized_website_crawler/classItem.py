import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
import json


@dataclass
class Item:
    itemId: str = ''                      # 项目ID，主键
    itemTitle: str = ''                   # 项目标题
    itemSummary: Optional[str] = None  # 项目摘要
    itemContent: Optional[str] = None  # 项目正文/说明内容文本
    itemSource: str = ""             # 项目来源平台
    itemURL: str = ""                # 项目链接地址
    itemLength: Optional[int] = None  # 项目内容长度：正文文本长度、视频时长等
    itemPostTime: str = ""           # 项目发布时间, yyyy-MM-dd HH:mm:ss 格式
    itemAuthorId: Optional[str] = None   # 项目作者/发布者ID
    itemAuthorName: Optional[str] = None # 项目作者/发布者名称
    itemAuthorURL: Optional[str] = None  # 项目作者/发布者主页链接地址
    itemViewNum: Optional[int] = None    # 项目被浏览数
    itemCommentNum: Optional[int] = None # 项目评论数
    itemLikeNum: Optional[int] = None    # 项目点赞数
    itemCollectNum: Optional[int] = None # 项目收藏数
    itemShareNum: Optional[int] = None   # 项目转发/分享数
    itemAccessTime: str = ""         # 项目浏览或采集到的时间, yyyy-MM-dd HH:mm:ss 格式

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=4)

    @staticmethod
    def json2File(itemList: List["Item"], filePath: str) -> int:
        """
        将 itemList 写入 filePath，带去重功能。
        - 若 filePath 以 .jsonl/.ndjson 结尾：采用 NDJSON 逐行“真实追加”；
        - 否则视为 .json 数组文件：读取 → 合并去重 → 写回。
        返回值：本次新增写入的去重后条目数。
        """
        # 预处理：过滤空 itemId，先在传入列表内去重（保持后出现的覆盖先出现的）
        filtered: Dict[str, dict] = {}
        for it in itemList:
            if not it or not it.itemId:
                continue
            filtered[it.itemId] = asdict(it)

        if not filtered:
            return 0

        _, ext = os.path.splitext(filePath)
        ext = ext.lower()

        # 路径所在目录
        dirpath = os.path.dirname(filePath)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)

        # print(ext)
        # --- JSON Lines 模式：.jsonl / .ndjson ---
        if ext in (".json", ".jsonl", ".ndjson"):
            # 读取已有 itemId 集，避免重复写入
            existing_ids = set()
            if os.path.exists(filePath):
                with open(filePath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict) and "itemId" in obj:
                                existing_ids.add(obj["itemId"])
                        except json.JSONDecodeError:
                            # 略过坏行
                            continue

            to_append = [v for k, v in filtered.items() if k not in existing_ids]
            if not to_append:
                return 0

            with open(filePath, "a", encoding="utf-8") as f:
                print(f'正在写入数据:{filePath}')
                for obj in to_append:
                    f.write(json.dumps(obj, ensure_ascii=False))
                    f.write("\n")
            return len(to_append)
        return None

        # # --- 普通 JSON 数组模式：.json 或其他后缀 ---
        # existing_map: Dict[str, dict] = {}
        # if os.path.exists(filePath) and os.path.getsize(filePath) > 0:
        #     try:
        #         with open(filePath, "r", encoding="utf-8") as f:
        #             data = json.load(f)
        #         if isinstance(data, list):
        #             for obj in data:
        #                 if isinstance(obj, dict) and "itemId" in obj and obj["itemId"]:
        #                     existing_map[obj["itemId"]] = obj
        #         else:
        #             # 如果不是数组，视为空数组开始（避免破坏用户原文件结构）
        #             pass
        #     except (json.JSONDecodeError, OSError):
        #         # 文件损坏或不可解析，视为空数组
        #         pass
        #
        # # 合并去重：保留文件中已有项（旧）+ 追加新项（新覆盖旧）
        # merged = {**existing_map, **filtered}
        # # 为了可读性，写回为数组（保持 stable 顺序：先已有后新增）
        # # 先把 existing_map 的 key 顺序保留，再加上新增的 key
        # ordered_items = []
        # seen = set()
        # for k in existing_map.keys():
        #     ordered_items.append(merged[k])
        #     seen.add(k)
        # for k, v in merged.items():
        #     if k not in seen:
        #         ordered_items.append(v)
        # new_count = len(ordered_items) - len(existing_map)
        #
        # with open(filePath, "w", encoding="utf-8") as f:
        #     json.dump(ordered_items, f, ensure_ascii=False, indent=2)
        #
        # return new_count

