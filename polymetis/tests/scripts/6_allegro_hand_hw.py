# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import time

import torch

from polymetis import RobotInterface


if __name__ == "__main__":
    # Initialize robot interface
    robot = RobotInterface(
        ip_address="localhost",
    )

    # Get metadata
    num_dofs = robot.metadata.robot_model_cfg.num_dofs

    # Get joint positions
    joint_pos = robot.get_joint_positions()
    assert len(joint_pos) == num_dofs

    # Go home
    robot.go_home()
    time.sleep(0.5)

    # Move to joint positions
    robot.move_to_joint_positions(0.01 * torch.randn(num_dofs))
