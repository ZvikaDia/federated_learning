"""This is a dummy ClearML task. This should be replaced by your own experiment code."""
import random
import time

from clearml import Task
from tqdm import tqdm

task = Task.init(
    project_name='test federated',
    task_name='hello world',
    reuse_last_task_id=False
)

param = {'args_test_arg1': 164}
task.connect(param)

#task.execute_remotely(queue_name="test_federated")


random.seed()

user_properties = task.get_user_properties()

if "next_scalar" in user_properties:

    i = int ( user_properties["next_scalar"]["value"])
else :
    i = 0

for i in tqdm(range(i , 10000)):
    task.get_logger().report_scalar(
        title="Performance Metric",
        series="Series 1",
        iteration=i,
        value=random.randint(0, 100)
    )
    time.sleep(2)
    task.set_user_properties({"name": "next_scalar", "description": "network type", "value": i },  stable=True)
