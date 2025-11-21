import uuid
from urllib.parse import urljoin, urlparse
import random
import time

import DrissionPage.errors

from classItem import Item
from time import sleep
from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from tqdm import tqdm
from .utils.utils import parse_post_time,SingleProcessDrissionPageBrowser

# ---------------- 站点配置（按实际页面改） ----------------
SOURCE = '134_imemo'
MAX_THREADS  = 12  # 线程数量
BASE_URL = "https://www.imemo.ru/en/news/events"   # 新闻列表页



CARD_SELECTOR = 'css:.post-list div.post '        # 每条新闻卡片
TIME_SELECTOR = 'css:.text-content .date'  # 完整的css定位
TITLE_SELECTOR = 'css:.text-content h4'  # 完整的css定位
URL_SELECTOR= 'css:.text-content div a'  # 完整的css定位
SCROLL_STEP_PX = 1600                   # 每次下拉步长
MAX_SCROLLS = 100                       # 最大滚动次数兜底
CONFIRM_EXTRA_SCROLLS = 2               # 看到“昨天/更早”后，再多滚几次确认
ACCEPT_RELATIVE_TIME = True             # 是否解析“x分钟前/小时前/昨天”等
TIME_THRESHOLD = 1                      # 时间限制 单位/天



def make_abs(url: str) -> str:
    if not url:
        return ""
    return url if bool(urlparse(url).netloc) else urljoin(BASE_URL, url)
# ----------------- 抓取主流程（DrissionPage） -----------------
def crawl_today_news_by_drissionpage(baseUrl:str) -> list[Item]:
    """
    返回“今天”的新闻列表（字典结构），直到遇到“昨天或更早”的新闻为止。
    只收集今天的；昨天或更早的只作为停止信号，不收集。
    """
    try:
        co = ChromiumOptions()
        co.set_argument('--proxy-server=http://127.0.0.1:7897')
        browser = ChromiumPage(co)
        sleep(3)
        home_tab = browser.new_tab()
        home_tab.get(baseUrl)  # 打开列表页

        items: list[dict] = []
        for i in range(MAX_SCROLLS):
            # 解析已加载卡片
            # 解析这一页所有的date
            dates = []
            news_dates = home_tab.eles(TIME_SELECTOR)
            for newsDate in news_dates:
                newsDate = parse_post_time(newsDate.text.strip(), False)
                dates.append(newsDate)
            lastNewTime = dates[-1]
            # print(lastNewTime)

            # 解析这一页所有的title
            titles = []
            news_titles = home_tab.eles(TITLE_SELECTOR)
            for newsTitle in news_titles:
                newsTitle = newsTitle.text
                titles.append(newsTitle)


            # 解析这一页所有的url
            urls = []
            news_urls = home_tab.eles(URL_SELECTOR)
            for newsUrl in news_urls:
                newsUrl = newsUrl.attr('href')
                urls.append(newsUrl)

            # 在时间限制内的 上述三种信息 合并到metas中
            metas = []
            if len(dates) == len(news_dates) ==len(urls):
                for j in range(len(dates)):
                    print(dates[j])
                    if (datetime.now(lastNewTime.tzinfo).date() - dates[j].date()).days < TIME_THRESHOLD:
                        metas.append({"itemURL": urls[j], "itemPostTime": dates[j].strftime("%Y-%m-%d %H:%M:%S"), "itemTitle": titles[j]})

            # 开始遍历该页限定时间内的新闻
            print(f'总共有{len(metas)}个文章要爬取')
            # —— 详情并发：同一 Chromium + 多线程 + 多 Tab（实验性） —— #
            lock_new_tab = threading.Lock()  # 保护 br.new_tab()
            try:
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
                    futs = [ex.submit(get_detail_paper_data, m, browser, lock_new_tab) for m in metas]
                    print(f'总共有{len(futs)}个任务等待返回')
                    for fut in tqdm(as_completed(futs), total=len(futs), desc="处理中", unit="任务"):
                        item = fut.result()
                        if item:
                            items.append(item)
            finally:
                ...
            if (datetime.now(lastNewTime.tzinfo).date() - lastNewTime.date()).days > TIME_THRESHOLD:
                print(lastNewTime.date())
                break
            # 执行翻页
            next_page_ele = home_tab.ele('css:.pagination').eles('css:li')[-1]
            next_page_ele.click()
            # 等待一点时间让接口/渲染完成（也可结合 page.wait.xxx）
            sleep(random.uniform(0.6, 1.2))
            print(f'翻页{i + 1}次')
    finally:
        browser.quit()
    return items

def get_detail_paper_data(meta, browser, lock_new_tab):
    print('开始获取主页详细信息')
    with lock_new_tab:
        tab = browser.new_tab('about:blank')
    temp_item = Item()
    tab.get(meta['itemURL'])
    sleep(2)

    # itemUrl
    temp_item.itemURL = meta['itemURL']

    # itemId
    itemId = str(uuid.uuid4())
    temp_item.itemId = itemId

    # title & postTime
    temp_item.itemTitle = meta['itemTitle']
    temp_item.itemPostTime = meta['itemPostTime']

    # itemAuthorName
    temp_item.itemAuthorName = ''

    # itemAuthorURL
    temp_item.itemAuthorURL = ''

    # itemAuthorId
    temp_item.itemAuthorId = ''



    #itemSummary
    itemSummary = ''
    temp_item.itemSummary = itemSummary

    #itemContent
    content = ''
    try:
        p_list = tab.eles('css:.text-content p')
    except:
        print("没有定位到文章")
        return
    for k in p_list:
        content += k.text
    temp_item.itemContent = content


    #itemSource
    temp_item.itemSource = SOURCE

    # itemLength
    temp_item.itemLength = len(temp_item.itemContent)

    # itemViewNum  *
    temp_item.itemViewNum = 0

    # itemCommentNum
    comment_num = 0
    try:
        comment_ele = tab.ele("css:.comments-title")
        if comment_ele:
            comment_num = int(comment_ele.text.replace('Comments (', '').replace(')', '').strip())
    except:
        pass
    temp_item.itemCommentNum = comment_num


    # itemLikeNum
    like_num = 0
    temp_item.itemLikeNum = like_num

    # itemCollectNum
    collect_num = 0
    temp_item.itemCollectNum = collect_num

    # itemShareNum
    temp_item.itemShareNum = 0

    # itemAccessTime
    temp_item.itemAccessTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    print(temp_item)
    tab.close()
    return temp_item


def run():
    items = crawl_today_news_by_drissionpage(BASE_URL)
    Item.json2File(items, f'./data/{SOURCE}/{SOURCE}_{datetime.today().strftime("%y%m%d")}.json')
    result = {}
    for index, item in enumerate(items):
        title = item.itemTitle
        url = item.itemURL
        mobile_url = ''
        result[title] = {
            "ranks": [index + 1],
            "url": url,
            "mobileUrl": mobile_url,
        }
    return result

if __name__ == '__main__':
    ...
