"""This is a dummy ClearML task. This should be replaced by your own experiment code."""
import pprint
import random
import time

from clearml import Task
from tqdm import tqdm


import datetime
import tempfile

def add_timestamp_to_file(file_path  ):
  """
  Reads the content of a text file, adds a new line with the current timestamp,
  and saves the result to a temporary file.

  Args:
    file_path: The path to the input text file.

  Returns:
    The path to the temporary file.
  """

  try:
    if file_path is not None: 
        with open(file_path, 'r') as f:
          content = f.read()
    else:
        content = "starting"
        

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_content = f"{content}\n{current_time}"

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
      temp_file.write(new_content)

    task.upload_artifact('wights_file',temp_file)

    return temp_file.name

  except FileNotFoundError:
    print(f"Error: File '{file_path}' not found.")
    return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return
 



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
print ("user_properties:")
pprint.pprint(user_properties)

if len (user_properties ) == 0:
    task.set_user_properties({"name": "next_scalar", "description": "network type", "value": 0 },{"name": "execution_semaphore", "description": "execution_semaphore", "value": "Starting"})

if "next_scalar" in user_properties:

    i = int ( user_properties["next_scalar"]["value"])
else :
    i = 0


wights_file = None

class Load_model:
    if "wights_file" in task.artifacts:
        wights_file = task.artifacts['wights_file'].get_local_copy()
    else:
        wights_file = None

Load_model ()

for i in (range(i , 10000)):
    task.get_logger().report_scalar(
        title="Performance Metric",
        series="Series 1",
        iteration=i,
        value=random.randint(0, 100)
    )
    print (f"iteration:{i}")
    time.sleep(1)
    user_properties = task.get_user_properties()

    if  user_properties["next_scalar"]["value"] == "switching_task":
        add_timestamp_to_file (wights_file)
        task.set_user_properties({"name": "next_scalar", "description": "network type", "value": i},
                                 {"name": "execution_semaphore", "description": "execution_semaphore",
                                  "value": "switching_task_preparation_done"})
        break

