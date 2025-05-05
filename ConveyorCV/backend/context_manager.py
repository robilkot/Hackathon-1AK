import logging
import time
from typing import Dict, Any, Optional
from model.model import IPCMessage, IPCMessageType

logger = logging.getLogger(__name__)


class ContextManager:
    def __init__(self):
        self.__processes = {}
        self.__saved_contexts = {}  # Store contexts by process name
        logger.info("ContextManager initialized")

    def register_process(self, name: str, pipe_connection):
        """Register a process with its communication pipe"""
        self.__processes[name] = pipe_connection
        logger.info(f"Process '{name}' registered with ContextManager")

    def save_contexts(self, shape_detector_process=None, shape_processor_process=None, sticker_validator_process=None):
        """Save contexts from all registered processes"""
        start_time = time.time()
        logger.info(f"Saving contexts from all processes")

        #logger.info(f"Processes collection: {self.__processes.items()}")

        for name, pipe in self.__processes.items():
            try:
                logger.info(f"Requesting context from {name}")
                pipe.send(IPCMessage.create_get_context(name))

                wait_start = time.time()
                while not pipe.poll() and time.time() - wait_start < 5:
                    time.sleep(0.05)

                if pipe.poll():
                    response = pipe.recv()
                    if response.message_type == IPCMessageType.CONTEXT:
                        self.__saved_contexts[name] = response.content
                        #logger.info(f"Saved context from {name}: {response.content}")
                    else:
                        logger.warning(f"Unexpected response type from {name}: {response.message_type}")
                else:
                    logger.warning(f"Timeout waiting for context from {name}")
            except Exception as e:
                logger.error(f"Error saving context from {name}: {str(e)}", exc_info=True)

        elapsed = time.time() - start_time
        logger.info(f"Saved contexts for {len(self.__saved_contexts)} processes in {elapsed:.2f}s")

    def restore_contexts(self, shape_detector_process=None, shape_processor_process=None,
                         sticker_validator_process=None):
        """Restore contexts to processes"""
        try:
            logger.info(f"Processes collection: {self.__processes.items()}")

            for name, process in [
                ("detector", shape_detector_process),
                ("processor", shape_processor_process),
                ("validator", sticker_validator_process)
            ]:
                logger.info(f"Restoring context from {name}")

                if not process:
                    logger.info(f"Process {name} not provided, skipping")
                    continue

                has_saved_context = name in self.__saved_contexts
                #logger.info(f"Is name in saved contexts: {has_saved_context}")

                has_restore_method = hasattr(process, "restore_context")
                #logger.info(f"Is hasattr(process, restore_context {has_restore_method}")

                if has_saved_context and has_restore_method:
                    process.restore_context(self.__saved_contexts[name])
                    logger.info(f"Context restored for {name}")
        except Exception as e:
            logger.error(f"Error restoring contexts: {str(e)}", exc_info=True)

    def get_saved_context(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a saved context by process name"""
        return self.__saved_contexts.get(name)

    def clear_contexts(self):
        """Clear all saved contexts"""
        self.__saved_contexts.clear()
        logger.info("All saved contexts cleared")

    def get_parameters(self, process_name: str):
        """Get parameters from a specific process using pipe communication"""
        if process_name not in self.__processes:
            logger.error(f"Process {process_name} not registered")
            return None

        pipe = self.__processes[process_name]

        try:
            message = IPCMessage(IPCMessageType.PARAMS, process_name, {"action": "get"})
            logger.info(f"Requesting parameters from {process_name}")
            pipe.send(message)

            wait_start = time.time()
            while not pipe.poll() and time.time() - wait_start < 5:
                time.sleep(0.05)

            if pipe.poll():
                response = pipe.recv()
                if response.message_type == IPCMessageType.PARAMS:
                    logger.info(f"Received parameters from {process_name}")
                    return response.content
                else:
                    logger.warning(f"Unexpected response type from {process_name}: {response.message_type}")
            else:
                logger.warning(f"Timeout waiting for parameters from {process_name}")

        except Exception as e:
            logger.error(f"Error getting parameters from {process_name}: {str(e)}", exc_info=True)

        return None

    def set_parameters(self, process_name: str, params):
        """Set parameters for a specific process using pipe communication"""
        if process_name not in self.__processes:
            logger.error(f"Process {process_name} not registered")
            return False

        pipe = self.__processes[process_name]

        try:
            message = IPCMessage(IPCMessageType.PARAMS, process_name, {"action": "set", "params": params})
            logger.info(f"Setting parameters for {process_name}")
            pipe.send(message)

            wait_start = time.time()
            while not pipe.poll() and time.time() - wait_start < 5:
                time.sleep(0.05)

            if pipe.poll():
                response = pipe.recv()
                if response.message_type == IPCMessageType.PARAMS:
                    logger.info(f"Parameters set for {process_name}")
                    return True
                else:
                    logger.warning(f"Unexpected response type from {process_name}: {response.message_type}")
            else:
                logger.warning(f"Timeout waiting for acknowledgment from {process_name}")

        except Exception as e:
            logger.error(f"Error setting parameters for {process_name}: {str(e)}", exc_info=True)

        return False