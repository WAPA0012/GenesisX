"""统一的 LLM 输出清理（CoT 残留治理，2026-08 重构）。

step_plan 端点的 step-3.7-flash 强制推理模式，输出常混入：
- 格式标记复述（"【动作:类型】【主题:内容】"）
- 元思考句（"首先得抓核心""然后组织语言""哦对，要符合要求"）
- 编号列表残留（"1. "）

此前清理逻辑散落在 llm_client / life_loop / action_executor 四处、口径不一，
导致 THINK/固化/agentic loop 的存储文本仍带大量推理噪音。此模块提供统一
入口，所有"LLM 输出 → 存储/展示"路径共用同一套规则。

设计原则：保守清理——宁可漏删不可误杀；清理后为空则回退到仅去标记的
原文（避免信息丢失）。
"""
import re

# 元思考句开头（推理模型自言自语的典型模式；允许前面带一个连接字：那/再/就/还…）
_META_PREFIX = re.compile(
    r"^[那再就还又也但并]?[并而]?"
    r"(首先|然后|接着|其次|最后|等下|哦对|嗯+|对了|总之|综上|所以|因此|"
    r"我需要|我应该|我要|让我|现在让我|接下来我|思考部分|回答问题|组织语言|"
    r"理清楚|重新理|符合要求|按照要求|根据要求|回答末尾|直接告诉我|"
    r"用户现在|用户需要|现在需要|需要总结|数下字数|要更顺一点|再润色|要精简|"
    r"以此开启|以此回应|以此展开)[，。：:、\s]*"
)
# 句中语气词插入（"…，哦对，要准确"）：连同前后标点压成一个逗号。
# 只匹配逗号/顿号后（句子边界"。"保持完整，句首插入词由 _META_PREFIX 处理）
_INTERJECTION_RE = re.compile(r"[，,、]\s*(?:哦对|等下|对了|嗯)[，。：、]?\s*")
# 格式标记（含变体冒号/空白）
_MARKER_RE = re.compile(r"【\s*(动作|主题)\s*[:：][^】]*】")
# 编号开头
_NUM_PREFIX = re.compile(r"^[\d.、ⅣⅠ②①\a-v]{1,4}\s*[.、）)]?\s*")


# 引号段（LLM 常把实际消息放引号里，外面裹叙述）
_QUOTE_RE = re.compile(r'[\"“”\'『「]([^\"“”\'』」]{6,240})[\"“”\'』」]')


def extract_message(text: str, max_len: int = 200) -> str:
    """从 LLM 生成的社交内容中提取实际消息。

    优先取最长的引号内段落（模型习惯把真实发言放引号里、外面裹
    "比如…等下数下字"之类的叙述）；没有引号段时退回 clean_text。
    """
    if not text:
        return ""
    cands = [m.group(1).strip() for m in _QUOTE_RE.finditer(text)]
    if cands:
        best = max(cands, key=len)
        return best[:max_len]
    return clean_text(text, max_len=max_len)


# 消息质量残留检测（清理后仍含这些 = 生成失败，宁可不发）
_RESIDUE_MARKERS = ("等下", "哦对", "数下字", "调整下", "要自然", "太生硬",
                    "不要解释", "以此开启", "字数控制", "润色")


def is_valid_message(text: str, min_len: int = 8) -> bool:
    """社交消息质量门：清理后仍带推理残留或过短 → 无效。

    发布一条 CoT 碎片比不发更伤社交——宁缺毋滥。
    """
    if not text or len(text.strip()) < min_len:
        return False
    if any(m in text for m in _RESIDUE_MARKERS):
        return False
    # 标点占比过半 = 没有实质内容
    punct = sum(1 for c in text if c in "。，、！？；：""''…—,.!?;:\"' ")
    return punct < len(text) / 2


def _split_sentences(text: str):
    """按句末标点切分，保留标点。"""
    return re.split(r"(?<=[。！？!？;\n])", text)


def clean_text(text: str, max_len: int = 400) -> str:
    """清理 LLM 输出中的 CoT 残留，返回适合存储/展示的正文。

    规则：
    1. 去掉【动作:..】【主题:..】格式标记
    2. 逐句剥掉元思考前缀；剥掉后所剩无几的短句整句丢弃
    3. 压缩空白、去首尾标点、截断到 max_len
    4. 若清理后过短（<3 字），回退为"仅去标记"的原文截断
    """
    if not text:
        return ""

    no_marker = _MARKER_RE.sub("", text)
    # 先压掉句中语气词插入，让"…，哦对，要准确"断成两个短句（后者会被短句规则丢弃）
    no_marker = _INTERJECTION_RE.sub("，", no_marker)
    # 逗号后的元连接词（"…，首先得把…"）断成新句，让前缀剥离规则能吃到
    no_marker = re.sub(r"[，,]\s*(首先|然后|接着|所以|等下|哦对|总之|综上)", r"。 \1", no_marker)

    kept = []
    for raw in _split_sentences(no_marker):
        s = _NUM_PREFIX.sub("", raw.strip())
        if not s:
            continue
        # 连剥两层元思考前缀（如"那首先，思考部分…"）
        stripped = _META_PREFIX.sub("", _META_PREFIX.sub("", s))
        if len(stripped) < 4:
            # 元思考开头且剥完所剩无几 → 整句丢弃；
            # 但本来就很短的句子（如"好。"）保留原样
            if len(s) >= 6:
                continue
            stripped = s
        kept.append(stripped)

    out = "".join(kept) if kept else no_marker
    out = re.sub(r"\s+", " ", out).strip(" 。.，,；;、")
    if len(out) < 3:
        out = re.sub(r"\s+", " ", no_marker).strip(" 。.，,；;、")

    return out[:max_len] if len(out) > max_len else out
