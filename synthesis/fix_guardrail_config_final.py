with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'r') as f:
    content = f.read()

old = '''class GuardrailConfig:
    """Configuration for synthesis guardrails."""
    min_confidence: float = 0.85
    allowed_imports: List[str] = field(default_factory=lambda: ["os", "json", "typing", "collections", "itertools", "functools", "pathlib", "hashlib"])
    forbidden_patterns: List[str] = field(default_factory=lambda: ["eval(", "exec(", "compile(", "__import__", "subprocess", "socket", "requests", "urllib", "threading", "multiprocessing"])
    gate_syntax_valid: bool = True
    gate_unit_tests_pass: bool = True
    gate_integration_tests_pass: bool = False
    gate_confidence_threshold: bool = True
    gate_no_forbidden_patterns: bool = True
    gate_allowed_imports_only: bool = True
    gate_human_approval: bool = False

    # Legacy compatibility
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    timeout_seconds: int = 30'''

new = '''class GuardrailConfig:
    """Configuration for synthesis guardrails."""
    min_confidence: float = 0.85
    allowed_imports: List[str] = field(default_factory=lambda: ["os", "json", "typing", "collections", "itertools", "functools", "pathlib", "hashlib"])
    forbidden_patterns: List[str] = field(default_factory=lambda: ["eval(", "exec(", "compile(", "__import__", "subprocess", "socket", "requests", "urllib", "threading", "multiprocessing"])
    gate_syntax_valid: bool = True
    gate_unit_tests_pass: bool = True
    gate_integration_tests_pass: bool = False
    gate_confidence_threshold: bool = True
    gate_no_forbidden_patterns: bool = True
    gate_allowed_imports_only: bool = True
    gate_human_approval: bool = False

    # Legacy compatibility
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    timeout_seconds: int = 30

    def __init__(
        self,
        min_confidence: float = 0.85,
        allowed_imports: List[str] = None,
        forbidden_patterns: List[str] = None,
        gate_syntax_valid: bool = True,
        gate_unit_tests_pass: bool = True,
        gate_integration_tests_pass: bool = False,
        gate_confidence_threshold: bool = True,
        gate_no_forbidden_patterns: bool = True,
        gate_allowed_imports_only: bool = True,
        gate_human_approval: bool = False,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        self.min_confidence = min_confidence
        self.allowed_imports = allowed_imports or ["os", "json", "typing", "collections", "itertools", "functools", "pathlib", "hashlib"]
        self.forbidden_patterns = forbidden_patterns or ["eval(", "exec(", "compile(", "__import__", "subprocess", "socket", "requests", "urllib", "threading", "multiprocessing"]
        self.gate_syntax_valid = gate_syntax_valid
        self.gate_unit_tests_pass = gate_unit_tests_pass
        self.gate_integration_tests_pass = gate_integration_tests_pass
        self.gate_confidence_threshold = gate_confidence_threshold
        self.gate_no_forbidden_patterns = gate_no_forbidden_patterns
        self.gate_allowed_imports_only = gate_allowed_imports_only
        self.gate_human_approval = gate_human_approval
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    # Legacy compatibility properties
    @property
    def max_tokens(self) -> int:
        return 2048

    @property
    def temperature(self) -> float:
        return 0.1

    @property
    def max_retries(self) -> int:
        return 3

    @property
    def timeout_seconds(self) -> int:
        return 30'''

content = content.replace(old, new)
with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'w') as f:
    f.write(content)
print('Fixed GuardrailConfig with __init__')