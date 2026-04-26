import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    status: str # "success", "suspicious", "failed"
    messages: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

class BaseValidator:
    def validate(self, output_path: str) -> ValidationResult:
        if not os.path.exists(output_path):
            return ValidationResult("failed", [f"File not found: {output_path}"])
        size = os.path.getsize(output_path)
        if size == 0:
            return ValidationResult("failed", [f"File is empty: {output_path}"])
        return ValidationResult("success", [], {"file_size": float(size)})

class FastqValidator(BaseValidator):
    def validate(self, output_path: str) -> ValidationResult:
        res = super().validate(output_path)
        if res.status == "failed": return res
        
        # Simple read count (lines / 4)
        try:
            with open(output_path, 'rb') as f:
                lines = sum(1 for _ in f)
            read_count = lines // 4
            res.metrics["read_count"] = float(read_count)
            
            if read_count == 0:
                res.status = "failed"
                res.messages.append("FASTQ contains 0 reads.")
            elif read_count < 1000:
                res.status = "suspicious"
                res.messages.append(f"Low read count detected: {read_count}")
        except Exception as e:
            res.status = "failed"
            res.messages.append(f"Error reading FASTQ: {str(e)}")
        
        return res

class BamValidator(BaseValidator):
    def validate(self, output_path: str) -> ValidationResult:
        res = super().validate(output_path)
        if res.status == "failed": return res
        
        # Heuristic: BAM files < 100 bytes are usually just headers
        if res.metrics["file_size"] < 100:
            res.status = "suspicious"
            res.messages.append("BAM file is unusually small (possible header only).")
        return res

class ValidatorRegistry:
    def __init__(self):
        self._validators = {
            "FASTQ": FastqValidator(),
            "BAM": BamValidator(),
            "DEFAULT": BaseValidator()
        }

    def get(self, file_type: str) -> BaseValidator:
        return self._validators.get(file_type.upper(), self._validators["DEFAULT"])

validator_registry = ValidatorRegistry()
