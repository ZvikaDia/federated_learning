"""
Create a ClearML Monitoring Service that posts alerts on Slack Channel groups based on some logic

Creating a new Slack Bot (ClearML Bot):
1. Login to your Slack account
2. Go to https://api.slack.com/apps/new
3. Give the new App a name (For example "ClearML Bot") and select your workspace
4. Press Create App
5. In "Basic Information" under "Display Information" fill in the following fields
    - In "Short description" insert "ClearML Bot"
    - In "Background color" insert #202432
6. Press Save Changes
7. In "OAuth & Permissions" under "Scopes" click on "Add an OAuth Scope" and
   select from the dropdown list the following three permissions:
        channels:join
        channels:read
        chat:write
8. Now under "OAuth Tokens & Redirect URLs" press on "Install App to Workspace",
   then hit "Allow" on the confirmation dialog
9. Under "OAuth Tokens & Redirect URLs" copy the "Bot User OAuth Access Token" by clicking on "Copy" button
10. To use the copied API Token in the ClearML Slack service,
    execute the script with --slack_api "<api_token_here>"  (notice the use of double quotes around the token)

We are done!
"""

import argparse
import os
import pprint
from pathlib import Path
from time import sleep
from typing import Optional, Callable, List, Union

from clearml import Task
from clearml.automation.monitor import Monitor
from datetime import datetime
from time import time, sleep
from typing import Optional, Sequence


class UserFilter:
    def __init__(self, include=None, exclude=None):
        # type: (Optional[Union[str, List[str]]], Optional[Union[str, List[str]]]) -> ()
        # Either `include` or `exclude` should be specified, but not both
        if include is not None and exclude is not None:
            raise ValueError("Specify either 'include' or 'exclude', not both!")
        include = include or list()
        if isinstance(include, str):
            include = [include]
        exclude = exclude or list()
        if isinstance(exclude, str):
            exclude = [exclude]
        res = Task._get_default_session().send_request("users", "get_all")
        if not res.ok:
            raise RuntimeError("Cannot get list of all users!")
        all_users = {d["name"]: d["id"] for d in res.json()["data"]["users"]}
        for user in include + exclude:
            if user not in all_users:
                print(f"Cannot translate user '{user}' to any known user ID - "
                      f"will use it verbatim")
        self.include = [all_users.get(user, user) for user in include]  # Map usernames to user IDs
        self.exclude = [all_users.get(user, user) for user in exclude]

    def __call__(self, task):
        # type: (Task) -> bool
        if self.include:
            return task.data.user not in self.include
        return task.data.user in self.exclude


