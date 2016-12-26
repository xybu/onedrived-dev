class TaskBase:

    def __init__(self, repo, task_pool):
        """
        :param onedrived.od_repo.OneDriveLocalRepository | None repo:
        :param onedrived.od_task.TaskPool task_pool:
        """
        self.repo = repo
        self.task_pool = task_pool

    @property
    def local_abspath(self):
        return self._local_abspath

    @local_abspath.setter
    def local_abspath(self, path):
        self._local_abspath = path

    def handle(self):
        raise NotImplementedError('Subclass should override this stub.')
