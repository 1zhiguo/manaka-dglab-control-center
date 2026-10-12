"""Bilingual source catalog for community Manaka missions and utilities.

The catalog is an index only.  It never mirrors or downloads third-party files.
Most source material identifies an F95Zone reply by ordinal number rather than a
stable post id, so those entries open the corresponding thread page and retain
the ordinal prominently in the UI.  Known stable post URLs are overridden.
"""

from __future__ import annotations

F95_THREAD = (
    "https://f95zone.to/threads/"
    "secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/"
)
USER9527_POST = F95_THREAD + "post-20360819"

CATEGORIES = (
    ("core", "基础前置", "Core"),
    ("persistent", "持续任务", "Persistent"),
    ("story", "剧情任务", "Story"),
    ("modes", "小游戏与模式", "Modes"),
    ("utilities", "功能扩展", "Utilities"),
    ("tools", "开发工具与其他", "Tools & Other"),
)

RAW_CATALOG = """#3 | v1 | drchainchair2 | <no name> | -
#11 | v1 | Himiko054 | Manaka's Greatest Adventure. | -
#120 | v1 | BGmkr | Pet Daytime Dares | Hard, but possible.
#180 | v1 | BGmkr | Conbini Climax | Near impossible. Also broken. (final mission not functioning)
#275 | v1 | cactuar | run | Reach Mall from Home in given time
#332 | v1 | EvGem | Walk In Mall | -
#1602 | v2 | tkpj8pn2 | Hide behind an NPC in line | -
#1799 | v2 | tkpj8pn2 | Conbini Cameras | Finally someone done that! <3
#1860 | v1 | SekiYuri | SekiMissions | Must try at least once. Has matches with Greatest Adventure.
#2 | v1 | drchainchair2 | <Set of many missions, see link> | -
#4 | v1 | cactuar | <no name, 3 step mission> | -
#5 | v1 | Banned Octo | <no name, 3 missions> | -
#10 | v1 | hacumefetitopikt.com | Manaka's Bathroom Streak
#33 | v1 | hacumefetitopikt.com | Forgotten Wallet | -
#44 | v1 | hacumefetitopikt.com | Alleyway Gambit | -
#46 | v1 | Soitat | Apartment Fun | -
#63 | v1 | hacumefetitopikt.com | Locked Out | -
#70 | v1 | hacumefetitopikt.com | Park Stroll | -
#94 | v1 | doffin | Yakuza's Punishment | -
#147 | v1 | Tghyt | Slave To Fate | -
#174 | v1 | cfgvuh | schoolbet | -
#175 | v1 | eroeroiz | Stealth Ninja Action | -
#234 | v1 | artemis31 | Performing Tasks From my Master | -
#251 | v1 | jack7791101 | truck. | -
#257 | v1 | BGmkr | Challenge Missions | -
#268 | v1 | artemis31 | Condom Shopping Blackmail | -
#274 | v1 | Muhdog | Late Night Store Run | -
#323 | v1 | bergi | Brat Missions | -
#381 | v1 | Figgobyom | Floor Presentation | -
#386 | v1 | RazMon365 | Pact With Unknown | -
#418 | v1 | Sam OuOB | Exorcist Maiden | (i legit rolled on floor laughing from the mission lore)
#432 | v2 | Suzutsuki117 | Prefect Manaka | -
#466 | v2 | zizheng2019 | The Price of Losing Control | Borderline unplayable. You may try, tho.
#470 | v2 | raptorr64 | Fetch | -
#514 | v2 | muffinmad | Kenji Missions | -
#696 | v2 | cactuar | Blackmail | -
#757 | v1 | 9-9-9-9-9 | Masturbation Marathon | Apply patch in #1021 if not using Futa
#798 | v2 | mcnv | Camera flash | -
#802 | v2 | hacumefetitopikt.com | Adventure time | Also contains Timestop utility. Use post #989 version tho.
#819 | v1 | RandomUsername5692 | Alice's New Life as an Exhibitionist | Unfinished and abandoned
#1132 | v2 | ria.jamie | Mistake (EN/JP) | Great story missions
#1520 | v1 | isnull | Missing Person Case (EN/CN) | -
#1528 | v1 | isnull | Chapter of the Night (EN/CN) | -
#1529 | v1 | wertocean | Nocturnal Summons | -
#1654 | v2 | hacumefetitopikt.com | Midnight Meditation | -
#1676 | v1 | in4theride75 | The Trap | -
#1730 | v2 | n96kraft | The [Crucible, Dare, Gauntlet] | pack of 3 missions
#2267 | v2 | tkpj8pn2 | Glory Hole Trap | -
#2279 | v2 | raptorr64 | Exposure Urges | -
Thread | v2 | inaruslynx | Xxxhibitionist Sex Mod | -
#472 | v2 | cherry_sigma | Multi Stage Item Search (MSIS) | There's a MSIS+ version in #1877 below
#477 | v2 | cherry_sigma | Aftermath | -
#637 | v2 | hacumefetitopikt.com | Dial A Kidnapper | -
#1050 | v2 | hacumefetitopikt.com | Hunted | -
#1084 | v2 | Suzutsuki117 | Naked Key Snatch | -
#1109 | v2 | Suzutsuki117 | Naked Coat Snatch | -
#1126 | v2 | hacumefetitopikt.com | Aftermath Plug-in for Hunted | Requires Hunted (#1050)
#1223 | v2 | Suzutsuki117 | Hide&Seek | -
#1341 | v2 | Larpus | TimedCuffGame | -
#1420 | v2 | Suzutsuki117 | Female Alert | Requires NPC Mod Behaviour
#1557 | v2 | |||Byo||| | Traveling Tasks | Interesting concept of saving the state between points
#1862 | v2 | Suzutsuki117 | Home Key Search | Like a drone mission, but better.
#1877 | v2 | cherry_sigma + D. Dog Cat | MSIS+ | Upgraded version of MSIS (#472)
#1962 | v2 | hacumefetitopikt.com | Neighborhood Streak and Flashing Watch (NSFW: The Hunt) | just try it.
#1975 | Plugins + v2 | yoloahah95 | Hardcore Manaka | A set of different addons AND persistent missions. Read link.
#2033 | v2 | Eicosa | FansChat | (Finally, exhibitionism.)
#2048 | (Plugins) v2 | TsunoDragon | Ruin Exposure Mission (JP/EN) | Requires several other mods, see link.
#2063 | v2 | Maorate | Lilith's Fun | -
#2098 | v2 | raptorr64 | Vampire Manaka | -
#2183 | v2 | Eicosa + Nn312 | Fans Chat v14 | Expanded version of #2033.
#2202 | v2 | Eicosa + skaderp | Fans Chat + Replies | Also #2033. Possibly based on older version of Fans Chat.
#26 | v1 | InvasionOfZeroes | CheeseRP | Useful, lol
#486 | v2 | cherry_sigma | Item Shifter | -
#491 | v2 | cherry_sigma | Out Of Bounds Warp | Useful for funny photos or shortcuts in DT
#512 | Plugin | cherry_sigma | Incuffable Manaka | Imo should be a part of base game
#528 | v2 | Suzutsuki117 | Penalty Vibrator | -
#540 | Plugin | cherry_sigma | NPCs Got Used To It | No gameover, basically.
#546 | Plugin | cherry_sigma | Nothing Left Outside | May break many Story missions.
#820 | v2 | |||Byo||| | Moaning | -
#871 | v2 | AkameVanish | dropClothes | Adds ability to drop and pickup clothes like coat
#883 | v2 | tkpj8pn2 | NPCs Pickup Items | -
#936 | v2 | Throwwuwway | Orgasm Extender | -
#972 | v2 | Throwwuwway | Expose Ecstasy | -
#989 | v2 | hacumefetitopikt.com | Timestop (on orgasm) | Patched version.
#1010 | v2 | HallumiFriend | Exposure Ecstasy | -
#1048 | v2 | |||Byo||| | Anal Plug Animation | -
#1048 | v2 | |||Byo||| | Defined Ecstasy | (oh god that's a lot of sliders)
#1075 | v2 | HallumiFriend | Cosplay Shop | Rebuy lost items while outside
#1078 | v2 | Suzutsuki117 | Auto Ecstasy | -
#1125 | v2 | Suzutsuki117 | Conditional Home Door | -
#1265 | v2 | hacumefetitopikt.com | Stamina Booster | Works both ways
#1291 | Plugin | [unknown] + notgold123 | Restore missing sounds for Clit and Nipple rotors.
#1328 | v2 | screeone + tkpj8pn2 | Broken Vibe | Better/Worse Random for vibes
#1564 | Plugin | LoidM42 | Desperate Dash | dash on High vibrator mode
#1597 | v2 | AkaiKo | Waist Override | -
#1669 | v2 | AkaiKo | FindMy | finally. working locator.
#1830 | v2 | raptorr64 | EdgingVibe | Replaces "High" vibrator setting with "Edging" setting
#1865 | v2 | Suzutsuki117 | Body Paint Kit Vendor | -
#1907 | v2 | 9-9-9-9-9 | Always Pee | "Go and flood the town，Manaka!" - author (c)
#1950 | v2 | raptorr64 + Th3Unkn0w1ng | Blinding Light | Concept mod for using lighting for suffering
#1953 | v2 | tkpj8pn2 | Fix Drop Load Bug | DON'T restore Key and Remote on save reload when dropped.
#2014 | v2 | Suzutsuki117 | Auto Brightness | -
#2020 | v2 | Alucard80 + momomodqqd | Drop casual clothes on actions | -
#2038 | v2 | Saileka | More Vibrator Settings (CN) | -
#2042 | v2 | tkpj8pn2 | Parkour | Y-level movement for Manaka, updated.
#2059 | v2 | raptorr64 + Saileka | Adaptive Light | Better interaction with light sources (maybe a copy of #1950, didn't check)
#2062 | Plugin | Manneeon | Piercing Fixes | Hide things when coat is closed + anim fixes
#2062 | Plugin | Manneeon | Mask Color Fixes | Don't discolor the mask
#2109 | v2 | tkpj8pn2 | Clothing Drop | -
#2132 | v2 | Suzutsuki117 | Game Over After Sex | -
#2140 | v2 | hacumefetitopikt.com | Unhandcuff | Updated from #540
#2159 | v2 | FarenGate3 | Piston Control | Piston machines are now controlled
#2171 | v2 | FarenGate3 | Keyed Shibari | Shibari now act like Keyed handcuffs
#2182 | Plugin | Nn312 | Custom Windows | Makes game window resizable
#2188 | v2 | raptorr64 + skytester | Edging Vibe (CN) | Modified and translated from #1830
#2229 | v2 | AkameVanish + useruser9527 | DropClothes | Modified from #871
#2229 | v2 | Suzutsuki117 + useruser9527 | Auto Ecstasy | Modified from #1078
Thread | Plugin | CinaBunZee | Texture Edits for Manaka
#978 | Various | useruser9527 | Simplified Chinese (简体中文) translation of various mods in this thread.
#946 | Text (v2) | hacumefetitopikt.com | Tutorial for creating a mission, spans over several posts.
#834 | Tool (v2) | AkameVanish | Tools for easier v2 mission creation
#1484 | Text (v2) | shcinedake | Simplified Chinese translation of Custom Mission v2 code documentation
#1596 | Text | zzz4200+jljljl37+eltiachan | How to edit game save file (on example of equipment effects)
#1708 | v1 | SenpaiSource | Simpliest persistent v1 mission. Code can be used as a reference.
#2043 | Demo (v2) | hacumefetitopikt.com | Example of modding API for Hunted (Mini-games#1050)
#2068 | Tool (v1) | [Unknown] + Kanokanoka | Fix_TimerHandcuff | Tool for adding/removing janky timed handcuffs
#2180 | Tool (v2) | Nn312 | Fine-tuned controls for developers for sex scenes in your missions.
#2184 | Audio | Nn312 | Extracted in-game audio assets from SFM.
#2242 | Library (v2) | hacumefetitopikt.com | Translations library for your missions.
#2421 | Tool (v2) | hacumefetitopikt.com | A goddamn linter/analyser for the .code files.
#2421 | Text (v2) | hacumefetitopikt.com | Notepad++ syntax highlighting format file"""

