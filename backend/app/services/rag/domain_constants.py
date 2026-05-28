"""RAG 术语分类领域常量

提供规范化的领域标识符、人类可读标签、分组辅助函数，
以及 arXiv 类别到领域的映射，供整个术语系统使用。
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Final


class TermDomain(str, Enum):
    """术语条目的规范化领域标识符"""

    # 计算机科学 & AI
    COMPUTER_SCIENCE = "computer_science"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    NATURAL_LANGUAGE_PROCESSING = "natural_language_processing"
    COMPUTER_VISION = "computer_vision"
    SYSTEMS = "systems"
    SECURITY = "security"
    INFORMATION_RETRIEVAL = "information_retrieval"
    MULTIMODAL = "multimodal"
    SOFTWARE_ENGINEERING = "software_engineering"
    DATABASE = "database"
    NETWORKING = "networking"

    # 数学
    MATHEMATICS = "mathematics"
    STATISTICS = "statistics"
    LINEAR_ALGEBRA = "linear_algebra"
    CALCULUS = "calculus"
    PROBABILITY = "probability"
    OPTIMIZATION = "optimization"
    GRAPH_THEORY = "graph_theory"

    # 物理
    PHYSICS = "physics"
    QUANTUM_MECHANICS = "quantum_mechanics"
    THERMODYNAMICS = "thermodynamics"
    ELECTROMAGNETISM = "electromagnetism"
    CONDENSED_MATTER = "condensed_matter"
    ASTROPHYSICS = "astrophysics"

    # 生物学 & 医学
    BIOLOGY = "biology"
    MOLECULAR_BIOLOGY = "molecular_biology"
    GENETICS = "genetics"
    BIOCHEMISTRY = "biochemistry"
    MEDICINE = "medicine"
    PHARMACOLOGY = "pharmacology"
    NEUROSCIENCE = "neuroscience"
    BIOINFORMATICS = "bioinformatics"

    # 工程
    ENGINEERING = "engineering"
    ELECTRICAL_ENGINEERING = "electrical_engineering"
    MECHANICAL_ENGINEERING = "mechanical_engineering"
    CIVIL_ENGINEERING = "civil_engineering"
    CHEMICAL_ENGINEERING = "chemical_engineering"
    MATERIALS_SCIENCE = "materials_science"
    ROBOTICS = "robotics"
    CONTROL_THEORY = "control_theory"
    SIGNAL_PROCESSING = "signal_processing"

    # 化学
    CHEMISTRY = "chemistry"
    ORGANIC_CHEMISTRY = "organic_chemistry"
    INORGANIC_CHEMISTRY = "inorganic_chemistry"
    PHYSICAL_CHEMISTRY = "physical_chemistry"
    ANALYTICAL_CHEMISTRY = "analytical_chemistry"

    # 其他
    ECONOMICS = "economics"
    LINGUISTICS = "linguistics"
    PHILOSOPHY = "philosophy"
    EDUCATION = "education"


# 前端展示用中文标签
DOMAIN_LABELS_ZH: Final[dict[str, str]] = {
    TermDomain.COMPUTER_SCIENCE.value: "计算机科学",
    TermDomain.ARTIFICIAL_INTELLIGENCE.value: "人工智能",
    TermDomain.MACHINE_LEARNING.value: "机器学习",
    TermDomain.DEEP_LEARNING.value: "深度学习",
    TermDomain.NATURAL_LANGUAGE_PROCESSING.value: "自然语言处理",
    TermDomain.COMPUTER_VISION.value: "计算机视觉",
    TermDomain.SYSTEMS.value: "系统",
    TermDomain.SECURITY.value: "安全",
    TermDomain.INFORMATION_RETRIEVAL.value: "信息检索",
    TermDomain.MULTIMODAL.value: "多模态",
    TermDomain.SOFTWARE_ENGINEERING.value: "软件工程",
    TermDomain.DATABASE.value: "数据库",
    TermDomain.NETWORKING.value: "网络",
    TermDomain.MATHEMATICS.value: "数学",
    TermDomain.STATISTICS.value: "统计学",
    TermDomain.LINEAR_ALGEBRA.value: "线性代数",
    TermDomain.CALCULUS.value: "微积分",
    TermDomain.PROBABILITY.value: "概率论",
    TermDomain.OPTIMIZATION.value: "最优化",
    TermDomain.GRAPH_THEORY.value: "图论",
    TermDomain.PHYSICS.value: "物理学",
    TermDomain.QUANTUM_MECHANICS.value: "量子力学",
    TermDomain.THERMODYNAMICS.value: "热力学",
    TermDomain.ELECTROMAGNETISM.value: "电磁学",
    TermDomain.CONDENSED_MATTER.value: "凝聚态物理",
    TermDomain.ASTROPHYSICS.value: "天体物理",
    TermDomain.BIOLOGY.value: "生物学",
    TermDomain.MOLECULAR_BIOLOGY.value: "分子生物学",
    TermDomain.GENETICS.value: "遗传学",
    TermDomain.BIOCHEMISTRY.value: "生物化学",
    TermDomain.MEDICINE.value: "医学",
    TermDomain.PHARMACOLOGY.value: "药理学",
    TermDomain.NEUROSCIENCE.value: "神经科学",
    TermDomain.BIOINFORMATICS.value: "生物信息学",
    TermDomain.ENGINEERING.value: "工程",
    TermDomain.ELECTRICAL_ENGINEERING.value: "电气工程",
    TermDomain.MECHANICAL_ENGINEERING.value: "机械工程",
    TermDomain.CIVIL_ENGINEERING.value: "土木工程",
    TermDomain.CHEMICAL_ENGINEERING.value: "化学工程",
    TermDomain.MATERIALS_SCIENCE.value: "材料科学",
    TermDomain.ROBOTICS.value: "机器人学",
    TermDomain.CONTROL_THEORY.value: "控制理论",
    TermDomain.SIGNAL_PROCESSING.value: "信号处理",
    TermDomain.ECONOMICS.value: "经济学",
    TermDomain.LINGUISTICS.value: "语言学",
    TermDomain.PHILOSOPHY.value: "哲学",
    TermDomain.EDUCATION.value: "教育",
    TermDomain.CHEMISTRY.value: "化学",
    TermDomain.ORGANIC_CHEMISTRY.value: "有机化学",
    TermDomain.INORGANIC_CHEMISTRY.value: "无机化学",
    TermDomain.PHYSICAL_CHEMISTRY.value: "物理化学",
    TermDomain.ANALYTICAL_CHEMISTRY.value: "分析化学",
}

# 英文标签
DOMAIN_LABELS_EN: Final[dict[str, str]] = {
    TermDomain.COMPUTER_SCIENCE.value: "Computer Science",
    TermDomain.ARTIFICIAL_INTELLIGENCE.value: "Artificial Intelligence",
    TermDomain.MACHINE_LEARNING.value: "Machine Learning",
    TermDomain.DEEP_LEARNING.value: "Deep Learning",
    TermDomain.NATURAL_LANGUAGE_PROCESSING.value: "Natural Language Processing",
    TermDomain.COMPUTER_VISION.value: "Computer Vision",
    TermDomain.SYSTEMS.value: "Systems",
    TermDomain.SECURITY.value: "Security",
    TermDomain.INFORMATION_RETRIEVAL.value: "Information Retrieval",
    TermDomain.MULTIMODAL.value: "Multimodal",
    TermDomain.SOFTWARE_ENGINEERING.value: "Software Engineering",
    TermDomain.DATABASE.value: "Database",
    TermDomain.NETWORKING.value: "Networking",
    TermDomain.MATHEMATICS.value: "Mathematics",
    TermDomain.STATISTICS.value: "Statistics",
    TermDomain.LINEAR_ALGEBRA.value: "Linear Algebra",
    TermDomain.CALCULUS.value: "Calculus",
    TermDomain.PROBABILITY.value: "Probability",
    TermDomain.OPTIMIZATION.value: "Optimization",
    TermDomain.GRAPH_THEORY.value: "Graph Theory",
    TermDomain.PHYSICS.value: "Physics",
    TermDomain.QUANTUM_MECHANICS.value: "Quantum Mechanics",
    TermDomain.THERMODYNAMICS.value: "Thermodynamics",
    TermDomain.ELECTROMAGNETISM.value: "Electromagnetism",
    TermDomain.CONDENSED_MATTER.value: "Condensed Matter Physics",
    TermDomain.ASTROPHYSICS.value: "Astrophysics",
    TermDomain.BIOLOGY.value: "Biology",
    TermDomain.MOLECULAR_BIOLOGY.value: "Molecular Biology",
    TermDomain.GENETICS.value: "Genetics",
    TermDomain.BIOCHEMISTRY.value: "Biochemistry",
    TermDomain.MEDICINE.value: "Medicine",
    TermDomain.PHARMACOLOGY.value: "Pharmacology",
    TermDomain.NEUROSCIENCE.value: "Neuroscience",
    TermDomain.BIOINFORMATICS.value: "Bioinformatics",
    TermDomain.ENGINEERING.value: "Engineering",
    TermDomain.ELECTRICAL_ENGINEERING.value: "Electrical Engineering",
    TermDomain.MECHANICAL_ENGINEERING.value: "Mechanical Engineering",
    TermDomain.CIVIL_ENGINEERING.value: "Civil Engineering",
    TermDomain.CHEMICAL_ENGINEERING.value: "Chemical Engineering",
    TermDomain.MATERIALS_SCIENCE.value: "Materials Science",
    TermDomain.ROBOTICS.value: "Robotics",
    TermDomain.CONTROL_THEORY.value: "Control Theory",
    TermDomain.SIGNAL_PROCESSING.value: "Signal Processing",
    TermDomain.ECONOMICS.value: "Economics",
    TermDomain.LINGUISTICS.value: "Linguistics",
    TermDomain.PHILOSOPHY.value: "Philosophy",
    TermDomain.EDUCATION.value: "Education",
    TermDomain.CHEMISTRY.value: "Chemistry",
    TermDomain.ORGANIC_CHEMISTRY.value: "Organic Chemistry",
    TermDomain.INORGANIC_CHEMISTRY.value: "Inorganic Chemistry",
    TermDomain.PHYSICAL_CHEMISTRY.value: "Physical Chemistry",
    TermDomain.ANALYTICAL_CHEMISTRY.value: "Analytical Chemistry",
}


# 父级分组: 顶级领域 -> 子领域值列表
DOMAIN_GROUPS: Final[dict[str, list[str]]] = {
    "computer_science": [
        TermDomain.COMPUTER_SCIENCE.value,
        TermDomain.ARTIFICIAL_INTELLIGENCE.value,
        TermDomain.MACHINE_LEARNING.value,
        TermDomain.DEEP_LEARNING.value,
        TermDomain.NATURAL_LANGUAGE_PROCESSING.value,
        TermDomain.COMPUTER_VISION.value,
        TermDomain.SYSTEMS.value,
        TermDomain.SECURITY.value,
        TermDomain.INFORMATION_RETRIEVAL.value,
        TermDomain.MULTIMODAL.value,
        TermDomain.SOFTWARE_ENGINEERING.value,
        TermDomain.DATABASE.value,
        TermDomain.NETWORKING.value,
    ],
    "mathematics": [
        TermDomain.MATHEMATICS.value,
        TermDomain.STATISTICS.value,
        TermDomain.LINEAR_ALGEBRA.value,
        TermDomain.CALCULUS.value,
        TermDomain.PROBABILITY.value,
        TermDomain.OPTIMIZATION.value,
        TermDomain.GRAPH_THEORY.value,
    ],
    "physics": [
        TermDomain.PHYSICS.value,
        TermDomain.QUANTUM_MECHANICS.value,
        TermDomain.THERMODYNAMICS.value,
        TermDomain.ELECTROMAGNETISM.value,
        TermDomain.CONDENSED_MATTER.value,
        TermDomain.ASTROPHYSICS.value,
    ],
    "biology_medicine": [
        TermDomain.BIOLOGY.value,
        TermDomain.MOLECULAR_BIOLOGY.value,
        TermDomain.GENETICS.value,
        TermDomain.BIOCHEMISTRY.value,
        TermDomain.MEDICINE.value,
        TermDomain.PHARMACOLOGY.value,
        TermDomain.NEUROSCIENCE.value,
        TermDomain.BIOINFORMATICS.value,
    ],
    "engineering": [
        TermDomain.ENGINEERING.value,
        TermDomain.ELECTRICAL_ENGINEERING.value,
        TermDomain.MECHANICAL_ENGINEERING.value,
        TermDomain.CIVIL_ENGINEERING.value,
        TermDomain.CHEMICAL_ENGINEERING.value,
        TermDomain.MATERIALS_SCIENCE.value,
        TermDomain.ROBOTICS.value,
        TermDomain.CONTROL_THEORY.value,
        TermDomain.SIGNAL_PROCESSING.value,
    ],
    "chemistry": [
        TermDomain.CHEMISTRY.value,
        TermDomain.ORGANIC_CHEMISTRY.value,
        TermDomain.INORGANIC_CHEMISTRY.value,
        TermDomain.PHYSICAL_CHEMISTRY.value,
        TermDomain.ANALYTICAL_CHEMISTRY.value,
    ],
}


def get_domain_label(domain: str, lang: str = "zh") -> str:
    """返回领域标识符的人类可读标签"""
    labels = DOMAIN_LABELS_ZH if lang == "zh" else DOMAIN_LABELS_EN
    return labels.get(domain, domain)


def get_domain_group(domain: str) -> str | None:
    """返回子领域的父级分组，如果是顶级领域则返回 None"""
    for group, members in DOMAIN_GROUPS.items():
        if domain in members:
            return group
    return None


# ── arXiv 类别到领域映射 ─────────────────────────────────────────────

# 从 arXiv 类别前缀模式到 TermDomain 值的映射。
# 模式按顺序匹配，第一个命中有效。
_ARXIV_CATEGORY_DOMAIN_MAP: Final[list[tuple[str, str]]] = [
    # 计算机科学 & AI
    (r"^cs\.AI$", "artificial_intelligence"),
    (r"^cs\.LG$", "machine_learning"),
    (r"^cs\.NE$", "machine_learning"),
    (r"^cs\.CL$", "natural_language_processing"),
    (r"^cs\.CV$", "computer_vision"),
    (r"^cs\.IR$", "information_retrieval"),
    (r"^cs\.MM$", "multimodal"),
    (r"^cs\.SE$", "software_engineering"),
    (r"^cs\.DB$", "database"),
    (r"^cs\.NI$", "networking"),
    (r"^cs\.CR$", "security"),
    (r"^cs\.OS$", "systems"),
    (r"^cs\.DC$", "systems"),
    (r"^cs\.DS$", "computer_science"),
    (r"^cs\.RO$", "robotics"),
    (r"^cs\.SY$", "systems"),
    (r"^cs\.IT$", "information_retrieval"),
    (r"^cs\.[A-Z]{2}$", "computer_science"),  # 通用 CS 兜底

    # 数学
    (r"^math\.[A-Z]{2}$", "mathematics"),
    (r"^math$", "mathematics"),

    # 统计学
    (r"^stat\.ML$", "machine_learning"),
    (r"^stat\.TH$", "statistics"),
    (r"^stat\.ME$", "statistics"),
    (r"^stat\.AP$", "statistics"),
    (r"^stat\.CO$", "statistics"),
    (r"^stat\.OT$", "statistics"),
    (r"^stat$", "statistics"),

    # 物理
    (r"^physics\.[a-z-]+$", "physics"),
    (r"^physics$", "physics"),
    (r"^quant-ph$", "quantum_mechanics"),
    (r"^hep-th$", "physics"),
    (r"^hep-ph$", "physics"),
    (r"^hep-ex$", "physics"),
    (r"^hep-lat$", "physics"),
    (r"^astro-ph\.[A-Z]{2}$", "astrophysics"),
    (r"^gr-qc$", "physics"),
    (r"^nucl-th$", "physics"),
    (r"^nucl-ex$", "physics"),
    (r"^cond-mat\.[a-z-]+$", "condensed_matter"),
    (r"^physics\.flu-dyn$", "engineering"),

    # 生物学 & 医学
    (r"^q-bio\.[A-Z]{2}$", "biology"),
    (r"^q-bio$", "biology"),
    (r"^q-bio\.BM$", "biochemistry"),
    (r"^q-bio\.GN$", "genetics"),
    (r"^q-bio\.MN$", "molecular_biology"),
    (r"^q-bio\.NC$", "neuroscience"),
    (r"^q-bio\.QM$", "bioinformatics"),
    (r"^q-bio\.TO$", "biology"),

    # 化学
    (r"^chem-ph$", "physical_chemistry"),
    (r"^physics\.chem-ph$", "physical_chemistry"),

    # 工程
    (r"^eess\.[A-Z]{2}$", "engineering"),
    (r"^eess\.SP$", "signal_processing"),
    (r"^eess\.SY$", "control_theory"),
    (r"^eess\.IV$", "computer_vision"),
    (r"^eess\.AS$", "signal_processing"),
    (r"^eess$", "engineering"),

    # 经济学
    (r"^econ\.[A-Z]{2}$", "economics"),
    (r"^q-fin\.[A-Z]{2}$", "economics"),
    (r"^q-fin$", "economics"),
]


def map_arxiv_category_to_domain(arxiv_cat: str) -> str | None:
    """将单个 arXiv 类别字符串映射为 TermDomain 值。

    参数:
        arxiv_cat: arXiv 类别字符串，如 ``"cs.CL"``, ``"math.OC"``,
                   ``"quant-ph"``, ``"physics.optics"``。

    返回:
        对应的 ``TermDomain`` 值（如 ``"natural_language_processing"``,
        ``"mathematics"``, ``"quantum_mechanics"``），未找到映射时返回 ``None``。
    """
    if not arxiv_cat or not isinstance(arxiv_cat, str):
        return None

    cat = arxiv_cat.strip()
    if not cat:
        return None

    for pattern, domain in _ARXIV_CATEGORY_DOMAIN_MAP:
        if re.match(pattern, cat):
            return domain
    return None


def map_arxiv_categories_to_domain(categories: list[str]) -> str | None:
    """将 arXiv 类别列表映射为最具体的 TermDomain 值。

    当论文有多个类别时，此函数使用第一个找到的非通用匹配。
    "通用" 指顶级领域如 ``"computer_science"``, ``"mathematics"``,
    ``"biology"`` —— 更具体的子领域优先。

    参数:
        categories: arXiv 类别字符串列表，如 ``["cs.CL", "cs.AI"]``。

    返回:
        ``TermDomain`` 值，未找到映射时返回 ``None``。
    """
    if not categories:
        return None

    generic_domains = {
        "computer_science", "mathematics", "physics", "biology",
        "engineering", "chemistry", "statistics", "economics",
        "biochemistry", "signal_processing",
    }

    # 第一轮: 查找具体（非通用）匹配
    for cat in categories:
        domain = map_arxiv_category_to_domain(cat)
        if domain and domain not in generic_domains:
            return domain

    # 第二轮: 回退到任意匹配
    for cat in categories:
        domain = map_arxiv_category_to_domain(cat)
        if domain:
            return domain

    return None
