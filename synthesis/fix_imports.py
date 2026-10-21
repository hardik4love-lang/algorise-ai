with open('synthesis_guardrails.py', 'r') as f:
    content = f.read()

old = '''import asyncio
import hashlib
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional'''

new = '''import asyncio
import hashlib
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from policy.policy_engine import PolicyRule, PolicyRegistry, RuleScope, RuleProvenance'''

content = content.replace(old, new)
with open('synthesis_guardrails.py', 'w') as f:
    f.write(content)
print('Fixed imports')