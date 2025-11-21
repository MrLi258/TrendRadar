import random
from datetime import datetime, time, timedelta
from dateutil import parser as dtparser
from zoneinfo import ZoneInfo

SITE_TZ = ZoneInfo("Asia/Shanghai")       # 用站点/期望判断的时区
from DrissionPage import ChromiumPage
# ----------------- 时间工具 -----------------
def parse_post_time(raw: str, accept_relative_time=False) -> datetime | None:
    """把站点上显示的时间解析为带时区的 datetime（站点时区）"""
    if not raw:
        return None

    try:
        s = raw.strip()
        # 把法语对应的月份替换成英语
        months_fr = {
            'janvier': 'January',
            'février': 'February',
            'mars': 'March',
            'avril': 'April',
            'mai': 'May',
            'juin': 'June',
            'juillet': 'July',
            'août': 'August',
            'septembre': 'September',
            'octobre': 'October',
            'novembre': 'November',
            'décembre': 'December'
        }

        s_lower = s.lower()
        for fr, en in months_fr.items():
            if fr in s_lower:
                s_lower = s_lower.replace(fr, en)
                break




        now = datetime.now(SITE_TZ)
        # 可选：处理相对时间
        if accept_relative_time:
            if "刚刚" in s:
                return now
            if "分钟前" in s:
                try:
                    mins = int(s.split("分钟")[0])
                    return now - timedelta(minutes=mins)
                except Exception:
                    pass
            if "小时前" in s:
                try:
                    hours = int(s.split("小时")[0])
                    return now - timedelta(hours=hours)
                except Exception:
                    pass
            if "天前" in s:
                try:
                    days = int(s.split("天")[0])
                    return now - timedelta(days=days)
                except Exception:
                    pass
            if "今天" in s:
                print('今天匹配成功')
                try:
                    time_part = s.replace('今天', '').strip()
                    full_time = datetime.now().strftime("%Y-%m-%d") + " " + time_part
                    return datetime.strptime(full_time, "%Y-%m-%d %H:%M")
                except Exception as e:
                    print(e)
                    pass
            if s == "昨天":
                # 给一个保守时间点（中午），只用于“是否当日”的判断
                return (now - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

        # 绝对时间：尽量交给 dateutil 解析
        dt = dtparser.parse(s_lower, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SITE_TZ)
        else:
            dt = dt.astimezone(SITE_TZ)
        return dt
    except Exception as e:
        print(e)
        return None



class SingleProcessDrissionPageBrowser:
    def __init__(self, scroll:bool = True):
        self.browser = ChromiumPage()
        self.scroll = scroll
        self.node_css = ''
        self.last_round_node_count = 0
        self.current_node_count = 0
        self.last_page_num = 1
        self.current_page_num = 1
        self.no_new_rounds = 3  # 不变的轮次，表示下拉或者翻页到底，退出
    def getChromiumPage(self):
        return self.browser

    def tabNextPage(self, tab, scroll_step_px:int = 1600):
        if self.scroll:
            # 执行下拉（用 JS 最通用）
            tab.run_js(f"window.scrollBy(0, {scroll_step_px});")
            # 等待一点时间让接口/渲染完成（也可结合 page.wait.xxx）
            time.sleep(random.uniform(0.6, 1.2))
            tab.eles(self.node_css)

