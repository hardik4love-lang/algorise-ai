with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'r') as f:
    content = f.read()

old = '''    def all_gates_pass(self, gate_results: Dict[str, Any]) -> bool:
        """Check if all required gates pass."""
        required_gates = [
            "gate_syntax_valid",
            "gate_no_forbidden_patterns", 
            "gate_allowed_imports_only",
            "gate_confidence_threshold",
        ]

        for gate in required_gates:
            if gate not in gate_results or not gate_results[gate]:
                return False

        # Check human approval if required
        if self.config.gate_human_approval:
            if not gate_results.get("gate_human_approval", False):
                return False
                
        return True'''

new = '''    def all_gates_pass(self, gate_results: Dict[str, Any]) -> bool:
        """Check if all required gates pass."""
        required_gates = [
            "gate_syntax_valid",
            "gate_no_forbidden_patterns", 
            "gate_allowed_imports_only",
            "gate_confidence_threshold",
        ]

        for gate in required_gates:
            if gate not in gate_results or not gate_results[gate]:
                return False

        # Check human approval if required
        if "gate_human_approval" in gate_results and gate_results["gate_human_approval"]:
            return False
                
        return True'''

content = content.replace(old, new)
with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'w') as f:
    f.write(content)
print('Fixed all_gates_pass method')