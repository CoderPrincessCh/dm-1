import requests
import re
import csv
from time import sleep
from html import unescape

DRAMALIST_API = "https://www.missevan.com/dramaapi/filter"
SEARCH_API = "https://www.missevan.com/dramaapi/search"
headers = {
    "User-Agent": "Mozilla/5.0"
}

def clean_html(raw_html):
    # 去除 HTML 标签
    text = re.sub(r"<.*?>", "", raw_html)
    return unescape(text)

def extract_producers(abstract_html: str):
    text = clean_html(abstract_html)

    # 提取“联合出品”、“出品”、“联合制作” 等句子
    match = re.search(r"(猫耳FM.*?出品|.*?联合出品|.*?出品)", text)
    producers = match.group(0).strip() if match else ""

    has_maoer = "猫耳FM" in producers
    return producers, "是" if has_maoer else "否"

def extract_episode_counts(abstract_html: str):
    text = clean_html(abstract_html)

    # 优先匹配：9集正剧 + 4个番外
    combo_match = re.search(
        r"(\d+)\s*[集话期]+\s*正剧\s*[,、，\s]*\s*(\d+)\s*[集话期]*\s*(番外|花絮|小剧场|福利)?",
        text
    )
    if combo_match:
        main_eps = int(combo_match.group(1))
        extra_eps = int(combo_match.group(2))
        total_eps = main_eps + extra_eps
    else:
        # 匹配：共X集正剧 / 正剧X集
        alt_main_match = re.search(r"(?:正剧\s*共?|共\s*)?(\d+)\s*[集话期]\s*正剧", text)
        if alt_main_match:
            main_eps = int(alt_main_match.group(1))
            total_eps = main_eps
        else:
            # 匹配：共X集（总集数）
            total_match = re.search(r"共\s*(\d+)\s*[集话期]", text)
            total_eps = int(total_match.group(1)) if total_match else None

            # 匹配：含X集番外等
            extra_match = re.search(r"含\s*(\d+)\s*[集话期]?.*?(番外|花絮|小剧场|福利)", text)
            extra_eps = int(extra_match.group(1)) if extra_match else 0

            main_eps = total_eps - extra_eps if total_eps is not None else None

    # 提取“前X集免费”
    free_match = re.search(r"(?:前|首)\s*(\d+)\s*[集话期]?.*?(免费|限免)", text)
    free_eps = int(free_match.group(1)) if free_match else 0

    # 付费集数 = 正剧 - 免费集数（不能小于0）
    if main_eps is not None:
        paid_eps = max(main_eps - free_eps, 0)
    else:
        paid_eps = None

    return total_eps, main_eps, paid_eps


def fetch_drama_list_page(page: int):
    url = f"{DRAMALIST_API}?filters=0_0_0_0&page={page}&order=1&page_size=20&type=3"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["info"]["Datas"]

def fetch_all_seasons_by_name(drama_name: str):
    """
    根据主剧名搜索，返回所有匹配剧（包含多季），
    返回列表，每个元素是 dict，包含价格、集数、名字、abstract
    """
    params = {"s": drama_name, "page": 1}
    resp = requests.get(SEARCH_API, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    candidates = resp.json()["info"]["Datas"]

    results = []
    for item in candidates:
        name = item.get("name", "")
        price_diamond = item.get("price", 0)

        # 只保留价格大于0的
        if price_diamond <= 0:
            continue

        # 过滤只要包含主剧名的结果
        if drama_name in name:
            abstract = item.get("abstract", "")
            total_eps, main_eps, paid_eps = extract_episode_counts(abstract)
            results.append({
                "剧名": name,
                "价格钻石": price_diamond,
                "总集数": total_eps,
                "正剧集数": main_eps,
                "abstract": abstract,
                "付费集数": paid_eps,
            })

    if not results:
        print(f"⚠️ 未找到匹配剧目: {drama_name}")
    return results


def clean_drama_name(name: str) -> str:
    """
    去掉“第X季”、“上季”、“下季”、“全一季”、“合集”等后缀，仅保留主剧名
    """
    return re.sub(r"[\s·]*(第[一二三四五六七八九十1234567890]+季|全[一二三四五六七八九十1234567890]+季|上季|下季|合集)$", "", name).strip()


def process_one_drama(drama):
    raw_name = drama["name"]
    drama_name = clean_drama_name(raw_name)
    drama_id = drama["id"]

    all_seasons = fetch_all_seasons_by_name(drama_name)
    results = []

    if not all_seasons:
        print(f"⚠️ {raw_name} 未找到任何季，跳过")
        return []

    for season in all_seasons:
        price_rmb = season["价格钻石"] / 10
        main_eps = season["正剧集数"]
        paid_eps = season["付费集数"]

        if paid_eps is None or paid_eps == 0:
            unit_price = 0
        else:
            unit_price = round(price_rmb / paid_eps, 2)

        if main_eps is None or main_eps == 0:
            avg_price = 0
            print(f"⚠️ {season['剧名']} 无法计算集均价（正剧未知或为0）")
        else:
            avg_price = round(price_rmb / main_eps, 2)

        results.append({
            "剧名": season["剧名"],
            "剧ID": drama_id,
            "总集数（含番外）": season["总集数"] if season["总集数"] else "未知",
            "正剧集数": main_eps if main_eps else "未知",
            "总价（元）": round(price_rmb, 2),
            "集均价（元）": avg_price,
            "付费集数": paid_eps if paid_eps else "未知",
            "付费集单价（元）": unit_price

        })

    return results

def main(export_csv=True):
    result = []
    page = 1
    max_pages = 100  # 最大抓取页数限制

    while True:
        if page > max_pages:
            print(f"📢 已达到最大抓取页数 {max_pages}，结束抓取。")
            break

        print(f"📦 正在抓取第 {page} 页剧列表...")
        try:
            dramas = fetch_drama_list_page(page)
        except Exception as e:
            print(f"❗ 第 {page} 页获取失败：{e}")
            break

        if not dramas:
            print("✅ 抓取完毕")
            break

        for drama in dramas:
            if drama.get("pay_type") != 2:
                continue

            season_results = process_one_drama(drama)
            if season_results:
                result.extend(season_results)
                for data in season_results:
                    print(f"✅ 收录：{data['剧名']} | 正剧{data['正剧集数']}集 | 集均价：¥{data['集均价（元）']}")

            sleep(0.3)

        page += 1
        sleep(0.5)

    if export_csv:
        with open("全部付费广播剧_集均价统计.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "剧名", "剧ID", "总集数（含番外）", "正剧集数", "付费集数", "总价（元）", "集均价（元）", "付费集单价（元）"
            ])
            writer.writeheader()
            writer.writerows(result)
        print("📄 导出完成：全部付费广播剧_集均价统计.csv")

    return result

if __name__ == "__main__":
    main()
