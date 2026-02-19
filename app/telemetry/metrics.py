"""
Metrics collection and reporting.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution."""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    steps_executed: int = 0
    steps_total: int = 0
    failures: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def complete(self, success: bool) -> None:
        """Mark execution as complete."""
        self.end_time = datetime.now()
        self.success = success
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_total": self.steps_total,
            "failures": self.failures,
            "duration_seconds": self.duration_seconds
        }


class MetricsCollector:
    """Collects and aggregates execution metrics."""
    
    def __init__(self):
        self.executions: List[ExecutionMetrics] = []
        self.current_execution: Optional[ExecutionMetrics] = None
    
    def start_execution(self, test_name: str, steps_total: int = 0) -> ExecutionMetrics:
        """
        Start tracking new execution.
        
        Args:
            test_name: Name of test being executed
            steps_total: Total number of steps
            
        Returns:
            ExecutionMetrics object
        """
        metrics = ExecutionMetrics(
            test_name=test_name,
            start_time=datetime.now(),
            steps_total=steps_total
        )
        
        self.current_execution = metrics
        logger.info(f"Started tracking execution: {test_name}")
        
        return metrics
    
    def complete_execution(self, success: bool) -> None:
        """
        Complete current execution.
        
        Args:
            success: Whether execution succeeded
        """
        if not self.current_execution:
            logger.warning("No execution to complete")
            return
        
        self.current_execution.complete(success)
        self.executions.append(self.current_execution)
        
        logger.info(
            f"Completed execution: {self.current_execution.test_name} "
            f"({'✓ SUCCESS' if success else '✗ FAILED'}) "
            f"in {self.current_execution.duration_seconds:.2f}s"
        )
        
        self.current_execution = None
    
    def record_step(self, success: bool, error: Optional[str] = None) -> None:
        """
        Record step execution.
        
        Args:
            success: Whether step succeeded
            error: Optional error message
        """
        if not self.current_execution:
            return
        
        self.current_execution.steps_executed += 1
        
        if not success and error:
            self.current_execution.failures.append(error)
    
    def get_summary(self) -> Dict:
        """
        Get summary of all executions.
        
        Returns:
            Summary dictionary
        """
        if not self.executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_duration": 0.0
            }
        
        total = len(self.executions)
        successful = sum(1 for e in self.executions if e.success)
        total_duration = sum(e.duration_seconds for e in self.executions)
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total) * 100,
            "average_duration": total_duration / total,
            "total_duration": total_duration
        }
    
    def get_recent_executions(self, limit: int = 10) -> List[ExecutionMetrics]:
        """
        Get recent executions.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of recent executions
        """
        return self.executions[-limit:]
    
    def export_metrics(self, file_path: str) -> None:
        """
        Export metrics to JSON file.
        
        Args:
            file_path: Path to export file
        """
        try:
            data = {
                "summary": self.get_summary(),
                "executions": [e.to_dict() for e in self.executions]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported metrics to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.executions.clear()
        self.current_execution = None
        logger.info("Metrics cleared")


# Global metrics collector instance
metrics_collector = MetricsCollector()
