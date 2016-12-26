import logging
import threading


class TaskWorkerThread(threading.Thread):

    exit_signal = False

    def __init__(self, name, task_pool):
        """
        :param onedrived.od_task.TaskPool task_pool:
        """
        super().__init__(name=name, daemon=False)
        self.task_pool = task_pool

    @classmethod
    def exit(cls):
        cls.exit_signal = True

    def run(self):
        logging.debug('Started.')
        while not self.exit_signal:
            # logging.debug('Getting semaphore.')
            self.task_pool.semaphore.acquire()
            # logging.debug('Got semaphore.')
            if self.exit_signal:
                break
            task = self.task_pool.pop_task()
            if task is not None:
                logging.debug('Acquired task %s.', task)
                task.handle()
        logging.debug('Stopped.')
