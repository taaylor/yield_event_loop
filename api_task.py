from typing import Generator

from my_asyncio import SystemCall


class NewTask(SystemCall):
    """Позволяет создать новую задачу"""

    def __init__(self, target: Generator):
        self.target = target

    def handle(self, sched, task):
        tid = sched.add_task(self.target)
        task.sendval = tid
        sched.schedule(task)


class KillTask(SystemCall):
    """Позволяет удалить задачу"""

    def __init__(self, task):
        self.tid = task.task_id

    def handle(self, sched, task):
        if self.tid in sched.task_map:
            sched.exit(sched.task_map[self.tid])
        sched.schedule(task)
