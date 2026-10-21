with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'r') as f:
    content = f.read()

# Find the end of the file and append the missing classes
# The file currently ends with the synthesize_code function
# We need to add the missing classes before the final synthesize_code function

# First, let's find where to insert the new classes
# The file ends with the synthesize_code function

# Find the end of the file content before the synthesize_code function
synthesize_code_start = content.find('async def synthesize_code(')
if synthesize_code_start == -1:
    # Try alternative
    synthesize_code_start = content.find('async def synthesize_code')
    
if synthesize_code_start != -1:
    # Find the end of the file or next class/function
    next_section = content.find('\n\n', synthesize_code_start + 1)
    # Insert before the synthesize_code function
    new_content = content[:synthesize_code_start] + '''

class SynthesisOrchestrator:
    """Main orchestrator for AI-assisted synthesis with guardrails.
    
    Coordinates LLM agents, guardrails, and policy enforcement
    to provide safe, automated code synthesis.
    """
    
    def __init__(
        self,
        config: GuardrailConfig = None,
        llm_provider: LLMProvider = None,
        policy_registry: PolicyRegistry = None,
    ):
        self.config = config or GuardrailConfig()
        self.llm_provider = llm_provider or MockLLMProvider()
        self.guardrails = SynthesisGuardrails(self.config)
        self.policy_registry = policy_registry
        
        # Metrics
        self.metrics = {
            "total_syntheses": 0,
            "successful": 0,
            "rejected": 0,
            "human_interventions": 0,
            "total_tokens": 0,
        }
    
    async def synthesize(
        self,
        prompt: str,
        context: Dict[str, Any] = None,
        mode: SynthesisMode = SynthesisMode.AUTONOMOUS,
    ) -> SynthesisResult:
        """Generate code using LLM with safety guardrails."""
        start_time = time.time()
        self.metrics["total_syntheses"] += 1
        
        # Build context
        context = context or {}
        context["timestamp"] = time.time()
        
        # Step 1: Generate code using LLM
        llm_response = await self.llm_provider.generate(
            prompt=prompt,
            config=self.config,
            context=context,
        )
        
        # Step 2: Run through guardrails
        guardrail_result = self.guardrails.run_all_gates(
            code=llm_response["code"],
            confidence=llm_response.get("confidence", 0.0),
        )
        
        # Determine status
        if result["all_passed"]:
            status = SynthesisStatus.SUCCESS
        else:
            status = SynthesisStatus.FAILED
        
        # Update metrics
        self.metrics["total_syntheses"] += 1
        if result["all_passed"]:
            self.metrics["successful"] += 1
        else:
            self.metrics["rejected"] += 1
        
        return SynthesisResult(
            status=status,
            synthesized_code=llm_response.get("code", ""),
            confidence=llm_response.get("confidence", 0.0),
            gate_results=gate_results,
            error_message="Code failed guardrail checks" if not result["all_passed"] else None,
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return {
            "total_syntheses": self.metrics["total_syntheses"],
            "successful": self.metrics["successful"],
            "rejected": self.metrics["rejected"],
            "human_interventions": self.metrics["human_interventions"],
            "total_tokens": self.metrics["total_tokens"],
            "success_rate": (
                self.metrics["successful"] / self.metrics["total_syntheses"]
                if self.metrics["total_syntheses"] > 0
                else 0.0
            ),
        }

'''

# Read the file and find where to insert
with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'r') as f:
    content = f.read()

# Find the end of the file (before the synthesize_code function)
synthesize_code_pos = content.find('async def synthesize_code(')
if synthesize_code_pos == -1:
    synthesize_code_pos = content.find('async def synthesize_code')

if synthesize_code_pos != -1:
    # Insert the new classes before synthesize_code
    new_content = content[:synthesize_code_pos] + '\n\n' + new_classes + '\n\n' + content[synthesize_code_pos:]
    with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'w') as f:
        f.write(new_content)
    print('Added SynthesisOrchestrator class')
else:
    # Append at end
    with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'a') as f:
        f.write('\n\n' + new_classes)
    print('Appended new classes at end')

print('Done adding SynthesisOrchestrator')