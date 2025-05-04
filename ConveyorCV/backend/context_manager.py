import multiprocessing
from typing import Dict, Optional

from model.model import DetectionContext


class ContextManager:
    def __init__(self):
        self.detector_context = None
        self.processor_context = None
        self.validator_context = None
        self.latest_seq_number = 0

    def save_contexts(self, detector_process, processor_process, validator_process):
        """Save the current context from all processes"""
        if detector_process and hasattr(detector_process, 'detector'):
            self.detector_context = detector_process.detector.get_context()

        if processor_process and hasattr(processor_process, 'shape_processor'):
            self.processor_context = processor_process.shape_processor.get_context()
            self.latest_seq_number = processor_process.shape_processor.objects_processed

        if validator_process and hasattr(validator_process, 'validator'):
            self.validator_context = validator_process.validator.get_context()

    def restore_contexts(self, detector_process, processor_process, validator_process):
        """Restore saved contexts to the new processes"""
        if self.detector_context and detector_process and hasattr(detector_process, 'detector'):
            detector_process.detector.set_context(self.detector_context)

        if self.processor_context and processor_process and hasattr(processor_process, 'shape_processor'):
            processor_process.shape_processor.set_context(self.processor_context)

        if self.validator_context and validator_process and hasattr(validator_process, 'validator'):
            validator_process.validator.set_context(self.validator_context)


context_manager = ContextManager()