from . import base


class UpdateItemTaskBase(base.TaskBase):

    def __init__(self, repo, task_pool, parent_relpath, item_name, item_id=None, is_folder=False):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool task_pool:
        :param str parent_relpath:
        :param str item_name:
        :param str | None item_id:
        :param True | False is_folder:
        """
        super().__init__(repo, task_pool)
        self.parent_relpath = parent_relpath
        self.item_name = item_name
        self.rel_path = parent_relpath + '/' + item_name
        self.item_id = item_id
        self.is_folder = is_folder
        self.local_abspath = repo.local_root + self.rel_path

    def get_item_request(self):
        if self.item_id is not None:
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, id=self.item_id)
        else:
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, path=self.rel_path)

    def handle(self):
        raise NotImplementedError()