ZH_NAMES = """未命名持续任务
真菜香的大冒险
白天宠物挑战
便利店高潮挑战
限时奔跑
商场漫步
排队时躲在 NPC 身后
便利店摄像头
Seki 系列任务
多任务合集
未命名三阶段任务
未命名三任务合集
真菜香的厕所裸奔
遗忘的钱包
小巷赌局
公寓乐趣
被锁在门外
公园漫步
黑道的惩罚
命运奴役
校园赌局
潜行忍者行动
主人的任务
卡车任务
挑战任务
安全套购物勒索
深夜商店跑腿
淘气鬼任务
地板展示
未知契约
驱魔少女
风纪委员真菜香
失控的代价
取物任务
健司任务
勒索
自慰马拉松
相机闪光
冒险时间
爱露出的爱丽丝新生活
失误（英/日）
失踪人口案件（英/中）
夜之章（英/中）
夜间召唤
午夜冥想
陷阱
试炼三部曲
光荣洞陷阱
暴露冲动
露出性爱模式
多阶段物品搜索（MSIS）
事后状态
呼叫绑匪
猎杀模式
裸体钥匙争夺
裸体外套争夺
猎杀模式事后插件
捉迷藏
限时手铐游戏
女性警戒
旅行任务
家门钥匙搜索
MSIS 增强版
社区裸奔与闪光手表
硬核真菜香
粉丝聊天
毁灭暴露任务（日/英）
莉莉丝的乐趣
吸血鬼真菜香
粉丝聊天 v14
粉丝聊天与回复
轻松 RP
物品位移器
越界传送
无法上铐的真菜香
惩罚震动器
NPC 习以为常
户外一无所有
呻吟
丢弃衣物
NPC 拾取物品
高潮延长
暴露快感
高潮时停
暴露快感
肛塞动画
自定义快感
角色扮演商店
自动快感
条件式家门
耐力增强
恢复敏感部位转子音效
故障震动器
绝望冲刺
腰部覆盖
寻找定位
寸止震动
人体彩绘商店
随时小便
致盲之光
修复丢弃物读档问题
自动亮度
动作时丢弃便服
更多震动器设置（中）
跑酷
自适应灯光
穿孔修复
面具颜色修复
衣物掉落
性爱后游戏结束
解除手铐
活塞控制
带钥匙的绳缚
自定义窗口
寸止震动（中）
丢弃衣物（汉化修改版）
自动快感（汉化修改版）
真菜香材质修改
本帖 Mod 简体中文汉化
任务制作教程
V2 任务制作工具
Custom Mission V2 文档简中翻译
存档修改教程
最简 V1 持续任务示例
猎杀模式 Mod API 示例
定时手铐修复工具
性爱场景开发者精细控制
游戏音频资源提取
任务翻译库
.code 文件检查与分析器
Notepad++ 语法高亮文件""".splitlines()


