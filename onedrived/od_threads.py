import logging
import threading


class TaskWorkerThread(threading.Thread):

    def __init__(self, name, task_pool):
        """
        :param onedrived.od_task.TaskPool task_pool:
        """
        super().__init__(name=name, daemon=False)
        self.task_pool = task_pool
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        logging.debug('Started.')
        while self._running:
            # logging.debug('Getting semaphore.')
            self.task_pool.semaphore.acquire()
            # logging.debug('Got semaphore.')
            if not self._running:
                break
            task = self.task_pool.pop_task()
            if task is not None:
                logging.debug('Got task %s.', task)
                task.handle()
        logging.info('Stopped.')
