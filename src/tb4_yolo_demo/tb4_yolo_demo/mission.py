import math
from pathlib import Path
import signal
import time
from datetime import datetime, timezone

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from irobot_create_msgs.action import Undock
from irobot_create_msgs.msg import DockStatus
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from nav_msgs.msg import OccupancyGrid, Path as NavPath
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener, TransformException

from .common import atomic_json, load_goals
from .map_tools import SavedMap


class Mission(Node):
    def __init__(self):
        super().__init__('mission')
        defaults = {'use_sim_time': True, 'localization_confirmed': False,
                    'goals_file': '', 'map_file': '', 'results_dir': 'evidence/runtime',
                    'readiness_timeout': 90., 'goal_timeout': 180., 'action_timeout': 15.,
                    'sensor_max_age': 2., 'amcl_max_age': 60., 'max_xy_variance': .5,
                    'max_yaw_variance': .3, 'clearance': .4, 'max_goals': 0}
        for key, value in defaults.items():
            if not self.has_parameter(key):
                self.declare_parameter(key, value)
        self.nomotion = self.create_client(Empty, '/request_nomotion_update')
        self.last_nomotion = 0.
        self.stop = False
        self.active = None
        self.amcl = self.scan = self.grid = self.dock = None
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', lambda m: setattr(self, 'amcl', m), QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(LaserScan, '/scan', lambda m: setattr(self, 'scan', m), qos_profile_sensor_data)
        self.create_subscription(DockStatus, '/dock_status', lambda m: setattr(self, 'dock', m), qos_profile_sensor_data)
        self.create_subscription(OccupancyGrid, '/map', lambda m: setattr(self, 'grid', m),
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE))
        self.nav = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.plan = ActionClient(self, ComputePathToPose, '/compute_path_to_pose')
        self.undock = ActionClient(self, Undock, '/undock')
        self.path_pub = self.create_publisher(NavPath, '/mission/planned_path',
                                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.lifecycle = {name: self.create_client(GetState, f'/{name}/get_state')
                          for name in ('map_server', 'amcl', 'planner_server', 'controller_server', 'bt_navigator')}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        self.output = Path(self.p('results_dir')).expanduser() / f'mission_{stamp}.json'
        self.report = {'started_utc': stamp, 'state': 'created', 'goals': [], 'undock': None,
                       'parameters': {key: self.p(key) for key in defaults}}
        self.save()

    def p(self, name):
        return self.get_parameter(name).value

    def save(self):
        atomic_json(self.output, self.report)

    def spin_for(self, seconds):
        end = time.monotonic()+seconds
        while time.monotonic() < end and rclpy.ok() and not self.stop:
            rclpy.spin_once(self, timeout_sec=min(.1, max(0., end-time.monotonic())))

    def wait(self, future, timeout, allow_stop=True):
        end = time.monotonic()+timeout
        while not future.done() and rclpy.ok() and time.monotonic() < end:
            if allow_stop and self.stop:
                raise InterruptedError('Mission interrupted')
            rclpy.spin_once(self, timeout_sec=.1)
        if not future.done():
            raise TimeoutError('ROS response timed out')
        return future.result()

    def age(self, stamp):
        return self.get_clock().now().nanoseconds*1e-9-stamp.sec-stamp.nanosec*1e-9

    def live_localization(self):
        if self.get_clock().now().nanoseconds <= 0:
            raise RuntimeError('Waiting for /clock')
        if self.grid is None or self.grid.header.frame_id != 'map':
            raise RuntimeError('Waiting for map')
        for label, msg, limit in [('scan', self.scan, self.p('sensor_max_age')),
                                   ('AMCL', self.amcl, self.p('amcl_max_age'))]:
            if msg is None or not 0 <= self.age(msg.header.stamp) <= limit:
                raise RuntimeError(f'{label} missing or stale')
        if self.amcl.header.frame_id != 'map':
            raise RuntimeError('AMCL frame must be map')
        covariance = self.amcl.pose.covariance
        if max(covariance[0], covariance[7]) > self.p('max_xy_variance') or covariance[35] > self.p('max_yaw_variance'):
            raise RuntimeError('AMCL uncertainty exceeds configured limits')
        for parent, child in [('map','odom'), ('odom','base_link'), ('map',self.scan.header.frame_id)]:
            tf = self.tf.lookup_transform(parent, child, Time())
            if not -self.p('sensor_max_age') <= self.age(tf.header.stamp) <= self.p('sensor_max_age'):
                raise RuntimeError(f'Stale TF: {parent} -> {child}')

    def ready(self):
        if not self.p('use_sim_time'):
            raise RuntimeError('Simulation mission requires use_sim_time=true')
        if not self.p('localization_confirmed'):
            raise RuntimeError('Inspect localization, then explicitly set localization_confirmed:=true')
        end = time.monotonic()+self.p('readiness_timeout')
        last = ''
        while time.monotonic() < end and not self.stop:
            try:
                self.spin_for(.2)
                if (self.amcl is None or self.age(self.amcl.header.stamp) > self.p('amcl_max_age')) and time.monotonic()-self.last_nomotion > 2.:
                    if self.nomotion.service_is_ready():
                        self.wait(self.nomotion.call_async(Empty.Request()), 2.)
                        self.last_nomotion = time.monotonic()
                self.live_localization()
                if self.dock is None or not 0 <= self.age(self.dock.header.stamp) <= self.p('sensor_max_age'):
                    raise RuntimeError('Waiting for fresh /dock_status')
                for name, client in self.lifecycle.items():
                    if not client.service_is_ready():
                        raise RuntimeError(f'Waiting for {name}/get_state')
                    state = self.wait(client.call_async(GetState.Request()), 2.)
                    if state.current_state.id != 3:
                        raise RuntimeError(f'{name} is not active')
                if not self.nav.server_is_ready() or not self.plan.server_is_ready():
                    raise RuntimeError('Nav2 action servers unavailable')
                return
            except (RuntimeError, TimeoutError, TransformException) as exc:
                if str(exc) != last:
                    self.get_logger().info(str(exc)); last = str(exc)
                self.spin_for(.5)
        if self.stop:
            raise InterruptedError('Stopped before readiness')
        raise TimeoutError(f'Readiness timeout: {last}')

    def cancel_active(self):
        if self.active is None:
            return
        try:
            response = self.wait(self.active.cancel_goal_async(), 5., allow_stop=False)
            self.report['cancel_requested'] = True
            self.report['cancel_response_code'] = response.return_code
            result = self.wait(self.active.get_result_async(), 10., allow_stop=False)
            self.report['cancel_terminal_status'] = result.status
            if self.report['goals'] and self.report['goals'][-1]['state'] == 'navigating':
                record = self.report['goals'][-1]
                record['action_status'] = result.status
                record['state'] = {4: 'succeeded', 5: 'canceled', 6: 'aborted'}.get(result.status, 'unknown')
        except Exception as exc:
            self.report['cancel_error'] = str(exc)
            self.get_logger().error(f'Cancellation not confirmed: {exc}')
        finally:
            self.active = None
            self.save()

    def action(self, client, goal, timeout, feedback=None, monitor=False):
        if not client.wait_for_server(timeout_sec=self.p('action_timeout')):
            raise TimeoutError(f'{client._action_name}: action server unavailable')
        send = client.send_goal_async(goal, feedback_callback=feedback)
        try:
            handle = self.wait(send, self.p('action_timeout'))
        except (TimeoutError, InterruptedError):
            # Resolve an in-flight acceptance before leaving to avoid an orphan goal.
            handle = self.wait(send, self.p('action_timeout'), allow_stop=False)
            if handle.accepted:
                self.active = handle
                self.cancel_active()
            raise
        if not handle.accepted:
            raise RuntimeError(f'{client._action_name}: goal rejected')
        self.active = handle
        result = handle.get_result_async()
        end = time.monotonic()+timeout
        try:
            while not result.done():
                if self.stop:
                    raise InterruptedError('Mission canceled by operator')
                if time.monotonic() >= end:
                    raise TimeoutError(f'{client._action_name}: execution timeout')
                rclpy.spin_once(self, timeout_sec=.1)
                if monitor:
                    self.live_localization()
            response = result.result()
            self.active = None
            return response
        except BaseException:
            self.cancel_active()
            raise

    def pose(self, goal):
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x, pose.pose.position.y = goal['x'], goal['y']
        pose.pose.orientation.z = math.sin(goal['yaw']/2)
        pose.pose.orientation.w = math.cos(goal['yaw']/2)
        return pose

    def feedback(self, message):
        if time.monotonic()-self.last_feedback >= 5.:
            fb = message.feedback
            self.get_logger().info(f'Remaining={fb.distance_remaining:.2f} m; recoveries={fb.number_of_recoveries}')
            self.last_feedback = time.monotonic()

    def run(self):
        try:
            goals = load_goals(self.p('goals_file'))
            self.report['configured_goals'] = goals
            saved = SavedMap(self.p('map_file'))
            for goal in goals:
                saved.check(goal['x'],goal['y'],self.p('clearance'))
            self.report['state'] = 'waiting_ready'; self.save()
            self.ready()
            if self.dock.is_docked:
                self.report['state'] = 'undocking'; self.save()
                result = self.action(self.undock, Undock.Goal(), 45.)
                self.report['undock'] = {'status': result.status, 'is_docked': result.result.is_docked}
                self.save()
                if result.status != GoalStatus.STATUS_SUCCEEDED or result.result.is_docked:
                    raise RuntimeError('Undock did not succeed')
                self.spin_for(.5)
                if self.dock.is_docked:
                    raise RuntimeError('/dock_status still reports docked after undock')
            limit = self.p('max_goals')
            selected = goals[:limit] if limit > 0 else goals
            for goal in selected:
                record = {'goal': goal, 'state': 'planning', 'started_utc': datetime.now(timezone.utc).isoformat()}
                self.report['goals'].append(record)
                self.report['state'] = 'running'; self.save()
                self.live_localization()
                pose = self.pose(goal)
                request = ComputePathToPose.Goal(); request.goal = pose; request.use_start = False
                plan = self.action(self.plan, request, 20.)
                record['planner_status'] = plan.status
                if plan.status != GoalStatus.STATUS_SUCCEEDED or len(plan.result.path.poses) < 1:
                    raise RuntimeError(f"No live Nav2 path to {goal['name']}")
                self.path_pub.publish(plan.result.path)
                record['path'] = [[p.pose.position.x,p.pose.position.y] for p in plan.result.path.poses]
                nav_goal = NavigateToPose.Goal(); nav_goal.pose = self.pose(goal)
                record['state'] = 'navigating'; self.save()
                self.get_logger().info(f"Sending {goal['name']} ({goal['x']:.2f}, {goal['y']:.2f}, {goal['yaw']:.2f})")
                self.last_feedback = 0.
                start = time.monotonic()
                result = self.action(self.nav, nav_goal, self.p('goal_timeout'), self.feedback, monitor=True)
                record['wall_seconds'] = time.monotonic()-start
                record['action_status'] = result.status
                record['state'] = {4:'succeeded',5:'canceled',6:'aborted'}.get(result.status, 'unknown')
                tf = self.tf.lookup_transform('map','base_link',Time())
                record['final_position'] = [tf.transform.translation.x, tf.transform.translation.y]
                self.save()
                self.get_logger().info(f"{goal['name']}: {record['state']} (action status={result.status})")
                if result.status != GoalStatus.STATUS_SUCCEEDED:
                    raise RuntimeError(f"{goal['name']} ended with status {result.status}; stopping sequence")
            self.report['state'] = 'succeeded'
            self.report['completed_goals'] = len(selected)
            return 0
        except (Exception, KeyboardInterrupt) as exc:
            self.cancel_active()
            self.report['state'] = 'canceled' if self.stop or isinstance(exc, (KeyboardInterrupt,InterruptedError)) else 'failed'
            self.report['error'] = str(exc)
            if self.report['goals'] and self.report['goals'][-1]['state'] in ('planning','navigating'):
                self.report['goals'][-1]['state'] = self.report['state']
            self.get_logger().error(str(exc))
            return 1
        finally:
            self.report['finished_utc'] = datetime.now(timezone.utc).isoformat()
            self.save()
            self.get_logger().info(f'Mission result: {self.output}')


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = Mission()
    previous = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, lambda *_: setattr(node, 'stop', True))
    try:
        code = node.run()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(code)
