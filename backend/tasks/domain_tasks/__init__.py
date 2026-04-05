# Domain task vault package
from .dsa import DSA_TASKS
from .frontend_tasks import FRONTEND_TASKS
from .backend_tasks import BACKEND_TASKS
from .sql_tasks import SQL_TASKS
from .debugging_tasks import DEBUGGING_TASKS

ALL_DOMAIN_TASKS = {
    "dsa": DSA_TASKS,
    "frontend": FRONTEND_TASKS,
    "backend": BACKEND_TASKS,
    "sql": SQL_TASKS,
    "debugging": DEBUGGING_TASKS,
}
