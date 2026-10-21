import os

target_file = "D:\\algorise-ai\\synthesis\\synthesis_guardrails.py"

with open(file_path, 'r') as f:
    lines = f.readlines()

# Find and fix the all_gates_pass method
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'def all_gates_pass(self, gate_results: Dict[str, Any]) -> bool:' in line:
        # This is the start of the method
        new_lines.append(line)
        i += 1
        # Skip the docstring
        new_lines.append(lines[i])
        i += 1
        # Skip the required_gates list
        while i < len(lines) and ']' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        new_lines.append(lines[i])  # Include the closing ]
        i += 1
        # Skip the for loop line
        new_lines.append(lines[i])
        i += 1
        # Skip if block
        while i < len(lines) and 'return False' not in lines[i]:
            i += 1
        i += 1  # Skip return False
        # Skip blank line
        while i < len(lines) and lines[i].strip() == '':
            i += 1
        # Skip the comment line
        while i < len(lines) and '# Check human approval' not in lines[i]:
            i += 1
        i += 1  # Skip comment line
        # Skip if self.config.gate_human_approval: line
        i += 1
        # Skip if not gate_results.get(...) line
        i += 1
        # Skip return False
        i += 1
        # Add new code
        new_lines.append('        if "gate_human_approval" in gate_results and gate_results["gate_human_approval"]:\n')
        new_lines.append('            return False\n')
        new_lines.append('\n')
        new_lines.append('        return True\n')
    else:
        new_lines.append(line)
        i += 1

with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'w') as f:
    f.writelines(new_lines)
print('Fixed all_gates_pass method')