def _page_url(reference: str) -> str:
    if reference == "Thread":
        return F95_THREAD
    number = int(reference.removeprefix("#"))
    page = ((number - 1) // 20) + 1
    return F95_THREAD if page == 1 else f"{F95_THREAD}page-{page}"


def _category_for_index(index: int) -> str:
    if index < 9:
        return "persistent"
    if index < 49:
        return "story"
    if index < 71:
        return "modes"
    if index < 117:
        return "utilities"
    return "tools"


def _parse_rows() -> list[dict]:
    rows = []
    source_lines = RAW_CATALOG.splitlines()
    if len(source_lines) != len(ZH_NAMES):
        raise RuntimeError("Mod catalog names are out of sync")
    for index, (line, name_zh) in enumerate(zip(source_lines, ZH_NAMES, strict=True)):
        parts = line.split(" | ", 4)
        reference, kind, author, name_en = parts[:4]
        note_en = parts[4] if len(parts) == 5 else ""
        url = USER9527_POST if reference == "#978" else _page_url(reference)
        rows.append(
            {
                "category": _category_for_index(index),
                "reference": reference if reference != "Thread" else "Thread",
                "kind": kind,
                "author": author,
                "nameEn": name_en,
                "nameZh": name_zh,
                "noteEn": "" if note_en == "-" else note_en,
                "url": url,
                "pinned": False,
            }
        )
    return rows


CATALOG_ROWS = tuple(_parse_rows())


def build_mod_catalog(language: str) -> list[dict]:
    """Return localized display fields while preserving both names for search."""

    english = language == "en"
    category_names = {key: en if english else zh for key, zh, en in CATEGORIES}
    pinned = (
        {
            "category": "core",
            "reference": "Thread",
            "kind": "Plugin / V1",
            "author": "F95Zone community",
            "nameEn": "CustomMission 1 (V1 Loader)",
            "nameZh": "CustomMission 1（V1 任务加载器）",
            "noteEn": "Required loader for V1 JSON missions.",
            "url": F95_THREAD,
            "pinned": True,
        },
        {
            "category": "core",
            "reference": "Thread",
            "kind": "Plugin / V2",
            "author": "F95Zone community",
            "nameEn": "CustomMission 2 (V2 Loader)",
            "nameZh": "CustomMission 2（V2 任务加载器）",
            "noteEn": "Required loader for V2 .code packages.",
            "url": F95_THREAD,
            "pinned": True,
        },
    )
    result = []
    for source in (*pinned, *CATALOG_ROWS):
        item = dict(source)
        item["displayName"] = source["nameEn"] if english else source["nameZh"]
        item["alternateName"] = source["nameZh"] if english else source["nameEn"]
        item["categoryLabel"] = category_names[source["category"]]
        item["note"] = source["noteEn"]
        item["searchText"] = " ".join(
            str(source.get(key, ""))
            for key in ("nameEn", "nameZh", "author", "reference", "kind", "category")
        ).lower()
        result.append(item)
    return result

