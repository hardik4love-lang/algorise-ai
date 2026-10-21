import re

with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'r') as f:
    content = f.read()

# Find and replace the GuardrailConfig class
pattern = r'class GuardrailConfig:.*?(?=\nclass |\n\nclass |\Z)'
replacement = '''class GuardrailConfig:
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

content = re.sub(r'class GuardrailConfig:.*?(?=\nclass |\n\nclass |\Z)', 
    '''class GuardrailConfig:
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
    timeout_seconds: int = 30''', content, flags=re.DOTALL)

with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'w') as f:
    f.write(content)
print('Fixed GuardrailConfig')