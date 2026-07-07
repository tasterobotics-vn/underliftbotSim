import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient
from rclpy.action.client import ClientGoalHandle, GoalStatus
from rclpy.action.server import ServerGoalHandle, GoalResponse, CancelResponse
from nav2_msgs.action import DockRobot, UndockRobot
from custom_message.action import MoveThings
from std_msgs.msg import Float64MultiArray
from geometry_msgs.msg import Polygon, Point32
from tf2_ros import TransformException, TransformStamped
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.time import Time
from rclpy.duration import Duration
import yaml
import time
import threading
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

class CurrentTask:
    def __init__(self):
        self.currentTaskBegin = None
        self.currentTaskDestination = None
        self.currentTask = None
        self.currentAction = None
        self.currentTaskStatus = False

    def resetCurrentTask(self):
        self.currentTaskBegin = ""
        self.currentTaskDestination = ""
        self.currentTask = ""
        self.currentAction = ""
        self.currentTaskStatus = False


class LiftingExecution(Node):
    def __init__(self):
        super().__init__("lifting_executor")
        self.callbackGroup1_ = MutuallyExclusiveCallbackGroup()
        self.callbackGroup2_ = MutuallyExclusiveCallbackGroup()

        self.dockGoalHandle_ = None
        self.undockGoalHandle_ = None
        self.moveThingsGoalHandle_: ServerGoalHandle = None

        self.dockActionClient_ = ActionClient(self, DockRobot, "dock_robot", callback_group=self.callbackGroup1_)
        self.unDockActionClient_ = ActionClient(self, UndockRobot, "undock_robot", callback_group=self.callbackGroup1_)

        self.moveThingsActionServer_ = ActionServer(self, MoveThings, "move_things", 
                                                    goal_callback=self.moveThingsGoalCallback,
                                                    cancel_callback=self.moveThingCancelCallback,
                                                    execute_callback=self.moveThingsExecuteCallback,
                                                    callback_group=self.callbackGroup2_)
        
        self.liftCmdPositionPub_ = self.create_publisher(Float64MultiArray, "cmd_lift_pose", 1)
        self.robotGlobalFootprintPub_ = self.create_publisher(Polygon, "/global_costmap/footprint", 1)
        self.robotLocalFootprintPub_ = self.create_publisher(Polygon, "/local_costmap/footprint", 1)

        self.tfBuffer = Buffer()
        self.baseLiftTfListener = TransformListener(self.tfBuffer, self)
        
        self.destinations = self.loadDockNames()
        self.currentTask_ = CurrentTask()
        self.goalLock_ = threading.Lock()

        self.liftUpPositionValue = 0.15
        self.liftDownPositionValue = 0.05
        self.liftThreshold = 0.035

        self.nonLiftingFootprint = Polygon()
        self.nonLiftingFootprint.points = [
            Point32(x=0.3395,  y=0.275,  z=0.0),
            Point32(x=0.3395,  y=-0.275, z=0.0),
            Point32(x=-0.3395, y=-0.275, z=0.0),
            Point32(x=-0.3395, y=0.275,  z=0.0),
        ]

        self.liftingFootprint = Polygon()
        self.liftingFootprint.points = [
            Point32(x=0.3395,  y=0.8,  z=0.0),
            Point32(x=0.3395,  y=-0.8, z=0.0),
            Point32(x=-0.3395, y=-0.8, z=0.0),
            Point32(x=-0.3395, y=0.8,  z=0.0),
        ]

    def loadDockNames(self, yaml_path=None):
        if yaml_path is None:
            yaml_path = Path(get_package_share_directory("underliftbot_navigation2")) / "config" / "dock_database.yaml"

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        docks_section = data.get("docks", {})  
        dock_names = list(docks_section.keys()) 
        return dock_names
    
    def moveLift(self, position):
        liftPositionMsg = Float64MultiArray()
        # Publish message to move lift up
        if position == True:
            liftPositionMsg.data = [self.liftUpPositionValue]
            self.liftCmdPositionPub_.publish(liftPositionMsg)
        else:
        # Publish message to move lift down
            liftPositionMsg.data = [self.liftDownPositionValue]
            self.liftCmdPositionPub_.publish(liftPositionMsg)

    def liftAndWaiting(self, position, timeout = -1):
        self.moveLift(position=position)

        start_time = self.get_clock().now()
        deadline = None
        t = None
        if timeout >= 0:
            deadline = start_time + Duration(seconds=timeout)

        while rclpy.ok():
            if deadline is not None and self.get_clock().now() >= deadline:
                self.get_logger().warn(f"liftAndWaiting timed out after {timeout:.2f} seconds")
                return False
            try:
                t = self.tfBuffer.lookup_transform("base_link", "lift_link", Time())
            except TransformException as ex:
                self.get_logger().warn("Could not transform between lift_link and base_link")
                time.sleep(0.5)
                continue
            
            z = t.transform.translation.z

            if (abs(z - self.liftDownPositionValue) <= self.liftThreshold) and (position == False):
                self.robotGlobalFootprintPub_.publish(self.nonLiftingFootprint)
                self.robotLocalFootprintPub_.publish(self.nonLiftingFootprint)
                return True
            
            if (abs(z - self.liftUpPositionValue) <= self.liftThreshold) and (position == True):
                self.robotGlobalFootprintPub_.publish(self.liftingFootprint)
                self.robotLocalFootprintPub_.publish(self.liftingFootprint)
                return True

            time.sleep(0.5)

    def sendDockGoal(self, dockId):
        self.dockActionClient_.wait_for_server()
        goal = DockRobot.Goal()
        goal.use_dock_id = True
        goal.dock_id = dockId
        self.get_logger().info("Sending dock goal....")
        self.dockActionClient_.send_goal_async(goal=goal).add_done_callback(self.dockGoalResponseCallback)

    def dockGoalResponseCallback(self, future):
        self.dockGoalHandle_: ClientGoalHandle = future.result()
        if self.dockGoalHandle_.accepted:
            self.get_logger().info("Dock robot action accepted ")
            self.dockGoalHandle_.get_result_async().add_done_callback(self.dockResultCallback)
            self.currentTask_.currentAction = "Dock"
        else:
            self.get_logger().info("Dock robot action rejected")
            self.currentTask_.currentTask = ""

    def dockResultCallback(self, future):
        status = future.result().status
        result = future.result().result
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("Successfully dock robot")
            position = False
            if self.currentTask_.currentTask == self.currentTask_.currentTaskBegin:
                # Lift up
                position=True
            elif self.currentTask_.currentTask == self.currentTask_.currentTaskDestination:
                # Lift down
                position=False

            if (self.liftAndWaiting(position=position, timeout=-1) == False):
                self.currentTask_.currentTask = ""
            else: 
                self.sendUndockGoal(dockType="simple_charging_dock")

        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error("Aborted dock robot")
            self.currentTask_.currentTask = ""

        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn("Canceled dock robot")
            self.currentTask_.currentTask = ""

        self.get_logger().info(f"Status: {result.success}")
        self.get_logger().info(f"Error code: {result.error_code}")

    def dockFeedbackCallback(self, feedbackMsg):
        feedback = feedbackMsg.feedback.state
        self.get_logger().info(f"Dock feedback state: {feedback}")

    def cancelDockGoal(self):
        if self.dockGoalHandle_ is not None:
            self.get_logger().info("Send cancel request to dock action")
            self.dockGoalHandle_.cancel_goal_async()

    def sendUndockGoal(self, dockType):
        self.unDockActionClient_.wait_for_server()

        goal = UndockRobot.Goal()
        goal.dock_type = dockType
        
        self.get_logger().info("Sending undock goal...")
        self.unDockActionClient_.send_goal_async(goal=goal).add_done_callback(self.undockGoalResponseCallback)

    def undockGoalResponseCallback(self, future):
        self.undockGoalHandle_: ClientGoalHandle = future.result()
        if self.undockGoalHandle_.accepted:
            self.get_logger().info("Undock robot action accepted ")
            self.undockGoalHandle_.get_result_async().add_done_callback(self.undockResultCallback)
            self.currentTask_.currentAction = "UnDock"
        else:
            self.get_logger().info("Undock robot action rejected")
            self.currentTask_.currentTask = ""

    def undockResultCallback(self, future):
        status = future.result().status
        result = future.result().result
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("Successfully undock robot")
            if self.currentTask_.currentTask == self.currentTask_.currentTaskBegin:
                self.currentTask_.currentTask = self.currentTask_.currentTaskDestination
                self.sendDockGoal(dockId=self.currentTask_.currentTaskDestination)
            elif self.currentTask_.currentTask == self.currentTask_.currentTaskDestination:
                self.currentTask_.currentTaskStatus = True
            else:
                self.get_logger().error("Unexpected behavior !!!")
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error("Aborted undock robot")
            self.currentTask_.currentTask = ""
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn("Canceled undock robot")
            self.currentTask_.currentTask = ""

        self.get_logger().info(f"Status: {result.success}")
        self.get_logger().info(f"Error code: {result.error_code}")

    def cancelUndockGoal(self):
        if self.undockGoalHandle_ is not None:
            self.get_logger().info("Send cancel request to undock action")
            self.undockGoalHandle_.cancel_goal_async()

    def moveThingsGoalCallback(self, goal_handle: MoveThings.Goal):
        self.get_logger().info("Received a new goal")

        if (goal_handle.begin not in self.destinations) or (goal_handle.destination not in self.destinations):
            self.get_logger().warn("Invalid goal ! Pls check begin or destination is correct or not")
            return GoalResponse.REJECT
        
        if self.moveThingsGoalHandle_ is not None and self.moveThingsGoalHandle_.is_active:
            self.moveThingsGoalHandle_.abort()

        self.currentTask_.currentTaskBegin = goal_handle.begin
        self.currentTask_.currentTaskDestination = goal_handle.destination

        self.get_logger().info("Accept move things action goal")
        return GoalResponse.ACCEPT
    
    def moveThingCancelCallback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info("Received cancel request to cancel move things action")
        return CancelResponse.ACCEPT
    
    def moveThingsExecuteCallback(self, goal_handle: ServerGoalHandle):
        with self.goalLock_:
            self.moveThingsGoalHandle_ = goal_handle

        result = MoveThings.Result()
        feedback = MoveThings.Feedback()
        currentFeedbackMsg = ""

        self.get_logger().info("Executing goal ...")
        self.currentTask_.currentTask = self.currentTask_.currentTaskBegin
        self.currentTask_.currentTaskStatus = False
        self.sendDockGoal(dockId=self.currentTask_.currentTask)
        while rclpy.ok():
            feedbackMsg = ""
            if not goal_handle.is_active:
                result.result = MoveThings.Result.FAILED
                self.currentTask_.resetCurrentTask()
                self.liftAndWaiting(position=False, timeout=-1)
                return result
            
            if goal_handle.is_cancel_requested:
                result.result = MoveThings.Result.CANCELED
                if self.currentTask_.currentTaskStatus == True:
                    result.result = MoveThings.Result.SUCCEEDDED
                    self.get_logger().info("Received cancel request but sub goals already succeeded")
                    goal_handle.succeed()
                else:
                    result.result = MoveThings.Result.CANCELED
                    self.get_logger().info("Received cancel request, canceling move things goal")
                    if self.currentTask_.currentAction == "Dock":
                        self.cancelDockGoal()
                    elif self.currentTask_.currentAction == "UnDock":
                        self.cancelUndockGoal()
                    self.liftAndWaiting(position=False, timeout=-1)
                    goal_handle.canceled()

                self.currentTask_.resetCurrentTask()
                return result
            
            if self.currentTask_.currentTaskStatus == True:
                result.result = MoveThings.Result.SUCCEEDDED
                self.get_logger().info("Move things goal succeeded")
                goal_handle.succeed()
                self.currentTask_.resetCurrentTask()
                return result
            
            if self.currentTask_.currentTask == "":
                result.result = MoveThings.Result.FAILED
                self.get_logger().info("Aborted goal due to fail to execute sub goals")
                goal_handle.abort()
                self.liftAndWaiting(position=False, timeout=-1)
                self.currentTask_.resetCurrentTask()
                return result
            
            #self.get_logger().info("")
            if (self.currentTask_.currentAction is not None) and (self.currentTask_.currentTask != ""):
                feedbackMsg = self.currentTask_.currentAction + self.currentTask_.currentTask

            if (feedbackMsg != "") and (currentFeedbackMsg != feedbackMsg):
                feedback.current_state = feedbackMsg
                goal_handle.publish_feedback(feedback=feedback)
                currentFeedbackMsg = feedbackMsg
            
            time.sleep(1.0)


def main():
    rclpy.init()
    exector = MultiThreadedExecutor()
    liftTingExecutionNode = LiftingExecution()
    exector.add_node(liftTingExecutionNode)
    exector.spin()
    rclpy.shutdown()

if __name__ == "__main__":
    main()

