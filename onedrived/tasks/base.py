class TaskBase:

    def __init__(self, repo, task_pool):
        """
        :param onedrived.od_repo.OneDriveLocalRepository | None repo:
        :param onedrived.od_task.TaskPool task_pool:
        """
        self.repo = repo
        self.task_pool = task_pool
        self._local_abspath = None

    @property
    def local_abspath(self):
        return self._local_abspath

    def handle(self):
        raise NotImplementedError('Subclass should override this stub.')
