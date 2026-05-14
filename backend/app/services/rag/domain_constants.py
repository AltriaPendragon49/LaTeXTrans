"""Domain constants for RAG terminology classification.

Provides canonical domain identifiers, human-readable labels,
and grouping helpers used throughout the terminology system.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class TermDomain(str, Enum):
    """Canonical domain identifiers for terminology entries."""

    # Computer Science & AI
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

    # Mathematics
    MATHEMATICS = "mathematics"
    STATISTICS = "statistics"
    LINEAR_ALGEBRA = "linear_algebra"
    CALCULUS = "calculus"
    PROBABILITY = "probability"
    OPTIMIZATION = "optimization"
    GRAPH_THEORY = "graph_theory"

    # Physics
    PHYSICS = "physics"
    QUANTUM_MECHANICS = "quantum_mechanics"
    THERMODYNAMICS = "thermodynamics"
    ELECTROMAGNETISM = "electromagnetism"
    CONDENSED_MATTER = "condensed_matter"
    ASTROPHYSICS = "astrophysics"

    # Biology & Medicine
    BIOLOGY = "biology"
    MOLECULAR_BIOLOGY = "molecular_biology"
    GENETICS = "genetics"
    BIOCHEMISTRY = "biochemistry"
    MEDICINE = "medicine"
    PHARMACOLOGY = "pharmacology"
    NEUROSCIENCE = "neuroscience"
    BIOINFORMATICS = "bioinformatics"

    # Engineering
    ENGINEERING = "engineering"
    ELECTRICAL_ENGINEERING = "electrical_engineering"
    MECHANICAL_ENGINEERING = "mechanical_engineering"
    CIVIL_ENGINEERING = "civil_engineering"
    CHEMICAL_ENGINEERING = "chemical_engineering"
    MATERIALS_SCIENCE = "materials_science"
    ROBOTICS = "robotics"
    CONTROL_THEORY = "control_theory"
    SIGNAL_PROCESSING = "signal_processing"

    # Other
    ECONOMICS = "economics"
    LINGUISTICS = "linguistics"
    PHILOSOPHY = "philosophy"
    EDUCATION = "education"


# Human-readable labels (Chinese) for frontend display
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
}

# Human-readable labels (English)
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
}


# Parent grouping: high-level domain -> list of sub-domain values
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
}


def get_domain_label(domain: str, lang: str = "zh") -> str:
    """Return human-readable label for a domain identifier."""
    labels = DOMAIN_LABELS_ZH if lang == "zh" else DOMAIN_LABELS_EN
    return labels.get(domain, domain)


def get_domain_group(domain: str) -> str | None:
    """Return the parent group for a sub-domain, or None if it's a top-level domain."""
    for group, members in DOMAIN_GROUPS.items():
        if domain in members:
            return group
    return None