class FederatedMonitor(Monitor):
    """
    Create a monitoring service that alerts on Task failures / completion in a Slack channel
    """

    def __init__(self):
        # type: (str, str, Optional[str], Optional[List[Callable[[Task], bool]]]) -> ()
        """
        Create a Slack Monitoring object.
        It will alert on any Task/Experiment that failed or completed

        :param slack_api_token: Slack bot API Token. Token should start with "xoxb-"
        :param channel: Name of the channel to post alerts to
        :param message_prefix: optional message prefix to add before any message posted
            For example: message_prefix="Hey <!here>,"
        :param filters: An optional collection of callables that will be passed a Task
            object and return True/False if it should be filtered away
        """
        super(FederatedMonitor, self).__init__()

        self.switch_next_iteration = 20
        self.next_queue = "test_federated"

    def get_query_parameters(self):
        # type: () -> dict
        """
        Return the query parameters for the monitoring.

        :return dict: Example dictionary: {'status': ['failed'], 'order_by': ['-last_update']}
        """
        filter_tags = list() if self.include_archived else ["-archived"]
        if not self.include_manual_experiments:
            filter_tags.append("-development")
        return dict(order_by=["-last_update"], system_tags=filter_tags)

    def monitor_step(self):
        # type: () -> ()
        """
        Implement the main query / interface of the monitor class.
        In order to combine multiple Monitor objects, call `monitor_step` manually.
        If Tasks are detected in this call,

        :return: None
        """
        previous_timestamp = self._previous_timestamp or time()
        timestamp = time()
        try:
            # retrieve experiments orders by last update time
            task_filter = {
                'page_size': 100,
                'page': 0,
                'project': self._get_projects_ids(),
            }
            task_filter.update(self.get_query_parameters())

            queried_tasks = Task.get_tasks(task_name=self._task_name_filter, task_filter=task_filter)
        except Exception as ex:
            # do not update the previous timestamp
            print('Exception querying Tasks: {}'.format(ex))
            return

        # process queried tasks
        for task in queried_tasks:
            try:
                self.process_task(task)
            except Exception as ex:
                print('Exception processing Task ID={}:\n{}'.format(task.id, ex))

        self._previous_timestamp = timestamp

    def process_task(self, task):
        """
        # type: (Task) -> ()
        Called on every Task that we monitor.
        This is where we send the Slack alert

        :return: None
        """
        # skipping failed tasks with low number of iterations

        if task.get_last_iteration() > self.switch_next_iteration:
            #self.switch_next_iteration = task.get_last_iteration() + 20

            user_properties = task.get_user_properties()
            print("user_properties:")
            pprint.pprint(user_properties)

            if user_properties["execution_semaphore"]["value"] == "switching_task_preparation_done":

                if self.next_queue == "test_federated":
                    self.next_queue = "test_federated_2"
                else:
                    self.next_queue = "test_federated"

                user_properties["execution_semaphore"]["value"] == f"requeue to {self.next_queue}"

                task.set_user_properties (user_properties )
                #     print(
                #         "Skipping {} experiment id={}, number of iterations {} < {}".format(
                #             task.status, task.id, task.get_last_iteration(), self.min_num_iterations
                #         )
                #     )
                #     return
                # if any(f(task) for f in self.filters):
                #     if self.verbose:
                #         print("Experiment id={} {} did not pass all filters".format(task.id, task.status))
                #     return
                #
                # print('Experiment id={} {}, raising alert on channel "{}"'.format(task.id, task.status, self.channel))

                console_output = task.get_reported_console_output(number_of_reports=3)
                print(console_output)

                task.mark_stopped(force=True , status_message="Switch queue to:{} ".format(self.next_queue))

                task.set_initial_iteration (task.get_last_iteration() + 1 )

                Task.enqueue(task.id, queue_name=self.next_queue)
            else:
                user_properties["execution_semaphore"]["value"] == f"switching_task"

                task.set_user_properties (user_properties )

        # message = "{}Experiment ID <{}|{}> *{}*\nProject: *{}*  -  Name: *{}*\n" "```\n{}\n```".format(
        #     self._message_prefix,
        #     task.get_output_log_web_page(),
        #     task.id,
        #     task.status,
        #     task.get_project_name(),
        #     task.name,
        #     ("\n".join(console_output))[-2048:],
        # )


def main():
    print("ClearML experiment monitor Slack service\n")

    # Slack Monitor arguments

    # create the slack monitoring object
    federated_monitor = FederatedMonitor()

    # configure the monitoring filters
    federated_monitor.min_num_iterations = 1
    federated_monitor.include_manual_experiments = False
    federated_monitor.include_archived = False
    federated_monitor.verbose = True

    federated_monitor.set_projects(project_names_re=["test federated"])

    # federated_monitor.status_alerts += ["completed"]

    # start the monitoring Task
    # Connecting ClearML with the current process,
    # from here on everything is logged automatically
    task = Task.init(project_name='DevOps', task_name='Slack Alerts', task_type=Task.TaskTypes.monitor)
    # if not args.local:
    #    task.execute_remotely(queue_name=args.service_queue)
    # we will not get here if we are running locally

    # Start the monitor service, this function will never end
    federated_monitor.monitor(pool_period=10)


if __name__ == "__main__":
    main()
